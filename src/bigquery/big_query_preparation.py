import os
from google.cloud import bigquery
# Conflict エラーを処理するために Conflict をインポート
from google.api_core.exceptions import NotFound, Conflict 
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# ----------------------------------------------------
# ▼▼▼ ユーザー設定 ▼▼▼
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID")
TABLE_ID = os.getenv("TABLE_ID")
INDEX_NAME = f"{TABLE_ID}_embedding_index" # テーブル名から自動生成

# ----------------------------------------------------
# ▼▼▼ コスト制御フラグ ▼▼▼
# 
# True:  データを強制的にリロード（洗い替え）します。
#        sql_step1c (INSERT ... SELECT) が実行され、
#        クエリ課金が発生します。
#        公開データセットの最新情報を取り込みたい場合に True にします。
#
# False: データをリロードしません。
#        テーブルが既に存在する場合、sql_step1b, 1c をスキップします。
#        クエリ課金は発生しません。
#        （初回実行時のみデータがロードされます）
#
FORCE_RELOAD_DATA = False
#
# ▲▲▲ コスト制御フラグ ▲▲▲
# ----------------------------------------------------


# BigQueryクライアントの初期化
client = bigquery.Client(project=PROJECT_ID)

# --- データセットの確認と作成 ---
# (既存のコード ... )
dataset_full_id = f"{PROJECT_ID}.{DATASET_ID}"
dataset_ref = client.dataset(DATASET_ID)

try:
    client.get_dataset(dataset_ref)
    print(f"データセット {dataset_full_id} は既に存在します。")
except NotFound:
    print(f"データセット {dataset_full_id} が見つかりません。新規作成します...")
    dataset = bigquery.Dataset(dataset_ref)
    # 'patents-public-data' が US にあるため、ロケーションを 'US' に指定
    dataset.location = "US"
    client.create_dataset(dataset)
    print(f"データセット {dataset_full_id} をロケーション 'US' に作成しました。")

# --- テーブルの完全なID ---
table_full_id_sql = f"`{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"

# ----------------------------------------------------
# ステップ1a：テーブルのスキーマ定義 (PRIMARY KEY を含む)
# ----------------------------------------------------
print(f"ステップ1a: テーブル {table_full_id_sql} のスキーマを定義します...")

# 「CREATE TABLE IF NOT EXISTS」を使用
sql_step1a_schema = f"""
CREATE TABLE IF NOT EXISTS {table_full_id_sql}
(
  publication_number STRING NOT NULL,
  embedding_v1 ARRAY<FLOAT64>
);
"""

table_created = False
try:
    job_1a = client.query(sql_step1a_schema)
    job_1a.result()
    # テーブルが「今回新規作成された」かどうかを結果から判断
    if job_1a.ddl_operation_performed == "CREATE":
        print("ステップ1a: テーブルが新規作成されました。")
        table_created = True
    else:
        print("ステップ1a: テーブルは既に存在します。")
        
except Exception as e:
    print(f"ステップ1aでエラー: {e}")
    exit()

# ----------------------------------------------------
# ステップ1b & 1c：データのクリアと挿入 (制御フラグに基づく)
# ----------------------------------------------------

# 新規作成時 または 強制リロードが True の場合のみ実行
if table_created or FORCE_RELOAD_DATA:
    
    if table_created:
        print("（新規作成のため、データ挿入を実行します）")
    if FORCE_RELOAD_DATA:
        print(f"（FORCE_RELOAD_DATA=True のため、データを強制洗い替えします）")

    # --- ステップ1b：テーブルのデータをクリア ---
    print(f"ステップ1b: テーブル {table_full_id_sql} の既存データをクリアします...")
    sql_step1b_truncate = f"""
    TRUNCATE TABLE {table_full_id_sql};
    """
    try:
        job_1b = client.query(sql_step1b_truncate)
        job_1b.result()
        print("ステップ1b: テーブルクリア完了。")
    except Exception as e:
        print(f"ステップ1bで警告（テーブルが空の場合など）: {e}")

    # --- ステップ1c：データの挿入 (INSERT ... SELECT) ---
    print(f"ステップ1c: テーブル {table_full_id_sql} へデータを挿入します...")
    print("（この処理にはクエリ課金が発生し、時間がかかる場合があります）")

    sql_step1c_insert = f"""
    INSERT INTO {table_full_id_sql} (publication_number, embedding_v1)
    SELECT
      publication_number,
      embedding_v1
    FROM
      `patents-public-data.google_patents_research.publications`
    WHERE
      country = 'Japan'
      AND embedding_v1 IS NOT NULL
      AND ARRAY_LENGTH(embedding_v1) = 64;
    """
    try:
        job_1c = client.query(sql_step1c_insert)
        job_1c.result()
        print(f"ステップ1c: データ挿入が完了しました。 Job ID: {job_1c.job_id}")
    except Exception as e:
        print(f"ステップ1cでエラーが発生しました: {e}")
        exit()
else:
    print(f"ステップ1b & 1c: スキップしました。")
    print(f"（FORCE_RELOAD_DATA=False で、テーブルは既に存在するため）")
    print(f"（課金は発生していません）")

print("-" * 30)

# ----------------------------------------------------
# ステップ2：ベクトルインデックスの作成
# ----------------------------------------------------
# (既存のコードのまま)
print(f"ステップ2: ベクトルインデックス `{INDEX_NAME}` の作成を開始します...")
print("（注意: この処理はバックグラウンドで数十分～数時間かかります）")

sql_step2 = f"""
CREATE VECTOR INDEX IF NOT EXISTS `{INDEX_NAME}`
ON {table_full_id_sql} (embedding_v1)
OPTIONS (distance_type = 'COSINE', index_type = 'IVF');
"""

try:
    job_2 = client.query(sql_step2)
    job_2.result()
    print(f"ステップ2: インデックス作成ジョブの投入が完了しました。 Job ID: {job_2.job_id}")
    print("BigQueryコンソールでインデックス作成の完了を確認してください。")
    print("-" * 30)
except Conflict as e:
    if "Already Exists" in str(e) and "vector index on it" in str(e):
        print(f"ステップ2: インデックス `{INDEX_NAME}` は既に存在するため、作成をスキップしました。")
        print("（これはスクリプトの再実行によるもので、正常な動作です。）")
        print("-" * 30)
    else:
        print(f"ステップ2で予期しないConflictエラーが発生しました: {e}")
        raise e
except Exception as e:
    print(f"ステップ2でその他のエラーが発生しました: {e}")
    exit()

print("準備スクリプトが終了しました。")


# import os
# from google.cloud import bigquery
# from google.api_core.exceptions import NotFound
# from dotenv import load_dotenv

# # .envファイルから環境変数を読み込む
# load_dotenv()

# # ----------------------------------------------------
# # ▼▼▼ ユーザー設定 ▼▼▼
# PROJECT_ID = os.getenv("GCP_PROJECT_ID")
# DATASET_ID = os.getenv("DATASET_ID")
# TABLE_ID = os.getenv("TABLE_ID")
# INDEX_NAME = f"{TABLE_ID}_embedding_index" # テーブル名から自動生成
# # ▲▲▲ ユーザー設定 ▲▲▲
# # ----------------------------------------------------

# # BigQueryクライアントの初期化
# client = bigquery.Client(project=PROJECT_ID)

# # --- データセットの確認と作成 ---
# dataset_full_id = f"{PROJECT_ID}.{DATASET_ID}"
# dataset_ref = client.dataset(DATASET_ID)

# try:
#     client.get_dataset(dataset_ref)
#     print(f"データセット {dataset_full_id} は既に存在します。")
# except NotFound:
#     print(f"データセット {dataset_full_id} が見つかりません。新規作成します...")
#     dataset = bigquery.Dataset(dataset_ref)
#     # 'patents-public-data' が US にあるため、ロケーションを 'US' に指定
#     dataset.location = "US"
#     client.create_dataset(dataset)
#     print(f"データセット {dataset_full_id} をロケーション 'US' に作成しました。")

# # --- テーブルの完全なID ---
# table_full_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# # ----------------------------------------------------
# # ステップ1a：テーブルのスキーマ定義 (PRIMARY KEY を含む)
# # ----------------------------------------------------
# print(f"ステップ1a: テーブル `{table_full_id}` のスキーマを定義します...")

# # PRIMARY KEY(publication_number) NOT ENFORCED が重要
# # これにより VECTOR_SEARCH が publication_number をキーとして認識します
# sql_step1a_schema = f"""
# CREATE OR REPLACE TABLE `{table_full_id}`
# (
#   publication_number STRING NOT NULL,
#   embedding_v1 ARRAY<FLOAT64>,
#   PRIMARY KEY(publication_number) NOT ENFORCED
# );
# """

# try:
#     job_1a = client.query(sql_step1a_schema)
#     job_1a.result()
#     print("ステップ1a: テーブルスキーマ定義完了。")
# except Exception as e:
#     print(f"ステップ1aでエラー: {e}")
#     # 続行不可の可能性があるため終了
#     exit()

# # ----------------------------------------------------
# # ステップ1b：テーブルのデータをクリア (冪等性のため)
# # ----------------------------------------------------
# print(f"ステップ1b: テーブル `{table_full_id}` の既存データをクリアします...")
# sql_step1b_truncate = f"""
# TRUNCATE TABLE `{table_full_id}`;
# """

# try:
#     job_1b = client.query(sql_step1b_truncate)
#     job_1b.result()
#     print("ステップ1b: テーブルクリア完了。")
# except Exception as e:
#     print(f"ステップ1bでエラー（テーブルが空の場合など）: {e}")

# # ----------------------------------------------------
# # ステップ1c：データの挿入 (INSERT ... SELECT)
# # ----------------------------------------------------
# print(f"ステップ1c: テーブル `{table_full_id}` へデータを挿入します...")
# print("（この処理にはクエリ課金が発生し、時間がかかる場合があります）")

# # ARRAY_LENGTH(embedding_v1) = 64 で、長さ0のベクトルを除外 (重要)
# sql_step1c_insert = f"""
# INSERT INTO `{table_full_id}` (publication_number, embedding_v1)
# SELECT
#   publication_number,
#   embedding_v1
# FROM
#   `patents-public-data.google_patents_research.publications`
# WHERE
#   country = 'Japan'
#   AND embedding_v1 IS NOT NULL
#   AND ARRAY_LENGTH(embedding_v1) = 64;
# """

# try:
#     job_1c = client.query(sql_step1c_insert)
#     job_1c.result()  # ジョブの完了を待つ
#     print(f"ステップ1c: データ挿入が完了しました。 Job ID: {job_1c.job_id}")
#     print("-" * 30)
# except Exception as e:
#     print(f"ステップ1cでエラーが発生しました: {e}")
#     exit()

# # ----------------------------------------------------
# # ステップ2：ベクトルインデックスの作成
# # ----------------------------------------------------
# print(f"ステップ2: ベクトルインデックス `{INDEX_NAME}` の作成を開始します...")
# print("（注意: この処理はバックグラウンドで数十分～数時間かかります）")

# sql_step2 = f"""
# CREATE VECTOR INDEX IF NOT EXISTS `{INDEX_NAME}`
# ON `{table_full_id}` (embedding_v1)
# OPTIONS (distance_type = 'COSINE', index_type = 'IVF');
# """

# try:
#     job_2 = client.query(sql_step2)
#     job_2.result()  # ジョブの完了を待つ
#     print(f"ステップ2: インデックス作成ジョブの投入が完了しました。 Job ID: {job_2.job_id}")
#     print("BigQueryコンソールでインデックス作成の完了を確認してください。")
#     print("-" * 30)
# except Exception as e:
#     print(f"ステップ2でエラーが発生しました: {e}")

# print("準備スクリプトが終了しました。")


# sql_step2 = f"""
# CREATE VECTOR INDEX IF NOT EXISTS `{INDEX_NAME}`
# ON `{table_full_id}` (embedding_v1)
# OPTIONS (distance_type = 'COSINE', index_type = 'IVF');
# """

# try:
#     job_2 = client.query(sql_step2)
#     job_2.result()  # ジョブの完了を待つ
#     print(f"ステップ2: インデックス作成ジョブの投入が完了しました。 Job ID: {job_2.job_id}")
#     print("BigQueryコンソールでインデックス作成の完了を確認してください。")
#     print("-" * 30)
# except Conflict as e:
#     # "Already Exists" エラーを具体的にキャッチする
#     if "Already Exists" in str(e) and "vector index on it" in str(e):
#         print(f"ステップ2: インデックス `{INDEX_NAME}` は既に存在するため、作成をスキップしました。")
#         print("（これはスクリプトの再実行によるもので、正常な動作です。）")
#         print("-" * 30)
#     else:
#         # その他の Conflict エラーは予期しないものとして再送出
#         print(f"ステップ2で予期しないConflictエラーが発生しました: {e}")
#         raise e
# except Exception as e:
#     print(f"ステップ2でその他のエラーが発生しました: {e}")
#     exit() # インデックス作成が他の理由で失敗した場合、続行しない方が安全

# print("準備スクリプトが終了しました。")
