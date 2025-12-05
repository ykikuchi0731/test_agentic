"""Scan HTML files for invisible <div class="accshow"> elements.

This module scans HTML files and identifies <div> elements with class 'accshow'
that are not visible after rendering due to CSS rules defined in <style> tags.
These are typically accordion-style widgets that are initially hidden.

Results are reported in CSV format.
"""
import logging
import csv
from pathlib import Path
from typing import List, Dict, Tuple, Set
from bs4 import BeautifulSoup, Tag
import re
import tinycss2

logger = logging.getLogger(__name__)


class DivAccshowScanner:
    """
    Scan HTML files for invisible <div> elements with class 'accshow'.

    This scanner specifically targets accordion-style content that is initially
    hidden via CSS rules. These are typically <div class="accshow"> elements
    that are invisible due to CSS properties like:
    - opacity: 0
    - height: 0 (combined with overflow: hidden)
    - display: none
    - visibility: hidden

    Checks CSS rules from <style> tags to determine visibility.
    """

    # CSS properties that make elements invisible
    INVISIBLE_STYLES = [
        (r'display\s*:\s*none', 'display:none'),
        (r'visibility\s*:\s*hidden', 'visibility:hidden'),
        (r'opacity\s*:\s*0(?:\.0+)?(?:\s|;|$)', 'opacity:0'),
        (r'height\s*:\s*0(?:pt|px)?(?:\s|;|$)', 'height:0'),
        (r'width\s*:\s*0(?:pt|px)?(?:\s|;|$)', 'width:0'),
    ]

    def __init__(self):
        """Initialize scanner."""
        self.stats = {
            "files_scanned": 0,
            "files_with_invisible": 0,
            "invisible_elements": 0
        }
        self.results = []
        self.css_rules = {}  # Maps selectors to property sets
        logger.info("InvisibleElementScanner initialized")

    def parse_css_rules(self, soup: BeautifulSoup) -> Dict[str, Set[str]]:
        """
        Parse CSS rules from <style> tags and build a map of selectors to invisible properties.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary mapping CSS selectors to set of invisible property reasons
        """
        css_invisibility_map = {}

        # Find all style tags
        style_tags = soup.find_all('style')

        for style_tag in style_tags:
            css_content = style_tag.string
            if not css_content:
                continue

            try:
                # Parse CSS using tinycss2
                rules = tinycss2.parse_stylesheet(css_content, skip_comments=True, skip_whitespace=True)

                for rule in rules:
                    if rule.type == 'qualified-rule':
                        # Get selector
                        selector_tokens = rule.prelude
                        selector = ''.join(token.serialize() for token in selector_tokens).strip()

                        # Parse declarations
                        declarations = tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True)

                        invisible_properties = set()
                        declaration_dict = {}

                        for decl in declarations:
                            if decl.type == 'declaration':
                                prop_name = decl.name.lower()
                                prop_value = ''.join(token.serialize() for token in decl.value).strip().lower()
                                declaration_dict[prop_name] = prop_value

                        # Check for invisible properties
                        if declaration_dict.get('display') == 'none':
                            invisible_properties.add('css_rule:display:none')

                        if declaration_dict.get('visibility') == 'hidden':
                            invisible_properties.add('css_rule:visibility:hidden')

                        if declaration_dict.get('opacity') in ('0', '0.0', '0.00'):
                            invisible_properties.add('css_rule:opacity:0')

                        # Check for height:0 (standalone or with overflow:hidden)
                        height_val = declaration_dict.get('height', '')
                        if height_val in ('0', '0px', '0pt'):
                            if declaration_dict.get('overflow') == 'hidden':
                                invisible_properties.add('css_rule:height:0+overflow:hidden')
                            else:
                                invisible_properties.add('css_rule:height:0')

                        # Check for width:0 (standalone)
                        width_val = declaration_dict.get('width', '')
                        if width_val in ('0', '0px', '0pt'):
                            invisible_properties.add('css_rule:width:0')

                        if invisible_properties:
                            css_invisibility_map[selector] = invisible_properties

            except Exception as e:
                logger.debug(f"Error parsing CSS: {e}")
                continue

        return css_invisibility_map

    def element_matches_selector(self, element: Tag, selector: str) -> bool:
        """
        Check if an element matches a CSS selector (simplified matching).

        Args:
            element: BeautifulSoup Tag element
            selector: CSS selector string

        Returns:
            True if element matches selector
        """
        try:
            # Use BeautifulSoup's CSS selector matching
            # Check if element matches by seeing if it's in the results
            results = element.find_parents() or []
            results.insert(0, element)

            # Try to select from root
            root = element
            while root.parent and root.parent.name:
                root = root.parent

            matches = root.select(selector) if hasattr(root, 'select') else []
            return element in matches
        except Exception:
            return False

    def check_css_rules(self, element: Tag, css_rules: Dict[str, Set[str]]) -> Tuple[bool, str]:
        """
        Check if element is hidden by CSS rules.

        Args:
            element: BeautifulSoup Tag element
            css_rules: Dictionary of CSS rules

        Returns:
            Tuple of (is_invisible: bool, reason: str)
        """
        for selector, invisible_props in css_rules.items():
            if self.element_matches_selector(element, selector):
                # Return first matching invisible property
                return (True, list(invisible_props)[0])

        return (False, '')

    def check_inline_style(self, element: Tag) -> Tuple[bool, str]:
        """
        Check if element has inline style that makes it invisible.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Tuple of (is_invisible: bool, reason: str)
        """
        style = element.get('style', '')
        if not style:
            return (False, '')

        style_lower = style.lower()

        # Check each invisible style pattern
        for pattern, reason in self.INVISIBLE_STYLES:
            if re.search(pattern, style_lower):
                return (True, f'inline_style:{reason}')

        return (False, '')

    def is_invisible(self, element: Tag, css_rules: Dict[str, Set[str]]) -> Tuple[bool, str]:
        """
        Check if an element is invisible due to CSS styles.

        Specifically targets <div> elements with class 'accshow' that are invisible.
        Checks both CSS rules from <style> tags AND inline styles.

        Args:
            element: BeautifulSoup Tag element
            css_rules: Dictionary of CSS rules from parse_css_rules

        Returns:
            Tuple of (is_invisible: bool, reason: str)
        """
        # Only check <div> elements with 'accshow' class
        if element.name != 'div':
            return (False, '')

        classes = element.get('class', [])
        if isinstance(classes, list):
            class_list = classes
        else:
            class_list = [classes] if classes else []

        if 'accshow' not in class_list:
            return (False, '')

        # Check if this accshow div is invisible via CSS rules
        is_hidden, reason = self.check_css_rules(element, css_rules)
        if is_hidden:
            return (True, reason)

        # Check if this accshow div is invisible via inline style
        is_hidden, reason = self.check_inline_style(element)
        if is_hidden:
            return (True, reason)

        return (False, '')

    def get_element_info(self, element: Tag) -> Dict[str, str]:
        """
        Extract identifying information from an element.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Dictionary with element information
        """
        info = {
            'tag': element.name,
            'id': element.get('id', ''),
            'class': ' '.join(element.get('class', [])) if element.get('class') else '',
            'style': element.get('style', ''),
        }

        # Get text content (truncated)
        text = element.get_text(strip=True)
        info['text_preview'] = text[:50] + '...' if len(text) > 50 else text

        return info

    def get_element_path(self, element: Tag) -> str:
        """
        Get a CSS selector-like path to the element.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            Path string (e.g., "div > p.myclass > span")
        """
        path_parts = []
        current = element

        while current and current.name:
            part = current.name
            if current.get('id'):
                part += f"#{current.get('id')}"
            elif current.get('class'):
                classes = current.get('class')
                if isinstance(classes, list) and classes:
                    part += f".{classes[0]}"
            path_parts.insert(0, part)
            current = current.parent

        return ' > '.join(path_parts[-5:])  # Last 5 levels to keep it readable

    def scan_html(self, html_content: str, file_path: Path) -> List[Dict[str, str]]:
        """
        Scan HTML content for invisible elements.

        Args:
            html_content: HTML string to scan
            file_path: Path to the HTML file (for reporting)

        Returns:
            List of dictionaries with invisible element information
        """
        invisible_elements = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Parse CSS rules first
            css_rules = self.parse_css_rules(soup)
            logger.debug(f"Found {len(css_rules)} CSS rules with invisible properties")

            # Find all elements (excluding script, style tags)
            all_elements = soup.find_all(True)

            for element in all_elements:
                # Skip script and style tags
                if element.name in ['script', 'style', 'meta', 'link']:
                    continue

                is_invisible, reason = self.is_invisible(element, css_rules)

                if is_invisible:
                    info = self.get_element_info(element)
                    invisible_elements.append({
                        'file': str(file_path),
                        'tag': info['tag'],
                        'id': info['id'],
                        'class': info['class'],
                        'reason': reason,
                        'style': info['style'],
                        'text_preview': info['text_preview'],
                        'path': self.get_element_path(element)
                    })

            return invisible_elements

        except Exception as e:
            logger.error(f"Error scanning HTML in {file_path}: {e}")
            return []

    def process_file(self, file_path: Path) -> List[Dict[str, str]]:
        """
        Process a single HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            List of invisible elements found
        """
        logger.info(f"Processing file: {file_path}")
        self.stats["files_scanned"] += 1

        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Scan for invisible elements
            invisible_elements = self.scan_html(html_content, file_path)

            if invisible_elements:
                logger.info(f"Found {len(invisible_elements)} invisible element(s) in {file_path.name}")
                self.stats["files_with_invisible"] += 1
                self.stats["invisible_elements"] += len(invisible_elements)
                self.results.extend(invisible_elements)
            else:
                logger.debug(f"No invisible elements found in {file_path.name}")

            return invisible_elements

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []

    def process_directory(self, directory: Path, recursive: bool = False) -> List[Dict[str, str]]:
        """
        Process all HTML files in a directory.

        Args:
            directory: Path to directory containing HTML files
            recursive: If True, process subdirectories recursively

        Returns:
            List of all invisible elements found
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
        logger.info(f"Files with invisible:    {self.stats['files_with_invisible']}")
        logger.info(f"Invisible elements:      {self.stats['invisible_elements']}")
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
                fieldnames = ['file', 'tag', 'id', 'class', 'reason', 'style', 'text_preview', 'path']
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
    recursive: bool = False
) -> Dict[str, int]:
    """
    Main function to scan HTML files for invisible <div class="accshow"> elements.

    Args:
        directory: Path to directory containing HTML files
        output_csv: Path to output CSV file
        recursive: If True, process subdirectories recursively

    Returns:
        Statistics dictionary
    """
    scanner = DivAccshowScanner()
    scanner.process_directory(directory, recursive=recursive)
    scanner.write_csv_report(output_csv)
    return scanner.stats
