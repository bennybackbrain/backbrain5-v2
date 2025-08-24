from typing import Optional
from pypdf import PdfReader
from io import BytesIO

def extract_text_from_pdf_bytes(data: bytes, max_pages: Optional[int]=None) -> str:
    """
    Extrahiert Text aus PDF-Bytes. max_pages=None = alle Seiten.
    """
    reader = PdfReader(BytesIO(data))
    pages = reader.pages
    out = []
    n = len(pages) if max_pages is None else min(len(pages), max_pages)
    for i in range(n):
        try:
            txt = pages[i].extract_text() or ""
        except Exception:
            txt = ""
        out.append(txt.strip())
    return "\n\n".join([t for t in out if t])
