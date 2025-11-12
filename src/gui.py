import pandas as pd
import streamlit as st

from app.generator import Generator
from app.retriever import Retriever
from infra.loader.common_loader import CommonLoader
from ui.gui.page1 import page_1
from ui.gui.page2 import page_2
from ui.gui.page99 import page_99

# 定数
# TODO: GUI関連の定数の適切な定義場所を考える。移動する。
KNOWLEDGE_DIR = "eval/knowledge"


# セッションステート
# TODO: データはRepositoryクラス、処理はRAGクラスなどにラップしたい。
def init_session_state():
    # 不変
    if "loader" not in st.session_state:
        st.session_state.loader = CommonLoader()
    if "retriever" not in st.session_state:
        st.session_state.retriever = Retriever(knowledge_dir=KNOWLEDGE_DIR)
    if "generator" not in st.session_state:
        st.session_state.generator = Generator()
    # 可変
    if "df_retrieved" not in st.session_state:
        st.session_state.df_retrieved = pd.DataFrame()
    if "matched_chunk_markdowns" not in st.session_state:
        st.session_state.matched_chunk_markdowns = []
    if "reasons" not in st.session_state:
        st.session_state.reasons = []
    if "query" not in st.session_state:
        st.session_state.query = None
    if "retrieved_docs" not in st.session_state:
        st.session_state.retrieved_docs = []
    if "file_id" not in st.session_state:
        st.session_state.file_id = "no_file_yet"
    if "n_chunk" not in st.session_state:
        st.session_state.n_chunk = 0


def main():
    st.set_page_config(layout="wide")
    init_session_state()
    pg = st.navigation([page_1, page_2, page_99])
    pg.run()


if __name__ == "__main__":
    main()
