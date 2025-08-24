import os
from fastapi import Request, HTTPException

API_SECRET = os.getenv("API_SECRET", "").strip()


def _maybe_check_api_secret(request: Request) -> None:
    """
    Prüft den API-Secret-Header.
    Akzeptiert sowohl `X-Api-Secret: <key>` als auch `Authorization: Bearer <key>`.
    """
    if not API_SECRET:
        # kein Secret gesetzt → alles erlauben
        return

    auth = request.headers.get("X-Api-Secret")

    if not auth:
        # Fallback: Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth = auth_header.split(" ", 1)[1]

    if auth != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
