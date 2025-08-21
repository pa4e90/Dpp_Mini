import streamlit as st
import pandas as pd
from datetime import date
from pydantic import BaseModel, field_validator, ValidationError

st.set_page_config(page_title="DPP Mini", layout="wide")
st.title("DPP Mini")


def gtin_is_valid(s: str) -> bool:
    if not s.isdigit() or len(s) not in (8, 12, 13, 14):
        return False
    data, check = s[:-1], int(s[-1])
    total = 0
    for i, ch in enumerate(reversed(data)):  # right→left
        d = int(ch)
        total += d * (3 if i % 2 == 0 else 1)  # 3,1,3,1...
    calc = (10 - (total % 10)) % 10
    return calc == check

# ---------- Validation model ----------
class Item(BaseModel):
    gtin: str
    batch: str
    expiry: date  # accepts 'YYYY-MM-DD'

    @field_validator("gtin")
    @classmethod
    def validate_gtin(cls, v: str) -> str:
        v = v.strip()
        if not gtin_is_valid(v):
            raise ValueError("Invalid GTIN (must be 8/12/13/14 digits with correct check digit).")
        return v

# ---------- Session state store ----------
COLUMNS = ["gtin", "batch", "expiry"]
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

# ---------- Sidebar upload ----------
st.sidebar.header("Upload CSV (optional)")
file = st.sidebar.file_uploader("CSV with gtin,batch,expiry", type=["csv"])
if file is not None:
    try:
        up = pd.read_csv(file)
        missing = [c for c in COLUMNS if c not in up.columns]
        if missing:
            st.sidebar.error(f"Missing columns: {missing}")
        else:
            st.session_state.data = (
                pd.concat([st.session_state.data, up[COLUMNS]], ignore_index=True)
                  .drop_duplicates(subset=COLUMNS, keep="last")
            )
            st.sidebar.success(f"Loaded {len(up)} rows.")
    except Exception as e:
        st.sidebar.error(f"Upload failed: {e}")

# ---------- Add single item ----------
st.subheader("Add single item")
c1, c2, c3 = st.columns(3)
with c1:
    gtin = st.text_input("GTIN")
with c2:
    batch = st.text_input("Batch")
with c3:
    expiry = st.text_input("Expiry (YYYY-MM-DD)")

if st.button("Validate & Add"):
    try:
        item = Item(gtin=gtin.strip(), batch=batch.strip(), expiry=expiry.strip())
        st.session_state.data.loc[len(st.session_state.data)] = [
            item.gtin, item.batch, item.expiry.isoformat()
        ]
        st.session_state.data.drop_duplicates(subset=COLUMNS, keep="last", inplace=True)
        st.success("Item added.")
    except ValidationError as ve:
        st.error("; ".join([e["msg"] for e in ve.errors()]))
    except Exception as e:
        st.error(str(e))

# ---------- Table & actions ----------
st.subheader(f"Items ({len(st.session_state.data)})")
st.dataframe(st.session_state.data, use_container_width=True)

csv_bytes = st.session_state.data.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_bytes, file_name="items.csv", mime="text/csv")
