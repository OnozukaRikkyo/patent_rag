import re
from pathlib import Path

import pandas as pd
import streamlit as st
from langchain_core.documents import Document

from app.retriever import Retriever
from infra.loader.common_loader import CommonLoader
from model.patent import Patent


# TODO: 検索実行はGUIではなくRetrieverやRAG側で制御すべきか考える。
def retrieve(retriever: Retriever, query: Patent) -> pd.DataFrame:
    """
    検索を実行して、検索結果を返す
    """
    query_ids: list[str] = []
    knowledge_ids: list[str] = []
    retrieved_paths: list[str] = []
    retrieved_chunks: list[str] = []

    retrieved_docs: list[Document] = retriever.retrieve(query)
    st.session_state.retrieved_docs = retrieved_docs

    for doc in retrieved_docs:
        query_ids.append(query.publication.doc_number)
        knowledge_ids.append(doc.metadata["publication_number"])
        retrieved_paths.append(doc.metadata["path"])
        retrieved_chunks.append(doc.page_content)

    df = pd.DataFrame(
        {
            "query_id": query_ids,
            "knowledge_id": knowledge_ids,
            "retrieved_path": retrieved_paths,
            "retrieved_chunk": retrieved_chunks,
        }
    )
    return df


def _normalize_text(text: str) -> str:
    """
    改行・タブ・半角/全角スペースなどの空白文字を全て除去して返す
    """
    if text is None:
        return ""
    # \s で英数字系空白、\u3000 で全角スペース
    return re.sub(r"[\s\u3000]+", "", text)


def create_matched_md(index: int, xml_loader: CommonLoader, MAX_CHAR: int) -> str:
    """
    一致箇所とその前後MAX_CHAR文字を含めMarkdownテキストを作成する。
    一致箇所をハイライト表示するためにHTMLタグを追加する。
    """
    chunk: str = st.session_state.df_retrieved["retrieved_chunk"].iloc[index]
    path: str = st.session_state.df_retrieved["retrieved_path"].iloc[index]

    knowledge: Patent = xml_loader.run(Path(path))
    knowledge_str: str = knowledge.to_str()

    normalized_chunk = _normalize_text(chunk)
    normalized_knowledge = _normalize_text(knowledge_str)

    parts: list[str] = normalized_knowledge.split(normalized_chunk)
    first_part: str = parts[0]
    second_part: str = parts[1] if len(parts) > 1 else ""

    markdown_text = f"""
        {first_part[-MAX_CHAR:]}
        <span style="background-color: yellow; color: black; padding: 2px 4px; border-radius: 3px;">{normalized_chunk}</span>
        {second_part[:MAX_CHAR]}
        """
    return markdown_text

from google.cloud import bigquery
from dotenv import load_dotenv
import os
# .envファイルから環境変数を読み込む
load_dotenv()

# ----------------------------------------------------
# ▼▼▼ ユーザー設定 ▼▼▼
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID")
TABLE_ID = os.getenv("TABLE_ID")


def format_patent_number_for_bigquery(patent: Patent) -> str:
    """
    PatentオブジェクトからBigQuery用の特許番号フォーマット（JP-XXXXX-X）を生成する。

    Args:
        patent: Patentオブジェクト

    Returns:
        BigQuery用にフォーマットされた特許番号（例: JP-2012173419-A, JP-7550342-B2）
    """
    doc_number = patent.publication.doc_number
    country = patent.publication.country or "JP"
    kind = patent.publication.kind


    # BigQueryクライアントの初期化
    client = bigquery.Client(project=PROJECT_ID)


    # SQLクエリ(LIKE演算子で部分一致)
    query = f"""
    SELECT publication_number
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE publication_number LIKE '%{doc_number}%'
    """

    # クエリの実行
    query_job = client.query(query)

    # 結果の取得
    results = query_job.result()

    # 結果の表示
    for row in results:
        formatted_number =  str(row.publication_number)
        
        return formatted_number
    print("該当する特許番号が見つかりませんでした。")
    return ""
 
def format_patent_number_for_bigquery_compose_id(patent: Patent) -> str:
    """
    PatentオブジェクトからBigQuery用の特許番号フォーマット（JP-XXXXX-X）を生成する。

    Args:
        patent: Patentオブジェクト

    Returns:
        BigQuery用にフォーマットされた特許番号（例: JP-2012173419-A, JP-7550342-B2）
    """
    doc_number = patent.publication.doc_number
    country = patent.publication.country or "JP"
    kind = patent.publication.kind

    # kindから種別コード（A, B, B2など）を抽出
    kind_code = ""
    if kind:
        # 日本語のkind（例: "公開特許公報(A)", "特許公報(B2)"）からコードを抽出
        import re
        match = re.search(r'\(([AB]\d?)\)', kind)
        if match:
            kind_code = match.group(1)

    # kindが取得できない場合は、デフォルトでAを使用
    if not kind_code:
        kind_code = "A"

    # フォーマット: JP-{doc_number}-{kind_code}
    formatted_number = f"{country}-{doc_number}-{kind_code}"

    return formatted_number
