"""
Azure Blob Storage utilities for image storage.
"""

import logging
from typing import Literal
from os.path import join

logger = logging.getLogger(__name__)


def store_image_to_blob(
    connection_string: str,
    container_name: str,
    filename: str,
    image_data: bytes,
) -> str:
    """
    Store image data to Azure Blob Storage.

    Args:
        connection_string: Azure Storage connection string
        container_name: Name of the blob container
        filename: Name of the file to store
        image_data: Binary image data

    Returns:
        URL of the uploaded blob

    Raises:
        ImportError: If azure-storage-blob is not installed
        Exception: If blob upload fails
    """
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        raise ImportError(
            "Azure Storage Blob SDK not installed. Install with: pip install azure-storage-blob"
        )

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # Ensure container exists
    try:
        container_client = blob_service_client.get_container_client(container_name)
        container_client.create_container()
        logger.info(f"Created container: {container_name}")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            logger.info(f"Container {container_name} already exists")
        else:
            logger.warning(f"Could not create container {container_name}: {e}")

    # Upload blob
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=filename
    )
    logger.info(f"Uploading {filename} to Azure Blob Storage...")
    blob_client.upload_blob(image_data, overwrite=True)

    url = blob_client.url
    logger.info(f"Uploaded {filename} to {url}")
    return url


def store_image_to_target(
    target: Literal["blob", "local"],
    image_data: bytes,
    filename: str,
    config,
) -> str:
    """
    Store the extracted image data to the specified target.

    Args:
        target: Storage target ("blob" or "local")
        image_data: Binary image data
        filename: Name of the file to store
        config: ExtractionConfig object with storage settings

    Returns:
        Path or URL of the stored image
    """
    if target == "local":
        filepath = join(config.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        logger.info(f"Saved {filename} to local directory: {config.output_dir}")
        return filepath

    elif target == "blob":
        # Use Azurite as fallback if no connection string is provided
        if not config.blob_connection_string:
            azurite_connection_string = (
                "DefaultEndpointsProtocol=http;"
                "AccountName=devstoreaccount1;"
                "AccountKey=Eby8vdM02xNOcqFlUebSXLt3wmfqNBvBNNHh6bM1t1cTkDpPMM9y5S2k6J6z8uxZVd1L6b9Gg6nxFn5RlEQLzk0K4w==;"
                "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            )
            logger.info(
                "No blob connection string provided, using Azurite (local Azure Storage Emulator)"
            )
            connection_string = azurite_connection_string
        else:
            connection_string = config.blob_connection_string

        try:
            return store_image_to_blob(
                connection_string=connection_string,
                container_name=config.output_dir,  # Use output_dir as container name
                filename=filename,
                image_data=image_data,
            )
        except Exception as e:
            logger.error(f"Error uploading to blob storage: {e}")
            # Fallback to local storage if blob upload fails
            logger.warning(f"Falling back to local storage for {filename}")
            filepath = join(config.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_data)
            logger.info(f"Saved {filename} to local directory: {config.output_dir} (fallback)")
            return filepath

    else:
        raise ValueError(f"Unknown target: {target}")