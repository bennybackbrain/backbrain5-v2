import os
from pathlib import Path
from typing import List
from app.common import settings

# Lokaler Daten-Root (Render: writeable unter /opt/render/project/src)
DATA_ROOT = Path(os.environ.get("BB_DATA_ROOT", "/opt/render/project/src/BACKBRAIN")).resolve()

def _base(kind: str) -> Path:
    if kind == "entries":
        return DATA_ROOT / "entries"
    if kind == "summaries":
        return DATA_ROOT / "summaries"
    raise ValueError("kind must be 'entries' or 'summaries'")

def write_text(kind: str, filename: str, content: str) -> None:
    base = _base(kind)
    base.mkdir(parents=True, exist_ok=True)
    (base / filename).write_text(content, encoding="utf-8")

def read_text(kind: str, filename: str) -> str:
    p = _base(kind) / filename
    return p.read_text(encoding="utf-8")

def list_names(kind: str, limit: int = 200) -> List[str]:
    base = _base(kind)
    if not base.exists():
        return []
    names = sorted([p.name for p in base.iterdir() if p.is_file()])
    return names[:limit]
