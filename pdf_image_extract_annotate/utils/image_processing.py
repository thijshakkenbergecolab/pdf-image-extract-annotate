"""
Image processing utilities for PDF image extraction.
"""

import logging
from pymupdf import Document, Pixmap, csRGB

from ..models import ImageMetadata, ExtractedImageData

logger = logging.getLogger(__name__)


def handle_alpha_channel(pix: Pixmap) -> Pixmap:
    """
    Remove alpha channel from a pixmap if present.

    Args:
        pix: Input pixmap

    Returns:
        Pixmap without alpha channel
    """
    if pix.alpha:
        return Pixmap(pix, 0)
    return pix


def recover_pixmap(doc: Document, img_metadata: ImageMetadata) -> ExtractedImageData:
    """
    Recover image data from PDF, handling special cases like SMask and ColorSpace.

    This is based on the recoverpix function from PyMuPDF utilities.

    Args:
        doc: PDF document object
        img_metadata: Metadata about the image to extract

    Returns:
        ExtractedImageData containing the image bytes and metadata
    """
    xref = img_metadata.xref
    smask = img_metadata.smask

    # Special case: /SMask or /Mask exists
    if smask > 0:
        pix0 = Pixmap(doc.extract_image(xref)["image"])
        pix0 = handle_alpha_channel(pix0)
        mask = Pixmap(doc.extract_image(smask)["image"])

        try:
            pix = Pixmap(pix0, mask)
        except Exception as e:
            # Fallback to original base image in case of problems
            logger.error(
                f"Error combining pixmap with mask for xref {xref}: {e}. Using base image only."
            )
            pix = Pixmap(doc.extract_image(xref)["image"])

        ext = "pam" if pix0.n > 3 else "png"

        return ExtractedImageData(
            ext=ext, colorspace=pix.colorspace.n, image=pix.tobytes(ext)
        )

    # Special case: /ColorSpace definition exists
    # Convert these cases to RGB PNG images to be safe
    if "/ColorSpace" in doc.xref_object(xref, compressed=True):
        pix = Pixmap(doc, xref)
        pix = Pixmap(csRGB, pix)
        return ExtractedImageData(ext="png", colorspace=3, image=pix.tobytes("png"))

    # Normal case: extract image directly
    extracted = doc.extract_image(xref)
    return ExtractedImageData(
        ext=extracted["ext"],
        colorspace=extracted["colorspace"],
        image=extracted["image"],
    )