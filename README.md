# PDFImageExtractAnnotate

A Python package for extracting images from PDF documents and creating annotated versions with watermarks showing the extracted image filenames.

## Features

- **Image Extraction**: Extract all images from PDF documents with configurable filters
- **Page-based Organization**: Images are organized by page number for easy reference
- **Watermark Annotation**: Add watermarks to the original PDF showing extracted image filenames
- **Flexible Filtering**: Filter images by dimensions, file size, or relative compression
- **Azure Blob Storage Support**: Optional support for storing images in Azure Blob Storage
- **Customizable Watermarks**: Configure font size, color, background, and text format

## Installation

### From PyPI (when published)

```bash
pip install pdf-image-extract-annotate
```

### From Source

```bash
git clone https://github.com/thijshakkenbergecolab/pdf-image-extract-annotate
cd pdf-image-extract-annotate
pip install -e .
```

### With Azure Support

```bash
pip install pdf-image-extract-annotate[azure]
```

## Quick Start

### Basic Image Extraction

```python
from pathlib import Path
from pdf_image_extract_annotate import PDFImageExtractor, ExtractionConfig

# Configure extraction
config = ExtractionConfig(
    output_dir="extracted_images",
    dim_limit=50,  # Minimum dimension in pixels
    abs_size=1000  # Minimum file size in bytes
)

# Extract images
extractor = PDFImageExtractor(config)
result = extractor.extract_all_images(Path("document.pdf"))

print(f"Extracted {result['images_extracted']} images")
print(f"Saved to: {result['output_directory']}")
```

### Extract and Watermark PDF

```python
from pathlib import Path
from pdf_image_extract_annotate import PDFImageWatermarker, WatermarkConfig

# Configure watermark appearance
watermark_config = WatermarkConfig(
    font_size=10,
    font_color=(1.0, 0.0, 0.0),  # Red text
    background_color=(1.0, 1.0, 1.0, 0.7),  # Semi-transparent white
    text_format="filename"  # Show just the filename
)

# Process PDF
watermarker = PDFImageWatermarker(
    pdf_path=Path("document.pdf"),
    watermark_config=watermark_config
)

result = watermarker.process_pdf_with_watermarks()

# Save the annotated PDF
result.output_pdf.save("annotated_document.pdf")
result.output_pdf.close()

print(f"Extracted {result.images_extracted} images")
print(f"Watermarked {result.images_watermarked} images")
```

## Configuration Options

### ExtractionConfig

- `output_dir` (str): Directory to save extracted images
- `dim_limit` (int): Minimum dimension filter (0 = no limit)
- `rel_size` (float): Relative size filter (0.0-1.0, 0 = no limit)
- `abs_size` (int): Absolute size filter in bytes (0 = no limit)
- `blob_connection_string` (str, optional): Azure Blob Storage connection string

### WatermarkConfig

- `font_size` (int): Font size for watermark text
- `font_color` (tuple): RGB color values (0.0-1.0)
- `background_color` (tuple): RGBA background color
- `text_format` (str): Format for watermark text ("filename", "filepath", or "custom")
- `padding` (int): Padding around text in pixels

## Output Structure

Images are organized using a page-based structure:

```
output_dir/
├── images/
│   ├── page_1/
│   │   ├── img00001.png
│   │   └── img00002.jpg
│   ├── page_2/
│   │   └── img00003.png
│   └── page_N/
│       └── imgXXXXX.ext
└── annotated_pdf.pdf  (if using watermarker)
```

## Advanced Usage

### Using with Azure Blob Storage

```python
from pdf_image_extract_annotate import PDFImageExtractor, ExtractionConfig

config = ExtractionConfig(
    output_dir="my-container",
    blob_connection_string="DefaultEndpointsProtocol=https;..."
)

extractor = PDFImageExtractor(config)
result = extractor.extract_all_images(Path("document.pdf"))
```

### Custom Image Filtering

```python
from pdf_image_extract_annotate import PDFImageExtractor, ExtractionConfig

# Only extract large, high-quality images
config = ExtractionConfig(
    output_dir="high_quality_images",
    dim_limit=200,      # At least 200px in smallest dimension
    rel_size=0.5,       # At least 50% of uncompressed size
    abs_size=50000      # At least 50KB
)
```

### Dependency Injection in Larger Projects

```python
from pathlib import Path
from pdf_image_extract_annotate import PDFImageWatermarker, ExtractionConfig, WatermarkConfig

class DocumentProcessor:
    def __init__(self, extraction_config: ExtractionConfig, watermark_config: WatermarkConfig):
        self.extraction_config = extraction_config
        self.watermark_config = watermark_config

    def process_document(self, pdf_path: Path):
        watermarker = PDFImageWatermarker(
            pdf_path=pdf_path,
            extraction_config=self.extraction_config,
            watermark_config=self.watermark_config
        )
        return watermarker.process_pdf_with_watermarks()
```

## API Reference

### Classes

- `PDFImageExtractor`: Core image extraction functionality
- `PDFImageWatermarker`: Extended extractor with watermarking capabilities
- `ExtractionConfig`: Configuration for image extraction
- `WatermarkConfig`: Configuration for watermark appearance
- `ImageMetadata`: Metadata for extracted images
- `ImageWatermarkEntry`: Entry for images with watermark information
- `WatermarkResult`: Result of the PDF watermarking process

## Requirements

- Python 3.11+
- PyMuPDF >= 1.23.0
- pydantic >= 2.0.0
- azure-storage-blob >= 12.0.0 (optional, for Azure support)

## Development

### Setting up development environment

```bash
# Clone the repository
git clone https://github.com/thijshakkenbergecolab/pdf-image-extract-annotate
cd pdf-image-extract-annotate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black pdf_image_extract_annotate tests

# Type checking
mypy pdf_image_extract_annotate
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pdf_image_extract_annotate

# Run specific test file
pytest tests/test_extractor.py
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For issues, questions, or suggestions, please open an issue on GitHub.