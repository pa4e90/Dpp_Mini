# dppmini/filters.py
from __future__ import annotations

import re
from datetime import date

import pandas as pd

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _parse_date(s: str | None) -> date | None:
    s = _norm(s)
    if not s or not _DATE_RE.match(s):
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def apply_filters(
    df: pd.DataFrame,
    gtin_contains: str | None = None,
    batch_contains: str | None = None,
    expiry_from: str | None = None,  # "YYYY-MM-DD"
    expiry_to: str | None = None,  # "YYYY-MM-DD"
) -> tuple[pd.DataFrame, dict]:
    """
    Returns (filtered_df, warnings_dict).
    warnings_dict has keys 'from' and/or 'to' when the date text is invalid.
    """
    res = df.copy()
    warns: dict[str, str] = {}

    # text filters
    if gtin_contains:
        q = _norm(gtin_contains)
        res = res[res["gtin"].str.contains(q, na=False)]
    if batch_contains:
        q = _norm(batch_contains)
        res = res[res["batch"].str.contains(q, case=False, na=False)]

    # date range on real dates
    if not res.empty:
        d = pd.to_datetime(res["expiry"], errors="coerce").dt.date

        d_from = _parse_date(expiry_from)
        d_to = _parse_date(expiry_to)

        if expiry_from and d_from is None:
            warns["from"] = "Use full date: YYYY-MM-DD"
        if expiry_to and d_to is None:
            warns["to"] = "Use full date: YYYY-MM-DD"

        if d_from is not None:
            res = res[d >= d_from]
            d = d[d >= d_from]  # keep aligned index
        if d_to is not None:
            res = res[d <= d_to]

    return res, warns
