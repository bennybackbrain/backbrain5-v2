# Backbrain 5.2 V2 – Render Deploy

1) Verbinde dieses Repo in Render als **Web Service**.
2) Verwende die bereits gesetzten ENV-Variablen im Dashboard (Key/Value), keine Secrets im YAML.
3) StartCommand: `uvicorn app.api_app:app --host 0.0.0.0 --port 10000`
4) Health-Check: GET `/health`
5) Alias (optional): `/public/*` wenn `ENABLE_PUBLIC_ALIAS=true`.

**API:**
- `GET  /health`
- `GET  /list-files?kind=entries|summaries&limit=200`
- `GET  /read-file?kind=entries|summaries&name=<file>`
- `POST /write-file`  JSON: `{ "kind":"entries|summaries", "name":"x.md", "content":"..." }`
