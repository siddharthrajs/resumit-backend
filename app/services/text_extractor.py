import io
import logging
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract

logger = logging.getLogger(__name__)


def is_text_garbled(text: str) -> bool:
    """Check if extracted text appears garbled/corrupted."""
    if not text or len(text.strip()) < 50:
        return True

    # Count alphanumeric vs special characters
    alnum_count = sum(1 for c in text if c.isalnum())
    total_count = len(text.replace(" ", "").replace("\n", ""))

    if total_count == 0:
        return True

    # If less than 70% alphanumeric, likely garbled
    ratio = alnum_count / total_count
    return ratio < 0.7


def extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    """Extract text using pdfplumber (handles most font encodings)."""
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_with_ocr(pdf_bytes: bytes) -> str:
    """Extract text using OCR (Tesseract) - slower but reliable."""
    images = convert_from_bytes(pdf_bytes, dpi=300)
    text = ""
    for image in images:
        page_text = pytesseract.image_to_string(image)
        text += page_text + "\n"
    return text.strip()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using OCR.
    """
    # Force OCR for now - most reliable for varied PDFs
    print("[INFO] Using OCR extraction...")
    text = extract_with_ocr(pdf_bytes)
    print(f"[OCR] Text length: {len(text)}")
    print(f"[OCR] First 500 chars:\n{text[:500]}")
    return text
