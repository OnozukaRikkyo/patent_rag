"""BigQueryでpatent_lookupテーブルを作成"""

from google.cloud import bigquery

PROJECT_ID = "llmatch-471107"
DATASET_ID = "dataset_lookup"
TABLE_ID = "patent_lookup"
SOURCE_DATASET = "dataset03"


def create_patent_lookup_table():
    """patent_lookupテーブルを作成"""
    client = bigquery.Client(project=PROJECT_ID, location="us-central1")

    query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    CLUSTER BY doc_number
    OPTIONS(
        description="Patent doc_number to result_X table mapping",
        labels=[("purpose", "lookup_index")]
    )
    AS
    SELECT
        _TABLE_SUFFIX AS result_table,
        publication.doc_number,
        path
    FROM `{PROJECT_ID}.{SOURCE_DATASET}.result_*`
    WHERE _TABLE_SUFFIX BETWEEN '1' AND '18'
    """

    print(f"テーブル作成中: {DATASET_ID}.{TABLE_ID}")
    query_job = client.query(query)
    query_job.result()

    table = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")
    print(f"完了: {table.num_rows:,} 件, {table.num_bytes / 1024**2:.2f} MB")


if __name__ == "__main__":
    create_patent_lookup_table()