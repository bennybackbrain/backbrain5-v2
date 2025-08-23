from webdav3.client import Client
from typing import List
from .common import settings
import posixpath, io

def _client() -> Client:
    options = {
        "webdav_hostname": settings.webdav_url,
        "webdav_login": settings.webdav_username,
        "webdav_password": settings.webdav_password,
        "disable_check": True,
        "verbose": False,
    }
    return Client(options)

def _norm(*parts: str) -> str:
    # Sichere POSIX-Pfade ohne Traversal
    p = posixpath.join(*parts).replace("\\","/")
    if ".." in p:
        raise ValueError("Illegal path traversal")
    return p

def ensure_dir(path: str):
    c = _client()
    segs = [s for s in path.strip("/").split("/") if s]
    cur = ""
    for s in segs:
        cur = _norm(cur, s)
        if not c.check(cur):
            c.mkdir(cur)

def write_text(kind: str, name: str, content: str):
    base = settings.inbox_dir if kind == "entries" else settings.summaries_dir
    target = _norm(base, name)
    dirpath = posixpath.dirname(target)
    ensure_dir(dirpath)
    c = _client()
    data = io.BytesIO(content.encode("utf-8"))
    c.upload_to(data, target)

def read_text(kind: str, name: str) -> str:
    base = settings.inbox_dir if kind == "entries" else settings.summaries_dir
    target = _norm(base, name)
    c = _client()
    if not c.check(target):
        raise FileNotFoundError(name)
    bio = io.BytesIO()
    c.download_from(bio, target)
    return bio.getvalue().decode("utf-8")

def list_names(kind: str, limit: int = 200) -> List[str]:
    base = settings.inbox_dir if kind == "entries" else settings.summaries_dir
    c = _client()
    if not c.check(base):
        return []
    # list() liefert volle Pfade → nur Basename zurückgeben
    items = c.list(base)
    out = []
    for it in items:
        if it.endswith("/"):  # Ordner überspringen
            continue
        out.append(it.split("/")[-1])
    return sorted(out)[:limit]
