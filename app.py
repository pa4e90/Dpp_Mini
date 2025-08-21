import streamlit as st
import pandas as pd
from pydantic import BaseModel

st.set_page_config(page_title="DPP Mini", layout="wide")
st.title("DPP Mini")

class Item(BaseModel):
    gtin: str
    batch: str
    expiry: str  # YYYY-MM-DD for now

st.sidebar.header("Upload CSV (optional)")
file = st.sidebar.file_uploader("CSV with gtin,batch,expiry", type=["csv"])

data = pd.read_csv(file) if file else pd.DataFrame(columns=["gtin","batch","expiry"])
st.subheader("Items")
st.dataframe(data, use_container_width=True)

st.subheader("Add single item")
gtin = st.text_input("GTIN")
batch = st.text_input("Batch")
expiry = st.text_input("Expiry (YYYY-MM-DD)")
if st.button("Validate & Add"):
    try:
        item = Item(gtin=gtin, batch=batch, expiry=expiry)
        st.success(f"Valid: {item.model_dump()}")
    except Exception as e:
        st.error(str(e))
