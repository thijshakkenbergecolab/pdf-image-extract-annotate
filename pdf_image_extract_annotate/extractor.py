"""
PDF Image Extractor - Core extraction functionality.
"""

import logging
from dataclasses import dataclass, field
from os import makedirs
from os.path import exists, join
from pathlib import Path
from time import time
from typing import Dict, Any, List
from pymupdf import open as pdfopen

from .models import ImageMetadata, ExtractionConfig, ExtractedImageData
from .utils.image_processing import recover_pixmap

logger = logging.getLogger(__name__)


@dataclass
class PDFImageExtractor:
    """Extracts images from PDF documents with advanced handling of special cases."""

    config: ExtractionConfig
    extracted_xrefs: List[int] = field(default_factory=list)

    def __post_init__(self):
        # Create output directory if it doesn't exist
        if self.config.output_target == "local":
            if not exists(self.config.output_dir):
                logger.info(f"Creating output directory: {self.config.output_dir}")
                makedirs(self.config.output_dir, exist_ok=True)

            # Create images base directory for Option 4 structure
            images_dir = join(self.config.output_dir, "images")
            if not exists(images_dir):
                logger.info(f"Creating images directory: {images_dir}")
                makedirs(images_dir, exist_ok=True)

    def should_extract_image(
        self, img_metadata: ImageMetadata, image_data: ExtractedImageData
    ) -> bool:
        """Determine if an image should be extracted based on configured filters."""

        # Check dimension limit
        if (
            self.config.dim_limit > 0
            and img_metadata.min_dimension < self.config.dim_limit
        ):
            return False

        # Check absolute size limit
        if self.config.abs_size > 0 and len(image_data.image) < self.config.abs_size:
            return False

        # Check relative size limit
        if self.config.rel_size > 0.0:
            pixel_count = (
                img_metadata.width * img_metadata.height * image_data.colorspace
            )
            if (
                pixel_count > 0
                and len(image_data.image) / pixel_count < self.config.rel_size
            ):
                return False

        return True

    def extract_image_from_page(self, doc, page_num: int) -> List[str]:
        """Extract all valid images from a single page."""
        extracted_files: List[str] = []

        # Get all images on this page
        image_list = doc.get_page_images(page_num)
        logger.info(f"  Found {len(image_list)} image references on page {page_num + 1}")

        for img_index, img_tuple in enumerate(image_list):
            try:
                img_metadata = ImageMetadata.from_tuple(img_tuple)
            except (ValueError, IndexError) as e:
                logger.error(f"    Error parsing image {img_index + 1}: {e}")
                continue

            # Skip if already extracted (prevents duplicates)
            if img_metadata.xref in self.extracted_xrefs:
                logger.warning(f"    Skipping duplicate image (xref: {img_metadata.xref})")
                continue

            # Skip if no meaningful data
            if not img_metadata.has_data:
                logger.warning(f"    Skipping image with no data (xref: {img_metadata.xref})")
                continue

            try:
                # Recover the image data
                image_data = recover_pixmap(doc, img_metadata)

                # Apply filters to determine if we should extract this image
                if not self.should_extract_image(img_metadata, image_data):
                    logger.warning(f"    Filtered out image (xref: {img_metadata.xref})")
                    continue

                # Generate filename and page-specific directory
                filename = f"img{img_metadata.xref:05d}.{image_data.ext}"
                page_dir = join(self.config.output_dir, "images", f"page_{page_num + 1}")

                # Ensure page directory exists
                if not exists(page_dir):
                    makedirs(page_dir, exist_ok=True)
                    logger.info(f"Created page directory: {page_dir}")

                filepath = join(page_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(image_data.image)

                extracted_files.append(filepath)
                self.extracted_xrefs.append(img_metadata.xref)

                logger.info(
                    f"    ✓ Extracted: {filename} ({len(image_data.image)} bytes, {img_metadata.width}x{img_metadata.height})"
                )

            except Exception as e:
                logger.error(f"    ✗ Error extracting image {img_metadata.xref}: {e}")
                continue

        return extracted_files

    def extract_all_images(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract all images from a PDF document."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

        start_time = time()
        doc = pdfopen(str(pdf_path))

        try:
            page_count = doc.page_count
            all_extracted_files: List[str] = []
            all_image_xrefs: List[int] = []

            logger.info(f"Processing PDF: {pdf_path}")
            logger.info(f"Total pages: {page_count}")
            logger.info(f"Output directory: {self.config.output_dir}")

            for page_num in range(page_count):
                logger.info(f"\nProcessing page {page_num + 1}/{page_count}...")

                # Get all image references on this page
                image_list = doc.get_page_images(page_num)
                all_image_xrefs.extend([img[0] for img in image_list])

                # Extract images from this page
                extracted_files = self.extract_image_from_page(doc, page_num)
                all_extracted_files.extend(extracted_files)

            end_time = time()

            # Calculate statistics
            unique_images = len(set(all_image_xrefs))
            extracted_count = len(self.extracted_xrefs)

            result = {
                "pdf_path": str(pdf_path),
                "total_pages": page_count,
                "unique_images_found": unique_images,
                "images_extracted": extracted_count,
                "extraction_time": end_time - start_time,
                "extracted_files": all_extracted_files,
                "output_directory": self.config.output_dir,
            }

            return result

        finally:
            doc.close()