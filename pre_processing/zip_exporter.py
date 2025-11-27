"""Export ServiceNow articles to ZIP format for Notion import."""
import os
import zipfile
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
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
    
    def create_bulk_zip(self, articles_data: List[Dict[str, Any]]) -> str:
        """
        Create a single ZIP file containing multiple articles.
        
        Args:
            articles_data: List of dictionaries with article, attachments, and html
            
        Returns:
            Path to created ZIP file
            
        Example:
            articles_data = [
                {
                    'article': {...},
                    'attachments': [...],
                    'html_content': '...',
                    'category_path': [...]
                }
            ]
            zip_path = exporter.create_bulk_zip(articles_data)
        """
        from datetime import datetime

        logger.info(f"Creating bulk ZIP for {len(articles_data)} articles")

        # Generate timestamp for filename and folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = self.output_dir / f"servicenow_export_{timestamp}.zip"

        # Root folder name inside ZIP
        root_folder = "(Migration用) Merportal"

        # Articles folder with export timestamp
        articles_folder = f"articles_exported_{timestamp}"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add each article
            for i, article_data in enumerate(articles_data, 1):
                article = article_data['article']
                article_number = article.get('number', f'article_{i}')
                article_title = article.get('short_description', article_number)
                translations = article_data.get('translations', [])

                logger.info(f"Adding article {i}/{len(articles_data)}: {article_number}")

                # Create combined filename if there are translations
                if translations:
                    # Sort articles by language to ensure consistent ordering (ja before en)
                    article_lang = article.get('language', {})
                    if isinstance(article_lang, dict):
                        article_lang = article_lang.get('value', '')

                    articles_by_lang = [(article_lang, article_number, article_title)]
                    for trans in translations:
                        trans_lang = trans.get('language', {})
                        if isinstance(trans_lang, dict):
                            trans_lang = trans_lang.get('value', '')
                        trans_number = trans.get('number', '')
                        trans_title = trans.get('short_description', trans_number)
                        articles_by_lang.append((trans_lang, trans_number, trans_title))

                    # Sort by language (ja before en)
                    # Create a sort key that puts 'ja' first, then 'en', then others alphabetically
                    def lang_sort_key(item):
                        lang = item[0]
                        if lang == 'ja':
                            return (0, lang)
                        elif lang == 'en':
                            return (1, lang)
                        else:
                            return (2, lang)

                    articles_by_lang.sort(key=lang_sort_key)

                    # Build combined filename: KB_JP_KB_EN-TITLE_JP_TITLE_EN.html
                    numbers = [self._sanitize_filename(num) for _, num, _ in articles_by_lang]
                    titles = [self._sanitize_filename(title) for _, _, title in articles_by_lang]

                    combined_number = "_".join(numbers)
                    combined_title = "_".join(titles)

                    html_filename = f"{combined_number}-{combined_title}.html"
                    safe_number = combined_number  # For attachment directory

                    logger.info(f"  Combined with translations: {html_filename}")
                else:
                    # Single article without translations
                    safe_number = self._sanitize_filename(article_number)
                    safe_title = self._sanitize_filename(article_title)
                    html_filename = f"{safe_number}-{safe_title}.html"

                # HTML goes in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ folder
                html_path = f"{root_folder}/{articles_folder}/{html_filename}"

                # Attachments go in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ARTICLE_NUMBER/attachments/ folder
                article_attachments_dir = f"{root_folder}/{articles_folder}/{safe_number}/"

                # Update HTML with correct relative paths to attachments
                # Since HTML is in articles_exported_YYYYMMDD_HHMM/ and attachments are in articles_exported_YYYYMMDD_HHMM/ARTICLE_NUMBER/attachments/
                # The relative path from HTML should be: ARTICLE_NUMBER/attachments/filename
                html_content = article_data.get('html_content', '')
                attachments = article_data.get('attachments', [])
                updated_html, attachment_map = self._update_html_links(
                    html_content, attachments, safe_number
                )

                # Add HTML file in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ folder
                zf.writestr(html_path, updated_html)

                # Add attachments in (Migration用) Merportal/articles_exported_YYYYMMDD_HHMM/ARTICLE_NUMBER/attachments/ folder
                if attachments:
                    self._add_attachments_to_zip(zf, attachments, attachment_map, article_attachments_dir)
        
        logger.info(f"Bulk ZIP created: {zip_path}")
        return str(zip_path)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        # Remove or replace unsafe characters
        safe = re.sub(r'[^\w\-_\.]', '_', filename)
        return safe[:200]  # Limit length
    
    def _update_html_links(self, html_content: str,
                          attachments: List[Dict[str, Any]],
                          article_number: Optional[str] = None) -> tuple:
        """
        Update HTML to point to local attachment files.

        Args:
            html_content: Original HTML content
            attachments: List of attachments
            article_number: Article number for creating relative paths (optional)

        Returns:
            Tuple of (updated_html, attachment_map_for_zip)
            - attachment_map_for_zip contains paths for ZIP file structure (without article_number prefix)
        """
        if not html_content or not attachments:
            return html_content, {}

        soup = BeautifulSoup(html_content, 'lxml')
        attachment_map_for_zip = {}  # For _add_attachments_to_zip (relative to base_dir)
        attachment_map_for_html = {}  # For HTML updates (relative to HTML file location)

        # Map attachment sys_ids to local filenames
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

        # Update image sources with HTML paths
        for img in soup.find_all('img'):
            src = img.get('src', '')
            # Check if src references an attachment sys_id
            for sys_id, html_path in attachment_map_for_html.items():
                if sys_id in src:
                    img['src'] = html_path
                    logger.debug(f"Updated image src to {html_path}")

        # Update links with HTML paths
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for sys_id, html_path in attachment_map_for_html.items():
                if sys_id in href:
                    link['href'] = html_path
                    logger.debug(f"Updated link href to {html_path}")

        return str(soup), attachment_map_for_zip
    
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

