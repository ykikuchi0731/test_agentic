"""Process iframe-embedded Google Docs and Slides in HTML content."""
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IframeProcessor:
    """Process and transform iframe elements in HTML content."""

    def __init__(self, google_docs_exporter=None):
        """
        Initialize iframe processor.

        Args:
            google_docs_exporter: Optional GoogleDocsBrowserExporter instance
                                  for downloading Google Docs
        """
        self.google_docs_exporter = google_docs_exporter
        self.parser = "lxml"

        # URL patterns for Google Docs and Slides
        self.google_docs_pattern = re.compile(
            r"https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)"
        )
        self.google_slides_pattern = re.compile(
            r"https://docs\.google\.com/presentation/d/([a-zA-Z0-9-_]+)"
        )

    def detect_iframes(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Detect all iframe elements in HTML content.

        Args:
            html_content: HTML string to analyze

        Returns:
            List of iframe information dictionaries:
                {
                    'src': str (iframe source URL),
                    'type': str ('google_docs', 'google_slides', 'other'),
                    'file_id': str (Google Doc/Slide ID if applicable),
                    'element': BeautifulSoup Tag object
                }
        """
        if not html_content:
            return []

        try:
            soup = BeautifulSoup(html_content, self.parser)
            iframes = []

            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "")

                iframe_info = {
                    "src": src,
                    "type": "other",
                    "file_id": None,
                    "element": iframe,
                }

                # Check if it's a Google Doc
                docs_match = self.google_docs_pattern.search(src)
                if docs_match:
                    iframe_info["type"] = "google_docs"
                    iframe_info["file_id"] = docs_match.group(1)
                    logger.debug(f"Found Google Docs iframe: {iframe_info['file_id']}")

                # Check if it's a Google Slides
                slides_match = self.google_slides_pattern.search(src)
                if slides_match:
                    iframe_info["type"] = "google_slides"
                    iframe_info["file_id"] = slides_match.group(1)
                    logger.debug(f"Found Google Slides iframe: {iframe_info['file_id']}")

                iframes.append(iframe_info)

            logger.info(f"Found {len(iframes)} iframes in HTML")
            return iframes

        except Exception as e:
            logger.error(f"Error detecting iframes: {e}")
            return []

    def is_iframe_only_content(self, html_content: str) -> bool:
        """
        Check if HTML content contains only an iframe (no other meaningful content).

        Args:
            html_content: HTML string to analyze

        Returns:
            True if content is iframe-only, False otherwise

        Logic:
            - Returns True if there's at least one iframe
            - AND there's no other significant content (text, images, etc.)
        """
        if not html_content:
            return False

        try:
            soup = BeautifulSoup(html_content, self.parser)

            # Check if there are any iframes
            iframes = soup.find_all("iframe")
            if not iframes:
                return False

            # Remove iframes temporarily to check remaining content
            soup_copy = BeautifulSoup(str(soup), self.parser)
            for iframe in soup_copy.find_all("iframe"):
                iframe.decompose()

            # Remove scripts, styles, and whitespace
            for element in soup_copy(["script", "style"]):
                element.decompose()

            # Get remaining text
            text = soup_copy.get_text(strip=True)

            # Check if there's any meaningful remaining content
            # (more than just a few characters/whitespace)
            has_other_content = len(text) > 10  # Threshold for "meaningful" content

            result = not has_other_content
            logger.debug(
                f"Iframe-only check: {result} (remaining text length: {len(text)})"
            )
            return result

        except Exception as e:
            logger.error(f"Error checking iframe-only content: {e}")
            return False

    def process_google_docs_iframe(
        self, iframe_info: Dict[str, Any], article_title: str = "document", language_suffix: str = "", article_number: str = ""
    ) -> Dict[str, Any]:
        """
        Process Google Docs iframe: download as DOCX and prepare for removal.

        Args:
            iframe_info: Iframe information dictionary from detect_iframes()
            article_title: Article title for naming downloaded file
            language_suffix: Optional language suffix (e.g., '_ja', '_en') for translations
            article_number: Optional article number for filename prefix (e.g., 'KB0001')

        Returns:
            Processing result:
                {
                    'success': bool,
                    'action': str ('download', 'skip'),
                    'file_path': str (path to downloaded DOCX if successful),
                    'error': str (error message if failed),
                    'should_remove_html': bool (whether to remove iframe from HTML)
                }
        """
        result = {
            "success": False,
            "action": "skip",
            "file_path": None,
            "error": None,
            "should_remove_html": False,
        }

        if iframe_info["type"] != "google_docs":
            result["error"] = "Not a Google Docs iframe"
            return result

        if not self.google_docs_exporter:
            result["error"] = "Google Docs exporter not configured"
            logger.warning(
                "Cannot download Google Docs: exporter not provided. "
                "Initialize IframeProcessor with google_docs_exporter parameter."
            )
            return result

        # Ensure browser is started and user is logged in
        if not self._ensure_browser_ready():
            result["error"] = "Failed to initialize browser or login"
            return result

        try:
            # Download Google Doc with its original name (don't rename)
            logger.info(
                f"Downloading Google Doc: {iframe_info['file_id']}"
            )

            # Download using browser exporter (keeps original Google Doc title as filename)
            export_result = self.google_docs_exporter.export_single_document(
                iframe_info["file_id"], output_filename=None
            )

            # Log the download result with Google Doc link
            if export_result["success"]:
                doc_title = export_result.get("title", "Unknown")
                doc_url = f"https://docs.google.com/document/d/{iframe_info['file_id']}/edit"
                downloaded_path = Path(export_result["file_path"])

                logger.info(
                    f"Downloaded Google Doc: '{doc_title}' | "
                    f"File: {downloaded_path.name} | "
                    f"URL: {doc_url} | "
                    f"Article: {article_number} ({article_title})"
                )

            # Build context for logging
            article_context = f"Article: {article_number or 'unknown'}"
            if article_title and article_title != "document":
                article_context += f" ({article_title})"
            doc_context = f"Google Doc ID: {iframe_info['file_id']}"

            if export_result["success"]:
                result["success"] = True
                result["action"] = "download"
                result["file_path"] = export_result["file_path"]
                result["should_remove_html"] = True
                logger.info(
                    f"✅ Downloaded Google Doc to: {export_result['file_path']} | "
                    f"{article_context} | {doc_context}"
                )
            else:
                result["error"] = export_result.get("error", "Unknown error")
                doc_url = f"https://docs.google.com/document/d/{iframe_info['file_id']}/edit"

                # Log in structured format for mapping extraction
                logger.error(
                    f"❌ Failed to download Google Doc: '{export_result.get('title', 'Unknown')}' | "
                    f"File: N/A | "
                    f"URL: {doc_url} | "
                    f"Article: {article_number} ({article_title}) | "
                    f"Error: {result['error']}"
                )

        except Exception as e:
            result["error"] = f"Exception during download: {e}"
            file_id = iframe_info.get('file_id', 'unknown')
            doc_url = f"https://docs.google.com/document/d/{file_id}/edit" if file_id != 'unknown' else "N/A"

            # Log in structured format for mapping extraction
            logger.error(
                f"❌ Failed to download Google Doc: 'Unknown' | "
                f"File: N/A | "
                f"URL: {doc_url} | "
                f"Article: {article_number or 'unknown'} ({article_title}) | "
                f"Error: {e}"
            )

        return result

    def process_google_slides_iframe(
        self, iframe_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Google Slides iframe: convert to anchor link.

        Args:
            iframe_info: Iframe information dictionary from detect_iframes()

        Returns:
            Processing result:
                {
                    'success': bool,
                    'action': str ('convert_to_link'),
                    'link_html': str (HTML anchor tag to replace iframe),
                    'link_url': str (URL to Google Slides),
                    'error': str (error message if failed)
                }
        """
        result = {
            "success": False,
            "action": "convert_to_link",
            "link_html": None,
            "link_url": None,
            "error": None,
        }

        if iframe_info["type"] != "google_slides":
            result["error"] = "Not a Google Slides iframe"
            return result

        try:
            # Get the source URL
            slides_url = iframe_info["src"]

            # Create a clean presentation URL (not embed URL)
            # Convert: https://docs.google.com/presentation/d/ID/embed
            # To: https://docs.google.com/presentation/d/ID/edit
            if "/embed" in slides_url:
                slides_url = slides_url.replace("/embed", "/edit")

            # Create anchor link HTML
            link_html = (
                f'<p><a href="{slides_url}" target="_blank">'
                f"View Google Slides Presentation</a></p>"
            )

            result["success"] = True
            result["link_html"] = link_html
            result["link_url"] = slides_url

            logger.info(f"✅ Converted Google Slides iframe to link: {slides_url}")

        except Exception as e:
            result["error"] = f"Exception during conversion: {e}"
            logger.error(f"Error processing Google Slides iframe: {e}")

        return result

    def process_other_iframe(
        self, iframe_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process other (non-Google) iframe: convert to anchor link.

        Args:
            iframe_info: Iframe information dictionary from detect_iframes()

        Returns:
            Processing result:
                {
                    'success': bool,
                    'action': str ('convert_to_link'),
                    'link_html': str (HTML anchor tag to replace iframe),
                    'link_url': str (iframe source URL),
                    'error': str (error message if failed)
                }
        """
        result = {
            "success": False,
            "action": "convert_to_link",
            "link_html": None,
            "link_url": None,
            "error": None,
        }

        if iframe_info["type"] != "other":
            result["error"] = "Not an 'other' type iframe"
            return result

        try:
            # Get the source URL
            iframe_url = iframe_info["src"]

            if not iframe_url:
                result["error"] = "Iframe has no src attribute"
                return result

            # Create anchor link HTML
            link_html = (
                f'<p><a href="{iframe_url}" target="_blank">'
                f"View embedded content</a></p>"
            )

            result["success"] = True
            result["link_html"] = link_html
            result["link_url"] = iframe_url

            logger.info(f"✅ Converted iframe to link: {iframe_url}")

        except Exception as e:
            result["error"] = f"Exception during conversion: {e}"
            logger.error(f"Error processing other iframe: {e}")

        return result

    def process_html_iframes(
        self,
        html_content: str,
        article_title: str = "document",
        download_docs: bool = True,
        convert_slides: bool = True,
        article_number: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process all Google Docs and Slides iframes in HTML content.

        Args:
            html_content: HTML string to process
            article_title: Article title for naming downloaded files
            download_docs: Whether to download Google Docs as DOCX
            convert_slides: Whether to convert Google Slides iframes to links
            article_number: Optional article number for filename prefix

        Returns:
            Tuple of (modified_html, processing_summary):
                - modified_html: HTML with iframes processed
                - processing_summary: Dictionary with processing results
                    {
                        'iframes_found': int,
                        'docs_downloaded': List[str] (file paths),
                        'slides_converted': List[str] (URLs),
                        'other_converted': List[str] (URLs),
                        'errors': List[str],
                        'is_iframe_only': bool
                    }
        """
        summary = {
            "iframes_found": 0,
            "docs_downloaded": [],
            "slides_converted": [],
            "other_converted": [],
            "errors": [],
            "is_iframe_only": False,
        }

        if not html_content:
            return html_content, summary

        try:
            # Check if content is iframe-only
            summary["is_iframe_only"] = self.is_iframe_only_content(html_content)

            # Detect all iframes
            iframes = self.detect_iframes(html_content)
            summary["iframes_found"] = len(iframes)

            if not iframes:
                logger.debug("No iframes found in HTML")
                return html_content, summary

            # Parse HTML
            soup = BeautifulSoup(html_content, self.parser)

            # Find all iframes in the soup (need to find them in this soup, not the detection soup)
            soup_iframes = soup.find_all("iframe")

            # Track downloaded Google Docs to avoid duplicates (same file_id)
            downloaded_doc_ids = set()

            # Process each iframe
            for i, iframe_info in enumerate(iframes):
                # Get corresponding iframe from current soup
                if i < len(soup_iframes):
                    iframe_element = soup_iframes[i]
                else:
                    logger.warning(f"Could not find iframe {i} in soup")
                    continue

                # Process Google Docs
                if iframe_info["type"] == "google_docs" and download_docs:
                    file_id = iframe_info.get("file_id")

                    # Check if we've already downloaded this Google Doc
                    if file_id in downloaded_doc_ids:
                        logger.info(f"Skipping duplicate Google Doc iframe: {file_id} (already downloaded)")
                        # Still remove the iframe from HTML
                        iframe_element.decompose()
                        continue

                    result = self.process_google_docs_iframe(
                        iframe_info, article_title, article_number=article_number
                    )

                    if result["success"]:
                        # Store both file path and Google Doc URL
                        doc_info = {
                            "file_path": result["file_path"],
                            "doc_id": file_id,
                            "doc_url": f"https://docs.google.com/document/d/{file_id}/edit"
                        }
                        summary["docs_downloaded"].append(doc_info)
                        downloaded_doc_ids.add(file_id)  # Mark as downloaded

                        # Remove iframe from HTML if download successful
                        if result["should_remove_html"]:
                            iframe_element.decompose()
                            logger.info("Removed Google Docs iframe from HTML")
                    else:
                        summary["errors"].append(
                            f"Google Docs {iframe_info['file_id']}: {result['error']}"
                        )

                # Process Google Slides
                elif iframe_info["type"] == "google_slides" and convert_slides:
                    result = self.process_google_slides_iframe(iframe_info)

                    if result["success"]:
                        summary["slides_converted"].append(result["link_url"])

                        # Replace iframe with anchor link
                        link_soup = BeautifulSoup(result["link_html"], self.parser)
                        iframe_element.replace_with(link_soup)
                        logger.info("Replaced Google Slides iframe with link")
                    else:
                        summary["errors"].append(
                            f"Google Slides {iframe_info['file_id']}: {result['error']}"
                        )

                # Process other iframes - convert to links
                elif iframe_info["type"] == "other":
                    result = self.process_other_iframe(iframe_info)

                    if result["success"]:
                        summary["other_converted"].append(result["link_url"])

                        # Replace iframe with anchor link
                        link_soup = BeautifulSoup(result["link_html"], self.parser)
                        iframe_element.replace_with(link_soup)
                        logger.info(f"Replaced other iframe with link: {result['link_url']}")
                    else:
                        summary["errors"].append(
                            f"Other iframe {iframe_info['src']}: {result['error']}"
                        )

            # Return modified HTML
            modified_html = str(soup)
            return modified_html, summary

        except Exception as e:
            logger.error(f"Error processing HTML iframes: {e}")
            summary["errors"].append(f"Processing error: {e}")
            return html_content, summary

    def _ensure_browser_ready(self) -> bool:
        """
        Ensure browser is started and user is logged in for Google Docs export.

        Returns:
            True if browser is ready, False otherwise
        """
        if not self.google_docs_exporter:
            return False

        # Start browser if not already started
        if not self.google_docs_exporter.driver:
            logger.info("Starting browser for Google Docs export...")
            if not self.google_docs_exporter.start_browser():
                logger.error("Failed to start browser")
                return False

        # Perform login if not already logged in
        if not self.google_docs_exporter.is_logged_in:
            logger.info("Waiting for Google login...")
            logger.info("=" * 80)
            logger.info("MANUAL LOGIN REQUIRED")
            logger.info("=" * 80)
            logger.info("A browser window will open. Please log in to your Google account.")
            logger.info("After logging in, return to this terminal and press Enter to continue.")
            logger.info("=" * 80)

            if not self.google_docs_exporter.manual_login_wait():
                logger.error("Login failed or timed out")
                return False

        return True

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem
        """
        # Remove invalid filename characters
        invalid_chars = r'[/\\:*?"<>|]'
        sanitized = re.sub(invalid_chars, "_", filename)

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(". ")

        # Limit length (255 is max for most filesystems, leave room for extension)
        max_length = 240
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized or "document"

    def process_article_with_translations(
        self,
        original_html: str,
        translations: List[Dict[str, Any]],
        article_title: str = "document",
        article_number: str = "",
    ) -> Dict[str, Any]:
        """
        Process iframes in original article and its translations separately.

        This method handles the special case where articles with Google Docs iframes
        have translations. Since merging translated Google Docs doesn't make sense,
        we download each version separately.

        Args:
            original_html: HTML content of original article
            translations: List of translation dictionaries with 'text' and 'language' keys
            article_title: Article title for naming downloaded files
            article_number: Optional article number for filename prefix

        Returns:
            Processing result:
                {
                    'has_iframes': bool,
                    'requires_special_handling': bool,
                    'original': {
                        'html': str (processed HTML),
                        'summary': dict (iframe processing summary),
                        'downloaded_docs': List[str] (file paths)
                    },
                    'translations': List[{
                        'language': str,
                        'html': str (processed HTML),
                        'summary': dict (iframe processing summary),
                        'downloaded_docs': List[str] (file paths)
                    }],
                    'total_downloads': int,
                    'flag_message': str (message for special handling)
                }
        """
        result = {
            "has_iframes": False,
            "requires_special_handling": False,
            "original": {
                "html": original_html,
                "summary": None,
                "downloaded_docs": [],
            },
            "translations": [],
            "total_downloads": 0,
            "flag_message": None,
        }

        # Check if original has iframes
        original_iframes = self.detect_iframes(original_html)
        original_has_google_docs = any(
            i["type"] == "google_docs" for i in original_iframes
        )

        if not original_iframes and not translations:
            # No iframes, no translations - return as-is
            return result

        result["has_iframes"] = len(original_iframes) > 0

        # Process original article
        if original_iframes:
            logger.info(
                f"Processing {len(original_iframes)} iframes in original article"
            )

            processed_html, summary = self.process_html_iframes(
                html_content=original_html,
                article_title=article_title,
                download_docs=True,
                convert_slides=True,
                article_number=article_number,
            )

            result["original"]["html"] = processed_html
            result["original"]["summary"] = summary
            result["original"]["downloaded_docs"] = summary["docs_downloaded"]
            result["total_downloads"] += len(summary["docs_downloaded"])

        # Process translations
        if translations:
            logger.info(f"Processing {len(translations)} translations")

            for translation in translations:
                trans_html = translation.get("text", "")
                trans_language = translation.get("language", "unknown")
                trans_number = translation.get("number", "")
                trans_title = translation.get("short_description", trans_number or article_title)

                trans_iframes = self.detect_iframes(trans_html)

                if trans_iframes:
                    logger.info(
                        f"Processing {len(trans_iframes)} iframes in {trans_language} translation ({trans_number})"
                    )

                    # Use translation's own article number and title for filename
                    # This ensures each translation gets its own file: KB0001-Title.docx, KB0002-Title.docx, etc.
                    processed_trans_html, trans_summary = self._process_translation_iframes(
                        html_content=trans_html,
                        article_title=trans_title,
                        language_suffix="",  # No language suffix needed - use article number instead
                        article_number=trans_number,
                    )

                    result["translations"].append({
                        "language": trans_language,
                        "html": processed_trans_html,
                        "summary": trans_summary,
                        "downloaded_docs": trans_summary["docs_downloaded"],
                    })

                    result["total_downloads"] += len(trans_summary["docs_downloaded"])
                else:
                    # No iframes in this translation, keep as-is
                    result["translations"].append({
                        "language": trans_language,
                        "html": trans_html,
                        "summary": None,
                        "downloaded_docs": [],
                    })

        # Determine if special handling is required
        # Special handling needed if original has Google Docs AND has translations
        if original_has_google_docs and translations:
            result["requires_special_handling"] = True
            result["flag_message"] = (
                f"Article contains Google Docs iframe with {len(translations)} translation(s). "
                f"Downloaded {result['total_downloads']} separate DOCX files instead of merging. "
                f"Manual review recommended for proper organization in Notion."
            )
            logger.warning(result["flag_message"])

        return result

    def _process_translation_iframes(
        self,
        html_content: str,
        article_title: str,
        language_suffix: str,
        article_number: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process iframes in translated content with language-specific filenames.

        Args:
            html_content: HTML content to process
            article_title: Article title for naming
            language_suffix: Language suffix for filenames (e.g., '_ja')
            article_number: Optional article number for filename prefix

        Returns:
            Tuple of (modified_html, processing_summary)
        """
        summary = {
            "iframes_found": 0,
            "docs_downloaded": [],
            "slides_converted": [],
            "other_converted": [],
            "errors": [],
            "is_iframe_only": False,
        }

        if not html_content:
            return html_content, summary

        try:
            summary["is_iframe_only"] = self.is_iframe_only_content(html_content)

            iframes = self.detect_iframes(html_content)
            summary["iframes_found"] = len(iframes)

            if not iframes:
                return html_content, summary

            soup = BeautifulSoup(html_content, self.parser)

            # Find all iframes in the soup
            soup_iframes = soup.find_all("iframe")

            # Track downloaded Google Docs to avoid duplicates (same file_id)
            downloaded_doc_ids = set()

            for i, iframe_info in enumerate(iframes):
                # Get corresponding iframe from current soup
                if i < len(soup_iframes):
                    iframe_element = soup_iframes[i]
                else:
                    logger.warning(f"Could not find iframe {i} in soup")
                    continue

                # Process Google Docs with language suffix
                if iframe_info["type"] == "google_docs":
                    file_id = iframe_info.get("file_id")

                    # Check if we've already downloaded this Google Doc
                    if file_id in downloaded_doc_ids:
                        logger.info(f"Skipping duplicate Google Doc iframe in translation: {file_id} (already downloaded)")
                        # Still remove the iframe from HTML
                        iframe_element.decompose()
                        continue

                    result = self.process_google_docs_iframe(
                        iframe_info,
                        article_title,
                        language_suffix=language_suffix,
                        article_number=article_number,
                    )

                    if result["success"]:
                        summary["docs_downloaded"].append(result["file_path"])
                        downloaded_doc_ids.add(file_id)  # Mark as downloaded

                        if result["should_remove_html"]:
                            iframe_element.decompose()
                    else:
                        summary["errors"].append(
                            f"Google Docs {iframe_info['file_id']}: {result['error']}"
                        )

                # Process Google Slides
                elif iframe_info["type"] == "google_slides":
                    result = self.process_google_slides_iframe(iframe_info)

                    if result["success"]:
                        summary["slides_converted"].append(result["link_url"])
                        link_soup = BeautifulSoup(result["link_html"], self.parser)
                        iframe_element.replace_with(link_soup)
                    else:
                        summary["errors"].append(
                            f"Google Slides {iframe_info['file_id']}: {result['error']}"
                        )

                # Process other iframes
                elif iframe_info["type"] == "other":
                    result = self.process_other_iframe(iframe_info)

                    if result["success"]:
                        summary["other_converted"].append(result["link_url"])
                        link_soup = BeautifulSoup(result["link_html"], self.parser)
                        iframe_element.replace_with(link_soup)
                    else:
                        summary["errors"].append(
                            f"Other iframe {iframe_info['src']}: {result['error']}"
                        )

            modified_html = str(soup)
            return modified_html, summary

        except Exception as e:
            logger.error(f"Error processing translation iframes: {e}")
            summary["errors"].append(f"Processing error: {e}")
            return html_content, summary

    def get_iframe_summary(self, html_content: str) -> Dict[str, Any]:
        """
        Get summary of iframes in HTML without processing them.

        Args:
            html_content: HTML string to analyze

        Returns:
            Summary dictionary:
                {
                    'total_iframes': int,
                    'google_docs_count': int,
                    'google_slides_count': int,
                    'other_iframes_count': int,
                    'is_iframe_only': bool,
                    'google_docs_urls': List[str],
                    'google_slides_urls': List[str],
                    'other_urls': List[str]
                }
        """
        iframes = self.detect_iframes(html_content)

        google_docs = [i for i in iframes if i["type"] == "google_docs"]
        google_slides = [i for i in iframes if i["type"] == "google_slides"]
        other = [i for i in iframes if i["type"] == "other"]

        return {
            "total_iframes": len(iframes),
            "google_docs_count": len(google_docs),
            "google_slides_count": len(google_slides),
            "other_iframes_count": len(other),
            "is_iframe_only": self.is_iframe_only_content(html_content),
            "google_docs_urls": [i["src"] for i in google_docs],
            "google_slides_urls": [i["src"] for i in google_slides],
            "other_urls": [i["src"] for i in other],
        }
