from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import requests
import logging
from fastapi.responses import JSONResponse

app = FastAPI()

# ENV
WEBDAV_URL = os.getenv("WEBDAV_URL")
WEBDAV_USERNAME = os.getenv("WEBDAV_USERNAME")
WEBDAV_PASSWORD = os.getenv("WEBDAV_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "gpt-4.1.1")
INBOX_DIR = "BACKBRAIN5.2_V2/01_inbox"
SUMMARIES_DIR = "BACKBRAIN5.2_V2/summaries"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backbrain5-v2")

# MODELS
class WriteFileRequest(BaseModel):
    filename: str
    content: str
    kind: Optional[str] = "entry"  # "entry" oder "summary"

class WriteFileResponse(BaseModel):
    ok: bool
    path: str
    summary: Optional[str] = None
    error: Optional[str] = None

class ReadFileResponse(BaseModel):
    filename: str
    content: str

class ListFilesResponse(BaseModel):
    files: List[str]

class SummariesResponse(BaseModel):
    summaries: List[str]

# HELPERS

def webdav_path(kind: str, filename: str) -> str:
    if kind == "summary":
        return f"{SUMMARIES_DIR}/{filename}"
    return f"{INBOX_DIR}/{filename}"

def webdav_list(kind: str) -> List[str]:
    folder = SUMMARIES_DIR if kind == "summary" else INBOX_DIR
    url = f"{WEBDAV_URL}/{folder}/"
    resp = requests.request("PROPFIND", url, auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD), headers={"Depth": "1"})
    if resp.status_code not in (207, 200):
        raise HTTPException(status_code=502, detail=f"WebDAV list failed: {resp.status_code}")
    # Minimal XML parsing
    from xml.etree import ElementTree as ET
    tree = ET.fromstring(resp.text)
    files = []
    for resp_elem in tree.findall(".//{DAV:}response"):
        href = resp_elem.find("{DAV:}href")
        if href is not None:
            name = href.text.split("/")[-1]
            if name and name not in ("01_inbox", "summaries", ""):
                files.append(name)
    return files

def webdav_read(kind: str, filename: str) -> str:
    path = webdav_path(kind, filename)
    url = f"{WEBDAV_URL}/{path}"
    resp = requests.get(url, auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD))
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="File not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"WebDAV read failed: {resp.status_code}")
    return resp.text

def webdav_write(kind: str, filename: str, content: str) -> str:
    path = webdav_path(kind, filename)
    url = f"{WEBDAV_URL}/{path}"
    resp = requests.put(url, data=content.encode("utf-8"), auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD))
    if resp.status_code not in (200, 201, 204):
        raise HTTPException(status_code=502, detail=f"WebDAV write failed: {resp.status_code}")
    return path

def generate_summary(text: str) -> str:
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY set, using dummy summary.")
        return f"[Summary] {text[:50]}..."
    import requests
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Fasse folgenden Text prägnant zusammen:\n---\n{text}\n---"
    data = {
        "model": SUMMARIZER_MODEL,
        "messages": [
            {"role": "system", "content": "Du bist ein prägnanter deutscher Textzusammenfasser."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 256
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        summary = result["choices"][0]["message"]["content"].strip()
        return summary
    except Exception as e:
        logger.error(f"GPT-API error: {e}")
        return f"[Summary-Error] {str(e)}"

# ROUTES
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/write-file", response_model=WriteFileResponse)
def write_file(req: WriteFileRequest):
    try:
        path = webdav_write(req.kind, req.filename, req.content)
        logger.info(f"File written: {path}")
        summary_text = None
        if req.kind == "entry":
            summary_text = generate_summary(req.content)
            summary_name = req.filename.replace('.txt', '_summary.txt')
            try:
                summary_path = webdav_write("summary", summary_name, summary_text)
                logger.info(f"Summary written: {summary_path}")
            except Exception as e:
                logger.error(f"Summary write failed: {e}")
        return WriteFileResponse(ok=True, path=path, summary=summary_text)
    except HTTPException as e:
        logger.error(f"Write error: {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"ok": False, "error": e.detail})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.get("/read-file", response_model=ReadFileResponse)
def read_file(filename: str, kind: Optional[str] = "entry"):
    content = webdav_read(kind, filename)
    return ReadFileResponse(filename=filename, content=content)

@app.get("/list-files", response_model=ListFilesResponse)
def list_files(kind: Optional[str] = "entry"):
    files = webdav_list(kind)
    return ListFilesResponse(files=files)

@app.get("/get_all_summaries", response_model=SummariesResponse)
def get_all_summaries():
    files = webdav_list("summary")
    return SummariesResponse(summaries=files)
