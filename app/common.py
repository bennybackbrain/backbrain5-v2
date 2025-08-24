"""
common.py – zentrale Einstellungen und Hilfsfunktionen
-----------------------------------------------------

Diese Version ist für PUBLIC MODE gedacht.
- Auth ist deaktiviert
- Custom GPT kann ohne Token zugreifen
- Unbekannte ENV Variablen werden ignoriert
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Hauptpfade
    inbox_dir: str = "BACKBRAIN5.2_V2/01_inbox"
    summaries_dir: str = "BACKBRAIN5.2_V2/summaries"

    # Flags
    enable_public_alias: bool = True
    auto_summary_on_write: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"   # <<< sorgt dafür, dass zusätzliche ENV Variablen kein Fehler sind


settings = Settings()


def _maybe_check_api_secret(request=None) -> None:
    """
    PUBLIC MODE: Auth-Check ist deaktiviert.
    Alle Requests werden durchgelassen.
    """
    return
