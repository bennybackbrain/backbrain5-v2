from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from .common import settings
from .webdav_io import write_text, read_text, list_names

app = FastAPI(title="Backbrain API", version="5.2.v2")

@app.get("/health")
def health():
    return {"status":"ok","public": bool(settings.enable_public_alias)}

class WriteReq(BaseModel):
    kind: str = Field(pattern="^(entries|summaries)$")
    name: str
    content: str

@app.post("/write-file")
def write_file(req: WriteReq):
    try:
        write_text(req.kind, req.name, req.content)
        if getattr(settings,"auto_summary_on_write", False) and req.kind == "entries":
            # Platzhalter: echte Auto-Summary kann später hier rein
            pass
        return {"status":"created","kind":req.kind,"name":req.name}
    except Exception as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=400, detail=msg)

@app.get("/read-file")
def read_file(name: str = Query(...), kind: str = Query(..., pattern="^(entries|summaries)$")):
    try:
        content = read_text(kind, name)
        return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
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
    @pub.get("/public/health")       # GET
    def p_health(): return health()
    @pub.get("/public/list-files")   # GET
    def p_list(kind: str, limit: int = 200): return list_files(kind, limit)
    @pub.get("/public/read-file")    # GET
    def p_read(name: str, kind: str): return read_file(name, kind)
    @pub.post("/public/write-file")  # POST
    def p_write(req: WriteReq): return write_file(req)
    app.include_router(pub)
