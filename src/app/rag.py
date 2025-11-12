from pathlib import Path

from langchain_core.documents import Document

from app.generator import Generator
from app.retriever import Retriever
from infra.loader.common_loader import CommonLoader
from model.patent import Patent


class Rag:
    """
    RAGを表すクラスです。
    検索器（Retriever）と生成器（Generator）から構成されます。
    """

    def __init__(self, retriever: Retriever, generator: Generator):
        """
        コンストラクタです。検索器と生成器を注入（DI）します。
        """
        self.retriever = retriever
        self.generator = generator

    def run(self, query: Patent) -> tuple[list[Document], list[str]]:
        # 関連出願を検索
        retrieved_docs: list[Document] = self.retriever.retrieve(query)

        # 判断根拠を生成
        reasons: list[str] = []
        for doc in retrieved_docs:
            reason: str = self.generator.generate(query, doc)
            reasons.append(reason)

        return retrieved_docs, reasons
    
    def run_retriever(self, query_paths: list[Path]) -> tuple[list[str], list[str], list[str]]:
        query_dict: dict[str, Patent] = self._load_queries(query_paths)
        query_ids: list[str] = []
        knowledge_ids: list[str] = []
        reasons: list[str] = []
        for id, query in query_dict.items():
            retrieved_docs: list[Document] = self.retriever.retrieve(query)
            print(f"Query: {query.invention_title}")
            print(f"Query: {query.publication.doc_number}")
            for doc in retrieved_docs:
                print(f"Result: {doc.metadata['publication_number']}")
                query_ids.append(query.publication.doc_number)
                knowledge_ids.append(doc.metadata["publication_number"])
                reasons.append(self.generator.generate(query, doc))

        return query_ids, knowledge_ids, reasons

    def _load_queries(self, query_paths: list[Path]) -> dict[str, Patent]:
        xml_loader = CommonLoader()
        query_dict: dict[str, Patent] = {}
        for path in query_paths:
            query: Patent = xml_loader.run(path)
            id: str = query.publication.doc_number
            query_dict[id] = query
        return query_dict
