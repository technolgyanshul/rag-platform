from __future__ import annotations

from pathlib import Path


def extract_image_text(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract and Pillow are required for image OCR. "
            "Install with: pip install pytesseract Pillow  "
            "and ensure tesseract-ocr is installed on the system."
        ) from exc

    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract binary not found. Install it with: "
            "apt install tesseract-ocr  (Ubuntu/Debian) or brew install tesseract (macOS)."
        ) from exc

    image = Image.open(file_path)
    text = pytesseract.image_to_string(image).strip()
    if not text:
        return f"[No text detected in image: {Path(file_path).name}]"
    return text
