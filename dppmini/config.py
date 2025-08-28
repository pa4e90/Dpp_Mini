from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cfg(path: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            merged = defaults.copy()
            merged.update({k: data[k] for k in data if k in defaults})
            return merged
        except Exception:
            pass
    return defaults.copy()


def save_cfg(path: Path, cfg: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        # best-effort; don't crash the UI on FS errors
        pass
