import os

MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
WORDS = int(os.getenv("SUMMARY_WORDS", "120"))

def _fallback_summary(text: str, words: int) -> str:
    # sehr simple Fallback-Zusammenfassung (erste Zeile gekürzt)
    return (text.strip().split("\n")[0])[: words * 6]

def summarize(text: str, words: int = WORDS) -> str:
    """
    Liefert eine Kurzfassung mit ~WORDS Wörtern.
    - Nutzt OpenAI NUR, wenn OPENAI_API_KEY vorhanden ist UND das Paket verfügbar ist.
    - Fällt sonst auf eine einfache Heuristik zurück (kein externer Call).
    """
    if not text:
        return ""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_summary(text, words)

    try:
        # Import absichtlich hier drin, damit Build nicht scheitert, wenn openai nicht installiert ist.
        from openai import OpenAI  # type: ignore
    except Exception:
        return _fallback_summary(text, words)

    try:
        client = OpenAI(api_key=api_key)
        prompt = f"Fasse den folgenden Text in etwa {words} Wörtern sachlich zusammen:\n\n{text}"
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        # Wenn der API-Call fehlschlägt, nicht crashen – fallback
        return _fallback_summary(text, words)
