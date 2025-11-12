from dataclasses import dataclass


@dataclass
class Config:
    """
    アプリケーション全体の設定を保持するクラス。
    """

    # Embeddings, Retriever
    embedding_type = "openai"  # "openai" or "gemini"
    openai_embedding_model_name = "text-embedding-3-small"
    gemini_embedding_model_name = "models/gemini-embedding-exp-03-07"
    chunk_size = 400
    chunk_overlap = 100
    top_n = 3

    # Chroma
    # persist_dir = "data_store/chroma/gemini_v0.1"
    persist_dir = "data_store/chroma/openai_v1.0"

    # LLM
    llm_type = "openai" # "openai" or "gemini"
    openai_llm_name = "gpt-5-nano" # gpt-5-nano（最安）, gpt-5（最高品質） 
    gemini_llm_name = "gemini-2.5-flash" # Geminiはよくわからん。


cfg = Config()
