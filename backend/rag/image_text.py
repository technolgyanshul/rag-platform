from pathlib import Path


def extract_image_text(file_path: str) -> str:
    path = Path(file_path)
    return f"Image upload: {path.name}. OCR/caption extraction placeholder text for MVP retrieval."
