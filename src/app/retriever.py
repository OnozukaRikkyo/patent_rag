import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from infra.config import cfg
from infra.loader.common_loader import CommonLoader
from model.patent import Patent


class Retriever:
    def __init__(self, knowledge_dir: str):
        # TODO: リトリーバでベクトルストアを生成するのではなく、生成したベクトルストアをリトリーバにDIするほうがいいかも。
        self.knowledge_paths = list(Path(knowledge_dir).rglob("text.txt"))
        self.knowledge: dict[str, Patent] = {}
        self.loader = CommonLoader()
        # todo: Chroma、Faissなど、ベクトルストアの性能をちゃんと比較するべき。
        self.chroma = self._build_chroma()
        self.retriever = self.chroma.as_retriever(search_kwargs={"k": cfg.top_n})

    def _init_embeddings(self) -> Embeddings:
        """
        埋め込みモデルを初期化する。
        """
        type = cfg.embedding_type.lower()
        if type == "gemini":
            embeddings: Embeddings = GoogleGenerativeAIEmbeddings(
                model=cfg.gemini_embedding_model_name,
                api_key=os.getenv("GOOGLE_API_KEY"),  # type: ignore
            )
        elif type == "openai":
            embeddings: Embeddings = OpenAIEmbeddings(
                model=cfg.openai_embedding_model_name,
                api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore
            )
        else:
            raise ValueError(f"未定義の埋め込みモデルです: {cfg.embedding_type}")

        return embeddings

    def _build_chroma(self) -> Chroma:
        """
        ナレッジからベクトルストアを構築する。
        既存のベクトルストアが存在するならロードする。
        """
        embeddings: Embeddings = self._init_embeddings()

        if os.path.exists(cfg.persist_dir):
            chroma = Chroma(persist_directory=cfg.persist_dir, embedding_function=embeddings)
        else:
            # 430万件（500GB）超の大規模ナレッジで、とても重たい処理
            # TODO: この処理は「検索」ではないので、別クラスで実行したほうがいいかも。
            self.knowledge = self._load_knowledge()
            os.makedirs(cfg.persist_dir, exist_ok=True)

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=cfg.chunk_size,
                chunk_overlap=cfg.chunk_overlap,
                add_start_index=True,
            )
            knowledge_docs: list[Document] = [patent.to_doc() for patent in self.knowledge.values()]
            splitted_docs: list[Document] = splitter.split_documents(knowledge_docs)
            chroma = Chroma.from_documents(
                documents=splitted_docs,
                embedding=embeddings,
                persist_directory=cfg.persist_dir,
            )

        return chroma

    def _load_knowledge(self) -> dict[str, Patent]:
        knowledge = {}
        for path in self.knowledge_paths:
            patent: Patent = self.loader.run(path)
            id: str = patent.publication.doc_number
            knowledge[id] = patent
        return knowledge

    def _to_str(self, patent: Patent) -> str:
        """
        クエリ特許から、検索用の文字列を生成する
        """
        # todo: クエリ生成戦略をちゃんと考えるべき。
        query = f"{patent.invention_title}"
        query += f"\n{patent.claims[0]}"
        return query

    def retrieve(self, query: str | Patent) -> list[Document]:
        """
        新規出願特許（query）に関連する公開特許を返す。
        """
        # 仮：タイトルと請求項のみ
        # todo: 適切な検索クエリを設計する。
        if isinstance(query, str):
            query_str = query
        elif isinstance(query, Patent):
            query_str = self._to_str(query)
        else:
            raise ValueError("クエリは、strかPatent型にしてください。")

        # ベクトル検索
        retrieved_docs: list[Document] = self.retriever.invoke(query_str)

        # DocumentからPatentに変換：情報量が異なるので、完全に同じPatentにはならない。
        # Patentにする必要があるのか、設計しなおすべき。
        # 現状：XML構造のPatent = 内部処理用のPatent -> Documentに変換（ただし情報量が減る）
        # 今後：XML構造のPatent -> 内部処理用のPatent <-> Documentに変換（互換性あり）

        return retrieved_docs
