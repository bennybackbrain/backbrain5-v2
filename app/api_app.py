from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Form, Request
from pydantic import BaseModel, Field
import os
from app.common import settings
from app.webdav_io import write_text, read_text, list_names
from app.summarizer import summarize
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
    _secret = os.getenv("API_SECRET") or settings.api_secret

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


@app.post("/upload")
def upload(kind: str = Form(...), file: UploadFile = File(...), request: Request = None):
    _secret = os.getenv('API_SECRET') or settings.api_secret
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except Exception:
        content = raw.decode("latin-1", errors="replace")
    fname = file.filename
    write_text(kind, fname, content)
    _auto = (os.getenv('AUTO_SUMMARY_ON_WRITE','').lower() in ('1','true','yes')) or getattr(settings,'auto_summary_on_write', False)
    if _auto and kind == "entries":
        try:
            _sum = summarize(content)
        except Exception as e:
            _sum = f"[auto-summary failed: {type(e).__name__}]"
        write_text("summaries", fname, _sum)
    return {"ok": True, "kind": kind, "filename": fname}


from fastapi.responses import HTMLResponse

@app.get("/ui", include_in_schema=False)
def ui():
    return HTMLResponse("""<!doctype html>
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
</script></body></html>""")
