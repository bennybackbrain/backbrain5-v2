from typing import Optional
try:
    from fastapi import Request
except Exception:
    Request = None  # type: ignore

def _maybe_check_api_secret(request: Optional["Request"]=None) -> None:
    # Public mode: auth disabled
    return

class Settings:
    def __init__(self):
        # Feature flags
        self.enable_public_alias = True
        self.auto_summary_on_write = False

        # Local fallback paths (nur für Anzeige)
        self.inbox_dir = "BACKBRAIN/entries"
        self.summaries_dir = "BACKBRAIN/summaries"

        # WebDAV config (in Public mode ungenutzt, nur Attribute vorhanden)
        self.webdav_url = None
        self.webdav_username = None
        self.webdav_password = None
        self.nc_target_folder = "BACKBRAIN"

        # API secret disabled
        self.api_secret = None

settings = Settings()
