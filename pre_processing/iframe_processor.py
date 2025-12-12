"""Process iframe-embedded Google Docs and Slides in HTML content."""
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IframeProcessor:
    """Process and transform iframe elements in HTML content."""

    def __init__(self, google_docs_exporter=None):
        self.google_docs_exporter = google_docs_exporter
        self.parser = "lxml"
        self.google_docs_pattern = re.compile(r"https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)")
        self.google_slides_pattern = re.compile(r"https://docs\.google\.com/presentation/d/([a-zA-Z0-9-_]+)")

    def detect_iframes(self, html_content: str) -> List[Dict[str, Any]]:
        """Detect all iframe elements in HTML content."""
        if not html_content:
            return []
        try:
            soup = BeautifulSoup(html_content, self.parser)
            iframes = []
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "")
                iframe_info = {"src": src, "type": "other", "file_id": None, "element": iframe}
                if docs_match := self.google_docs_pattern.search(src):
                    iframe_info.update({"type": "google_docs", "file_id": docs_match.group(1)})
                    logger.debug(f"Found Google Docs iframe: {iframe_info['file_id']}")
                elif slides_match := self.google_slides_pattern.search(src):
                    iframe_info.update({"type": "google_slides", "file_id": slides_match.group(1)})
                    logger.debug(f"Found Google Slides iframe: {iframe_info['file_id']}")
                iframes.append(iframe_info)
            logger.info(f"Found {len(iframes)} iframes in HTML")
            return iframes
        except Exception as e:
            logger.error(f"Error detecting iframes: {e}")
            return []

    def is_iframe_only_content(self, html_content: str) -> bool:
        """Check if HTML content contains only an iframe (no other meaningful content)."""
        if not html_content:
            return False
        try:
            soup = BeautifulSoup(html_content, self.parser)
            if not soup.find_all("iframe"):
                return False
            soup_copy = BeautifulSoup(str(soup), self.parser)
            for element in soup_copy(["iframe", "script", "style"]):
                element.decompose()
            text = soup_copy.get_text(strip=True)
            result = len(text) <= 10
            logger.debug(f"Iframe-only check: {result} (remaining text length: {len(text)})")
            return result
        except Exception as e:
            logger.error(f"Error checking iframe-only content: {e}")
            return False

    def process_google_docs_iframe(self, iframe_info: Dict[str, Any], article_title: str = "document",
                                   language_suffix: str = "", article_number: str = "") -> Dict[str, Any]:
        """Process Google Docs iframe: download as DOCX and prepare for removal."""
        result = {"success": False, "action": "skip", "file_path": None, "error": None, "should_remove_html": False}

        if iframe_info["type"] != "google_docs":
            result["error"] = "Not a Google Docs iframe"
            return result

        if not self.google_docs_exporter:
            result["error"] = "Google Docs exporter not configured"
            logger.warning("Cannot download Google Docs: exporter not provided.")
            return result

        if not self._ensure_browser_ready():
            result["error"] = "Failed to initialize browser or login"
            return result

        try:
            requested_file_id = iframe_info['file_id']
            logger.info(f"Downloading Google Doc: {requested_file_id}")
            export_result = self.google_docs_exporter.export_single_document(requested_file_id, output_filename=None)
            doc_url = f"https://docs.google.com/document/d/{requested_file_id}/edit"

            if export_result["success"]:
                doc_title = export_result.get("title", "Unknown")
                downloaded_path = Path(export_result["file_path"])

                if downloaded_path.exists() and (file_age := time.time() - downloaded_path.stat().st_mtime) > 5:
                    logger.warning(f"⚠️  Downloaded file is {file_age:.1f}s old - may be from a previous download. "
                                 f"Requested: {requested_file_id}, File: {downloaded_path.name}")

                logger.info(f"Downloaded Google Doc: '{doc_title}' | File: {downloaded_path.name} | "
                          f"URL: {doc_url} | Article: {article_number} ({article_title})")

                result.update({"success": True, "action": "download", "file_path": export_result["file_path"],
                             "should_remove_html": True})
                logger.info(f"✅ Downloaded Google Doc to: {export_result['file_path']} | "
                          f"Article: {article_number or 'unknown'} ({article_title}) | Google Doc ID: {requested_file_id}")
            else:
                result["error"] = export_result.get("error", "Unknown error")
                logger.error(f"❌ Failed to download Google Doc: '{export_result.get('title', 'Unknown')}' | "
                           f"File: N/A | URL: {doc_url} | Article: {article_number} ({article_title}) | Error: {result['error']}")
        except Exception as e:
            result["error"] = f"Exception during download: {e}"
            logger.error(f"❌ Failed to download Google Doc: 'Unknown' | File: N/A | URL: {doc_url} | "
                       f"Article: {article_number or 'unknown'} ({article_title}) | Error: {e}")
        return result

    def process_google_slides_iframe(self, iframe_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process Google Slides iframe: convert to anchor link."""
        result = {"success": False, "action": "convert_to_link", "link_html": None, "link_url": None, "error": None}
        if iframe_info["type"] != "google_slides":
            result["error"] = "Not a Google Slides iframe"
            return result
        try:
            slides_url = iframe_info["src"].replace("/embed", "/edit") if "/embed" in iframe_info["src"] else iframe_info["src"]
            link_html = f'<p><a href="{slides_url}" target="_blank">View Google Slides Presentation</a></p>'
            result.update({"success": True, "link_html": link_html, "link_url": slides_url})
            logger.info(f"✅ Converted Google Slides iframe to link: {slides_url}")
        except Exception as e:
            result["error"] = f"Exception during conversion: {e}"
            logger.error(f"Error processing Google Slides iframe: {e}")
        return result

    def process_other_iframe(self, iframe_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process other (non-Google) iframe: convert to anchor link."""
        result = {"success": False, "action": "convert_to_link", "link_html": None, "link_url": None, "error": None}
        if iframe_info["type"] != "other":
            result["error"] = "Not an 'other' type iframe"
            return result
        try:
            if not (iframe_url := iframe_info["src"]):
                result["error"] = "Iframe has no src attribute"
                return result
            link_html = f'<p><a href="{iframe_url}" target="_blank">View embedded content</a></p>'
            result.update({"success": True, "link_html": link_html, "link_url": iframe_url})
            logger.info(f"✅ Converted iframe to link: {iframe_url}")
        except Exception as e:
            result["error"] = f"Exception during conversion: {e}"
            logger.error(f"Error processing other iframe: {e}")
        return result

    def _process_iframes_core(self, html_content: str, article_title: str, article_number: str,
                             download_docs: bool, convert_slides: bool) -> Tuple[str, Dict[str, Any]]:
        """Core iframe processing logic shared by process_html_iframes and _process_translation_iframes."""
        summary = {"iframes_found": 0, "docs_downloaded": [], "docs_failed": [], "slides_converted": [],
                  "other_converted": [], "errors": [], "is_iframe_only": False}

        if not html_content:
            return html_content, summary

        try:
            summary["is_iframe_only"] = self.is_iframe_only_content(html_content)
            iframes = self.detect_iframes(html_content)
            summary["iframes_found"] = len(iframes)

            if not iframes:
                logger.debug("No iframes found in HTML")
                return html_content, summary

            soup = BeautifulSoup(html_content, self.parser)
            soup_iframes = soup.find_all("iframe")
            downloaded_doc_ids = set()

            for i, iframe_info in enumerate(iframes):
                if i >= len(soup_iframes):
                    logger.warning(f"Could not find iframe {i} in soup")
                    continue
                iframe_element = soup_iframes[i]
                file_id = iframe_info.get("file_id")

                if iframe_info["type"] == "google_docs" and download_docs:
                    if file_id in downloaded_doc_ids:
                        logger.info(f"Skipping duplicate Google Doc iframe: {file_id} (already downloaded)")
                        iframe_element.decompose()
                        continue

                    result = self.process_google_docs_iframe(iframe_info, article_title, article_number=article_number)

                    if result["success"]:
                        doc_info = {"file_path": result["file_path"], "doc_id": file_id,
                                   "doc_url": f"https://docs.google.com/document/d/{file_id}/edit",
                                   "article_number": article_number, "article_title": article_title}
                        summary["docs_downloaded"].append(doc_info)
                        downloaded_doc_ids.add(file_id)
                        if result["should_remove_html"]:
                            iframe_element.decompose()
                            logger.info("Removed Google Docs iframe from HTML")
                    else:
                        failed_info = {"doc_id": file_id, "doc_url": f"https://docs.google.com/document/d/{file_id}/edit",
                                     "article_number": article_number, "article_title": article_title, "error": result['error']}
                        summary["docs_failed"].append(failed_info)
                        summary["errors"].append(f"Google Docs {file_id}: {result['error']}")

                elif iframe_info["type"] == "google_slides" and convert_slides:
                    result = self.process_google_slides_iframe(iframe_info)
                    if result["success"]:
                        summary["slides_converted"].append(result["link_url"])
                        iframe_element.replace_with(BeautifulSoup(result["link_html"], self.parser))
                        logger.info("Replaced Google Slides iframe with link")
                    else:
                        summary["errors"].append(f"Google Slides {file_id}: {result['error']}")

                elif iframe_info["type"] == "other":
                    result = self.process_other_iframe(iframe_info)
                    if result["success"]:
                        summary["other_converted"].append(result["link_url"])
                        iframe_element.replace_with(BeautifulSoup(result["link_html"], self.parser))
                        logger.info(f"Replaced other iframe with link: {result['link_url']}")
                    else:
                        summary["errors"].append(f"Other iframe {iframe_info['src']}: {result['error']}")

            return str(soup), summary
        except Exception as e:
            logger.error(f"Error processing iframes: {e}")
            summary["errors"].append(f"Processing error: {e}")
            return html_content, summary

    def process_html_iframes(self, html_content: str, article_title: str = "document", download_docs: bool = True,
                            convert_slides: bool = True, article_number: str = "") -> Tuple[str, Dict[str, Any]]:
        """Process all Google Docs and Slides iframes in HTML content."""
        return self._process_iframes_core(html_content, article_title, article_number, download_docs, convert_slides)

    def _ensure_browser_ready(self) -> bool:
        """Ensure browser is started and user is logged in for Google Docs export."""
        if not self.google_docs_exporter:
            return False
        if not self.google_docs_exporter.driver:
            logger.info("Starting browser for Google Docs export...")
            if not self.google_docs_exporter.start_browser():
                logger.error("Failed to start browser")
                return False
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

    def process_article_with_translations(self, original_html: str, translations: List[Dict[str, Any]],
                                         article_title: str = "document", article_number: str = "") -> Dict[str, Any]:
        """Process iframes in original article and its translations separately."""
        result = {"has_iframes": False, "requires_special_handling": False,
                 "original": {"html": original_html, "summary": None, "downloaded_docs": [], "failed_docs": []},
                 "translations": [], "total_downloads": 0, "flag_message": None}

        original_iframes = self.detect_iframes(original_html)
        original_has_google_docs = any(i["type"] == "google_docs" for i in original_iframes)

        if not original_iframes and not translations:
            return result

        result["has_iframes"] = len(original_iframes) > 0

        if original_iframes:
            logger.info(f"Processing {len(original_iframes)} iframes in original article")
            processed_html, summary = self.process_html_iframes(original_html, article_title, True, True, article_number)
            result["original"].update({"html": processed_html, "summary": summary,
                                      "downloaded_docs": summary["docs_downloaded"], "failed_docs": summary["docs_failed"]})
            result["total_downloads"] += len(summary["docs_downloaded"])

        if translations:
            logger.info(f"Processing {len(translations)} translations")
            for translation in translations:
                trans_html = translation.get("text", "")
                trans_language = translation.get("language", "unknown")
                trans_number = translation.get("number", "")
                trans_title = translation.get("short_description", trans_number or article_title)
                trans_iframes = self.detect_iframes(trans_html)

                if trans_iframes:
                    logger.info(f"Processing {len(trans_iframes)} iframes in {trans_language} translation ({trans_number})")
                    processed_trans_html, trans_summary = self._process_iframes_core(trans_html, trans_title, trans_number, True, True)
                    result["translations"].append({"language": trans_language, "html": processed_trans_html, "summary": trans_summary,
                                                  "downloaded_docs": trans_summary["docs_downloaded"], "failed_docs": trans_summary["docs_failed"]})
                    result["total_downloads"] += len(trans_summary["docs_downloaded"])
                else:
                    result["translations"].append({"language": trans_language, "html": trans_html, "summary": None, "downloaded_docs": []})

        if original_has_google_docs and translations:
            result["requires_special_handling"] = True
            result["flag_message"] = (f"Article contains Google Docs iframe with {len(translations)} translation(s). "
                                     f"Downloaded {result['total_downloads']} separate DOCX files instead of merging. "
                                     f"Manual review recommended for proper organization in Notion.")
            logger.warning(result["flag_message"])

        return result

    def get_iframe_summary(self, html_content: str) -> Dict[str, Any]:
        """Get summary of iframes in HTML without processing them."""
        iframes = self.detect_iframes(html_content)
        google_docs = [i for i in iframes if i["type"] == "google_docs"]
        google_slides = [i for i in iframes if i["type"] == "google_slides"]
        other = [i for i in iframes if i["type"] == "other"]

        return {"total_iframes": len(iframes), "google_docs_count": len(google_docs),
               "google_slides_count": len(google_slides), "other_iframes_count": len(other),
               "is_iframe_only": self.is_iframe_only_content(html_content),
               "google_docs_urls": [i["src"] for i in google_docs],
               "google_slides_urls": [i["src"] for i in google_slides],
               "other_urls": [i["src"] for i in other]}
