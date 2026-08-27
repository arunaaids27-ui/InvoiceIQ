"""
Invoice Preprocessing Module

Handles loading invoice files (PDF, PNG, JPG, JPEG)
and converting them into PIL Image objects.

No OCR or VLM here.
Only file -> image conversion.
"""

import os
import io
from typing import List

import fitz  # PyMuPDF
from PIL import Image


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


class InvoicePreprocessingError(Exception):
    """Raised when an invoice file cannot be read or converted."""
    pass


def validate_file(file_path: str) -> str:
    """Check whether the invoice file exists and is supported."""

    if not os.path.isfile(file_path):
        raise InvoicePreprocessingError(
            f"File not found: {file_path}"
        )

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise InvoicePreprocessingError(
            f"Unsupported file type: {ext}"
        )

    return ext


def convert_pdf_to_images(
    file_path: str,
    dpi: int = 200
) -> List[Image.Image]:
    """Convert every PDF page into a PIL Image."""

    images = []

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise InvoicePreprocessingError(
            f"Failed to open PDF: {e}"
        )

    try:
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page_index in range(len(doc)):
            page = doc[page_index]

            pix = page.get_pixmap(matrix=matrix)

            img_bytes = pix.tobytes("png")

            image = Image.open(
                io.BytesIO(img_bytes)
            ).convert("RGB")

            images.append(image)

    except Exception as e:
        raise InvoicePreprocessingError(
            f"Failed to render PDF pages: {e}"
        )

    finally:
        doc.close()

    if not images:
        raise InvoicePreprocessingError(
            "PDF contained no pages."
        )

    return images


def load_image_file(
    file_path: str
) -> List[Image.Image]:
    """Load JPG/PNG invoice as a PIL Image."""

    try:
        image = Image.open(file_path)
        image = image.convert("RGB")

    except Exception as e:
        raise InvoicePreprocessingError(
            f"Failed to open image: {e}"
        )

    return [image]


def preprocess_invoice(
    file_path: str,
    dpi: int = 200
) -> List[Image.Image]:
    """
    Main preprocessing function.

    PDF  -> multiple PIL Images
    JPG/PNG -> one PIL Image
    """

    ext = validate_file(file_path)

    if ext == ".pdf":
        return convert_pdf_to_images(
            file_path,
            dpi=dpi
        )

    return load_image_file(file_path)


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    test_path = "sample_invoice.jpg"

    try:
        pages = preprocess_invoice(test_path)

        print(
            f"Successfully processed "
            f"{len(pages)} image(s)."
        )

        for i, img in enumerate(pages):
            print(
                f"Image {i + 1}: "
                f"size={img.size}, "
                f"mode={img.mode}"
            )

    except InvoicePreprocessingError as e:
        print(f"Error: {e}")