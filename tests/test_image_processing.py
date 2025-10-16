"""
Tests for image processing utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from pdf_image_extract_annotate.utils.image_processing import (
    handle_alpha_channel,
    recover_pixmap,
)
from pdf_image_extract_annotate.models import ImageMetadata, ExtractedImageData


class TestImageProcessing:
    """Test suite for image processing utilities."""

    def test_handle_alpha_channel_with_alpha(self):
        """Test removing alpha channel from pixmap."""
        # Mock pixmap with alpha channel
        mock_pix = MagicMock()
        mock_pix.alpha = True

        with patch('pdf_image_extract_annotate.utils.image_processing.Pixmap') as mock_pixmap_class:
            mock_new_pix = MagicMock()
            mock_pixmap_class.return_value = mock_new_pix

            result = handle_alpha_channel(mock_pix)

            assert result == mock_new_pix
            mock_pixmap_class.assert_called_once_with(mock_pix, 0)

    def test_handle_alpha_channel_without_alpha(self):
        """Test pixmap without alpha channel is returned unchanged."""
        mock_pix = MagicMock()
        mock_pix.alpha = False

        result = handle_alpha_channel(mock_pix)

        assert result == mock_pix

    @patch('pdf_image_extract_annotate.utils.image_processing.Pixmap')
    def test_recover_pixmap_with_smask(self, mock_pixmap_class):
        """Test recovering pixmap with SMask."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.extract_image.side_effect = [
            {"image": b"base_image"},  # Base image
            {"image": b"mask_image"}   # Mask image
        ]

        # Mock pixmaps
        mock_pix0 = MagicMock()
        mock_pix0.alpha = False
        mock_pix0.n = 3  # RGB
        mock_mask = MagicMock()
        mock_combined = MagicMock()
        mock_combined.colorspace.n = 3
        mock_combined.tobytes.return_value = b"combined_image"

        mock_pixmap_class.side_effect = [
            mock_pix0,      # Base pixmap
            mock_mask,      # Mask pixmap
            mock_combined   # Combined pixmap
        ]

        # Create metadata with smask
        metadata = ImageMetadata(
            xref=1, smask=2, width=100, height=100,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )

        result = recover_pixmap(mock_doc, metadata)

        assert isinstance(result, ExtractedImageData)
        assert result.ext == "png"
        assert result.colorspace == 3
        assert result.image == b"combined_image"

    @patch('pdf_image_extract_annotate.utils.image_processing.Pixmap')
    def test_recover_pixmap_with_smask_error(self, mock_pixmap_class):
        """Test fallback when combining with mask fails."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.extract_image.side_effect = [
            {"image": b"base_image"},  # Base image
            {"image": b"mask_image"},  # Mask image
            {"image": b"fallback_image"}  # Fallback extraction
        ]

        # Mock pixmaps
        mock_pix0 = MagicMock()
        mock_pix0.alpha = False
        mock_pix0.n = 3
        mock_mask = MagicMock()
        mock_fallback = MagicMock()
        mock_fallback.colorspace.n = 3
        mock_fallback.tobytes.return_value = b"fallback_result"

        # Make combining fail
        def pixmap_side_effect(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                # Extract image calls
                if args[0] == {"image": b"base_image"}:
                    return mock_pix0
                elif args[0] == {"image": b"mask_image"}:
                    return mock_mask
                elif args[0] == {"image": b"fallback_image"}:
                    return mock_fallback
            elif len(args) == 2 and not isinstance(args[1], int):  # Combining pixmaps (not alpha removal)
                raise Exception("Combine failed")
            elif len(args) == 2 and isinstance(args[1], int):  # Alpha channel removal
                return mock_pix0  # Return the same pixmap
            # Default return with proper mocked attributes
            mock_result = MagicMock()
            mock_result.colorspace.n = 3
            mock_result.tobytes.return_value = b"fallback_result"
            return mock_result

        mock_pixmap_class.side_effect = pixmap_side_effect

        # Create metadata with smask
        metadata = ImageMetadata(
            xref=1, smask=2, width=100, height=100,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )

        result = recover_pixmap(mock_doc, metadata)

        assert isinstance(result, ExtractedImageData)
        assert result.ext == "png"
        assert result.image == b"fallback_result"

    @patch('pdf_image_extract_annotate.utils.image_processing.csRGB')
    @patch('pdf_image_extract_annotate.utils.image_processing.Pixmap')
    def test_recover_pixmap_with_colorspace(self, mock_pixmap_class, mock_csrgb):
        """Test recovering pixmap with ColorSpace definition."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.xref_object.return_value = "/ColorSpace /DeviceCMYK"

        # Mock pixmaps
        mock_pix1 = MagicMock()
        mock_pix2 = MagicMock()
        mock_pix2.tobytes.return_value = b"converted_image"

        mock_pixmap_class.side_effect = [mock_pix1, mock_pix2]

        # Create metadata
        metadata = ImageMetadata(
            xref=1, smask=0, width=100, height=100,
            bpc=8, colorspace="CMYK", name="test",
            image_name="test", filter_type="DCT"
        )

        result = recover_pixmap(mock_doc, metadata)

        assert isinstance(result, ExtractedImageData)
        assert result.ext == "png"
        assert result.colorspace == 3
        assert result.image == b"converted_image"
        mock_pixmap_class.assert_any_call(mock_doc, 1)
        mock_pixmap_class.assert_any_call(mock_csrgb, mock_pix1)

    def test_recover_pixmap_normal_case(self):
        """Test normal image extraction without special cases."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.xref_object.return_value = "normal object"
        mock_doc.extract_image.return_value = {
            "ext": "jpg",
            "colorspace": 3,
            "image": b"normal_image"
        }

        # Create metadata without smask
        metadata = ImageMetadata(
            xref=1, smask=0, width=100, height=100,
            bpc=8, colorspace="RGB", name="test",
            image_name="test", filter_type="DCT"
        )

        result = recover_pixmap(mock_doc, metadata)

        assert isinstance(result, ExtractedImageData)
        assert result.ext == "jpg"
        assert result.colorspace == 3
        assert result.image == b"normal_image"
        mock_doc.extract_image.assert_called_once_with(1)