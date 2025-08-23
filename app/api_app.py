from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
import os
from .common import settings
from .webdav_io import write_text, read_text, list_names
import posixpath

app = FastAPI(title="Backbrain API", version="5.2.v3")

@app.get("/health")
def health():
    return {
        'status': 'ok',
        'public': bool(settings.enable_public_alias),
        'auth': bool(os.getenv('API_SECRET') or settings.api_secret),
    }

class WriteReq(BaseModel):
    kind: str = Field(pattern="^(entries|summaries)$")
    # Beide akzeptieren: 'name' ODER 'filename'
    name: str | None = None
    filename: str | None = None
    content: str

@app.post("/write-file")
def write_file(req: WriteReq, request: Request):
    # optionaler Header-Auth
    if settings.api_secret and request.headers.get("x-api-secret") != settings.api_secret:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Api-Secret")

    try:
        fname = req.filename or req.name
        if not fname:
            raise HTTPException(status_code=422, detail="Either 'filename' or 'name' is required")
        write_text(req.kind, fname, req.content)

        base = settings.inbox_dir if req.kind == "entries" else settings.summaries_dir
        path = posixpath.join(base, fname)

        summary = None
        if getattr(settings, "auto_summary_on_write", False) and req.kind == "entries":
            # Platzhalter für spätere Auto-Summary
            pass

        # Einheitliche Antwort (Render-Stil + etwas extra)
        return {
            "ok": True,
            "path": path,
            "kind": req.kind,
            "filename": fname,
            "summary": summary,
            "error": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=400, detail=msg)

@app.get("/read-file")
def read_file(
    kind: str = Query(..., pattern="^(entries|summaries)$"),
    name: str | None = Query(None),
    filename: str | None = Query(None),
):
    try:
        fname = filename or name
        if not fname:
            raise HTTPException(status_code=422, detail="Either 'filename' or 'name' is required")
        content = read_text(kind, fname)
        # Einheitliche JSON-Antwort
        return {"filename": fname, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=400, detail=msg)

@app.get("/list-files")
def list_files(kind: str = Query(..., pattern="^(entries|summaries)$"), limit: int = 200):
    try:
        return {"files": list_names(kind, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Öffentliche Alias-Routen optional spiegeln (ohne Auth), wenn ENABLE_PUBLIC_ALIAS=true
if settings.enable_public_alias:
    from fastapi import APIRouter
    pub = APIRouter()
    @pub.get("/public/health")
    def p_health(): return health()
    @pub.get("/public/list-files")
    def p_list(kind: str, limit: int = 200): return list_files(kind, limit)
    @pub.get("/public/read-file")
    def p_read(kind: str, name: str | None = None, filename: str | None = None):
        return read_file(kind=kind, name=name, filename=filename)
    @pub.post("/public/write-file")
    def p_write(req: WriteReq): return write_file(req)
    app.include_router(pub)
