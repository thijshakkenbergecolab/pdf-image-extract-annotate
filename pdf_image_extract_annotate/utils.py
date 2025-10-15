"""
Utility functions for PDF image extraction and processing.
"""

import logging
from typing import Optional, Literal
from os.path import join
from pymupdf import Document, Pixmap, csRGB

from .models import ImageMetadata, ExtractedImageData, ExtractionConfig

logger = logging.getLogger(__name__)


def store_image_to_target(
    target: Literal["blob", "local"],
    image_data: bytes,
    filename: str,
    config: ExtractionConfig,
) -> str:
    """
    Store the extracted image data to the specified target (local filesystem or Azure Blob Storage).
    Returns the path or URL of the stored image.
    """
    if target == "local":
        filepath = join(config.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        logger.info(f"Saved {filename} to local directory: {config.output_dir}")
        return filepath

    elif target == "blob":
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            logger.error("Azure Storage Blob SDK not installed. Install with: pip install azure-storage-blob")
            # Fallback to local storage
            filepath = join(config.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_data)
            logger.info(f"Saved {filename} to local directory: {config.output_dir} (fallback)")
            return filepath

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
            blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )

            container_name = config.output_dir  # Use output_dir as container name
            logger.info(f"Using container: {container_name}")

            # Ensure container exists (create if it doesn't)
            try:
                container_client = blob_service_client.get_container_client(
                    container_name
                )
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    logger.info(f"Container {container_name} already exists")
                else:
                    logger.warning(f"Could not create container {container_name}: {e}")

            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=filename
            )
            logger.info(
                f"Uploading {filename} to Azure Blob Storage... using {blob_client.url}"
            )
            blob_client.upload_blob(image_data, overwrite=True)
            logger.info(f"Image {filename} uploaded to Azure Blob Storage, retrieving URL...")
            url = blob_client.url
            logger.info(
                f"Uploaded {filename} to Azure Blob Storage in container {container_name} at {url}"
            )
            return url

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


def recover_pixmap(doc: Document, img_metadata: ImageMetadata) -> ExtractedImageData:
    """
    Recover image data from PDF, handling special cases like SMask and ColorSpace.

    This is based on the recoverpix function from PyMuPDF utilities.
    """
    xref = img_metadata.xref
    smask = img_metadata.smask

    # Special case: /SMask or /Mask exists
    if smask > 0:
        pix0 = Pixmap(doc.extract_image(xref)["image"])
        if pix0.alpha:  # Remove alpha channel if present
            pix0 = Pixmap(pix0, 0)
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