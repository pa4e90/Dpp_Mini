import streamlit as st
import pandas as pd

st.set_page_config(page_title="DPP Mini", layout="wide")
st.title("DPP Mini")

class Item(BaseModel):
    gtin: str
    batch: str

st.sidebar.header("Upload CSV (optional)")
file = st.sidebar.file_uploader("CSV with gtin,batch,expiry", type=["csv"])

st.subheader("Add single item")
    gtin = st.text_input("GTIN")
    batch = st.text_input("Batch")
    expiry = st.text_input("Expiry (YYYY-MM-DD)")
if st.button("Validate & Add"):
    try:
    except Exception as e:
        st.error(str(e))
