import streamlit as st
from pathlib import Path
import pandas as pd
from llm.llm_data_loader import entry
import json

def display_single_result(result, idx):
    """
    単一の先行技術との比較結果を表示する（詳細ページ用）

    Args:
        result: 単一の審査結果
        idx: 先行技術の番号（表示用）
    """
    if isinstance(result, dict) and 'error' in result:
        st.error(f"エラーが発生しました: {result['error']}")
        return

    st.markdown("---")
    st.markdown(f"## 🔍 先行技術 #{idx + 1} との比較")
    st.markdown("---")

    # ヘッダー部分
    st.markdown("🚀" * 40)
    st.markdown("### 特許審査プロセス開始 (統合版)")
    st.markdown("🚀" * 40)

    # conversation_historyがある場合は、それを使って表示
    if 'conversation_history' in result and result['conversation_history']:
        for msg in result['conversation_history']:
            display_step_message(msg)
    else:
        # conversation_historyがない場合は、従来の形式で表示
        display_legacy_format(result)

    # 最終判断を強調表示
    if 'final_decision' in result:
        st.markdown("---")
        st.markdown("✅" * 40)
        st.markdown("### 特許審査プロセス完了")
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(result['final_decision'])
        st.markdown("✅" * 40)

    # 進歩性の判断結果をサマリー表示
    if 'inventiveness' in result:
        st.markdown("---")
        st.subheader("📊 進歩性判断サマリー")
        display_inventiveness_summary(result['inventiveness'])

def display_chat_messages(results):
    """
    LLMの出力を逐次チャット形式で表示する

    Args:
        results: llm_entryから返された審査結果のリスト
    """
    if not results:
        st.warning("審査結果が見つかりません")
        return

    # 各先行技術との比較結果を表示
    for idx, result in enumerate(results):
        display_single_result(result, idx)

def display_step_message(msg):
    """
    各ステップのメッセージをチャット形式で表示

    Args:
        msg: ステップ情報を含む辞書 (step, role, content)
    """
    step = msg.get('step', '')
    role = msg.get('role', '')
    content = msg.get('content', '')

    # ステップごとにアバターを設定
    avatar_map = {
        '構造化': '📋',
        '代理人': '⚖️',
        '審査官': '🔍',
        '主任審査官': '⚖️'
    }
    avatar = avatar_map.get(role, '💬')

    # ステップヘッダー
    st.markdown("=" * 80)
    st.markdown(f"### {avatar} ステップ{step}: {role}")
    st.markdown("=" * 80)

    # メッセージ内容を表示
    with st.chat_message("assistant", avatar=avatar):
        if isinstance(content, dict):
            # 構造化データの場合
            st.markdown("✅ 構造化完了:")
            if 'problem' in content:
                st.markdown(f"**課題:** {content['problem']}")
            if 'solution_principle' in content:
                st.markdown(f"**解決原理:** {content['solution_principle']}")
            if 'claim1_requirements' in content:
                st.markdown(f"**Claim 1要件:** {len(content['claim1_requirements'])}個")
                with st.expander("要件の詳細を表示"):
                    for req in content['claim1_requirements']:
                        st.markdown(f"- {req}")
        elif isinstance(content, str):
            # テキストメッセージの場合
            st.markdown("✅ 生成完了:")
            st.markdown("---")
            st.markdown(content)
            st.markdown("---")

def display_legacy_format(result):
    """
    conversation_historyがない場合の従来形式での表示

    Args:
        result: 審査結果の辞書
    """
    # 本願発明の構造化
    if 'application_structure' in result:
        st.markdown("=" * 80)
        st.markdown("### 📋 ステップ0.1: 本願発明の構造化")
        st.markdown("=" * 80)
        with st.chat_message("assistant", avatar="📋"):
            st.json(result['application_structure'])

    # 先行技術の構造化
    if 'prior_art_structure' in result:
        st.markdown("=" * 80)
        st.markdown("### 📋 ステップ0.2: 先行技術の構造化")
        st.markdown("=" * 80)
        with st.chat_message("assistant", avatar="📋"):
            st.json(result['prior_art_structure'])

    # 代理人の主張
    if 'applicant_arguments' in result:
        st.markdown("=" * 80)
        st.markdown("### ⚖️ ステップ1: 代理人の段階的主張")
        st.markdown("=" * 80)
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(result['applicant_arguments'])

    # 審査官の検証
    if 'examiner_review' in result:
        st.markdown("=" * 80)
        st.markdown("### 🔍 ステップ2: 審査官の専門的判断")
        st.markdown("=" * 80)
        with st.chat_message("assistant", avatar="🔍"):
            st.markdown(result['examiner_review'])

    # 最終判断
    if 'final_decision' in result:
        st.markdown("=" * 80)
        st.markdown("### ⚖️ ステップ3: 主任審査官の段階的統合判断")
        st.markdown("=" * 80)
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(result['final_decision'])

def display_inventiveness_summary(inventiveness):
    """
    進歩性判断のサマリーを表形式で表示

    Args:
        inventiveness: 進歩性判断の辞書
    """
    if 'error' in inventiveness:
        st.error("進歩性の判断結果を解析できませんでした")
        return

    # データフレーム形式に変換
    summary_data = []
    for claim_key, claim_data in inventiveness.items():
        if claim_key.startswith('claim'):
            inventive = claim_data.get('inventive', False)
            reason = claim_data.get('reason', '')
            summary_data.append({
                'クレーム': claim_key.upper(),
                '進歩性': '✅ あり' if inventive else '❌ なし',
                '理由': reason
            })

    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)

def ai_judge_detail(action="show_page"):
    """AI審査結果の詳細画面"""
    st.title("🔍 AI特許審査の詳細結果")

    with st.spinner("審査プロセスを実行中..."):
        results = entry(action=action)

    # 結果をチャット形式で表示
    display_chat_messages(results)
