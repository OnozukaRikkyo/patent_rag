# prepare.py

from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()
# ----------------------------------------------------
# ▼▼▼ ユーザー設定 ▼▼▼
PROJECT_ID = os.getenv("GCP_PROJECT_ID")  # ご自身のプロジェクトID
DATASET_ID = os.getenv("DATASET_ID")  # コピー先のデータセットID
TABLE_ID = os.getenv("TABLE_ID")       # 作成するテーブル名
INDEX_NAME = os.getenv("INDEX_NAME")   # 作成するインデックス名
# ▲▲▲ ユーザー設定 ▲▲▲
# ----------------------------------------------------

# BigQueryクライアントの初期化
# projectを指定することで、クエリ料金の支払いプロジェクトを明示します
client = bigquery.Client(project=PROJECT_ID)

# ----------------------------------------------------
# ステップ1：データのコピー
# ----------------------------------------------------
print(f"ステップ1: テーブル `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` の作成を開始します...")

sql_step1 = f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
AS
SELECT
  publication_number,
  embedding_v1
FROM
  `patents-public-data.google_patents_research.publications`
WHERE
  country = 'Japan'
  AND embedding_v1 IS NOT NULL
  AND ARRAY_LENGTH(embedding_v1) = 64; -- ← この条件を追加
"""

try:
    job1 = client.query(sql_step1)
    job1.result()  # ジョブの完了を待つ
    print(f"ステップ1: テーブル作成が完了しました。 Job ID: {job1.job_id}")
    print("-" * 30)

except Exception as e:
    print(f"ステップ1でエラーが発生しました: {e}")
    exit()

# ----------------------------------------------------
# ステップ2：ベクトルインデックスの作成
# ----------------------------------------------------
print(f"ステップ2: ベクトルインデックス `{INDEX_NAME}` の作成を開始します...")
print("（注意: この処理はバックグラウンドで数十分～数時間かかります）")

sql_step2 = f"""
CREATE VECTOR INDEX IF NOT EXISTS `{INDEX_NAME}`
ON `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` (embedding_v1)
OPTIONS (distance_type = 'COSINE', index_type = 'IVF');
"""

try:
    job2 = client.query(sql_step2)
    job2.result()  # ジョブの完了を待つ
    print(f"ステップ2: インデックス作成ジョブの投入が完了しました。 Job ID: {job2.job_id}")
    print("BigQueryコンソールでインデックス作成の完了を確認してください。")
    print("-" * 30)

except Exception as e:
    print(f"ステップ2でエラーが発生しました: {e}")

print("準備スクリプトが終了しました。")