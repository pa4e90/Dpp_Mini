import streamlit as st
import pandas as pd
from datetime import date
from pydantic import BaseModel, field_validator, ValidationError
from pathlib import Path
from dppmini.validators import normalize_gtin, gtin_is_valid, gtin_check_digit

# ✅ ensure data dir exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_PATH = DATA_DIR / "items.csv"

COLUMNS = ["gtin", "batch", "expiry"]

# ✅ init session state once
if "data" not in st.session_state:
    if DATA_PATH.exists():
        st.session_state.data = pd.read_csv(DATA_PATH, dtype=str)
    else:
        st.session_state.data = pd.DataFrame(columns=COLUMNS)

st.set_page_config(page_title="DPP Mini", layout="wide")
st.title("DPP Mini")

# ---------- helpers ----------
def normalize_gtin(s: str) -> str:                         # ✅ NEW (TOP-LEVEL)
    """Keep only digits; trims spaces/dashes/etc."""
    return "".join(ch for ch in s.strip() if ch.isdigit())

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
        v = normalize_gtin(v)                               # ✅ CHANGED (normalize first)
        if not gtin_is_valid(v):
            raise ValueError("Invalid GTIN (must be 8/12/13/14 digits with correct check digit).")
        return v                                            # normalized + validated

# ---------- Sidebar upload ----------
st.sidebar.header("Upload CSV (optional)")
file = st.sidebar.file_uploader("CSV with gtin,batch,expiry", type=["csv"])
if file is not None:
    try:
        up = pd.read_csv(file, dtype=str)
        up["gtin"] = up["gtin"].astype(str).map(normalize_gtin)
        mask = up["gtin"].map(gtin_is_valid)
        dropped = int((~mask).sum())
        up = up.loc[mask, COLUMNS]
        if dropped:
            st.sidebar.warning(f"Dropped {dropped} rows with invalid GTINs.")
        missing = [c for c in COLUMNS if c not in up.columns]
        if missing:
            st.sidebar.error(f"Missing columns: {missing}")
        else:
            # ✅ NEW: normalize and (optionally) drop invalid rows
            up["gtin"] = up["gtin"].astype(str).map(normalize_gtin)    # ✅ NEW
            mask = up["gtin"].map(gtin_is_valid)                       # ✅ NEW
            dropped = int((~mask).sum())
            up = up.loc[mask, COLUMNS]
            if dropped:
                st.sidebar.warning(f"Dropped {dropped} rows with invalid GTINs.")
            st.session_state.data = (
                pd.concat([st.session_state.data, up], ignore_index=True)
                  .drop_duplicates(subset=COLUMNS, keep="last")
            )
            st.sidebar.success(f"Loaded {len(up)} rows.")
            st.session_state.data.to_csv(DATA_PATH, index=False)       # persist after upload
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
        # ✅ CHANGED: pass raw; validator will normalize+validate
        item = Item(gtin=gtin, batch=batch.strip(), expiry=expiry.strip())
        st.session_state.data.loc[len(st.session_state.data)] = [
            item.gtin, item.batch, item.expiry.isoformat()
        ]
        st.session_state.data.drop_duplicates(subset=COLUMNS, keep="last", inplace=True)
        st.success("Item added.")
        st.session_state.data.to_csv(DATA_PATH, index=False)  # persist after add
    except ValidationError as ve:
        st.error("; ".join([e["msg"] for e in ve.errors()]))
    except Exception as e:
        st.error(str(e))

# ---------- Table & actions ----------
# Recent 3 panel (compact view)
recent = st.session_state.data.tail(3)  # last 3 rows
with st.expander(f"Recently added (last {len(recent)})", expanded=True):
    # show empty columns if there are no rows yet
    recent_view = recent if len(recent) else pd.DataFrame(columns=COLUMNS)
    st.dataframe(recent_view, use_container_width=True, height=160)

# Full table
st.subheader(f"All items ({len(st.session_state.data)})")
st.dataframe(st.session_state.data, use_container_width=True)

# Export (full dataset)
csv_bytes = st.session_state.data.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_bytes, file_name="items.csv", mime="text/csv")