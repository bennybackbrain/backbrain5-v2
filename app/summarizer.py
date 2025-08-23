import os, requests
from .common import settings

def _want_auto() -> bool:
    v = os.getenv("AUTO_SUMMARY_ON_WRITE", "")
    return bool(settings.__dict__.get("auto_summary_on_write")) or v.lower() in ("1","true","yes")

def summarize(text: str) -> str:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    model   = settings.summary_model or os.getenv("SUMMARY_MODEL") or "gpt-4o-mini"
    words   = settings.summary_words or int(os.getenv("SUMMARY_WORDS", "120"))
    if not api_key:
        return "[auto-summary disabled: missing OPENAI_API_KEY]"
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role":"system","content":"Fasse deutsch, sachlich und kurz zusammen."},
                {"role":"user","content": f"Bitte ~{words} Wörter:\n\n{text}"}
            ],
            "temperature": 0.2,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()
