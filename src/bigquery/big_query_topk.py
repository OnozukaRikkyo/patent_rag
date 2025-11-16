"""
BigQuery特許検索モジュール（VECTOR_SEARCH版）

このモジュールは、VECTOR_SEARCHを使用した高速かつ低コストな
特許の類似検索を提供します。

前提条件:
- `prepare.py` が実行され、検索対象のテーブルとインデックスが
  ご自身のプロジェクトに作成されている必要があります。
- 必要な環境変数（PROJECT_ID, DATASET_ID, TABLE_ID）が
  .envファイルまたは環境に設定されている必要があります。

【重要な変更点】
- VECTOR_SEARCH は base という STRUCT を返します
- base には STORING 句の有無に関わらず、すべてのカラムが含まれます
- base.publication_number のように直接アクセス可能です
- ROWID での JOIN は不要です（そもそも ROWID は存在しません）
"""

from google.cloud import bigquery
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path
# to_dataframe() で BigQuery の型を適切に扱うために推奨
# pip install db-dtypes 

# .envファイルから環境変数を読み込む (1回だけ)
load_dotenv()

# ----------------------------------------------------
# ▼▼▼ ユーザー設定 ▼▼▼
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID")
TABLE_ID = os.getenv("TABLE_ID")
# ▲▲▲ ユーザー設定 ▲▲▲
# ----------------------------------------------------

def search_similar_patents(target_patent_number, output_csv='similar_patents_vector.csv', top_k=1000):
    """
    指定した特許番号に類似する特許を VECTOR_SEARCH で検索し、CSVファイルに保存

    Parameters:
    -----------
    target_patent_number : str
        基準とする特許番号（例: 'JP-2023123456-A'）
    output_csv : str
        出力CSVファイル名
    top_k : int
        取得する類似特許の件数（デフォルト: 1000）

    Returns:
    --------
    pd.DataFrame
        類似特許の検索結果
    """
    
    # --- 1. 設定の検証 ---
    if not all([PROJECT_ID, DATASET_ID, TABLE_ID]):
        raise ValueError(
            "環境変数 PROJECT_ID, DATASET_ID, TABLE_ID のいずれかが設定されていません。"
        )

    client = bigquery.Client(project=PROJECT_ID)
    
    # prepare.py で作成した、インデックス付きのテーブル
    search_table_full_id = f"`{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"

    print(f"VECTOR_SEARCH検索開始: {target_patent_number}")
    print(f"検索対象テーブル: {search_table_full_id}")
    print(f"取得件数: {top_k}")

    # --- 2. VECTOR_SEARCH クエリの構築 ---
    # 【正しいアプローチ】
    # VECTOR_SEARCH は base という STRUCT を返します。
    # base には、STORING 句の有無に関わらず、ベーステーブルの
    # すべてのカラムが含まれます。
    # 
    # STORING 句がない場合：
    #   BigQuery が内部的に JOIN を実行（コストがかかる）
    # STORING 句がある場合：
    #   インデックスに保存されたカラムから直接取得（高速）
    #
    # どちらの場合でも、クエリの書き方は同じです。
# --- 1. サブクエリ（改行なし） ---
    sub_query = (
        f"SELECT embedding_v1 FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` "
        f"WHERE publication_number = '{target_patent_number}' LIMIT 1"
    )

    # --- 2. VECTOR_SEARCH を実行するメインクエリ ---
    query = f"""
    SELECT
        T.base.publication_number,
        T.distance AS cosine_distance,
        1 - T.distance AS cosine_similarity
    FROM
        VECTOR_SEARCH(
            TABLE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`,
            'embedding_v1',
            ({sub_query}),
            top_k => {top_k},
            distance_type => 'COSINE'
        ) AS T
    WHERE T.base.publication_number != '{target_patent_number}'
    ORDER BY distance ASC
    """

    # query = f"""
    # -- 検索パラメータを宣言
    # DECLARE target_patent_number STRING DEFAULT '{target_patent_number}';
    # DECLARE top_k INT64 DEFAULT {top_k};

    # -- VECTOR_SEARCH を使った検索クエリ
    # SELECT
    #   base.publication_number,
    #   distance AS cosine_distance,
    #   1 - distance AS cosine_similarity
    # FROM
    #   VECTOR_SEARCH(
    #     TABLE {search_table_full_id},                           -- 検索対象テーブル (インデックス付き)
    #     'embedding_v1',                                         -- 検索対象カラム
    #     (
    #       -- ターゲット特許のベクトルを取得
    #       -- ※元データ（公開データセット）から取得
    #       SELECT embedding_v1
    #       FROM `patents-public-data.google_patents_research.publications`
    #       WHERE publication_number = target_patent_number
    #     ),
    #     top_k => {top_k},                                         -- 上位K件
    #     options => '{{ "use_brute_force": false }}'             -- インデックス使用
    #   )
    # ORDER BY distance ASC;
    # """
    
    job_config = bigquery.QueryJobConfig()

    # --- 3. クエリの実行と結果の取得 ---
    try:
        print(f"実行クエリ: {query}") # デバッグ用にクエリ内容を表示
        query_job = client.query(query, job_config=job_config)
        df = query_job.to_dataframe()
        
    except Exception as e:
        print(f"クエリ実行中にエラーが発生しました (Job ID: {query_job.job_id}): {e}")
        raise e

    print(f"検索完了: {len(df)}件の類似特許を発見")

    if df.empty:
        print("類似する特許は見つかりませんでした。")
        return pd.DataFrame()

    # --- 4. CSVファイルに保存 ---
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"CSVファイルに保存: {output_csv}")

    # --- 5. 統計情報の表示 ---
    print("\n--- 統計情報 ---")
    print(f"最大類似度: {df['cosine_similarity'].max():.4f}")
    print(f"最小類似度: {df['cosine_similarity'].min():.4f}")
    print(f"平均類似度: {df['cosine_similarity'].mean():.4f}")
    print("\n--- Top 5 類似特許 ---")
    print(df.head())

    return df


# --- 使用例 ---
if __name__ == "__main__":
    # 基準とする特許番号
    target_patent = 'JP-S4926374-B1'  # ← この値は上記のデバッグ行によって上書きされます

    # VECTOR_SEARCHを使った検索
    print("=== VECTOR_SEARCHを使った高速検索 ===")
    
    try:
        results_df = search_similar_patents(
            target_patent_number=target_patent,
            output_csv=f'similar_patents_vector_{target_patent}.csv',
            top_k=1000
        )
    except Exception as e:
        print(f"スクリプトの実行に失敗しました: {e}")