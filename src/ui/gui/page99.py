"""
Streamlitのコンポーネントを手元にストックしておく用です。

公式サイトからコピペしています。
https://docs.streamlit.io/develop/api-reference

本番システムではこのページは使いません。
"""

import streamlit as st


def page_99():
    st.write("page99です")

    tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])

    with tab1:
        st.markdown("## 表示系")
        st_dataframe()
        st_json()

    with tab2:
        st.markdown("## 入力系")
        st_button()
        st_link_button()

def st_dataframe():
    st.markdown("### st.dataframe(df)")
    import pandas as pd

    row_1 = {"col_1": 1, "col_2": 2, "col_3": 3}
    row_2 = {"col_1": 3, "col_2": 2, "col_3": 1}
    row_3 = {"col_1": 2, "col_2": 1, "col_3": 3}
    df = pd.DataFrame([row_1, row_2, row_3])
    st.dataframe(df)

def st_json():
    st.markdown("### st.json(dict)")
    st.json(
        {
            "foo": "bar",
            "stuff": [
                "stuff 1",
                "stuff 2",
                "stuff 3",
            ],
            "level1": {"level2": {"level3": {"a": "b"}}},
        },
        expanded=2,
    )


def st_button():
    st.markdown("### st.button('label')")
    st.button("Reset", type="primary")
    if st.button("Say hello"):
        st.write("Why hello there")
    else:
        st.write("Goodbye")

    if st.button("Aloha", type="tertiary"):
        st.write("Ciao")

def st_link_button():
    st.markdown("### st.link_button('URL')")
    st.link_button("Go to gallery", "https://streamlit.io/gallery")
    st.link_button("Go to gallery", "https://streamlit.io/gallery", type="primary")