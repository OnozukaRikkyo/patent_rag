# Cloud Run 更新手順書

- 最終更新：2025年11月23日
- URLを固定したまま、アプリケーションを更新する手順

---

## 概要

Cloud Runサービス **patent-rag-web** の公開URLを変更せず、コードのみを更新します。

**公開URL（固定）**:
```
https://patent-rag-web-453242904538.us-central1.run.app/
```

---

## 前提条件

### 必須ツール・権限
- Google Cloud SDK (gcloud CLI) インストール済み
- gcloud認証完了済み
- プロジェクトへのアクセス権限

### 必要なAPI（有効化済みであること）
- Artifact Registry API
- Cloud Build API
- Cloud Run API
- Secret Manager API

### 環境変数ファイル (.env)

プロジェクトルート（`/home/sonozuka/staging/patent_rag/.env`）に以下を設定：

```bash
# リージョン
REGION="us-central1"

# プロジェクト情報
PROJECT_ID="llmatch-471107"
PROJECT_NUMBER="453242904538"

# Artifact Registry リポジトリ名
REPO="patent-rag"

# Cloud Run サービス名
SERVICE_NAME="patent-rag-web"

# コンテナイメージ
IMAGE="us-central1-docker.pkg.dev/llmatch-471107/patent-rag/patent-rag-web:latest"

# IAM サービスアカウント
SA_EMAIL="453242904538-compute@developer.gserviceaccount.com"

# API Keys
GOOGLE_API_KEY="AIzaSyBxxxxxx"
OPENAI_API_KEY="sk-proj-xxxxx"

# BigQuery設定
GCP_PROJECT_ID="llmatch-471107"
DATASET_ID="google_dataset"
TABLE_ID="google_japan_patents"
```

---

## 更新手順（2ステップ）

### 前準備：環境変数をロード

```bash
# プロジェクトディレクトリに移動
cd /home/sonozuka/staging/patent_rag

# .envファイルから環境変数をロード
set -a
source .env
set +a

# 確認
echo "IMAGE: $IMAGE"
echo "SERVICE_NAME: $SERVICE_NAME"
```

**期待される出力**:
```
IMAGE: us-central1-docker.pkg.dev/llmatch-471107/patent-rag/patent-rag-web:latest
SERVICE_NAME: patent-rag-web
```

---

### ステップ1: コンテナイメージのビルド

```bash
gcloud builds submit \
  --tag ${IMAGE} \
  --region=${REGION} \
  --project="${PROJECT_ID}"
```

**所要時間**: 約5-10分

**成功時の出力（最終行）**:
```
SUCCESS
```

---

### ステップ2: Cloud Runにデプロイ

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE} \
  --region ${REGION} \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest \
  --set-env-vars GCP_PROJECT_ID=${GCP_PROJECT_ID},DATASET_ID=${DATASET_ID},TABLE_ID=${TABLE_ID} \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900
```

**所要時間**: 約2-3分

**成功時の出力**:
```
Service [patent-rag-web] revision [patent-rag-web-00XXX-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://patent-rag-web-453242904538.us-central1.run.app
```

> **重要**: Revisionの番号は自動的にインクリメントされます。**URLは変わりません**。

---

## デプロイの確認

### ブラウザでの動作確認

以下のURLを開き、アプリケーションが正しく動作するか確認：
```
https://patent-rag-web-453242904538.us-central1.run.app
```

### CLIでの確認

```bash
# サービス状態とURLを確認
gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url,status.conditions[0].status)'
```

**出力例**:
```
https://patent-rag-web-453242904538.us-central1.run.app	True
```

### リビジョン履歴の確認

```bash
gcloud run revisions list \
  --service=${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=3
```

### ログの確認

```bash
gcloud run services logs read ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=20
```

**正常起動時のログ例**:
```
You can now view your Streamlit app in your browser.
URL: http://0.0.0.0:8080
```

---

## クイックリファレンス（コピペ用）

環境変数なしで実行する場合：

### ビルド
```bash
cd /home/sonozuka/staging/patent_rag && \
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/llmatch-471107/patent-rag/patent-rag-web:latest \
  --region=us-central1 \
  --project="llmatch-471107"
```

### デプロイ
```bash
gcloud run deploy patent-rag-web \
  --image us-central1-docker.pkg.dev/llmatch-471107/patent-rag/patent-rag-web:latest \
  --region us-central1 \
  --project="llmatch-471107" \
  --allow-unauthenticated \
  --service-account 453242904538-compute@developer.gserviceaccount.com \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest \
  --set-env-vars GCP_PROJECT_ID=llmatch-471107,DATASET_ID=google_dataset,TABLE_ID=google_japan_patents \
  --memory=2Gi --cpu=2 --timeout=900
```

---

## ロールバック手順

デプロイ後に問題が発生した場合、以前のRevisionに戻せます。

### CLIでのロールバック

```bash
# リビジョン一覧を表示
gcloud run revisions list --service=${SERVICE_NAME} --region=${REGION}

# 特定のリビジョンにトラフィックを100%割り当て
gcloud run services update-traffic ${SERVICE_NAME} \
  --to-revisions=patent-rag-web-00XXX-xxx=100 \
  --region=${REGION}
```

### Cloud Consoleでのロールバック

1. Cloud Run → patent-rag-web → 「リビジョン」タブ
2. 前のリビジョンを選択
3. 「トラフィックの管理」→ 100%に設定

---

## 開発サイクル

1. **ローカルで開発・テスト**
   ```bash
   cd /home/sonozuka/staging/patent_rag
   uv run streamlit run src/gui.py --server.port=8080
   ```

2. **ライブラリを追加する場合**
   ```bash
   uv add パッケージ名
   uv sync
   ```

3. **ビルド & デプロイ**
   - 上記の手順に従う

4. **動作確認**
   - URLにアクセス
   - ログを確認

5. **問題があればロールバック**

---

## トラブルシューティング

### gcloud認証エラー

```bash
gcloud auth login
gcloud config set project llmatch-471107
```

### ビルドエラー

```bash
# Cloud Build APIを有効化
gcloud services enable cloudbuild.googleapis.com --project=llmatch-471107
```

### シークレットエラー

```bash
# Secret Manager APIを有効化
gcloud services enable secretmanager.googleapis.com --project=llmatch-471107

# シークレットを作成
printf "%s" "${GOOGLE_API_KEY}" | gcloud secrets create GOOGLE_API_KEY \
  --data-file=- \
  --project="${PROJECT_ID}"

# サービスアカウントに権限を付与
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --project=${PROJECT_ID} \
  --member=serviceAccount:${SA_EMAIL} \
  --role=roles/secretmanager.secretAccessor
```

---

## まとめ

### 更新手順（2ステップ）
1. **ビルド**: `gcloud builds submit` (5-10分)
2. **デプロイ**: `gcloud run deploy` (2-3分)

### 所要時間
- **合計**: 約10-15分

### ポイント
- **URLは固定**: サービス名が同じなら、URLは変わりません
- **Revisionで管理**: 各デプロイは新しいRevisionとして保存されます
- **簡単ロールバック**: 問題があれば1クリックで前のバージョンに戻せます

---

## 参考資料

- [Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [Cloud Build ドキュメント](https://cloud.google.com/build/docs)
- [Artifact Registry ドキュメント](https://cloud.google.com/artifact-registry/docs)
