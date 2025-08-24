from __future__ import annotations

from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Form, Request, APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import os
import posixpath
from pathlib import Path
from typing import List

# Projekt-Module
from app.common import settings  # enthält enable_public_alias, inbox_dir, summaries_dir, auto_summary_on_write etc.
from app.webdav_io import write_text, read_text, list_names  # synchron, WebDAV-gestützt
from app.summarizer import summarize  # nutzt OPENAI_API_KEY + SUMMARY_MODEL/WORDS aus ENV


app = FastAPI(title="Backbrain API", version="5.2.v3-clean")


# -----------------------------
# Utility & Security
# -----------------------------

def _auto_summary_enabled() -> bool:
    # ENV überschreibt Settings; akzeptiere 1/true/yes
    env = os.getenv("AUTO_SUMMARY_ON_WRITE", "").lower()
    if env in ("1", "true", "yes"):  # explizit an
        return True
    if env in ("0", "false", "no"):   # explizit aus
        return False
    return bool(getattr(settings, "auto_summary_on_write", False))


def _maybe_check_api_secret(request: Request) -> None:
    """Nur wenn ein Secret gesetzt ist, wird der Header verlangt.
    Public-Alias-Routen lassen wir unabhängig davon zu.
    """
    secret = os.getenv("API_SECRET") or getattr(settings, "api_secret", None)
    if not secret:
        return  # keine Auth erzwungen
    supplied = request.headers.get("X-Api-Secret")
    if supplied != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _summary_name(fname: str) -> str:
    stem = os.path.splitext(fname)[0]
    return f"{stem}_summary.md"


# -----------------------------
# Schemas
# -----------------------------

class WriteReq(BaseModel):
    kind: str = Field(pattern=r"^(entries|summaries)$")
    # akzeptiere 'name' ODER 'filename'
    name: str | None = None
    filename: str | None = None
    content: str


# -----------------------------
# Routes
# -----------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "public": bool(getattr(settings, "enable_public_alias", False)),
        "auth": bool(os.getenv("API_SECRET") or getattr(settings, "api_secret", None)),
    }


@app.post("/write-file")
def write_file(req: WriteReq, request: Request):
    _maybe_check_api_secret(request)

    fname = req.filename or req.name
    if not fname:
        raise HTTPException(status_code=422, detail="Either 'filename' or 'name' is required")

    try:
        # 1) Haupt-Write
        write_text(req.kind, fname, req.content)

        # 2) Pfad für Antwort bestimmen
        base = settings.inbox_dir if req.kind == "entries" else settings.summaries_dir
        path = posixpath.join(base, fname)

        # 3) Optional: Auto-Summary
        summary_text: str | None = None
        if _auto_summary_enabled() and req.kind == "entries":
            try:
                summary_text = summarize(req.content)
                sum_name = _summary_name(fname)
                write_text("summaries", sum_name, summary_text)
            except Exception as e:
                summary_text = f"[auto-summary failed: {type(e).__name__}]"

        return {
            "ok": True,
            "path": path,
            "kind": req.kind,
            "filename": fname,
            "summary": summary_text,
            "error": None,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/read-file")
def read_file(
    kind: str = Query(..., pattern=r"^(entries|summaries)$"),
    name: str | None = Query(None),
    filename: str | None = Query(None),
):
    fname = filename or name
    if not fname:
        raise HTTPException(status_code=422, detail="Either 'filename' or 'name' is required")

    try:
        content = read_text(kind, fname)
        return {"filename": fname, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=400, detail=msg)


@app.get("/list-files")
def list_files(kind: str = Query(..., pattern=r"^(entries|summaries)$"), limit: int = 200):
    try:
        files = list_names(kind, limit=limit)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/upload")
def upload(kind: str = Form(...), file: UploadFile = File(...), request: Request | None = None):
    if request is not None:
        _maybe_check_api_secret(request)

    # 1) Dateiinhalt lesen
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except Exception:
        content = raw.decode("latin-1", errors="replace")

    fname = file.filename

    # 2) Speichern
    write_text(kind, fname, content)

    # 3) Optional: Auto-Summary
    if _auto_summary_enabled() and kind == "entries":
        try:
            _sum = summarize(content)
            sum_name = _summary_name(fname)
            write_text("summaries", sum_name, _sum)
        except Exception as e:
            # Nur loggen – Request bleibt erfolgreich
            print(f"[auto-summary:/upload] failed for {fname}: {e}")

    return {"ok": True, "kind": kind, "filename": fname}


# -----------------------------
# Convenience / Public Alias
# -----------------------------

if getattr(settings, "enable_public_alias", False):
    pub = APIRouter()

    @pub.get("/public/health")
    def p_health():
        return health()

    @pub.get("/public/list-files")
    def p_list(kind: str, limit: int = 200):
        return list_files(kind, limit)

    @pub.get("/public/read-file")
    def p_read(kind: str, name: str | None = None, filename: str | None = None):
        return read_file(kind=kind, name=name, filename=filename)

    @pub.post("/public/write-file")
    def p_write(req: WriteReq, request: Request):
        return write_file(req, request)

    app.include_router(pub)


# -----------------------------
# Batch-Helper
# -----------------------------

@app.get("/get_all_summaries")
def get_all_summaries(limit: int = 1000):
    try:
        files = list_names("summaries", limit=limit)
        # Inhalte als einfache Liste laden (leichtgewichtig)
        out: List[str] = []
        for fn in files:
            try:
                out.append(read_text("summaries", fn))
            except Exception:
                pass
        return {"summaries": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/force-summarize")
def force_summarize(all: bool = True, limit: int = 2000):
    """Erzeugt für alle entries fehlende *_summary.md in summaries.
    """
    if not all:
        return {"ok": True, "created": 0}

    created = 0
    try:
        entries = list_names("entries", limit=limit)
        sum_set = set(list_names("summaries", limit=limit))
        for fn in entries:
            sum_name = _summary_name(fn)
            if sum_name in sum_set:
                continue
            try:
                text = read_text("entries", fn)
                s = summarize(text)
                write_text("summaries", sum_name, s)
                created += 1
            except Exception as e:
                print(f"[force-summarize] skip {fn}: {e}")
        return {"ok": True, "created": created}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Minimal UI
# -----------------------------

@app.get("/ui", include_in_schema=False)
def ui():
    return HTMLResponse(
        """<!doctype html>
<html><head><meta charset=utf-8><title>Backbrain Upload</title>
<style>
body{font-family:system-ui;padding:24px}
#drop{border:2px dashed #888;padding:40px;text-align:center;border-radius:12px}
#drop.drag{border-color:#000}
</style></head>
<body>
<h1>Drag & Drop Upload</h1>
<p>Ziehen Sie Dateien hierher. <code>kind</code> = <b>entries</b> oder <b>summaries</b>.</p>
<label>Kind: <select id="kind"><option>entries</option><option>summaries</option></select></label>
<div id="drop">Dateien hier ablegen…</div>
<pre id="out"></pre>
<script>
const drop=document.getElementById('drop'), out=document.getElementById('out'), kindSel=document.getElementById('kind');
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop', async ev=>{
  const files=[...ev.dataTransfer.files];
  out.textContent='';
  for(const f of files){
    const fd=new FormData(); fd.append('kind', kindSel.value); fd.append('file', f);
    const res=await fetch('/upload',{method:'POST',body:fd});
    out.textContent+= (await res.text()) + '\n';
  }
});
</script></body></html>"""
    )
