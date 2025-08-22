from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import requests

app = FastAPI()

# ENV
WEBDAV_URL = os.getenv("WEBDAV_URL")
WEBDAV_USERNAME = os.getenv("WEBDAV_USERNAME")
WEBDAV_PASSWORD = os.getenv("WEBDAV_PASSWORD")
INBOX_DIR = "BACKBRAIN5.2_V2/01_inbox"
SUMMARIES_DIR = "BACKBRAIN5.2_V2/summaries"

# MODELS
class WriteFileRequest(BaseModel):
    filename: str
    content: str
    kind: Optional[str] = "entry"  # "entry" oder "summary"

class WriteFileResponse(BaseModel):
    ok: bool
    path: str

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

# ROUTES
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/write-file", response_model=WriteFileResponse)
def write_file(req: WriteFileRequest):
    path = webdav_write(req.kind, req.filename, req.content)
    return WriteFileResponse(ok=True, path=path)

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
