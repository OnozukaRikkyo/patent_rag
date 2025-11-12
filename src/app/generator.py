"""
回答生成器です。10月以降に実装します。
"""

import os

from langchain_core.documents import Document
from openai import OpenAI

from infra.config import cfg
from model.patent import Patent


class Generator:
    def __init__(self):
        self.client, self.model = self._init_llm()

    def _init_llm(self) -> tuple[OpenAI, str]:
        """
        OpenAIのLLMクライアントを初期化する。
        """
        type = cfg.llm_type.lower()
        if type == "openai":
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = cfg.openai_llm_name
        elif type == "gemini":
            # gemini用のURLを指定
            client = OpenAI(api_key=os.getenv("GOOGLE_API_KEY"), base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            model = cfg.gemini_llm_name
        else:
            raise ValueError(f"未定義のLLMです: {cfg.llm_type}")

        return client, model

    def generate(self, query: Patent, retrieved_doc: Document) -> str:
        """
        情報探索と一致箇所表示の根拠説明文を生成します。
        """
        query_content: str = query.to_str()
        retrieved_doc_content: str = retrieved_doc.page_content

        prompt = REASONING_TEMPLATE_SKT.format(
            query_content=query_content,
            retrieved_doc_content=retrieved_doc_content,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀な特許審査官です。ユーザからの質問に対して、正確かつ簡潔に答えてください。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        reason = response.choices[0].message.content
        if not reason:
            raise ValueError("根拠説明文の生成に失敗しました。")

        return reason


# TODO: プロンプト最適化
REASONING_TEMPLATE_SKT = """
出願内容と、それに類似する公知例の内容をよく理解してください。
なぜこの出願に対して、この公知例が類似していると判断されたのか理由を説明してください。

出願内容: 
{query_content}

出願内容に類似する公知例: 
{retrieved_doc_content}

それでは、判断理由の説明文を生成してください。
"""
