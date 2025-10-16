"""
Tests for blob storage utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from pdf_image_extract_annotate.utils.blob_storage import (
    store_image_to_blob,
    store_image_to_target,
)
from pdf_image_extract_annotate.models import ExtractionConfig


class TestBlobStorage:
    """Test suite for blob storage utilities."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self, temp_dir):
        """Create a test extraction configuration."""
        return ExtractionConfig(
            output_dir=str(temp_dir),
            blob_connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test==;EndpointSuffix=core.windows.net"
        )

    @patch('azure.storage.blob.BlobServiceClient')
    def test_store_image_to_blob(self, mock_blob_client_class):
        """Test storing image to blob storage."""
        # Mock blob service client
        mock_service = MagicMock()
        mock_blob_client_class.from_connection_string.return_value = mock_service

        # Mock container client
        mock_container = MagicMock()
        mock_service.get_container_client.return_value = mock_container

        # Mock blob client
        mock_blob = MagicMock()
        mock_blob.url = "https://test.blob.core.windows.net/container/test.jpg"
        mock_service.get_blob_client.return_value = mock_blob

        # Test data
        connection_string = "test_connection"
        container_name = "test_container"
        filename = "test.jpg"
        image_data = b"test_image_data"

        # Call function
        result = store_image_to_blob(
            connection_string, container_name, filename, image_data
        )

        # Assertions
        assert result == "https://test.blob.core.windows.net/container/test.jpg"
        mock_blob_client_class.from_connection_string.assert_called_once_with(connection_string)
        mock_service.get_container_client.assert_called_once_with(container_name)
        mock_container.create_container.assert_called_once()
        mock_service.get_blob_client.assert_called_once_with(
            container=container_name, blob=filename
        )
        mock_blob.upload_blob.assert_called_once_with(image_data, overwrite=True)

    def test_store_image_to_blob_import_error(self):
        """Test handling of missing azure-storage-blob package."""
        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(ImportError, match="Azure Storage Blob SDK not installed"):
                store_image_to_blob("conn", "container", "file.jpg", b"data")

    @patch('azure.storage.blob.BlobServiceClient')
    def test_store_image_to_blob_container_exists(self, mock_blob_client_class):
        """Test handling when container already exists."""
        # Mock blob service client
        mock_service = MagicMock()
        mock_blob_client_class.from_connection_string.return_value = mock_service

        # Mock container client that raises ContainerAlreadyExists
        mock_container = MagicMock()
        mock_container.create_container.side_effect = Exception("ContainerAlreadyExists")
        mock_service.get_container_client.return_value = mock_container

        # Mock blob client
        mock_blob = MagicMock()
        mock_blob.url = "https://test.blob.core.windows.net/container/test.jpg"
        mock_service.get_blob_client.return_value = mock_blob

        # Call function - should not raise
        result = store_image_to_blob(
            "conn", "container", "test.jpg", b"data"
        )

        assert result == "https://test.blob.core.windows.net/container/test.jpg"

    def test_store_image_to_target_local(self, temp_dir, config):
        """Test storing image to local filesystem."""
        config.blob_connection_string = None  # Force local storage
        filename = "test.jpg"
        image_data = b"test_image_data"

        result = store_image_to_target(
            "local", image_data, filename, config
        )

        expected_path = str(temp_dir / filename)
        assert result == expected_path

        # Verify file was written
        with open(expected_path, "rb") as f:
            assert f.read() == image_data

    @patch('pdf_image_extract_annotate.utils.blob_storage.store_image_to_blob')
    def test_store_image_to_target_blob(self, mock_store_blob, config):
        """Test storing image to blob storage."""
        mock_store_blob.return_value = "https://test.blob.core.windows.net/container/test.jpg"

        result = store_image_to_target(
            "blob", b"data", "test.jpg", config
        )

        assert result == "https://test.blob.core.windows.net/container/test.jpg"
        mock_store_blob.assert_called_once()

    def test_store_image_to_target_blob_with_azurite(self, temp_dir):
        """Test using Azurite when no connection string provided."""
        config = ExtractionConfig(output_dir=str(temp_dir))

        with patch('pdf_image_extract_annotate.utils.blob_storage.store_image_to_blob') as mock_store:
            mock_store.return_value = "http://127.0.0.1:10000/devstoreaccount1/test.jpg"

            result = store_image_to_target(
                "blob", b"data", "test.jpg", config
            )

            assert result == "http://127.0.0.1:10000/devstoreaccount1/test.jpg"
            # Verify Azurite connection string was used
            call_args = mock_store.call_args
            assert "devstoreaccount1" in call_args[1]["connection_string"]

    def test_store_image_to_target_blob_fallback(self, temp_dir, config):
        """Test fallback to local storage when blob upload fails."""
        with patch('pdf_image_extract_annotate.utils.blob_storage.store_image_to_blob') as mock_store:
            mock_store.side_effect = Exception("Upload failed")

            filename = "test.jpg"
            image_data = b"test_data"

            result = store_image_to_target(
                "blob", image_data, filename, config
            )

            # Should fallback to local storage
            expected_path = str(temp_dir / filename)
            assert result == expected_path

            # Verify file was written locally
            with open(expected_path, "rb") as f:
                assert f.read() == image_data

    def test_store_image_to_target_invalid(self, config):
        """Test invalid target raises ValueError."""
        with pytest.raises(ValueError, match="Unknown target: invalid"):
            store_image_to_target("invalid", b"data", "file.jpg", config)