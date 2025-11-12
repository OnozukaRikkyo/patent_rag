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
