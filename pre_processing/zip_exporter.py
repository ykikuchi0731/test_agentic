"""Export ServiceNow articles to ZIP format for Notion import."""
import os
import zipfile
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs
import json
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ZipExporter:
    """Export articles with attachments to ZIP format maintaining link relations."""

    def __init__(self, output_dir: str = './exports'):
        """
        Initialize ZIP exporter.

        Args:
            output_dir: Directory to save ZIP files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ZIP exporter initialized with output dir: {output_dir}")

    def create_article_zip(self, article: Dict[str, Any],
                          attachments: List[Dict[str, Any]],
                          html_content: str) -> str:
        """
        Create a ZIP file for a single article with attachments.

        Args:
            article: Article metadata
            attachments: List of attachment metadata with file paths
            html_content: HTML content of the article

        Returns:
            Path to created ZIP file

        Example:
            zip_path = exporter.create_article_zip(
                article={'number': 'KB0001', 'title': 'My Article'},
                attachments=[{'file_name': 'image.png', 'file_path': '/path/to/image.png'}],
                html_content='<html>...</html>'
            )
        """
        article_number = article.get('number', 'unknown')
        logger.info(f"Creating ZIP for article {article_number}")

        # Create sanitized filename
        safe_name = self._sanitize_filename(article_number)
        zip_path = self.output_dir / f"{safe_name}.zip"

        # Update HTML to fix attachment links
        updated_html, attachment_map = self._update_html_links(html_content, attachments)

        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            metadata = self._create_metadata(article, attachments)
            zf.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))

            # Add HTML content
            zf.writestr('article.html', updated_html)

            # Add attachments
            self._add_attachments_to_zip(zf, attachments, attachment_map)

            logger.info(f"Added {len(attachments)} attachments to ZIP")

        logger.info(f"ZIP created: {zip_path}")
        return str(zip_path)

    def create_bulk_zip(self, articles_data: List[Dict[str, Any]], max_articles_per_zip: int = 300) -> str:
        """
        Create ZIP file(s) containing articles, splitting into multiple ZIPs if needed.

        Args:
            articles_data: List of dictionaries with article, attachments, and html
            max_articles_per_zip: Maximum number of articles per ZIP file (default: 300)

        Returns:
            Path to primary created ZIP file (first one if split)

        Example:
            articles_data = [
                {
                    'article': {...},
                    'attachments': [...],
                    'html_content': '...',
                    'category_path': [...]
                }
            ]
            zip_path = exporter.create_bulk_zip(articles_data, max_articles_per_zip=300)
        """
        from datetime import datetime

        total_articles = len(articles_data)
        logger.info(f"Creating bulk ZIP for {total_articles} articles")

        # Generate timestamp for filename and folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Calculate number of ZIPs needed
        num_zips = (total_articles + max_articles_per_zip - 1) // max_articles_per_zip

        if num_zips > 1:
            logger.info(f"Splitting into {num_zips} ZIP files ({max_articles_per_zip} articles per ZIP)")

        # Root folder name inside ZIP
        root_folder = "(Migration用) Merportal"

        # Articles folder with export timestamp
        articles_folder = f"articles_exported_{timestamp}"

        # Track created ZIP paths
        created_zips = []

        # Process articles in chunks
        for zip_index in range(num_zips):
            start_idx = zip_index * max_articles_per_zip
            end_idx = min(start_idx + max_articles_per_zip, total_articles)
            chunk = articles_data[start_idx:end_idx]

            # Create ZIP filename with suffix if multiple ZIPs
            if num_zips > 1:
                zip_filename = f"servicenow_export_{timestamp}_{zip_index + 1:03d}.zip"
                logger.info(f"Creating ZIP {zip_index + 1}/{num_zips}: {zip_filename} ({len(chunk)} articles)")
            else:
                zip_filename = f"servicenow_export_{timestamp}.zip"

            zip_path = self.output_dir / zip_filename
            created_zips.append(str(zip_path))

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add each article in this chunk
                for i, article_data in enumerate(chunk, 1):
                    article = article_data['article']
                    article_number = article.get('number', f'article_{start_idx + i}')
                    article_title = article.get('short_description', article_number)
                    translations = article_data.get('translations', [])

                    global_index = start_idx + i
                    logger.info(f"Adding article {global_index}/{total_articles}: {article_number}")

                    # Generate filename (combined if translations exist)
                    html_filename, safe_number = self._generate_filename(
                        article, article_number, article_title, translations
                    )

                    # HTML goes in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ folder
                    html_path = f"{root_folder}/{articles_folder}/{html_filename}"

                    # Attachments go in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/attachments_ARTICLE_NUMBER/attachments/ folder
                    article_attachments_dir = f"{root_folder}/{articles_folder}/attachments_{safe_number}/"

                    # Update HTML with correct relative paths to attachments
                    html_content = article_data.get('html_content', '')
                    attachments = article_data.get('attachments', [])
                    updated_html, attachment_map = self._update_html_links(
                        html_content, attachments, f"attachments_{safe_number}"
                    )

                    # Add HTML file in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ folder
                    zf.writestr(html_path, updated_html)

                    # Add attachments in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/attachments_ARTICLE_NUMBER/attachments/ folder
                    if attachments:
                        self._add_attachments_to_zip(zf, attachments, attachment_map, article_attachments_dir)

            logger.info(f"ZIP created: {zip_path}")

        if num_zips > 1:
            logger.info(f"✅ Created {num_zips} ZIP files with {total_articles} total articles")
        else:
            logger.info(f"✅ Bulk ZIP created: {created_zips[0]}")

        # Return the first ZIP path
        return created_zips[0]

    def _generate_filename(self, article: Dict[str, Any], article_number: str,
                          article_title: str, translations: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Generate HTML filename and safe number for article.

        Args:
            article: Article data
            article_number: Article number
            article_title: Article title
            translations: List of translations

        Returns:
            Tuple of (html_filename, safe_number)
        """
        if not translations:
            # Single article without translations
            safe_number = self._sanitize_filename(article_number)
            safe_title = self._sanitize_filename(article_title)
            return f"{safe_number}-{safe_title}.html", safe_number

        # Sort articles by language to ensure consistent ordering (ja before en)
        article_lang = self._extract_language_value(article.get('language', {}))
        articles_by_lang = [(article_lang, article_number, article_title)]

        for trans in translations:
            trans_lang = self._extract_language_value(trans.get('language', {}))
            trans_number = trans.get('number', '')
            trans_title = trans.get('short_description', trans_number)
            articles_by_lang.append((trans_lang, trans_number, trans_title))

        # Sort by language (ja before en)
        articles_by_lang.sort(key=self._lang_sort_key)

        # Build combined filename: KB_JP_KB_EN-TITLE_JP_TITLE_EN.html
        numbers = [self._sanitize_filename(num) for _, num, _ in articles_by_lang]
        titles = [self._sanitize_filename(title) for _, _, title in articles_by_lang]

        combined_number = "_".join(numbers)
        combined_title = "_".join(titles)

        html_filename = f"{combined_number}-{combined_title}.html"
        logger.info(f"  Combined with translations: {html_filename}")

        return html_filename, combined_number

    @staticmethod
    def _extract_language_value(lang: Any) -> str:
        """Extract language value from dict or string."""
        if isinstance(lang, dict):
            return lang.get('value', '')
        return str(lang) if lang else ''

    @staticmethod
    def _lang_sort_key(item: Tuple[str, str, str]) -> Tuple[int, str]:
        """Sort key for language ordering (ja before en, then others)."""
        lang = item[0]
        if lang == 'ja':
            return (0, lang)
        elif lang == 'en':
            return (1, lang)
        else:
            return (2, lang)

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        # Remove or replace unsafe characters
        safe = re.sub(r'[^\w\-_\.]', '_', filename)
        return safe[:200]  # Limit length

    def _extract_attachment_info_from_url(self, url: str) -> Dict[str, Optional[str]]:
        """
        Extract attachment sys_id and filename from ServiceNow URL.

        Args:
            url: ServiceNow attachment URL

        Returns:
            Dictionary with 'sys_id' and 'filename' (may be None if not found)

        Examples:
            - https://instance.service-now.com/sys_attachment.do?sys_id=abc123
            - https://instance.service-now.com/api/now/attachment/abc123/file
            - https://instance.service-now.com/attachment.do?sys_id=abc123&filename=image.png
        """
        result = {'sys_id': None, 'filename': None}

        if not url:
            return result

        try:
            # Decode URL-encoded characters
            url = unquote(url)

            # Parse URL
            parsed = urlparse(url)

            # Method 1: Extract from query parameters (sys_attachment.do?sys_id=XXX)
            if parsed.query:
                params = parse_qs(parsed.query)
                if 'sys_id' in params:
                    result['sys_id'] = params['sys_id'][0]
                if 'filename' in params or 'file_name' in params:
                    result['filename'] = params.get('filename', params.get('file_name', [None]))[0]

            # Method 2: Extract from path (/attachment/XXX/file or /api/now/attachment/XXX/file)
            path_parts = parsed.path.split('/')
            if 'attachment' in path_parts:
                idx = path_parts.index('attachment')
                if idx + 1 < len(path_parts) and path_parts[idx + 1]:
                    # Check if next part is a sys_id (32-character hex string)
                    potential_sys_id = path_parts[idx + 1]
                    if len(potential_sys_id) == 32 and all(c in '0123456789abcdef' for c in potential_sys_id.lower()):
                        result['sys_id'] = potential_sys_id

            # Method 3: Extract filename from path
            if parsed.path:
                # Get last part of path that might be filename
                path_filename = parsed.path.split('/')[-1]
                # Only consider it a filename if it has an extension and is not a servlet (.do)
                if ('.' in path_filename and
                    path_filename not in ['file', 'download'] and
                    not path_filename.endswith('.do')):
                    result['filename'] = path_filename

        except Exception as e:
            logger.debug(f"Error parsing attachment URL {url}: {e}")

        return result

    def _update_html_links(self, html_content: str,
                          attachments: List[Dict[str, Any]],
                          article_number: Optional[str] = None) -> tuple:
        """
        Update HTML to point to local attachment files.

        Args:
            html_content: Original HTML content
            attachments: List of attachments
            article_number: Folder prefix for creating relative paths (e.g., "attachments_KB0001")

        Returns:
            Tuple of (updated_html, attachment_map_for_zip)
            - attachment_map_for_zip contains paths for ZIP file structure (relative to base_dir)
            - HTML links will be: {article_number}/attachments/filename (e.g., attachments_KB0001/attachments/file.png)
        """
        if not html_content or not attachments:
            return html_content, {}

        soup = BeautifulSoup(html_content, 'lxml')
        attachment_map_for_zip = {}  # For _add_attachments_to_zip (relative to base_dir)
        attachment_map_for_html = {}  # For HTML updates (relative to HTML file location)

        # Map attachment sys_ids and filenames to local paths
        for i, att in enumerate(attachments):
            sys_id = att.get('sys_id', '')
            file_name = att.get('file_name', f'attachment_{i}')
            safe_name = self._sanitize_filename(file_name)

            # Path for ZIP structure (relative to base_dir which is articles/NUMBER/)
            zip_path = f"attachments/{safe_name}"
            attachment_map_for_zip[sys_id] = zip_path

            # Path for HTML (relative to HTML file location in articles/)
            if article_number:
                html_path = f"{article_number}/attachments/{safe_name}"
            else:
                html_path = f"attachments/{safe_name}"
            attachment_map_for_html[sys_id] = html_path

        # Update all element types (img, video, source, a)
        elements_config = [
            ('img', 'src'),
            ('video', 'src'),
            ('source', 'src'),
            ('a[href]', 'href')
        ]

        for selector, attr in elements_config:
            for element in soup.select(selector):
                url = element.get(attr, '')
                if not url:
                    continue

                updated_url = self._find_attachment_match(
                    url, attachments, attachment_map_for_html
                )

                if updated_url:
                    element[attr] = updated_url
                    element_type = element.name
                    logger.debug(f"Updated {element_type} {attr} to {updated_url}")

        return str(soup), attachment_map_for_zip

    def _find_attachment_match(self, url: str, attachments: List[Dict[str, Any]],
                               attachment_map: Dict[str, str]) -> Optional[str]:
        """
        Find matching attachment for a URL.

        Args:
            url: URL to match
            attachments: List of attachments
            attachment_map: Map of sys_id to local path

        Returns:
            Local path if match found, None otherwise
        """
        # Skip non-attachment URLs (external links, etc.)
        # Check for ServiceNow attachment indicators
        if not any(pattern in url for pattern in ['attachment', 'sys_attachment']):
            return None

        # Extract attachment info from URL
        url_info = self._extract_attachment_info_from_url(url)
        url_sys_id = url_info.get('sys_id')
        url_filename = url_info.get('filename')

        # Try matching by sys_id from URL
        if url_sys_id and url_sys_id in attachment_map:
            logger.debug(f"Matched URL by sys_id: {url_sys_id}")
            return attachment_map[url_sys_id]

        # Try matching by filename from URL
        if url_filename:
            for att in attachments:
                file_name = att.get('file_name', '')
                if file_name == url_filename:
                    sys_id = att.get('sys_id', '')
                    matched_path = attachment_map.get(sys_id)
                    if matched_path:
                        logger.debug(f"Matched URL by filename: {url_filename}")
                        return matched_path

        # Fallback: simple substring matching
        for sys_id, html_path in attachment_map.items():
            if sys_id and sys_id in url:
                logger.debug(f"Matched URL by substring: {sys_id}")
                return html_path

        # Log when no match found for ServiceNow attachment
        logger.warning(
            f"Attachment not found in downloads: URL={url} | "
            f"sys_id={url_sys_id} | filename={url_filename} | "
            f"This attachment may be missing, deleted, or from an old article version. "
            f"The original URL will be kept in the HTML."
        )
        return None

    def _create_metadata(self, article: Dict[str, Any],
                        attachments: List[Dict[str, Any]],
                        category_path: Optional[List[Dict[str, Any]]] = None,
                        article_number: Optional[str] = None) -> Dict:
        """Create metadata JSON for the article."""
        metadata = {
            "article_number": article.get('number', ''),
            "title": article.get('short_description', ''),
            "sys_id": article.get('sys_id', ''),
            "workflow_state": article.get('workflow_state', ''),
            "created_on": article.get('sys_created_on', ''),
            "updated_on": article.get('sys_updated_on', ''),
            "author": article.get('author', {}),
            "category_path": [cat.get('label', '') for cat in (category_path or [])]
                            if category_path else [],
            "attachments": [
                {
                    "file_name": att.get('file_name', ''),
                    "size_bytes": att.get('size_bytes', 0),
                    "content_type": att.get('content_type', ''),
                    "local_path": f"attachments/{self._sanitize_filename(att.get('file_name', ''))}"
                }
                for att in attachments
            ]
        }
        return metadata

    def _create_bulk_index(self, articles_data: List[Dict[str, Any]]) -> Dict:
        """Create index file for bulk export."""
        return {
            "export_info": {
                "total_articles": len(articles_data),
                "export_date": "2025-10-31",
                "source": "ServiceNow Knowledge Base"
            },
            "articles": [
                {
                    "article_number": data['article'].get('number', ''),
                    "title": data['article'].get('short_description', ''),
                    "category": ' > '.join([c.get('label', '')
                                           for c in data.get('category_path', [])]),
                    "directory": f"articles/{self._sanitize_filename(data['article'].get('number', ''))}/",
                    "attachment_count": len(data.get('attachments', []))
                }
                for data in articles_data
            ]
        }

    def _add_attachments_to_zip(self, zf: zipfile.ZipFile,
                                attachments: List[Dict[str, Any]],
                                attachment_map: Dict[str, str],
                                base_dir: str = "") -> None:
        """Add attachment files to ZIP, deduplicating by filename."""
        added_paths = set()

        for att in attachments:
            file_path = att.get('file_path')
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"Attachment file not found: {file_path}")
                continue

            # Get local path in ZIP
            sys_id = att.get('sys_id', '')
            zip_path = attachment_map.get(sys_id,
                                         f"attachments/{self._sanitize_filename(att['file_name'])}")

            # Add base directory if provided
            if base_dir:
                zip_path = f"{base_dir}{zip_path}"

            # Skip if already added (deduplicate by ZIP path)
            if zip_path in added_paths:
                logger.debug(f"Skipping duplicate attachment: {zip_path}")
                continue

            # Add file to ZIP
            zf.write(file_path, zip_path)
            added_paths.add(zip_path)
            logger.debug(f"Added attachment: {zip_path}")
