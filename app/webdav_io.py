import os
import tempfile
from pathlib import Path
from typing import List

from app.common import settings

# Lokaler Daten-Root (Render: beschreibbar unter /opt/render/project/src)
DATA_ROOT = Path(os.environ.get("BB_DATA_ROOT", "/opt/render/project/src/BACKBRAIN")).resolve()

def _base_local(kind: str) -> Path:
    if kind == "entries":
        return DATA_ROOT / "entries"
    if kind == "summaries":
        return DATA_ROOT / "summaries"
    raise ValueError("kind must be 'entries' or 'summaries'")

def _dav_configured() -> bool:
    return bool(settings.webdav_url and settings.webdav_username and settings.webdav_password)

def _remote_dir(kind: str) -> str:
    # Ziel: <NC_TARGET_FOLDER>/<entries|summaries>
    base = settings.nc_target_folder or "BACKBRAIN"
    return f"{base.strip('/')}/{kind}"

def _remote_path(kind: str, filename: str) -> str:
    return f"/{_remote_dir(kind).strip('/')}/{filename}"

def _dav_client():
    from webdav3.client import Client
    options = {
        "webdav_hostname": settings.webdav_url,
        "webdav_login": settings.webdav_username,
        "webdav_password": settings.webdav_password,
        "disable_check": True,  # weniger HEAD-Checks
    }
    return Client(options)

def _ensure_remote_dir(cli, remote_dir: str) -> None:
    # erstellt z.B. /BACKBRAIN/entries
    parts = [p for p in remote_dir.strip("/").split("/") if p]
    path = ""
    for p in parts:
        path += "/" + p
        try:
            if not cli.check(path):
                cli.mkdir(path)
        except Exception:
            # wenn existiert -> egal
            pass

def write_text(kind: str, filename: str, content: str) -> None:
    if _dav_configured():
        try:
            cli = _dav_client()
            rdir = "/" + _remote_dir(kind).strip("/")
            _ensure_remote_dir(cli, rdir)
            # per Temp-Datei hochladen (stabiler als upload von Bytes)
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                cli.upload_sync(remote_path=_remote_path(kind, filename), local_path=tmp_path)
                return
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            print(f"[webdav_io] write_text: WebDAV failed ({e}), falling back to local)")

    # Fallback: lokal
    base = _base_local(kind)
    base.mkdir(parents=True, exist_ok=True)
    (base / filename).write_text(content, encoding="utf-8")

def read_text(kind: str, filename: str) -> str:
    if _dav_configured():
        try:
            cli = _dav_client()
            # lade remote in Tempdatei, dann lese
            with tempfile.NamedTemporaryFile("r", delete=False, encoding="utf-8") as tmp:
                tmp_path = tmp.name
            try:
                cli.download_sync(remote_path=_remote_path(kind, filename), local_path=tmp_path)
                return Path(tmp_path).read_text(encoding="utf-8")
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            print(f"[webdav_io] read_text: WebDAV failed ({e}), falling back to local)")

    # Fallback: lokal
    p = _base_local(kind) / filename
    return p.read_text(encoding="utf-8")

def list_names(kind: str, limit: int = 200) -> List[str]:
    if _dav_configured():
        try:
            cli = _dav_client()
            dir_path = "/" + _remote_dir(kind).strip("/")
            try:
                items = cli.listdir(dir_path)
            except Exception:
                return []
            names: List[str] = []
            for it in items:
                name = it.rsplit("/", 1)[-1]
                if not name or name.endswith("/"):
                    continue
                names.append(name)
            names.sort()
            return names[:limit]
        except Exception as e:
            print(f"[webdav_io] list_names: WebDAV failed ({e}), falling back to local)")

    # Fallback: lokal
    base = _base_local(kind)
    if not base.exists():
        return []
    names = sorted([p.name for p in base.iterdir() if p.is_file()])
    return names[:limit]
