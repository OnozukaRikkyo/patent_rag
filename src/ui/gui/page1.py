"""
必要機能：
- 任意の出願を読み込む機能：XML形式ファイルをアップロードする（中身はXMLだけど、拡張子はtxtとxmlの両方に対応しておいた方がいい）
- 情報探索機能：細かい指定はない　→出願IDと紐づきIDの対応関係を表形式で表示する
- 一致箇所表示機能：細かい指定はない　→テキストを表示し、一致箇所はハイライトさせる
- 判断根拠出力機能：情報探索と一致箇所表示の根拠を自然言語で表示　→判断根拠テキストボックスを作って、その中に「情報探索の根拠」と「一致箇所の根拠」を表示する。
"""

from pathlib import Path
import json

import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from infra.config import PathManager
from model.patent import Patent
# from ui.gui.utils import create_matched_md  # , retrieve
from ui.gui import query_detail
from ui.gui import ai_judge_detail
from ui.gui import prior_art_detail
from ui.gui import search_results_list

# プロジェクトルート（このファイルは ui/gui/ にあるので3階層上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 定数
# TODO: 切り替え可能にする？ 別の場所で管理する？
QUERY_PATH = PROJECT_ROOT / "eval" / "uploaded" / "uploaded_query.txt"
MAX_CHAR = 300


def reset_session_state():
    st.session_state.df_retrieved = pd.DataFrame()
    st.session_state.matched_chunk_markdowns = []
    st.session_state.reasons = []
    st.session_state.query = None
    st.session_state.retrieved_docs = []


def page_1():
    st.title("GENIAC-PRIZE prototype v1.0")
    st.write("1. から 4. までを順番に実行してください。")

    # 1. 任意の出願を読み込む
    st.header("1. 任意の出願を読み込む")
    step1()

    # 2. 情報探索
    st.header("2. 類似文献の検索")
    step2()

    # 3. AI審査
    st.header("3. AI審査")
    step3()

    # 4. 判断根拠出力
    st.header("4. 判断根拠出力")
    step4()

    # その他
    st.subheader("その他")
    step99()


def step1():
    uploaded_file: UploadedFile | None = st.file_uploader("1. XML形式の出願を１件アップロードしてください。", type=["xml", "txt"])
    if uploaded_file is not None:
        # アップロードされたファイルの中身を読み込む
        try:
            file_content: str = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            st.error("❌ ファイルのエンコーディングが正しくありません。UTF-8形式のファイルをアップロードしてください。")
            return
        except Exception as e:
            st.error(f"❌ ファイルの読み込みに失敗しました: {e}")
            return

        st.text_area("ファイルの中身:", file_content, height=200)

        if st.session_state.get("file_content") != file_content:
            # --- Phase 1: 一時ディレクトリに保存 ---
            temp_path = PathManager.get_temp_path("uploaded_query.txt")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            try:
                with st.spinner("XMLを解析中..."):
                    # XMLをparseしてdoc_numberを取得
                    query: Patent = st.session_state.loader.run(temp_path)
                    public_doc_number = query.publication.doc_number

                    if not public_doc_number:
                        st.error("特許番号(doc_number)が取得できませんでした。")
                        return

                # --- Phase 2: 正規のディレクトリにコピー ---
                permanent_path = PathManager.move_to_permanent(temp_path, public_doc_number)

                # アップロードディレクトリのパスを取得
                uploaded_dir = PathManager.get_uploaded_query_path(public_doc_number)

                # Session Stateの更新
                reset_session_state()
                st.session_state.file_content = file_content
                st.session_state.query = query
                st.session_state.project_dir = permanent_path.parent
                st.session_state.source_file = permanent_path
                st.session_state.uploaded_dir = uploaded_dir

                st.success(f"✓ 初期化完了: 特許ID {public_doc_number}")
                st.info(f"📁 データ保存先: {st.session_state.project_dir}")

            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {e}")
                import traceback
                st.code(traceback.format_exc())

        else:
            # すでにロード済み
            if "query" in st.session_state and st.session_state.query:
                st.success(f"✓ ロード済み: 特許ID {st.session_state.query.publication.doc_number}")

def step2():
    st.write("出願の公開番号（query_id）について、Google Patents Public Dataの埋め込みベクトルを用いて類似文献を検索し、上位の文献を表示します。")
    st.write("Google Patents Public Dataは、高精度かつ効率のよい埋め込みベクトルを提供しており、特許文献の意味的な類似性を捉えることができます。")
    st.write("このため、独自に膨大な文献のベクトル化が不要となり、コスト的に効率的な検索が可能です。")

    # 既存の検索結果ファイルをチェック
    existing_results = None
    doc_number = None

    # まず、session_stateにqueryがあるかチェック
    if "query" in st.session_state and st.session_state.query is not None:
        doc_number = st.session_state.query.publication.doc_number

    # session_stateにない場合は、evalディレクトリ内を探す
    if doc_number is None:
        eval_dir = PROJECT_ROOT / "eval"
        if eval_dir.exists():
            # evalディレクトリ内のサブディレクトリ（特許番号のディレクトリ）を探す
            subdirs = [d for d in eval_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            # 最新のディレクトリを使用（更新日時順）
            if subdirs:
                latest_subdir = max(subdirs, key=lambda d: d.stat().st_mtime)
                doc_number = latest_subdir.name

    # doc_numberが見つかった場合、topkディレクトリをチェック
    if doc_number:
        topk_dir = PathManager.get_topk_results_path(doc_number)

        if topk_dir.exists():
            # topkディレクトリ内のCSVファイルを探す
            csv_files = sorted(topk_dir.glob("*.csv"))
            if csv_files:
                # 最新のファイル（更新日時が最も新しいファイル）を取得
                latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
                existing_results = latest_file

    # 既存の結果がある場合は、情報を表示
    if existing_results:
        st.info(f"💾 既存の検索結果が見つかりました: {existing_results.parent.parent.name}/topk/{existing_results.name}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📂 既存の結果を読み込む", type="secondary", key="load_existing_search_results"):
                with st.spinner("結果を読み込み中..."):
                    try:
                        search_results_df = pd.read_csv(existing_results)
                        st.session_state.search_results_df = search_results_df
                        st.session_state.search_results_csv_path = str(existing_results)
                        st.session_state.df_retrieved = search_results_df
                        st.success(f"✅ {len(search_results_df):,}件の検索結果を読み込みました。")
                    except Exception as e:
                        st.error(f"❌ 結果の読み込みに失敗しました: {e}")

        with col2:
            # 検索を再実行する場合は、ステップ1が必須
            if st.button("🔄 検索を再実行", type="primary", key="rerun_search"):
                if "query" not in st.session_state or st.session_state.query is None:
                    st.warning("⚠️ 検索を実行するには、先にステップ1でファイルをアップロードしてください。")
                else:
                    query_detail.query_detail()
    else:
        # 既存の結果がない場合は、通常の検索ボタンのみ表示
        if st.button("検索", type="primary", key="new_search"):
            # 検索を新規実行する場合は、ステップ1が必須
            if "query" not in st.session_state or st.session_state.query is None:
                st.warning("⚠️ 先にステップ1でファイルをアップロードしてください。")
            else:
                query_detail.query_detail()

    # 検索結果がある場合、詳細ページへのリンクを表示
    if 'search_results_df' in st.session_state and st.session_state.search_results_df is not None:
        st.markdown("---")
        search_results_df = st.session_state.search_results_df

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**検索結果:** {len(search_results_df):,}件の類似特許が見つかりました")
        with col2:
            if st.button("📋 詳細を表示", key="search_results_detail_btn"):
                # 【修正箇所】文字列のパスに変更
                st.switch_page("ui/gui/search_results_list.py")

def step3():
    st.write(f"大規模言語モデルを活用し、類似度の高い先行技術文献に基づいてAI審査を実行します。")
    st.write(f"審査では、各先行技術文献が出願に対して新規性・進歩性を欠くかどうかを判断し、判定結果を示しします。")
    st.write(f"課題と解決方法、申請、審査、判定の各専門的な知識を組み合わせ、高精度な審査を目指します。")

    # 既存の結果ファイルをチェック（ステップ1実行の有無に関わらず）
    existing_results = None
    doc_number = None

    # まず、session_stateにqueryがあるかチェック
    if "query" in st.session_state and st.session_state.query is not None:
        doc_number = st.session_state.query.publication.doc_number

    # session_stateにない場合は、evalディレクトリ内を探す
    if doc_number is None:
        eval_dir = PROJECT_ROOT / "eval"
        if eval_dir.exists():
            # evalディレクトリ内のサブディレクトリ（特許番号のディレクトリ）を探す
            subdirs = [d for d in eval_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            # 最新のディレクトリを使用（更新日時順）
            if subdirs:
                latest_subdir = max(subdirs, key=lambda d: d.stat().st_mtime)
                doc_number = latest_subdir.name

    # doc_numberが見つかった場合、ai_judgeディレクトリをチェック
    if doc_number:
        ai_judge_dir = PathManager.get_ai_judge_result_path(doc_number)

        if ai_judge_dir.exists():
            # ai_judgeディレクトリ内のJSONファイルを探す
            json_files = sorted(ai_judge_dir.glob("*.json"))
            if json_files:
                # 最新のファイル（番号が最も大きいファイル）を取得
                latest_file = json_files[-1]
                existing_results = latest_file

    # 既存の結果がある場合は、情報を表示
    if existing_results:
        st.info(f"💾 既存の審査結果が見つかりました: {existing_results.parent.parent.name}/ai_judge/")

        col1, col2 = st.columns(2)
        with col1:
            # 【修正 1】keyを追加
            if st.button("📂 既存の結果を読み込む", type="secondary", key="btn_load_existing"):
                with st.spinner("結果を読み込み中..."):
                    try:
                        with open(existing_results, 'r', encoding='utf-8') as f:
                            results = json.load(f)
                        st.session_state.ai_judge_results = results
                        st.success(f"✅ {len(results)}件の審査結果を読み込みました。")
                    except Exception as e:
                        st.error(f"❌ 結果の読み込みに失敗しました: {e}")

        with col2:
            # AI審査を再実行する場合は、ステップ1が必須
            # 【修正 2】keyを追加
            if st.button("🔄 AI審査を再実行", type="primary", key="btn_rerun_ai"):
                if "query" not in st.session_state or st.session_state.query is None:
                    st.warning("⚠️ AI審査を実行するには、先にステップ1でファイルをアップロードしてください。")
                else:
                    with st.spinner("審査プロセスを実行中..."):
                        results = ai_judge_detail.entry(action="button_click")
                        if results:
                            st.session_state.ai_judge_results = results
                            st.success("✅ AI審査が完了しました。")
    else:
        # 既存の結果がない場合は、通常のAI審査ボタンのみ表示
        # 【修正 3】keyを追加
        if st.button("AI審査", type="primary", key="btn_new_run_ai"):
            # AI審査を新規実行する場合は、ステップ1が必須
            if "query" not in st.session_state or st.session_state.query is None:
                st.warning("⚠️ 先にステップ1でファイルをアップロードしてください。")
            else:
                n_topk = len(st.session_state.df_retrieved)
                st.session_state.n_topk = n_topk

                with st.spinner("審査プロセスを実行中..."):
                    results = ai_judge_detail.entry(action="button_click")
                    if results:
                        st.session_state.ai_judge_results = results
                        st.success("✅ AI審査が完了しました。")

    # AI審査結果がある場合、各先行技術へのリンクを表示
    if 'ai_judge_results' in st.session_state and st.session_state.ai_judge_results:
        st.markdown("---")
        st.subheader("📋 審査結果一覧")
        results = st.session_state.ai_judge_results

        for idx, result in enumerate(results):
            if isinstance(result, dict) and 'error' in result:
                st.error(f"先行技術 #{idx + 1}: エラーが発生しました")
                continue

            # 先行技術のdoc_numberを取得
            doc_number = result.get('prior_art_doc_number', f"先行技術 #{idx + 1}")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{idx + 1}.** {doc_number}")
            with col2:
                # ここはすでに key=f"detail_btn_{idx}" があるのでOKですが、
                # 前回の修正（switch_pageの引数）が適切か確認してください。
                if st.button(f"詳細を表示", key=f"detail_btn_{idx}"):
                    st.session_state.selected_prior_art_idx = idx
                    # 前回の修正: パスを文字列で指定（st.Page()を使わない場合）
                    st.switch_page("ui/gui/prior_art_detail.py")


def step4():
    # session stateの検証
    if "query" not in st.session_state or st.session_state.query is None:
        st.warning("⚠️ 先にステップ1でファイルをアップロードしてください。")
        return

    if "n_chunk" not in st.session_state:
        st.warning("⚠️ 先にステップ3でAI審査を実行してください。")
        return

    n_chunk = st.session_state.n_chunk

    if st.button("生成", type="primary"):
        st.session_state.reasons = []  # クリア

        status_text = st.empty()
        progress = st.progress(0)

        for i in range(n_chunk):
            status_text.text(f"{i + 1} / {n_chunk} 件目を生成中です...")
            reason = st.session_state.generator.generate(st.session_state.query, st.session_state.retrieved_docs[i])
            st.session_state.reasons.append(reason)
            progress.progress((i + 1) / n_chunk)
        status_text.text("生成が完了しました。")

    if st.session_state.reasons:
        for i, reason in enumerate(st.session_state.reasons):
            st.markdown(f"##### 判断根拠 {i + 1} / {n_chunk}")
            st.code(reason, language="markdown")


def step99():
    st.write("次の出願に対しても同様に、1. から順番に実行してください。")
    if st.button("リセット"):
        reset_session_state()
        st.success("クエリや検索結果の履歴をリセットしました。")

page_1()
