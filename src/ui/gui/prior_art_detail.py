import streamlit as st
from ui.gui.ai_judge_detail import display_single_result
from ui.gui import page1

def prior_art_detail():
    """先行技術の詳細ページ"""

    # session_stateから選択された先行技術のインデックスを取得
    if 'selected_prior_art_idx' not in st.session_state:
        st.error("❌ 先行技術が選択されていません。")
        if st.button("メインページに戻る"):
            st.switch_page(st.Page(page1.page_1))
        return

    # AI審査結果を取得
    if 'ai_judge_results' not in st.session_state or not st.session_state.ai_judge_results:
        st.error("❌ AI審査結果が見つかりません。")
        if st.button("メインページに戻る"):
            st.switch_page(st.Page(page1.page_1))
        return

    idx = st.session_state.selected_prior_art_idx
    results = st.session_state.ai_judge_results

    # インデックスの範囲チェック
    if idx < 0 or idx >= len(results):
        st.error(f"❌ 無効な先行技術番号です: {idx + 1}")
        if st.button("メインページに戻る"):
            st.switch_page(st.Page(page1.page_1))
        return

    result = results[idx]

    # タイトル
    doc_number = result.get('prior_art_doc_number', f"紐付き候補文献の審査結果 #{idx + 1}")
    st.title(f"🔍 公開番号: {doc_number}")

    # メインページに戻るボタン
    if st.button("⬅️ メインページに戻る"):
        st.switch_page(st.Page(page1.page_1))

    st.markdown("---")

    # 単一の結果を表示
    display_single_result(result, idx)

if __name__ == "__main__":
    prior_art_detail()