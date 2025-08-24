# app/mini_agent.py
import os
from openai import OpenAI

MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
WORDS = int(os.getenv("SUMMARY_WORDS", "120"))

def summarize(text: str, words: int = WORDS) -> str:
    """
    Liefert eine Kurzfassung mit ~WORDS Wörtern.
    Fallback: erste Zeile gekürzt, falls kein OPENAI_API_KEY gesetzt ist.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return (text.strip().split("\n")[0])[: words * 6]

    client = OpenAI(api_key=api_key)
    prompt = f"Fasse den folgenden Text in etwa {words} Wörtern sachlich zusammen:\n\n{text}"
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
