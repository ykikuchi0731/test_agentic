"""Convert HTML tables containing images to Notion column blocks.

This module scans HTML files and converts tables that contain images to div elements
with data-notion-column-list attributes, which Notion can convert to column blocks during import.
"""
import logging
from pathlib import Path
from typing import List, Tuple
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class TableToColumnConverter:
    """
    Convert HTML tables containing images to Notion-compatible column blocks.

    Background:
    - Notion's table block doesn't support embedding images
    - When importing HTML with images in tables, the layout gets corrupted
    - Solution: Convert such tables to column blocks using data-notion-column-list

    Process:
    1. Scan HTML files for tables containing images
    2. Convert those tables to div elements with data-notion-column-list
    3. Preserve tables without images (no conversion needed)
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize converter.

        Args:
            dry_run: If True, preview changes without modifying files
        """
        self.dry_run = dry_run
        self.stats = {
            "files_scanned": 0,
            "files_modified": 0,
            "tables_converted": 0,
            "tables_skipped": 0
        }
        logger.info(f"TableToColumnConverter initialized (dry_run={dry_run})")

    def has_image(self, element: Tag) -> bool:
        """
        Check if an element or its descendants contain an img tag.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            True if element contains an img tag
        """
        return element.find('img') is not None

    def convert_table_to_columns(self, table: Tag, soup: BeautifulSoup) -> list:
        """
        Convert a table element to Notion column block structure.

        Each table row becomes a separate column list (div with data-notion-column-list).
        This respects the original table layout.

        Args:
            table: BeautifulSoup table Tag
            soup: BeautifulSoup object for creating new tags

        Returns:
            List of div elements with data-notion-column-list structure (one per row)
        """
        column_lists = []

        # Get all rows
        rows = table.find_all('tr')
        if not rows:
            logger.warning("Table has no rows, returning empty list")
            return column_lists

        # Convert each row to a column list
        for row in rows:
            cells = row.find_all(['td', 'th'])
            num_cells = len(cells)

            if num_cells == 0:
                logger.debug("Row has no cells, skipping")
                continue

            # Create column list container for this row
            column_list = soup.new_tag('div')
            column_list['data-notion-column-list'] = ''

            # Calculate column ratio (equal distribution)
            column_ratio = 1.0 / num_cells

            # Create a column for each cell in the row
            for cell in cells:
                # Create column div
                column = soup.new_tag('div')
                column['data-notion-column-ratio'] = f"{column_ratio:.2f}"

                # Transfer cell contents to column
                if cell.string:
                    # Simple text content
                    p = soup.new_tag('p')
                    p.string = cell.string
                    column.append(p)
                else:
                    # Transfer all child elements
                    for child in list(cell.children):
                        if child.name:  # Only copy tag elements, not NavigableStrings
                            column.append(child.extract())
                        elif str(child).strip():  # Copy non-empty text nodes
                            p = soup.new_tag('p')
                            p.string = str(child).strip()
                            column.append(p)

                column_list.append(column)

            column_lists.append(column_list)

        logger.debug(f"Converted table to {len(column_lists)} column lists (one per row)")
        return column_lists

    def process_html(self, html_content: str) -> Tuple[str, int]:
        """
        Process HTML content and convert tables with images to column blocks.

        Args:
            html_content: HTML content as string

        Returns:
            Tuple of (modified HTML content, number of tables converted)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        tables_converted = 0

        # Find all tables
        tables = soup.find_all('table')

        for table in tables:
            # Check if table contains images
            if self.has_image(table):
                logger.info("Found table with images, converting to columns")

                # Convert table to column structure (one column list per row)
                column_blocks = self.convert_table_to_columns(table, soup)

                # Replace table with column blocks
                if column_blocks:
                    # Insert first column block in place of table
                    table.replace_with(column_blocks[0])
                    # Insert remaining column blocks after the first
                    for column_block in column_blocks[1:]:
                        column_blocks[0].insert_after(column_block)
                        column_blocks[0] = column_block  # Update reference for next insertion

                    tables_converted += 1
                else:
                    logger.warning("Table conversion produced no column blocks")
            else:
                logger.debug("Skipping table without images")
                self.stats["tables_skipped"] += 1

        return str(soup), tables_converted

    def process_file(self, file_path: Path) -> bool:
        """
        Process a single HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            True if file was modified, False otherwise
        """
        logger.info(f"Processing file: {file_path}")
        self.stats["files_scanned"] += 1

        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Process HTML
            modified_html, tables_converted = self.process_html(html_content)

            if tables_converted > 0:
                logger.info(f"Converted {tables_converted} table(s) in {file_path.name}")
                self.stats["tables_converted"] += tables_converted

                if not self.dry_run:
                    # Write modified HTML back to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_html)
                    logger.info(f"✅ File updated: {file_path.name}")
                else:
                    logger.info(f"[DRY RUN] Would update file: {file_path.name}")

                self.stats["files_modified"] += 1
                return True
            else:
                logger.debug(f"No tables with images found in {file_path.name}")
                return False

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False

    def process_directory(self, directory: Path, recursive: bool = False) -> dict:
        """
        Process all HTML files in a directory.

        Args:
            directory: Path to directory containing HTML files
            recursive: If True, process subdirectories recursively

        Returns:
            Statistics dictionary
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        logger.info("=" * 80)
        logger.info(f"Processing HTML files in: {directory}")
        logger.info("=" * 80)

        # Find HTML files
        pattern = "**/*.html" if recursive else "*.html"
        html_files = list(directory.glob(pattern))

        if not html_files:
            logger.warning(f"No HTML files found in {directory}")
            return self.stats

        logger.info(f"Found {len(html_files)} HTML file(s)")

        # Process each file
        for i, html_file in enumerate(html_files, 1):
            logger.info(f"[{i}/{len(html_files)}] Processing: {html_file.name}")
            self.process_file(html_file)

        # Summary
        logger.info("=" * 80)
        logger.info("Conversion Summary")
        logger.info("=" * 80)
        logger.info(f"Files scanned:      {self.stats['files_scanned']}")
        logger.info(f"Files modified:     {self.stats['files_modified']}")
        logger.info(f"Tables converted:   {self.stats['tables_converted']}")
        logger.info(f"Tables skipped:     {self.stats['tables_skipped']}")
        logger.info("=" * 80)

        return self.stats


def main(
    directory: Path,
    recursive: bool = False,
    dry_run: bool = False
) -> dict:
    """
    Main function to convert tables in HTML files.

    Args:
        directory: Path to directory containing HTML files
        recursive: If True, process subdirectories recursively
        dry_run: If True, preview changes without modifying files

    Returns:
        Statistics dictionary
    """
    converter = TableToColumnConverter(dry_run=dry_run)
    return converter.process_directory(directory, recursive=recursive)
