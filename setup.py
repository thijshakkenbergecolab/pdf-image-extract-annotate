"""
Setup configuration for PDFImageExtractAnnotate package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdf-image-extract-annotate",
    version="1.0.0",
    author="Thijs Hakkenberg",
    author_email="thijs.hakkenberg@ecolab.com",
    description="Extract images from PDFs and create annotated versions with watermarks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thijshakkenberg/pdf-image-extract-annotate",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyMuPDF>=1.23.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "azure": ["azure-storage-blob>=12.0.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf-extract-images=pdf_image_extract_annotate.cli:main",
        ],
    },
)