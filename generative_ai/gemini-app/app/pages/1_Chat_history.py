from helpers import clean_history, CONVERSATION_HISTORY, is_history
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Chat history",
    page_icon="📜",
)

history_placeholder = st.empty()

is_history()
df = pd.read_csv(CONVERSATION_HISTORY)
if df.empty:
    st.write("No chat history")
else:
    with history_placeholder.container():
        # st.dataframe(df)
        st.data_editor(
            df,
            column_config={"image": st.column_config.ImageColumn("Image")},
            hide_index=True,
        )

    if st.button("Clean history"):
        clean_history()
        history_placeholder.empty()
