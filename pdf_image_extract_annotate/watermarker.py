"""
PDF Image Watermarker - Adds watermarks showing file paths on the original PDF.
"""

import logging
from os import makedirs
from os.path import exists, join
from pathlib import Path
from time import time
from typing import Optional, List
from pymupdf import open as pdfopen, Rect, TEXT_ALIGN_CENTER

from .extractor import PDFImageExtractor
from .models import (
    ExtractionConfig,
    WatermarkConfig,
    ImageMetadata,
    ImageWatermarkEntry,
    WatermarkResult
)
from .utils.image_processing import recover_pixmap
from .utils.blob_storage import store_image_to_target

logger = logging.getLogger(__name__)


class PDFImageWatermarker(PDFImageExtractor):
    """Extracts images and adds watermarks showing file paths on the original PDF."""

    def __init__(
        self,
        pdf_path: Path,
        watermark_config: Optional[WatermarkConfig] = None,
        file_contents: Optional[bytes] = None,
        extraction_config: Optional[ExtractionConfig] = None,
        base_url: Optional[str] = None,
    ):
        self.pdf_path = pdf_path
        self.pdf_name_stem = pdf_path.stem
        self.watermark_config = watermark_config or WatermarkConfig()
        self.file_contents = file_contents

        if not self.pdf_path.exists() and not self.file_contents:
            raise ValueError("PDF file does not exist and no file contents provided")

        # Use provided config or create default
        if extraction_config:
            config = extraction_config
        else:
            config = ExtractionConfig(
                dim_limit=0,
                rel_size=0.0,
                abs_size=0,
                output_dir=self.pdf_name_stem,
            )

        super().__init__(config)
        self.watermark_entries: List[ImageWatermarkEntry] = []

    def extract_and_track_image(
        self, doc, page_num: int, img_metadata: ImageMetadata
    ) -> Optional[ImageWatermarkEntry]:
        """Extract a single image and create a watermark entry."""
        try:
            # Recover the image data
            image_data = recover_pixmap(doc, img_metadata)

            # Apply filters
            if not self.should_extract_image(img_metadata, image_data):
                logger.warning(f"    Filtered out image (xref: {img_metadata.xref})")
                return None

            # Generate filename and page-specific directory
            filename = f"img{img_metadata.xref:05d}.{image_data.ext}"
            page_dir = join(self.config.output_dir, "images", f"page_{page_num + 1}")

            # Ensure page directory exists
            if not exists(page_dir):
                makedirs(page_dir, exist_ok=True)
                logger.info(f"Created page directory: {page_dir}")

            # Store image in page-specific directory
            target = self.config.output_target
            if target == "local":
                filepath = join(page_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data.image)
                logger.info(f"    Stored image {filename} at {filepath} ({len(image_data.image)} bytes)")
            else:
                # For blob storage, include page path in filename
                blob_filename = f"images/page_{page_num + 1}/{filename}"
                try:
                    filepath = store_image_to_target(
                        target=target,
                        image_data=image_data.image,
                        filename=blob_filename,
                        config=self.config,
                    )
                except Exception as e:
                    logger.error(f"    Error storing image {filename}: {e}")
                    raise
                logger.info(
                    f"    Stored image {filename} at {filepath} ({len(image_data.image)} bytes)"
                )

            # Get coordinates for this image
            page = doc[page_num]
            bbox_x = bbox_y = bbox_width = bbox_height = 0

            try:
                # Get image rectangles for this xref
                image_rects = page.get_image_rects(img_metadata.xref)
                if image_rects:
                    # Use first rectangle if multiple instances
                    rect = image_rects[0]
                    bbox_x = rect.x0
                    bbox_y = rect.y0
                    bbox_width = rect.width
                    bbox_height = rect.height
                    logger.debug(
                        f"    Found coordinates: ({bbox_x:.0f}, {bbox_y:.0f}) size {bbox_width:.0f}×{bbox_height:.0f}"
                    )
                else:
                    logger.warning(f"    No coordinates found for xref {img_metadata.xref}")
                    return None  # Skip images without coordinates
            except Exception as coord_error:
                logger.error(
                    f"    Could not get coordinates for xref {img_metadata.xref}: {coord_error}"
                )
                return None

            # Create watermark entry
            entry = ImageWatermarkEntry(
                filepath=filepath,
                filename=filename,
                page_num=page_num + 1,  # 1-based page numbering
                xref=img_metadata.xref,
                width=img_metadata.width,
                height=img_metadata.height,
                bbox_x=bbox_x,
                bbox_y=bbox_y,
                bbox_width=bbox_width,
                bbox_height=bbox_height,
            )

            self.extracted_xrefs.append(img_metadata.xref)
            logger.info(
                f"    ✓ Extracted: {filename} ({len(image_data.image)} bytes, {img_metadata.width}x{img_metadata.height}) at ({bbox_x:.0f}, {bbox_y:.0f})"
            )

            return entry

        except Exception as e:
            logger.error(f"    ✗ Error extracting image {img_metadata.xref}: {e}")
            return None

    def process_pdf_with_watermarks(self) -> WatermarkResult:
        """Main method to extract images and add watermarks to the original PDF."""
        # Open document properly based on what's available
        if self.file_contents:
            doc = pdfopen(stream=self.file_contents, filetype="pdf")
        elif self.pdf_path.exists():
            doc = pdfopen(str(self.pdf_path))
        else:
            raise ValueError("No valid PDF source available")

        start_time = time()

        try:
            page_count = doc.page_count
            total_watermarked = 0

            logger.info(f"Processing PDF: {self.pdf_path}")
            logger.info(f"Total pages: {page_count}")
            logger.info(f"Output directory: {self.config.output_dir}")
            logger.info(
                f"Watermark config: {self.watermark_config.text_format} format, size {self.watermark_config.font_size}"
            )

            # Process each page
            page_entries_by_page = {}  # Track entries per page for watermarking

            for page_num in range(page_count):
                logger.debug(f"\nProcessing page {page_num + 1}/{page_count}...")

                # Extract images from this page
                entries = self.extract_images_from_page(doc, page_num)
                self.watermark_entries.extend(entries)

                if entries:
                    page_entries_by_page[page_num] = entries

            # Now add watermarks to all pages that have extracted images
            logger.info(
                f"\nAdding watermarks to {len(page_entries_by_page)} pages with images..."
            )

            for page_num, entries in page_entries_by_page.items():
                logger.debug(f"\nWatermarking page {page_num + 1}...")
                page = doc[page_num]
                watermarked_on_page = self.add_watermarks_to_page(page, entries)
                total_watermarked += watermarked_on_page

            end_time = time()

            return WatermarkResult(
                original_pdf=str(self.pdf_path),
                output_pdf=doc,  # Don't close here, let caller handle it
                total_pages=page_count,
                images_extracted=len(self.watermark_entries),
                images_watermarked=total_watermarked,
                processing_time=end_time - start_time,
                output_directory=self.config.output_dir,
                base_url=self.config.base_url,
            )

        except Exception as e:
            doc.close()  # Close on error
            raise e

    def extract_images_from_page(
        self, doc, page_num: int
    ) -> List[ImageWatermarkEntry]:
        """Extract all valid images from a single page and track them for watermarking."""
        entries: List[ImageWatermarkEntry] = []

        # Get all images on this page
        image_list = doc.get_page_images(page_num)
        logger.info(f"  Found {len(image_list)} image references on page {page_num + 1}")

        for img_index, img_tuple in enumerate(image_list):
            try:
                img_metadata = ImageMetadata.from_tuple(img_tuple)
            except (ValueError, IndexError) as e:
                logger.error(f"    Error parsing image {img_index + 1}: {e}")
                continue

            # Skip if already extracted
            if img_metadata.xref in self.extracted_xrefs:
                logger.warning(f"    Skipping duplicate image (xref: {img_metadata.xref})")
                continue

            # Skip if no meaningful data
            if not img_metadata.has_data:
                logger.warning(f"    Skipping image with no data (xref: {img_metadata.xref})")
                continue

            # Extract and track the image
            entry = self.extract_and_track_image(doc, page_num, img_metadata)
            if entry:
                entries.append(entry)

        return entries

    def add_watermarks_to_page(
        self, page, page_entries: List[ImageWatermarkEntry]
    ) -> int:
        """Add watermarks to all images on a page."""
        watermarked_count = 0

        logger.info(
            f"  Adding watermarks to {len(page_entries)} images on page {page_entries[0].page_num if page_entries else '?'}"
        )

        for entry in page_entries:
            if self.add_watermark_to_image(page, entry):
                watermarked_count += 1

        return watermarked_count

    def add_watermark_to_image(self, page, entry: ImageWatermarkEntry) -> bool:
        """Add a watermark overlay to a specific image on the page."""
        try:
            # Get watermark text
            watermark_text = entry.get_watermark_text(self.watermark_config.text_format)

            # Calculate text dimensions to center it properly
            # Use a reasonable approximation for text width/height
            text_lines = watermark_text.split("\n")
            max_line_length = max(len(line) for line in text_lines)

            # Estimate text dimensions (approximate)
            char_width = self.watermark_config.font_size * 0.6  # Rough approximation
            line_height = self.watermark_config.font_size * 1.2

            text_width = max_line_length * char_width
            text_height = len(text_lines) * line_height

            # Add padding
            padding = self.watermark_config.padding
            box_width = text_width + 2 * padding
            box_height = text_height + 2 * padding

            # Center the text box on the image
            center_x = entry.center_x
            center_y = entry.center_y

            # Calculate text box rectangle
            text_rect = Rect(
                center_x - box_width / 2,
                center_y - box_height / 2,
                center_x + box_width / 2,
                center_y + box_height / 2,
            )

            # Ensure the text box stays within image bounds
            image_rect = Rect(
                entry.bbox_x,
                entry.bbox_y,
                entry.bbox_x + entry.bbox_width,
                entry.bbox_y + entry.bbox_height,
            )

            # Clip text box to image bounds
            text_rect = text_rect & image_rect  # Intersection

            if text_rect.is_empty:
                logger.warning(
                    f"    Warning: Text box outside image bounds for {entry.filename}"
                )
                return False

            # Add semi-transparent background rectangle
            if self.watermark_config.background_color[3] > 0:  # If alpha > 0
                bg_color = self.watermark_config.background_color[
                    :3
                ]  # RGB only for rect
                page.draw_rect(text_rect, color=bg_color, fill=bg_color, width=0)

            # Add the text
            page.insert_textbox(
                text_rect,
                watermark_text,
                fontsize=self.watermark_config.font_size,
                color=self.watermark_config.font_color,
                align=TEXT_ALIGN_CENTER,
            )

            logger.debug(
                f"    ✓ Added watermark to {entry.filename} at center ({center_x:.0f}, {center_y:.0f})"
            )
            return True

        except Exception as e:
            logger.error(f"    ✗ Error adding watermark to {entry.filename}: {e}")
            return False