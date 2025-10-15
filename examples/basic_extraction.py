"""
Basic example of extracting images from a PDF.
"""

from pathlib import Path
from pdf_image_extract_annotate import PDFImageExtractor, ExtractionConfig


def main():
    # Path to your PDF file
    pdf_path = Path("example.pdf")

    # Configure extraction
    config = ExtractionConfig(
        output_dir="extracted_images",
        dim_limit=50,  # Skip images smaller than 50px
        abs_size=1000  # Skip images smaller than 1KB
    )

    # Create extractor and process PDF
    extractor = PDFImageExtractor(config)

    try:
        result = extractor.extract_all_images(pdf_path)

        # Print results
        print("=" * 60)
        print("PDF IMAGE EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"PDF: {result['pdf_path']}")
        print(f"Total pages: {result['total_pages']}")
        print(f"Unique images found: {result['unique_images_found']}")
        print(f"Images extracted: {result['images_extracted']}")
        print(f"Processing time: {result['extraction_time']:.2f} seconds")
        print(f"Output directory: {result['output_directory']}")

        if result['extracted_files']:
            print("\nExtracted files:")
            for file in result['extracted_files'][:5]:  # Show first 5
                print(f"  - {file}")
            if len(result['extracted_files']) > 5:
                print(f"  ... and {len(result['extracted_files']) - 5} more")

    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except Exception as e:
        print(f"Error processing PDF: {e}")


if __name__ == "__main__":
    main()