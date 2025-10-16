"""
PDFImageExtractAnnotate - Extract images from PDFs and annotate with filenames

A Python package for extracting images from PDF documents and creating annotated
versions with watermarks showing the extracted image filenames.
"""

from .extractor import PDFImageExtractor
from .watermarker import PDFImageWatermarker
from .models import (
    ExtractionConfig,
    WatermarkConfig,
    ImageMetadata,
    ExtractedImageData,
    ImageWatermarkEntry,
    WatermarkResult
)

__version__ = "1.0.0"
__all__ = [
    "PDFImageExtractor",
    "PDFImageWatermarker",
    "ExtractionConfig",
    "WatermarkConfig",
    "ImageMetadata",
    "ExtractedImageData",
    "ImageWatermarkEntry",
    "WatermarkResult"
]