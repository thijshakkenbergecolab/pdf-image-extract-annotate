"""
Tests for PDF watermarking functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pdf_image_extract_annotate.watermarker import PDFImageWatermarker
from pdf_image_extract_annotate.models import (
    ExtractionConfig,
    WatermarkConfig,
    ImageMetadata,
    ImageWatermarkEntry,
    ExtractedImageData
)


class TestPDFImageWatermarker:
    """Test suite for PDFImageWatermarker."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def pdf_path(self, temp_dir):
        """Create a dummy PDF file."""
        pdf_file = temp_dir / "test.pdf"
        pdf_file.touch()
        return pdf_file

    @pytest.fixture
    def watermark_config(self):
        """Create a test watermark configuration."""
        return WatermarkConfig(
            font_size=10,
            font_color=(1.0, 0.0, 0.0),
            text_format="filename",
            padding=5
        )

    @pytest.fixture
    def extraction_config(self, temp_dir):
        """Create a test extraction configuration."""
        return ExtractionConfig(
            output_dir=str(temp_dir / "output"),
            dim_limit=0,
            rel_size=0.0,
            abs_size=0
        )

    def test_init_with_pdf_path(self, pdf_path, watermark_config, extraction_config):
        """Test initialization with PDF path."""
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            watermark_config=watermark_config,
            extraction_config=extraction_config
        )

        assert watermarker.pdf_path == pdf_path
        assert watermarker.watermark_config == watermark_config
        assert watermarker.config == extraction_config

    def test_init_with_file_contents(self, pdf_path, watermark_config):
        """Test initialization with file contents."""
        file_contents = b"PDF content"
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            watermark_config=watermark_config,
            file_contents=file_contents
        )

        assert watermarker.file_contents == file_contents

    def test_init_raises_without_valid_source(self, temp_dir):
        """Test that initialization raises error without valid PDF source."""
        non_existent = temp_dir / "non_existent.pdf"

        with pytest.raises(ValueError, match="PDF file does not exist"):
            PDFImageWatermarker(pdf_path=non_existent)

    @patch('pdf_image_extract_annotate.watermarker.recover_pixmap')
    def test_extract_and_track_image(self, mock_recover, pdf_path, temp_dir):
        """Test extracting and tracking a single image."""
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            extraction_config=ExtractionConfig(output_dir=str(temp_dir))
        )

        # Mock document and page
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__getitem__.return_value = mock_page

        # Mock image rectangles
        mock_rect = MagicMock()
        mock_rect.x0 = 100
        mock_rect.y0 = 200
        mock_rect.width = 300
        mock_rect.height = 400
        mock_page.get_image_rects.return_value = [mock_rect]

        # Mock image data
        mock_recover.return_value = ExtractedImageData(
            ext="jpg", colorspace=3, image=b"test_image_data"
        )

        # Create image metadata
        img_metadata = ImageMetadata(
            xref=1, smask=0, width=300, height=400,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )

        entry = watermarker.extract_and_track_image(mock_doc, 0, img_metadata)

        assert entry is not None
        assert entry.filename == "img00001.jpg"
        assert entry.page_num == 1
        assert entry.bbox_x == 100
        assert entry.bbox_y == 200
        assert entry.bbox_width == 300
        assert entry.bbox_height == 400

    def test_add_watermark_to_image(self, pdf_path):
        """Test adding watermark to an image."""
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            watermark_config=WatermarkConfig(font_size=12)
        )

        # Mock page
        mock_page = MagicMock()

        # Create watermark entry
        entry = ImageWatermarkEntry(
            filepath="/path/to/image.jpg",
            filename="image.jpg",
            page_num=1,
            xref=1,
            width=300,
            height=400,
            bbox_x=100,
            bbox_y=200,
            bbox_width=300,
            bbox_height=400
        )

        result = watermarker.add_watermark_to_image(mock_page, entry)

        assert result is True
        mock_page.draw_rect.assert_called_once()
        mock_page.insert_textbox.assert_called_once()

    @patch('pdf_image_extract_annotate.watermarker.pdfopen')
    def test_process_pdf_with_watermarks(self, mock_pdfopen, pdf_path, temp_dir):
        """Test complete PDF processing with watermarks."""
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            extraction_config=ExtractionConfig(output_dir=str(temp_dir))
        )

        # Mock PDF document with proper spec
        from pymupdf import Document
        mock_doc = MagicMock(spec=Document)
        mock_doc.page_count = 1
        mock_doc.get_page_images.return_value = [
            (1, 0, 100, 100, 8, "RGB", "img1", "img1", "DCT")
        ]
        mock_pdfopen.return_value = mock_doc

        # Mock page
        mock_page = MagicMock()
        mock_doc.__getitem__.return_value = mock_page

        # Mock image rectangles
        mock_rect = MagicMock()
        mock_rect.x0 = 50
        mock_rect.y0 = 50
        mock_rect.width = 100
        mock_rect.height = 100
        mock_page.get_image_rects.return_value = [mock_rect]

        with patch('pdf_image_extract_annotate.watermarker.recover_pixmap') as mock_recover:
            mock_recover.return_value = ExtractedImageData(
                ext="jpg", colorspace=3, image=b"x" * 5000
            )

            result = watermarker.process_pdf_with_watermarks()

            assert result.total_pages == 1
            assert result.images_extracted == 1
            assert result.images_watermarked == 1
            assert result.output_directory == str(temp_dir)
            assert result.output_pdf == mock_doc

    def test_get_watermark_text_formats(self):
        """Test different watermark text formats."""
        entry = ImageWatermarkEntry(
            filepath="/path/to/image.jpg",
            filename="image.jpg",
            page_num=2,
            xref=1,
            width=100,
            height=100,
            bbox_x=0,
            bbox_y=0,
            bbox_width=100,
            bbox_height=100
        )

        assert entry.get_watermark_text("filename") == "image.jpg"
        assert entry.get_watermark_text("filepath") == "/path/to/image.jpg"
        assert entry.get_watermark_text("custom") == "image.jpg\n(Page 2)"
        assert entry.get_watermark_text("unknown") == "image.jpg"  # Default