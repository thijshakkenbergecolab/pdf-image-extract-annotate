"""
Tests for PDF document utilities.
"""

import pytest
from unittest.mock import MagicMock

from pdf_image_extract_annotate.utils.pdf_utils import (
    get_pdf_page_count,
    get_page_images,
)


class TestPDFUtils:
    """Test suite for PDF utilities."""

    def test_get_pdf_page_count(self):
        """Test getting page count from PDF document."""
        mock_doc = MagicMock()
        mock_doc.page_count = 10

        result = get_pdf_page_count(mock_doc)

        assert result == 10

    def test_get_page_images(self):
        """Test getting image references from a page."""
        mock_doc = MagicMock()
        expected_images = [
            (1, 0, 100, 100, 8, "RGB", "img1", "img1", "DCT"),
            (2, 0, 200, 200, 8, "RGB", "img2", "img2", "DCT")
        ]
        mock_doc.get_page_images.return_value = expected_images

        result = get_page_images(mock_doc, 0)

        assert result == expected_images
        mock_doc.get_page_images.assert_called_once_with(0)

    def test_get_page_images_empty(self):
        """Test getting images from page with no images."""
        mock_doc = MagicMock()
        mock_doc.get_page_images.return_value = []

        result = get_page_images(mock_doc, 5)

        assert result == []
        mock_doc.get_page_images.assert_called_once_with(5)