# Cloud Run デプロイ手順書

- 坂田作成
- 2025年11月2日 動作確認済み
- 2025年11月22日 デプロイ手順を更新(藤原，URLをそのままにコードを修正する方法を追記)

## 前提
- Windows WSL2 Ubuntu のターミナル上でコマンドを実行する
- Ubuntu に Google-Cloud-SDK（CLI）がインストール済である
- リージョンは、"us-central1" で統一する
- Google Could コンソール上で 各種API を有効済である
  - Artifact Registry API
  - Cloud Build API
  - Cloud Run API
  - Compute Engine API
  - Secret Manager API
  - GCコンソールの検索窓でAPI名を検索すれば確認・有効化できる。
- 環境変数を.envに記載済である

.envに環境変数を記載する。
```bash
# リージョン
REGION="us-central1"
# プロジェクト名
PROJECT_ID="llmatch-471107"

# リポジトリ名（注意: ユニークでないとエラー）
REPO="geniac"
# サービス名
SERVICE_NAME="geniac-proto-skt"
# コンテナイメージ
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/geniac-proto:uv311"

# IAM
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# OpenAI API キー
OPENAI_API_KEY="sk-xxxここをあなたのキーに置換するxxx"
```
---

## 1. 環境変数をロード

.envと同じディレクトリに移動して、環境変数をロードする。
```bash
cd /mnt/c/.envディレクトリ 
# 例: cd /mnt/c/Users/sakat/PythonCodes/GENIAC/GENIAC04
set -a
source .env
set +a
```

設定できたか確認する。
```bash
echo $PROJECT_ID
echo $PROJECT_NUMBER
echo $IMAGE　
# 結果 -> "us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/geniac-proto:uv311"
```

---

## 2. Artifact Registry を作成
us-central1 に新しくリポジトリを作成する。
```bash
gcloud artifacts repositories create ${REPO} \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --repository-format=docker \
  --description="Containers for GENIAC (${REGION})"
```
注意）リポジトリ名が既存のものと重複するとエラー。ユニークな名前にすること。 

---

## 3. IAM を設定
IAM（Identity and Access Management、アクセス管理）に関する設定。
CloudBuild から ArtifactRegistry に Push するための Writer 権限を付与する。
```bash
gcloud artifacts repositories add-iam-policy-binding ${REPO} \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/artifactregistry.writer"
```

CloudRun実行SA が ArtifactRegistry から Pull するための Reader 権限を付与する。
```bash
gcloud artifacts repositories add-iam-policy-binding ${REPO} \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.reader"
```

補足1）PERMISSION DENIED エラーが発生した場合、プロジェクトのオーナーに以下コマンドを実行してもらい、権限を付与頂く。
```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="user:sakatahiroyuki0112@gmail.com" \
  --role="roles/artifactregistry.admin"
```

補足2）権限はOKでもエラーが発生する場合、前提のAPI（Cloud Build API、Compute Engine API）が本当に有効化できているか、GSコンソール（Web）で確認する。

---

## 4. コンテナをビルド
Dockerfileやuv.lockが見えるディレクトに移動する。
Dockerコンテナイメージをビルドし、Artifact Registry にプッシュする。
```bash
gcloud builds submit \
  --tag ${IMAGE} \
  --region=${REGION} \
  --project="${PROJECT_ID}"
```
uvによるパッケージのインストールなど、Dockerfile記載の処理がされる。10分くらいかかる。
最後に "SUCCESS" と書いてあればOK。

---

## 5. シークレット（APIキー）

GOOGLE_API_KEY について、SA_EMAILに、secretmanager.secretAccessorロールを付与
```bash
printf "%s" ${GOOGLE_API_KEY}"" | gcloud secrets create GOOGLE_API_KEY \
  --data-file=- \
  --project="${PROJECT_ID}"

gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --project=${PROJECT_ID} \
  --member=serviceAccount:${SA_EMAIL} \
  --role=roles/secretmanager.secretAccessor
```

OPENAI_API_KEY が必要なら、同様に付与する
```bash
# gcloud secrets add-iam-policy-binding OPENAI_API_KEY ...
```

---

## 6. Cloud Run にデプロイ
ビルドしたコンテナを Cloud Run にデプロイする。
環境変数 `EMBEDDING_TYPE = openai`など、使用するモデルをここで指定している。
書き込みは `tmp/` 配下のみ許可されているので、永続化先を `/tmp/chroma/~~` としている。
```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE} \
  --region ${REGION} \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest \
  --set-env-vars EMBEDDING_TYPE=openai,LLM_TYPE=openai \
  --set-env-vars PERSIST_DIR=/tmp/chroma/openai_v1.0 \
  --set-env-vars KNOWLEDGE_DIR=eval/knowledge \
  --memory=1Gi --cpu=2 \
  --timeout=900
```

デプロイ完了するとURLが表示されるので、クリックしてブラウザを起動し、動作確認する。

注意）エラーの場合、前提条件のAPI（Secret Manager API）が有効化されているか確認、シークレットのAPIキー登録ができているか確認する。

---

TODO：
- tmp -> 永続化
- openai -> VertexAI
- knowledge_dir: ローカル -> GCS  





以下に、**Cloud Run の URL（[https://patent-rag-web-453242904538.us-central1.run.app/）を固定したまま、アプリの中身だけを改善していく開発サイクル**を、Markdown](https://patent-rag-web-453242904538.us-central1.run.app/）を固定したまま、アプリの中身だけを改善していく開発サイクル**を、Markdown) 形式でまとめました。

---

# Cloud Run（patent-rag-web）改善サイクル

**URL を固定したままコードを更新する運用手順**

本ドキュメントでは、Cloud Run サービス **patent-rag-web** の公開 URL を変更せず、アプリケーション（RAG・AI審査・UI など）の中身だけを継続的に更新するための開発サイクルをまとめる。

---

## 🎯 基本方針

Cloud Run では、

* サービス名 → URL を決める
* コード更新時には **新しい Revision を自動作成**
* URL は **サービス名が変わらない限り永続的に固定**

という仕組みになっている。

したがって、
**サービス名 patent-rag-web を維持したままデプロイすれば、URL は変わらず、中身だけが新しくなる**。

公開 URL：

```
https://patent-rag-web-453242904538.us-central1.run.app/
```

---

## 🔁 改善サイクル（推奨ワークフロー）

### 1. ローカルでコード修正

対象例：

* RAG（rag.py / retriever.py）
* LLM 構成（llm_pipeline.py / generator.py）
* BigQuery 検索（big_query_topk.py）
* UI（src/gui.py / page1.py）
* プロンプト調整
* モデル切り替え（embedding/LLM）

必要に応じて `pyproject.toml` や `uv.lock` が更新される。

---

### 2. Dockerfile の調整（通常は不要）

依存ライブラリが変わった場合のみ
`uv sync --python 3.13 --frozen` が uv.lock を反映するので、基本的に Dockerfile に変更は不要。

---

### 3. ビルド（Artifact Registry に新しいイメージを push）

```bash
gcloud builds submit \
  --tag ${IMAGE} \
  --region=${REGION} \
  --project=${GCP_PROJECT_ID}
```

成功すると、Artifact Registry に新しいコンテナイメージが登録される。

---

### 4. Cloud Run に再デプロイ（URL はそのまま）

既存のサービス名にそのままデプロイする：

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE} \
  --region ${REGION} \
  --project="${GCP_PROJECT_ID}" \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest \
  --set-env-vars GCP_PROJECT_ID=${GCP_PROJECT_ID} \
  --set-env-vars DATASET_ID=${DATASET_ID} \
  --set-env-vars TABLE_ID=${TABLE_ID} \
  --memory=2Gi --cpu=2 \
  --timeout=900
```

> **ポイント**
>
> * `SERVICE_NAME="patent-rag-web"` のため、URL は絶対に変わらない
> * 新しい Revision が自動作成され、トラフィック 100% が新 Revision に切り替わる

---

### 5. デプロイ後の確認

Cloud Run の画面で：

* **patent-rag-web** が “準備完了（Ready）”
* Revision が新しく増えている
* トラフィック割当が 100% になっている

ことを確認。

ブラウザで固定 URL を開き、改善された機能が反映されているかをチェックする。

---

### 6. ロールバック（必要なとき）

もし不具合があっても以前の Revision が保持されているため、Cloud Run の “Revision” タブから **1クリックで前の状態に戻す**ことができる。

---

## 📌 このサイクルで得られるメリット

* URL が変わらないため共有しやすい
* サービス稼働を止めずに更新可能
* 失敗しても即ロールバック
* uv.lock により依存関係の再現性が高い
* CI/CD に発展させやすい（Cloud Build → Cloud Run）

---

## 💡 補足：変更しないといけない可能性があるもの

| 項目                       | 変更頻度                         | 備考                               |
| ------------------------ | ---------------------------- | -------------------------------- |
| コード（Python）              | 毎回                           | 変更するとビルド→デプロイ                    |
| pyproject.toml / uv.lock | 依存追加時のみ                      | uv sync が反映                      |
| Dockerfile               | ほぼ不要                         | uv version / system libs が変わる時のみ |
| 環境変数                     | BigQuery dataset/table を変える時 | Cloud Run デプロイ時に渡す               |

---

## 📝 最終まとめ

Cloud Run の更新手順は以下の 2 コマンドに極限まで集約される：

### ① 新しいイメージをビルド

```bash
gcloud builds submit --tag ${IMAGE}
```

### ② 同じサービス名にデプロイ

```bash
gcloud run deploy patent-rag-web --image ${IMAGE}
```

この 2 ステップだけで
**URLそのまま、中身だけ最新**
という状態を永続的に保てる。

---
