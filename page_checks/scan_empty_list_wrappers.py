"""Scan HTML files for empty list wrapper elements that cause blank lines in Notion.

This module scans HTML files and identifies excessive empty <li> wrapper elements
with list-style-type:none that contain no content but create unwanted blank lines
when imported to Notion. These are typically used for indentation in the source
but render poorly in Notion's block structure.

Results are reported in CSV format.
"""
import logging
import csv
from pathlib import Path
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup, Tag
import re

logger = logging.getLogger(__name__)


class EmptyListWrapperScanner:
    """
    Scan HTML files for empty list wrapper elements that cause formatting issues.

    This scanner identifies nested <li> elements that:
    - Have list-style-type: none (or no list marker)
    - Contain only whitespace or a single <ul>/<ol> child
    - Create chains of 2+ such elements (causing multiple blank lines)

    These structures render as excessive blank lines in Notion, harming usability.
    """

    def __init__(self, min_nesting_depth: int = 2, min_wrapper_count: int = 3):
        """
        Initialize scanner.

        Args:
            min_nesting_depth: Minimum nesting depth to report (default: 2)
            min_wrapper_count: Minimum empty wrappers to report file (default: 3)
        """
        self.min_nesting_depth = min_nesting_depth
        self.min_wrapper_count = min_wrapper_count
        self.stats = {
            "files_scanned": 0,
            "files_with_wrappers": 0,
            "total_wrapper_chains": 0,
            "total_empty_wrappers": 0
        }
        self.results = []
        logger.info(f"EmptyListWrapperScanner initialized (min_depth={min_nesting_depth}, min_count={min_wrapper_count})")

    def is_empty_wrapper_li(self, li_element: Tag) -> bool:
        """
        Check if an <li> element is an empty wrapper.

        An empty wrapper is an <li> that:
        - Has list-style-type: none (explicitly or via no content)
        - Contains only whitespace and/or a single <ul>/<ol> element
        - Has no meaningful text content

        Args:
            li_element: BeautifulSoup Tag for <li> element

        Returns:
            True if this is an empty wrapper element
        """
        # Check if it has list-style-type: none
        style = li_element.get('style', '')
        has_no_marker = 'list-style-type' in style and 'none' in style

        # Get direct children (excluding whitespace text nodes)
        children = [child for child in li_element.children if child.name]

        # Check if it only contains a single ul/ol
        if len(children) == 1 and children[0].name in ['ul', 'ol']:
            # Check if there's any meaningful text directly in this li (not in children)
            direct_text = ''.join([str(c) for c in li_element.children if not hasattr(c, 'name')]).strip()
            if not direct_text:
                return True

        # Also check if it's an empty li with only nested lists
        if has_no_marker and len(children) <= 1:
            text_content = li_element.get_text(strip=True)
            # If the li has very little direct text and contains lists, it's likely a wrapper
            if children and children[0].name in ['ul', 'ol']:
                return True

        return False

    def find_wrapper_chain(self, li_element: Tag) -> Tuple[int, List[Tag]]:
        """
        Find the chain of empty wrapper <li> elements.

        Starting from an <li>, traverse down through nested empty wrappers
        until we find content or reach the end.

        Args:
            li_element: Starting <li> element

        Returns:
            Tuple of (depth, list of wrapper elements in chain)
        """
        chain = []
        current = li_element

        while current and current.name == 'li':
            if not self.is_empty_wrapper_li(current):
                break

            chain.append(current)

            # Find the child ul/ol
            child_list = None
            for child in current.children:
                if hasattr(child, 'name') and child.name in ['ul', 'ol']:
                    child_list = child
                    break

            if not child_list:
                break

            # Find the child li within the ul/ol
            child_li = None
            for child in child_list.children:
                if hasattr(child, 'name') and child.name == 'li':
                    child_li = child
                    break

            if not child_li:
                break

            current = child_li

        return (len(chain), chain)

    def get_line_number(self, element: Tag, html_content: str) -> int:
        """
        Estimate the line number of an element in the HTML.

        Args:
            element: BeautifulSoup Tag element
            html_content: Original HTML content

        Returns:
            Approximate line number (1-indexed)
        """
        try:
            # Get a unique string from the element
            element_str = str(element)[:100]
            # Find position in HTML
            pos = html_content.find(element_str[:50])
            if pos >= 0:
                # Count newlines up to this position
                return html_content[:pos].count('\n') + 1
        except Exception:
            pass
        return 0

    def get_element_path(self, element: Tag) -> str:
        """
        Get a CSS selector-like path to the element.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Path string
        """
        path_parts = []
        current = element

        depth = 0
        while current and current.name and depth < 5:
            part = current.name
            if current.get('id'):
                part += f"#{current.get('id')}"
            elif current.get('class'):
                classes = current.get('class')
                if isinstance(classes, list) and classes:
                    part += f".{classes[0]}"
            path_parts.insert(0, part)
            current = current.parent
            depth += 1

        return ' > '.join(path_parts)

    def scan_html(self, html_content: str, file_path: Path) -> List[Dict[str, any]]:
        """
        Scan HTML content for empty list wrapper chains.

        Args:
            html_content: HTML string to scan
            file_path: Path to the HTML file (for reporting)

        Returns:
            List of dictionaries with wrapper chain information
        """
        wrapper_chains = []
        processed_elements = set()  # Avoid double-counting

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all <li> elements
            all_li_elements = soup.find_all('li')

            for li_element in all_li_elements:
                # Skip if already processed as part of a chain
                if id(li_element) in processed_elements:
                    continue

                # Check if this is the start of an empty wrapper chain
                if self.is_empty_wrapper_li(li_element):
                    depth, chain = self.find_wrapper_chain(li_element)

                    # Only report if it meets threshold
                    if depth >= self.min_nesting_depth:
                        # Mark all elements in chain as processed
                        for elem in chain:
                            processed_elements.add(id(elem))

                        line_number = self.get_line_number(li_element, html_content)

                        wrapper_chains.append({
                            'file': str(file_path),
                            'line_number': line_number,
                            'nesting_depth': depth,
                            'wrapper_count': len(chain),
                            'parent_path': self.get_element_path(li_element)
                        })

            return wrapper_chains

        except Exception as e:
            logger.error(f"Error scanning HTML in {file_path}: {e}")
            return []

    def process_file(self, file_path: Path) -> List[Dict[str, any]]:
        """
        Process a single HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            List of wrapper chains found
        """
        logger.info(f"Processing file: {file_path}")
        self.stats["files_scanned"] += 1

        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Scan for empty wrapper chains
            wrapper_chains = self.scan_html(html_content, file_path)

            if wrapper_chains:
                total_wrappers = sum(chain['wrapper_count'] for chain in wrapper_chains)

                # Only report if total wrappers meet threshold
                if total_wrappers >= self.min_wrapper_count:
                    logger.info(f"Found {len(wrapper_chains)} wrapper chain(s) with {total_wrappers} total empty wrappers in {file_path.name}")
                    self.stats["files_with_wrappers"] += 1
                    self.stats["total_wrapper_chains"] += len(wrapper_chains)
                    self.stats["total_empty_wrappers"] += total_wrappers
                    self.results.extend(wrapper_chains)
                    return wrapper_chains
            else:
                logger.debug(f"No empty wrapper chains found in {file_path.name}")

            return []

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []

    def process_directory(self, directory: Path, recursive: bool = False) -> List[Dict[str, any]]:
        """
        Process all HTML files in a directory.

        Args:
            directory: Path to directory containing HTML files
            recursive: If True, process subdirectories recursively

        Returns:
            List of all wrapper chains found
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        logger.info("=" * 80)
        logger.info(f"Scanning HTML files in: {directory}")
        logger.info("=" * 80)

        # Find HTML files
        pattern = "**/*.html" if recursive else "*.html"
        html_files = list(directory.glob(pattern))

        if not html_files:
            logger.warning(f"No HTML files found in {directory}")
            return []

        logger.info(f"Found {len(html_files)} HTML file(s)")

        # Process each file
        for i, html_file in enumerate(html_files, 1):
            logger.info(f"[{i}/{len(html_files)}] Processing: {html_file.name}")
            self.process_file(html_file)

        # Summary
        logger.info("=" * 80)
        logger.info("Scan Summary")
        logger.info("=" * 80)
        logger.info(f"Files scanned:           {self.stats['files_scanned']}")
        logger.info(f"Files with wrappers:     {self.stats['files_with_wrappers']}")
        logger.info(f"Total wrapper chains:    {self.stats['total_wrapper_chains']}")
        logger.info(f"Total empty wrappers:    {self.stats['total_empty_wrappers']}")
        logger.info("=" * 80)

        return self.results

    def write_csv_report(self, output_path: Path) -> None:
        """
        Write scan results to CSV file.

        Args:
            output_path: Path to output CSV file
        """
        if not self.results:
            logger.warning("No results to write")
            return

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['file', 'line_number', 'nesting_depth', 'wrapper_count', 'parent_path']
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                writer.writerows(self.results)

            logger.info(f"✅ CSV report written to: {output_path}")
            logger.info(f"   Total rows: {len(self.results)}")

        except Exception as e:
            logger.error(f"Error writing CSV report: {e}")
            raise


def main(
    directory: Path,
    output_csv: Path,
    recursive: bool = False,
    min_nesting_depth: int = 2,
    min_wrapper_count: int = 3
) -> Dict[str, int]:
    """
    Main function to scan HTML files for empty list wrapper elements.

    Args:
        directory: Path to directory containing HTML files
        output_csv: Path to output CSV file
        recursive: If True, process subdirectories recursively
        min_nesting_depth: Minimum nesting depth to report (default: 2)
        min_wrapper_count: Minimum empty wrappers per file to report (default: 3)

    Returns:
        Statistics dictionary
    """
    scanner = EmptyListWrapperScanner(
        min_nesting_depth=min_nesting_depth,
        min_wrapper_count=min_wrapper_count
    )
    scanner.process_directory(directory, recursive=recursive)
    scanner.write_csv_report(output_csv)
    return scanner.stats
