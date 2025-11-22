# Cloud Run デプロイ手順書

- 坂田作成
- 2025年11月2日 動作確認済み

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

OPENAI_API_KEY について、SA_EMAILに、secretmanager.secretAccessorロールを付与
```bash
printf "%s" ${OPENAI_API_KEY}"" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- \
  --project="${PROJECT_ID}"

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --project=${PROJECT_ID} \
  --member=serviceAccount:${SA_EMAIL} \
  --role=roles/secretmanager.secretAccessor
```

GOOGLE_API_KYE が必要なら、同様に付与する
```bash
# gcloud secrets add-iam-policy-binding GOOGLE_API_KEY ...
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

