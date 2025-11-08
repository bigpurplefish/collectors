"""
PDF extraction module.

This module handles opening the PDF file and extracting specific pages
for further processing.
"""

import pdfplumber
from pathlib import Path
from typing import Optional


class PDFExtractor:
    """
    Handles PDF file operations and page extraction.
    """

    def __init__(self, pdf_path: Path):
        """
        Initialize the PDF extractor.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.pdf = None

    def __enter__(self):
        """Context manager entry - open the PDF."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        self.pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the PDF."""
        if self.pdf:
            self.pdf.close()

    def get_page(self, page_number: int):
        """
        Get a specific page from the PDF.

        Args:
            page_number: Page number (1-indexed)

        Returns:
            pdfplumber.Page object

        Raises:
            ValueError: If page number is invalid
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager.")

        if page_number < 1 or page_number > len(self.pdf.pages):
            raise ValueError(
                f"Invalid page number {page_number}. "
                f"PDF has {len(self.pdf.pages)} pages."
            )

        # pdfplumber uses 0-indexed pages
        return self.pdf.pages[page_number - 1]

    def extract_page_text(self, page_number: int) -> str:
        """
        Extract all text from a page.

        Args:
            page_number: Page number (1-indexed)

        Returns:
            Page text content
        """
        page = self.get_page(page_number)
        return page.extract_text() or ""

    def extract_tables(self, page_number: int) -> list:
        """
        Extract all tables from a page.

        Args:
            page_number: Page number (1-indexed)

        Returns:
            List of tables, where each table is a list of rows
        """
        page = self.get_page(page_number)
        tables = page.extract_tables()
        return tables or []

    def extract_table(self, page_number: int, table_settings: Optional[dict] = None) -> list:
        """
        Extract a single table from a page with custom settings.

        Args:
            page_number: Page number (1-indexed)
            table_settings: Optional dictionary of pdfplumber table extraction settings

        Returns:
            Table as a list of rows
        """
        page = self.get_page(page_number)

        if table_settings:
            table = page.extract_table(table_settings)
        else:
            table = page.extract_table()

        return table or []
