"""
PDF document utilities.
"""

import logging
from typing import List, Tuple
from pymupdf import Document

logger = logging.getLogger(__name__)


def get_pdf_page_count(doc: Document) -> int:
    """
    Get the number of pages in a PDF document.

    Args:
        doc: PDF document object

    Returns:
        Number of pages in the document
    """
    return doc.page_count


def get_page_images(doc: Document, page_num: int) -> List[Tuple]:
    """
    Get all image references from a specific page.

    Args:
        doc: PDF document object
        page_num: Page number (0-indexed)

    Returns:
        List of image tuples containing metadata
    """
    return doc.get_page_images(page_num)