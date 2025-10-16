"""
Data models for PDF image extraction and watermarking.
"""

from typing import Tuple, Optional, List, Any, Literal
from pydantic import BaseModel, Field, field_validator
from pymupdf import Document


class ImageMetadata(BaseModel):
    """Metadata for an extracted image."""

    xref: int = Field(..., description="Cross-reference number of the image")
    smask: int = Field(..., description="Soft mask xref (0 if none)")
    width: int = Field(..., description="Width of the image in pixels")
    height: int = Field(..., description="Height of the image in pixels")
    bpc: int = Field(..., description="Bits per component")
    colorspace: str = Field(..., description="Color space of the image")
    name: str = Field(..., description="Name of the image")
    image_name: str = Field(..., description="Image name identifier")
    filter_type: str = Field(..., description="Filter type used for the image")

    @classmethod
    def from_tuple(cls, img_tuple: Tuple) -> "ImageMetadata":
        """Create ImageMetadata from the tuple returned by get_page_images()."""
        if len(img_tuple) != 9:
            raise ValueError(
                f"Expected 9 elements in image tuple, got {len(img_tuple)}: {img_tuple}"
            )

        return cls(
            xref=img_tuple[0],
            smask=img_tuple[1],
            width=img_tuple[2],
            height=img_tuple[3],
            bpc=img_tuple[4],
            colorspace=img_tuple[5],
            name=img_tuple[6],
            image_name=img_tuple[7],
            filter_type=img_tuple[8],
        )

    @property
    def has_data(self) -> bool:
        """Check if the image has meaningful data."""
        return self.xref != 0

    @property
    def has_mask(self) -> bool:
        """Check if the image has a transparency mask."""
        return self.smask > 0

    @property
    def min_dimension(self) -> int:
        """Get the minimum dimension (width or height)."""
        return min(self.width, self.height)


class ExtractionConfig(BaseModel):
    """Configuration for image extraction."""

    dim_limit: int = Field(
        default=0, description="Minimum dimension limit (0 = no limit)"
    )
    rel_size: float = Field(
        default=0.0, description="Relative size limit (0.0 = no limit)"
    )
    abs_size: int = Field(
        default=0, description="Absolute size limit in bytes (0 = no limit)"
    )
    output_dir: str = Field(
        default="extracted_images", description="Output directory name"
    )
    blob_connection_string: Optional[str] = None

    @field_validator("rel_size")
    @classmethod
    def validate_rel_size(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("rel_size must be between 0.0 and 1.0")
        return v

    @field_validator("dim_limit", "abs_size")
    @classmethod
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @property
    def output_target(self) -> Literal["blob", "local"]:
        """Determine the output target based on the configuration."""
        if self.blob_connection_string:
            return "blob"
        return "local"

    @property
    def base_url(self) -> str:
        """Get the base URL for blob storage if configured."""
        if self.blob_connection_string:
            # Extract the account name from the connection string
            account_name = self.blob_connection_string.split(";")[1].split("=")[1]
            return f"https://{account_name}.blob.core.windows.net/{self.output_dir}/"
        return ""


class ExtractedImageData(BaseModel):
    """Data structure for extracted image information."""

    ext: str = Field(..., description="File extension")
    colorspace: int = Field(..., description="Number of color channels")
    image: bytes = Field(..., description="Binary image data")


class WatermarkConfig(BaseModel):
    """Configuration for watermark overlay."""

    font_size: int = Field(default=12, description="Font size for watermark text")
    font_color: Tuple[float, float, float] = Field(
        default=(1.0, 0.0, 0.0), description="RGB color for text (0-1)"
    )
    background_color: Tuple[float, float, float, float] = Field(
        default=(1.0, 1.0, 1.0, 0.8),
        description="RGBA background color for text box (0-1)",
    )
    text_format: str = Field(
        default="filename",
        description="Text format: 'filename', 'filepath', or 'custom'",
    )
    padding: int = Field(default=4, description="Padding around text in pixels")


class ImageWatermarkEntry(BaseModel):
    """Entry for an image with watermark information."""

    filepath: str
    filename: str
    page_num: int
    xref: int
    width: int
    height: int
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float

    @property
    def center_x(self) -> float:
        """Get the center X coordinate of the image."""
        return self.bbox_x + self.bbox_width / 2

    @property
    def center_y(self) -> float:
        """Get the center Y coordinate of the image."""
        return self.bbox_y + self.bbox_height / 2

    def get_watermark_text(self, format_type: str = "filename") -> str:
        """Get the text to display as watermark."""
        if format_type == "filename":
            return self.filename
        elif format_type == "filepath":
            return self.filepath
        elif format_type == "custom":
            return f"{self.filename}\n(Page {self.page_num})"
        else:
            return self.filename


class WatermarkResult(BaseModel):
    """Result of the PDF watermarking process."""

    original_pdf: str
    output_pdf: Document
    total_pages: int
    images_extracted: int
    images_watermarked: int
    processing_time: float
    output_directory: str
    base_url: str

    model_config = {"arbitrary_types_allowed": True}