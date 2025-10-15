"""
Example of extracting images and adding watermarks to a PDF.
"""

from pathlib import Path
from pdf_image_extract_annotate import PDFImageWatermarker, WatermarkConfig, ExtractionConfig


def main(pdf_path: Path):


    # Configure watermark appearance
    watermark_config = WatermarkConfig(
        font_size=10,
        font_color=(1.0, 0.0, 0.0),  # Red text
        background_color=(1.0, 1.0, 1.0, 0.7),  # Semi-transparent white background
        text_format="filename",  # Show just the filename
        padding=3
    )

    # Configure extraction (optional)
    extraction_config = ExtractionConfig(
        output_dir="watermarked_output",
        dim_limit=0,  # No dimension limit
        rel_size=0.0,  # No relative size limit
        abs_size=0  # No absolute size limit
    )

    # Create watermarker
    watermarker = PDFImageWatermarker(
        pdf_path=pdf_path,
        watermark_config=watermark_config,
        extraction_config=extraction_config
    )

    try:
        # Process PDF
        result = watermarker.process_pdf_with_watermarks()

        # Save the annotated PDF
        output_path = pdf_path.stem + "_watermarked.pdf"
        result.output_pdf.save(output_path)
        result.output_pdf.close()

        # Print results
        print("=" * 60)
        print("PDF WATERMARKING COMPLETE")
        print("=" * 60)
        print(f"Original PDF: {result.original_pdf}")
        print(f"Watermarked PDF: {output_path}")
        print(f"Pages processed: {result.total_pages}")
        print(f"Images extracted: {result.images_extracted}")
        print(f"Images watermarked: {result.images_watermarked}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Images saved to: {result.output_directory}/")

        if result.images_extracted > 0:
            print(f"\n✓ Successfully created PDF with image path watermarks!")
            print(f"✓ {result.images_watermarked}/{result.images_extracted} images were watermarked")
        else:
            print(f"\n⚠ No images were found in the PDF")

    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except Exception as e:
        print(f"Error processing PDF: {e}")


if __name__ == "__main__":
    # Path to your PDF file
    pdf = Path("example.pdf")
    main(pdf)