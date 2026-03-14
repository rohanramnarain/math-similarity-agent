"""OCR helper for the class demo.

This file provides a tiny wrapper that extracts text from an image path.
If OCR dependencies are missing or OCR fails, the function returns a clear error.
"""

from __future__ import annotations

import os
from pathlib import Path


def extract_text_from_image(image_path: str) -> tuple[str, str | None]:
    """Extract text from an image using pytesseract.

    Returns:
        A tuple of (text, error_message). If OCR succeeds, error_message is None.
    """
    path = Path(image_path)
    if not path.exists():
        return "", f"Image not found: {image_path}"

    try:
        import pytesseract
        from PIL import Image

        tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    except Exception as exc:  # Placeholder-friendly dependency guard.
        return "", f"OCR dependencies not available: {exc}"

    try:
        text = pytesseract.image_to_string(Image.open(path))
        text = text.strip()
        if not text:
            return "", "OCR produced empty text"
        return text, None
    except Exception as exc:
        return "", f"OCR failed: {exc}"
