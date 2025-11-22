from pathlib import Path
import json
import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

# --- 既存のインポート (環境に合わせてパスは維持) ---
from infra.config import PROJECT_ROOT, PathManager
from model.patent import Patent
from ui.gui import query_detail
from ui.gui import ai_judge_detail
# from ui.gui import prior_art_detail # 必要に応じて利用
# from ui.gui import search_results_list # 必要に応じて利用

# 定数
MAX_CHAR = 300

# 除外するシステムディレクトリ名のリスト
EXCLUDE_DIRS = {
    "uploaded", "topk", "temp", "query", "knowledge",
    "__pycache__", ".git", ".ipynb_checkpoints"
}

def reset_session_state():
    """セッションステートの初期化"""
    keys_to_reset = [
        "df_retrieved", "matched_chunk_markdowns", "reasons",
        "query", "retrieved_docs", "search_results_df",
        "ai_judge_results", "file_content", "project_dir",
        "current_doc_number"
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

def load_existing_project_data(doc_number: str):
    """
    既存のプロジェクトデータをロードしてsession_stateにセットする
    """
    reset_session_state()

    try:
        # 1. パスの特定
        uploaded_dir = PathManager.get_uploaded_query_path(doc_number)
        # NOTE: 保存時のファイル名が固定でない場合、検索が必要
        # ここでは実装簡略化のため、ディレクトリ内の最初のtxt/xmlを探すか、
        # 元コードの仕様に合わせて "uploaded_query.txt" を探します
        query_file = uploaded_dir / "uploaded_query.txt"

        if not query_file.exists():
            st.error(f"❌ 出願テキストが見つかりません: {query_file}")
            return False

        # 2. 出願データのロード (Step 1相当)
        with open(query_file, "r", encoding="utf-8") as f:
            file_content = f.read()

        # XML解析 (Loaderを使用)
        query: Patent = st.session_state.loader.run(query_file)

        # Session State 設定
        st.session_state.file_content = file_content
        st.session_state.query = query
        st.session_state.project_dir = uploaded_dir.parent
        st.session_state.uploaded_dir = uploaded_dir
        st.session_state.current_doc_number = doc_number

        # 3. 検索結果のロード (Step 2相当)
        topk_dir = PathManager.get_topk_results_path(doc_number)
        if topk_dir.exists():
            csv_files = sorted(topk_dir.glob("*.csv"))
            if csv_files:
                latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
                search_results_df = pd.read_csv(latest_csv)
                st.session_state.search_results_df = search_results_df
                st.session_state.df_retrieved = search_results_df
                # 検索結果CSVパスも保存しておくと便利
                st.session_state.search_results_csv_path = str(latest_csv)

        # 4. AI審査結果のロード (Step 3相当)
        ai_judge_dir = PathManager.get_ai_judge_result_path(doc_number)
        if ai_judge_dir.exists():
            json_files = sorted(ai_judge_dir.glob("*.json"))
            if json_files:
                latest_json = json_files[-1] # 名前順または日付順
                with open(latest_json, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                st.session_state.ai_judge_results = results

        return True

    except Exception as e:
        st.error(f"データのロード中にエラーが発生しました: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False


def page_1():
    st.title("GENIAC-PRIZE prototype v1.1")

    # --- モード選択（サイドバー） ---
    mode = st.sidebar.radio(
        "モード選択",
        ("1. 新規アップロード", "2. 既存文献の表示")
    )

    if mode == "1. 新規アップロード":
        view_new_upload()
    else:
        view_existing_project()


def view_new_upload():
    """画面１：新規アップロードモード"""
    st.header("📝 新規出願の審査")
    st.write("新しいXMLファイルをアップロードして、一連のプロセスを実行します。")

    # Step 1: アップロード処理
    st.subheader("1. 出願データの読み込み")

    uploaded_file: UploadedFile | None = st.file_uploader("XML形式の出願を１件アップロードしてください。", type=["xml", "txt"])

    if uploaded_file is not None:
        # ファイル読み込み処理
        try:
            file_content: str = uploaded_file.read().decode("utf-8")
        except Exception as e:
            st.error(f"❌ ファイルの読み込みに失敗しました: {e}")
            return

        st.text_area("ファイルの中身:", file_content, height=150)

        # Session Stateの内容と異なる場合のみ再処理（リロード対策）
        if st.session_state.get("file_content") != file_content:
            process_new_upload(file_content)
        else:
            if "query" in st.session_state:
                st.success(f"✓ ロード済み: 特許ID {st.session_state.query.publication.doc_number}")

    # 共通ステップの表示（データがロードされている場合のみ）
    if "query" in st.session_state:
        render_common_steps()


def process_new_upload(file_content):
    """新規アップロード時のバックエンド処理"""
    try:
        # --- Phase 1: 一時ディレクトリに保存 ---
        temp_path = PathManager.get_temp_path("uploaded_query.txt")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        with st.spinner("XMLを解析中..."):
            # XMLをparseしてdoc_numberを取得
            query: Patent = st.session_state.loader.run(temp_path)
            public_doc_number = query.publication.doc_number

            if not public_doc_number:
                st.error("特許番号(doc_number)が取得できませんでした。")
                return

        # --- Phase 2: 正規のディレクトリにコピー ---
        permanent_path = PathManager.move_to_permanent(temp_path, public_doc_number)
        uploaded_dir = PathManager.get_uploaded_query_path(public_doc_number)

        # Session Stateの更新
        reset_session_state()
        st.session_state.file_content = file_content
        st.session_state.query = query
        st.session_state.project_dir = permanent_path.parent
        st.session_state.source_file = permanent_path
        st.session_state.uploaded_dir = uploaded_dir
        st.session_state.current_doc_number = public_doc_number

        st.success(f"✓ 初期化完了: 特許ID {public_doc_number}")

    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")


def view_existing_project():
    """画面２：既存文献表示モード"""
    st.header("📂 既存プロジェクトの参照")
    st.write("過去に処理した出願データを選択して表示します。")

    # evalディレクトリをスキャン
    eval_dir = PROJECT_ROOT / "eval"
    if not eval_dir.exists():
        st.warning("保存されたデータが見つかりません。")
        return

    # ディレクトリ一覧取得（システムフォルダを除外）
    projects = [
        d.name for d in eval_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith('.')
        and d.name not in EXCLUDE_DIRS  # ここでシステムフォルダを除外
    ]
    projects.sort(reverse=True) # 新しい順（簡易的）

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_doc = st.selectbox("出願IDを選択してください", projects)
    with col2:
        load_btn = st.button("読込", type="primary", use_container_width=True)

    # 読み込みボタン押下時
    if load_btn and selected_doc:
        with st.spinner(f"{selected_doc} のデータを読み込んでいます..."):
            if load_existing_project_data(selected_doc):
                st.success(f"✅ {selected_doc} を読み込みました")
            else:
                st.error("読み込みに失敗しました")

    # --- 修正箇所: データ表示ロジックを安全に変更 ---
    # current_doc_number がキーとして存在しない場合に備えて .get() を使用
    current_doc = st.session_state.get("current_doc_number")

    # query があり、かつ current_doc も取得できている場合のみ表示
    if "query" in st.session_state and current_doc:
        st.markdown("---")
        st.subheader(f"選択中の出願: {current_doc}")

        with st.expander("出願テキストを確認する"):
            # file_content も念のため get で取得（あるいは空文字をデフォルトに）
            content = st.session_state.get("file_content", "")
            st.text_area("ファイルの中身:", content, height=150)

        render_common_steps()

    elif "query" in st.session_state and not current_doc:
        # 旧データが残っている場合のフォールバック
        st.warning("⚠️ セッション情報が古いため、ブラウザをリロードするか、再度「読込」ボタンを押してください。")


def render_common_steps():
    """
    Step 2以降の共通処理
    新規アップロード後も、既存ロード後も、この関数でUIを描画する
    """

    # --- Step 2: 類似文献検索 ---
    st.header("2. 類似文献の検索")
    st.write("Google Patents Public Dataの埋め込みベクトルを用いて類似文献を検索します。")

    has_search_results = 'search_results_df' in st.session_state and st.session_state.search_results_df is not None

    if has_search_results:
        st.info(f"💾 検索結果: {len(st.session_state.search_results_df):,}件 取得済み")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 詳細リストを表示", key="goto_search_list"):
                st.switch_page("ui/gui/search_results_list.py")
        with col2:
            if st.button("🔄 検索をやり直す", key="rerun_search"):
                query_detail.query_detail()
    else:
        if st.button("検索実行", type="primary", key="run_new_search"):
            query_detail.query_detail()

    # --- Step 3: AI審査 ---
    st.header("3. AI審査")
    st.write("LLMを活用し、類似文献に基づいて新規性・進歩性を審査します。")

    has_ai_results = 'ai_judge_results' in st.session_state and st.session_state.ai_judge_results

    if has_ai_results:
        st.info(f"💾 審査結果: {len(st.session_state.ai_judge_results)}件 取得済み")

        # 結果リストの表示
        with st.expander("審査結果一覧を開く", expanded=True):
            for idx, result in enumerate(st.session_state.ai_judge_results):
                if isinstance(result, dict) and 'error' in result:
                    st.error(f"No.{idx+1}: エラー")
                    continue

                doc_num = result.get('prior_art_doc_number', f"Doc #{idx+1}")
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.write(f"**{idx+1}. {doc_num}**")
                with c2:
                    if st.button("詳細", key=f"ai_detail_{idx}"):
                        st.session_state.selected_prior_art_idx = idx
                        st.switch_page("ui/gui/prior_art_detail.py")

        if st.button("🔄 AI審査をやり直す", key="rerun_ai_judge"):
             run_ai_judge()
    else:
        if st.button("AI審査実行", type="primary", key="run_ai_judge_new"):
            # 検索結果がないと実行できない
            if not has_search_results:
                st.warning("⚠️ 先に「2. 類似文献の検索」を実行してください。")
            else:
                run_ai_judge()

    # --- Step 4: 判断根拠出力 ---
    st.header("4. 判断根拠出力")

    # 前提条件チェック
    if not has_ai_results:
        st.write("⚠️ AI審査を実行すると表示されます。")
    else:
        # NOTE: 元のコードにある n_chunk は session_state に依存していたため、
        # ここでは retrieved_docs の長さなどから動的に設定するか、デフォルト値を設けます
        n_chunk_default = len(st.session_state.ai_judge_results)

        if st.button("根拠テキスト生成", type="primary"):
            if "retrieved_docs" not in st.session_state or not st.session_state.retrieved_docs:
                 st.error("文献データ(retrieved_docs)がメモリにありません。再検索が必要な可能性があります。")
            else:
                generate_reasons(n_chunk_default)

        if "reasons" in st.session_state and st.session_state.reasons:
            for i, reason in enumerate(st.session_state.reasons):
                st.markdown(f"##### 判断根拠 {i + 1}")
                st.code(reason, language="markdown")


def run_ai_judge():
    """AI審査実行ラッパー"""
    st.session_state.n_topk = len(st.session_state.df_retrieved)
    with st.spinner("審査プロセスを実行中..."):
        results = ai_judge_detail.entry(action="button_click")
        if results:
            st.session_state.ai_judge_results = results
            st.success("✅ AI審査が完了しました。")
            st.rerun() # 状態反映のためリロード

def generate_reasons(n_chunk):
    """根拠生成ロジック"""
    st.session_state.reasons = []
    status_text = st.empty()
    progress = st.progress(0)

    # インデックスエラーを防ぐため、実際の配列長とn_chunkの小さい方を取る
    actual_limit = min(n_chunk, len(st.session_state.retrieved_docs))

    for i in range(actual_limit):
        status_text.text(f"{i + 1} / {actual_limit} 件目を生成中です...")
        # generatorがsession_stateにある前提
        if "generator" in st.session_state:
            reason = st.session_state.generator.generate(
                st.session_state.query,
                st.session_state.retrieved_docs[i]
            )
            st.session_state.reasons.append(reason)
        else:
            st.error("Generatorが初期化されていません。")
            break
        progress.progress((i + 1) / actual_limit)

    status_text.text("生成が完了しました。")


if __name__ == "__main__":
    page_1()