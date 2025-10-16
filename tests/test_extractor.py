"""
Tests for PDF image extraction functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pdf_image_extract_annotate.extractor import PDFImageExtractor
from pdf_image_extract_annotate.models import ExtractionConfig, ImageMetadata, ExtractedImageData


class TestPDFImageExtractor:
    """Test suite for PDFImageExtractor."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def extraction_config(self, temp_dir):
        """Create a test extraction configuration."""
        return ExtractionConfig(
            output_dir=str(temp_dir),
            dim_limit=50,
            rel_size=0.1,
            abs_size=1000
        )

    @pytest.fixture
    def extractor(self, extraction_config):
        """Create a PDFImageExtractor instance."""
        return PDFImageExtractor(extraction_config)

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        config = ExtractionConfig(output_dir=str(temp_dir / "test_output"))
        extractor = PDFImageExtractor(config)

        assert (temp_dir / "test_output").exists()
        assert (temp_dir / "test_output" / "images").exists()

    def test_should_extract_image_dimension_filter(self, extractor):
        """Test image filtering based on dimensions."""
        # Image below dimension limit (40x40, min dimension = 40 < 50)
        small_metadata = ImageMetadata(
            xref=1, smask=0, width=40, height=40,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )
        small_data = ExtractedImageData(ext="jpg", colorspace=3, image=b"test" * 300)
        assert not extractor.should_extract_image(small_metadata, small_data)

        # Image above dimension limit (100x100, min dimension = 100 >= 50)
        # Also needs to pass size checks: 3000 bytes > 1000 (abs_size)
        # And rel_size check: 3000 / (100*100*3) = 0.1 >= 0.1
        large_metadata = ImageMetadata(
            xref=2, smask=0, width=100, height=100,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )
        large_data = ExtractedImageData(ext="jpg", colorspace=3, image=b"test" * 1000)  # 4000 bytes
        assert extractor.should_extract_image(large_metadata, large_data)

    def test_should_extract_image_size_filter(self, extractor):
        """Test image filtering based on file size."""
        metadata = ImageMetadata(
            xref=1, smask=0, width=100, height=100,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )

        # Image below absolute size limit (500 bytes < 1000)
        small_data = ExtractedImageData(ext="jpg", colorspace=3, image=b"x" * 500)
        assert not extractor.should_extract_image(metadata, small_data)

        # Image above absolute size limit (5000 bytes >= 1000)
        # Also needs to pass rel_size check: 5000 / (100*100*3) = 0.167 >= 0.1
        large_data = ExtractedImageData(ext="jpg", colorspace=3, image=b"x" * 5000)
        assert extractor.should_extract_image(metadata, large_data)

    @patch('pdf_image_extract_annotate.extractor.pdfopen')
    def test_extract_all_images(self, mock_pdfopen, temp_dir):
        """Test extracting all images from a PDF."""
        # Create a fresh extractor with no filters to ensure all images pass
        config = ExtractionConfig(output_dir=str(temp_dir), dim_limit=0, rel_size=0.0, abs_size=0)
        extractor = PDFImageExtractor(config)

        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.page_count = 2

        # Create a counter to track calls and return appropriate data for each call
        call_count = [0]
        def get_page_images_side_effect(page_num):
            # First call to extract_image_from_page AND first call to get xrefs
            if call_count[0] in [0, 1]:  # Page 0 calls
                call_count[0] += 1
                return [(1, 0, 100, 100, 8, "RGB", "img1", "img1", "DCT"),
                        (2, 0, 200, 200, 8, "RGB", "img2", "img2", "DCT")]
            else:  # Page 1 calls
                call_count[0] += 1
                return [(3, 0, 100, 100, 8, "RGB", "img3", "img3", "DCT"),
                        (4, 0, 200, 200, 8, "RGB", "img4", "img4", "DCT")]

        mock_doc.get_page_images.side_effect = get_page_images_side_effect
        mock_pdfopen.return_value = mock_doc

        # Mock recover_pixmap to return test data
        with patch('pdf_image_extract_annotate.extractor.recover_pixmap') as mock_recover:
            mock_recover.return_value = ExtractedImageData(
                ext="jpg", colorspace=3, image=b"x" * 5000
            )

            pdf_path = temp_dir / "test.pdf"
            pdf_path.touch()  # Create dummy file

            result = extractor.extract_all_images(pdf_path)

            assert result["total_pages"] == 2
            assert result["images_extracted"] == 4  # 2 images per page, all pass filters
            assert len(result["extracted_files"]) == 4
            mock_doc.close.assert_called_once()

    def test_extract_image_from_page_handles_errors(self, extractor):
        """Test that extraction handles errors gracefully."""
        mock_doc = MagicMock()
        mock_doc.get_page_images.return_value = [
            (1, 0, 100, 100, 8, "RGB", "img1", "img1", "DCT"),
            (0, 0, 0, 0, 0, "", "", "", ""),  # Invalid image data
        ]

        with patch('pdf_image_extract_annotate.extractor.recover_pixmap') as mock_recover:
            mock_recover.side_effect = [
                ExtractedImageData(ext="jpg", colorspace=3, image=b"x" * 5000),
                Exception("Failed to recover image")
            ]

            files = extractor.extract_image_from_page(mock_doc, 0)

            # Should extract only the valid image
            assert len(files) == 1
            assert len(extractor.extracted_xrefs) == 1