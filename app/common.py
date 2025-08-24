"""
common.py – zentrale Einstellungen und Hilfsfunktionen
-----------------------------------------------------

Diese Version ist für PUBLIC MODE gedacht.
Das heißt:
- KEIN Secret-Check
- Custom GPT kann ohne Token auf die API zugreifen
- Sämtliche Endpunkte sind offen, nur durch Render/Nextcloud abgesichert

Wenn später Auth gebraucht wird, kann _maybe_check_api_secret angepasst werden
(z.B. mit Header "X-Api-Secret" oder "Authorization: Bearer <token>").
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Hauptpfade (für Nextcloud / lokale Fallbacks)
    inbox_dir: str = "BACKBRAIN5.2_V2/01_inbox"
    summaries_dir: str = "BACKBRAIN5.2_V2/summaries"

    # Flags
    enable_public_alias: bool = True
    auto_summary_on_write: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def _maybe_check_api_secret(request=None) -> None:
    """
    PUBLIC MODE: Auth-Check ist deaktiviert.
    Alle Requests werden durchgelassen.
    """
    return
