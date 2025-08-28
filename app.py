from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from pydantic import BaseModel, ValidationError, field_validator

from dppmini.config import load_cfg, save_cfg
from dppmini.dates import expiry_is_future_or_today
from dppmini.filters import apply_filters
from dppmini.validators import gtin_check_digit, gtin_is_valid, normalize_gtin

# ---------- Paths / constants ----------
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_PATH = DATA_DIR / "items.csv"
CFG_PATH = DATA_DIR / "config.json"
COLUMNS = ["gtin", "batch", "expiry", "created_at"]  # FIXED (underscore)
DEDUPE_KEYS = ["gtin", "batch", "expiry"]


# ---------- Helpers ----------
def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure required columns exist; fill missing created_at with now."""
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = now_iso() if c == "created_at" else ""
    return df[COLUMNS].astype(str)


def fix_gtin_if_possible(s: str) -> str | None:
    s = normalize_gtin(s)
    if len(s) in (7, 11, 12, 13):  # bodies
        body = s if len(s) in (7, 11, 12) else s[:-1]
        return body + str(gtin_check_digit(body))
    return s if gtin_is_valid(s) else None


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    buf.write("sep=,\n")  # <-- Excel hint to use comma
    df.to_csv(
        buf,
        index=False,
        columns=COLUMNS,  # fixed order: ["gtin","batch","expiry","created_at"]
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel


# ---------- Session init ----------
if "data" not in st.session_state:
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, dtype=str)
        st.session_state.data = ensure_columns(df)
    else:
        st.session_state.data = pd.DataFrame(columns=COLUMNS)

st.set_page_config(page_title="DPP Mini", layout="wide")
st.title("DPP Mini")

# ---------- Settings ----------
DEFAULT_CFG = {
    "auto_fix_gtin": False,
    "enforce_future_expiry": False,
}

if "cfg" not in st.session_state:
    st.session_state.cfg = load_cfg(CFG_PATH, DEFAULT_CFG)

with st.sidebar.expander("Settings", expanded=False):
    auto_fix = st.checkbox(
        "Auto-fix GTIN check digit",
        value=st.session_state.cfg["auto_fix_gtin"],
    )
    past_off = st.checkbox(
        "Disallow past expiry dates",
        value=st.session_state.cfg["enforce_future_expiry"],
    )
    if (
        auto_fix != st.session_state.cfg["auto_fix_gtin"]
        or past_off != st.session_state.cfg["enforce_future_expiry"]
    ):
        st.session_state.cfg["auto_fix_gtin"] = auto_fix
        st.session_state.cfg["enforce_future_expiry"] = past_off
        save_cfg(CFG_PATH, st.session_state.cfg)


# ---------- Filters ----------
with st.sidebar.expander("Filters", expanded=False):
    if "filters" not in st.session_state:
        st.session_state.filters = {"gtin": "", "batch": "", "from": "", "to": ""}

    st.session_state.filters["gtin"] = st.text_input(
        "GTIN contains",
        st.session_state.filters["gtin"],
    )
    st.session_state.filters["batch"] = st.text_input(
        "Batch contains",
        st.session_state.filters["batch"],
    )
    c_from, c_to = st.columns(2)
    with c_from:
        st.session_state.filters["from"] = st.text_input(
            "Expiry from (YYYY-MM-DD)",
            st.session_state.filters["from"],
        )
    with c_to:
        st.session_state.filters["to"] = st.text_input(
            "Expiry to (YYYY-MM-DD)",
            st.session_state.filters["to"],
        )

    if st.button("Clear filters"):
        st.session_state.filters = {"gtin": "", "batch": "", "from": "", "to": ""}
        st.rerun()


# ---------- Validation model ----------
class Item(BaseModel):
    gtin: str
    batch: str
    expiry: date  # YYYY-MM-DD

    @field_validator("gtin")
    @classmethod
    def validate_gtin(cls, v: str) -> str:
        v = normalize_gtin(v)
        if not gtin_is_valid(v):
            raise ValueError("Invalid GTIN (must be 8/12/13/14 digits with correct check digit).")
        return v

    @field_validator("batch")  # FIXED: decorator was missing
    @classmethod
    def validate_batch(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Batch is required.")
        return v


# ---------- Sidebar upload ----------
st.sidebar.header("Upload CSV (optional)")
file = st.sidebar.file_uploader("CSV with gtin,batch,expiry", type=["csv"])
if file is not None:
    try:
        up = pd.read_csv(file, dtype=str)
        missing = [c for c in ["gtin", "batch", "expiry"] if c not in up.columns]
        if missing:
            st.sidebar.error(f"Missing columns: {missing}")
        else:
            up["gtin"] = up["gtin"].astype(str).map(normalize_gtin)
            mask_gtin = up["gtin"].map(gtin_is_valid)
            dropped_gtin = int((~mask_gtin).sum())

            if st.session_state.cfg["enforce_future_expiry"]:
                exp_ok = up["expiry"].astype(str).map(expiry_is_future_or_today)
                dropped_exp = int((~exp_ok).sum())
                mask = mask_gtin & exp_ok
            else:
                dropped_exp = 0
                mask = mask_gtin

            up = up.loc[mask, ["gtin", "batch", "expiry"]].copy()
            up["created_at"] = now_iso()

            before = len(st.session_state.data)
            st.session_state.data = pd.concat(
                [st.session_state.data, ensure_columns(up)], ignore_index=True
            ).drop_duplicates(subset=DEDUPE_KEYS, keep="last")
            added = len(st.session_state.data) - before
            st.session_state.data.to_csv(DATA_PATH, index=False)

            st.sidebar.success(f"Loaded {len(up)} valid rows (added: {added}).")
            if dropped_gtin or dropped_exp:
                parts = []
                if dropped_gtin:
                    parts.append(f"invalid GTIN: {dropped_gtin}")
                if dropped_exp:
                    parts.append(f"past expiry: {dropped_exp}")
                st.sidebar.warning("Dropped rows → " + ", ".join(parts))
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
        norm = normalize_gtin(gtin)
        if st.session_state.cfg["auto_fix_gtin"]:
            maybe = fix_gtin_if_possible(norm)
            if maybe:
                norm = maybe

        item = Item(gtin=norm, batch=batch, expiry=expiry.strip())

        if st.session_state.cfg["enforce_future_expiry"] and not expiry_is_future_or_today(
            item.expiry.isoformat()
        ):
            st.error("Expiry is in the past and 'Disallow past expiry dates' is ON.")
        else:
            st.session_state.data.loc[len(st.session_state.data)] = [
                item.gtin,
                item.batch,
                item.expiry.isoformat(),
                now_iso(),
            ]
            st.session_state.data.drop_duplicates(subset=DEDUPE_KEYS, keep="last", inplace=True)
            st.session_state.data.to_csv(DATA_PATH, index=False)
            st.success("Item added.")
    except ValidationError as ve:
        st.error("; ".join([e["msg"] for e in ve.errors()]))
    except Exception as e:
        st.error(str(e))

# ---------- Table & actions ----------
df_view, filter_warns = apply_filters(
    st.session_state.data,
    gtin_contains=st.session_state.filters["gtin"],
    batch_contains=st.session_state.filters["batch"],
    expiry_from=st.session_state.filters["from"],
    expiry_to=st.session_state.filters["to"],
)

# show any date warnings in the sidebar (non-blocking)
if filter_warns.get("from"):
    st.sidebar.warning(f"Expiry from: {filter_warns['from']}")
if filter_warns.get("to"):
    st.sidebar.warning(f"Expiry to: {filter_warns['to']}")

df_sorted = df_view.copy()
if not df_sorted.empty:
    df_sorted["created_at_dt"] = pd.to_datetime(df_sorted["created_at"], errors="coerce")
    df_sorted.sort_values("created_at_dt", ascending=False, inplace=True)
    df_sorted.drop(columns=["created_at_dt"], inplace=True)

recent = df_sorted.head(3)
with st.expander(f"Recently added (last {len(recent)})", expanded=True):
    view = recent if len(recent) else pd.DataFrame(columns=COLUMNS)
    st.dataframe(view, use_container_width=True, height=160)

st.subheader(f"All items ({len(df_sorted)})")
st.dataframe(df_sorted, use_container_width=True)

# Export (full dataset)
csv_bytes = dataframe_to_csv_bytes(df_sorted)
st.download_button("Download CSV", data=csv_bytes, file_name="items.csv", mime="text/csv")
# ---------- Edit rows ----------
st.markdown("### Edit rows")
enable_edit = st.checkbox("Enable edit mode", value=False, key="edit_mode")

if enable_edit and not df_sorted.empty:
    # Select a row to edit (show a friendly label)
    options = []
    for i, r in df_sorted.iterrows():
        label = f"{r['gtin']} | {r['batch']} | {r['expiry']} | {r['created_at']}"
        options.append((label, i))
    labels = [o[0] for o in options]
    idx_map = {o[0]: o[1] for o in options}

    selected_label = st.selectbox("Choose a row", labels)
    row = df_sorted.loc[idx_map[selected_label]]

    # Editor inputs
    # Editor inputs
    e1, e2, e3 = st.columns(3)

    with e1:
        new_gtin = st.text_input(
            "GTIN (edit)",
            row["gtin"],
            key=f"edit-gtin-{row['created_at']}",
        )

    with e2:
        new_batch = st.text_input(
            "Batch (edit)",
            row["batch"],
            key=f"edit-batch-{row['created_at']}",
        )

    with e3:
        new_expiry = st.text_input(
            "Expiry (edit, YYYY-MM-DD)",
            row["expiry"],
            key=f"edit-expiry-{row['created_at']}",
        )

    if st.button("Save changes", type="primary"):
        try:
            norm = normalize_gtin(new_gtin)
            if st.session_state.cfg["auto_fix_gtin"]:
                maybe = fix_gtin_if_possible(norm)
                if maybe:
                    norm = maybe

            item = Item(gtin=norm, batch=new_batch, expiry=new_expiry.strip())

            if st.session_state.cfg["enforce_future_expiry"] and not expiry_is_future_or_today(
                item.expiry.isoformat()
            ):
                st.error("Expiry is in the past and 'Disallow past expiry dates' is ON.")
            else:
                mask = st.session_state.data["created_at"] == row["created_at"]
                st.session_state.data.loc[mask, ["gtin", "batch", "expiry"]] = [
                    item.gtin,
                    item.batch,
                    item.expiry.isoformat(),
                ]
                st.session_state.data = st.session_state.data.drop_duplicates(
                    subset=DEDUPE_KEYS, keep="last"
                ).reset_index(drop=True)
                st.session_state.data.to_csv(DATA_PATH, index=False)
                st.success("Row updated.")
                st.rerun()
        except ValidationError as ve:
            st.error("; ".join([e["msg"] for e in ve.errors()]))
        except Exception as e:
            st.error(str(e))

# ---------- Delete rows ----------
st.markdown("### Delete rows")
st.caption("Enable delete mode to remove a row permanently.")
enable_delete = st.checkbox("Enable delete mode", value=False)

if enable_delete and not df_sorted.empty:
    for i, row in df_sorted.iterrows():
        cols = st.columns([5, 2])
        with cols[0]:
            st.write(
                f"{row['gtin']}  |  {row['batch']}  |  {row['expiry']}  |  {row['created_at']}"
            )
        with cols[1]:
            if st.button("🗑️ Delete", key=f"del-{i}"):
                idx = st.session_state.data.index[
                    (st.session_state.data["gtin"] == row["gtin"])
                    & (st.session_state.data["batch"] == row["batch"])
                    & (st.session_state.data["expiry"] == row["expiry"])
                    & (st.session_state.data["created_at"] == row["created_at"])
                ]
                if len(idx):
                    st.session_state.data.drop(index=idx[0], inplace=True)
                    st.session_state.data.reset_index(drop=True, inplace=True)
                    st.session_state.data.to_csv(DATA_PATH, index=False)
                    st.success("Row deleted.")
                    st.rerun()
