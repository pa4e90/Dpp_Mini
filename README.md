# DPP Mini

Small Streamlit MVP for collecting items (GTIN, batch, expiry), validating GTIN check digits, uploading CSVs, and exporting data.  
Data is saved locally to `data/items.csv` (git-ignored).

---

## Quickstart

### 1) Create and activate virtualenv
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
# or:
# pip install streamlit pydantic pandas python-dotenv pytest
```

### 3) Run the app
```bash
streamlit run app.py
```
Open the printed URL (typically http://localhost:8501).

### 4) Run tests (optional)
```bash
pytest -q
```

---

## Sample CSV
```csv
gtin,batch,expiry
4006381333931,B123,2026-12-31
1212121212234,B999,2027-06-30
036000291452,BUPC,2026-01-01
```

---

## Usage

- Add single item: enter GTIN / Batch / Expiry → click **Validate & Add**.  
  GTIN is normalized (spaces/dashes removed) and validated by check digit.

- Upload CSV: use the sidebar to upload a file with columns `gtin,batch,expiry`.  
  Invalid rows are dropped; duplicates are removed; data is persisted to `data/items.csv`.

- Download: use **Download CSV** to export the full dataset.

---

## Features
- GTIN normalization (digits-only) + check-digit validation (EAN-8/12/13/14)
- CSV upload with normalization, invalid-row filtering, de-duplication
- Persistence to `data/items.csv`
- “Recently added” panel (last 3) and full table

---

## Project structure (example)
```
Dpp_Mini/
  app.py
  dppmini/
    __init__.py
    validators.py
  data/
    items.csv            # created at runtime; git-ignored
  test/
    conftest.py
    test_validators.py
  sample_items.csv
  requirements.txt
  .streamlit/
    config.toml          # optional
```

---

## Configuration (optional)
Disable the Streamlit usage prompt by creating `.streamlit/config.toml` with:
```toml
[browser]
gatherUsageStats = false
```

---

## Git ignore
```
data/*.csv
```
