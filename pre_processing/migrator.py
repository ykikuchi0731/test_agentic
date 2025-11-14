"""Orchestrator for ServiceNow to Notion migration via ZIP export."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrate the migration process: extract from ServiceNow and create ZIP exports."""

    def __init__(
        self,
        servicenow_kb,
        output_dir: str = "./migration_output",
        google_docs_exporter=None,
        process_iframes: bool = True,
    ):
        """
        Initialize migration orchestrator.

        Args:
            servicenow_kb: ServiceNow KnowledgeBase instance
            output_dir: Directory for migration artifacts (ZIPs, logs, etc.)
            google_docs_exporter: Optional GoogleDocsBrowserExporter instance for iframe processing
            process_iframes: Whether to process Google Docs/Slides iframes (default: True)
        """
        self.servicenow_kb = servicenow_kb
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process_iframes = process_iframes

        # Initialize ZIP exporter
        from .zip_exporter import ZipExporter

        self.zip_exporter = ZipExporter(str(self.output_dir / "zips"))

        # Initialize iframe processor if enabled
        self.iframe_processor = None
        if process_iframes:
            from .iframe_processor import IframeProcessor

            self.iframe_processor = IframeProcessor(
                google_docs_exporter=google_docs_exporter
            )
            logger.info("Iframe processor initialized")

        logger.info("Migration orchestrator initialized (ZIP export mode)")

    def export_all_to_zip(
        self, query: Optional[str] = None, zip_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export all articles to a ZIP file for Notion import.

        Args:
            query: ServiceNow query to filter articles
            zip_filename: Optional custom filename for ZIP

        Returns:
            Export results summary

        Process:
            1. Fetch latest versions of articles from ServiceNow
            2. Get merged translations for each article
            3. Download attachments
            4. Create ZIP export with all data
        """
        logger.info("Starting ZIP export process")

        results = {
            "total_articles": 0,
            "zip_created": False,
            "zip_path": None,
            "errors": [],
        }

        try:
            # Fetch articles with full data
            logger.info("Fetching articles from ServiceNow")
            articles_data = self._fetch_all_articles(query)
            results["total_articles"] = len(articles_data)

            if not articles_data:
                logger.warning("No articles found")
                return results

            # Create ZIP export
            logger.info(f"Creating ZIP export with {len(articles_data)} articles")
            zip_path = self.zip_exporter.create_bulk_zip(articles_data)

            # Rename if custom filename provided
            if zip_filename:
                from pathlib import Path
                import shutil
                zip_path_obj = Path(zip_path)
                new_path = zip_path_obj.parent / zip_filename
                shutil.move(str(zip_path), str(new_path))
                zip_path = str(new_path)
                logger.info(f"Renamed ZIP to: {zip_filename}")

            results["zip_created"] = True
            results["zip_path"] = zip_path

            logger.info(f"✅ ZIP export complete: {zip_path}")
            return results

        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            results["errors"].append(str(e))
            return results

    def export_single_to_zip(
        self, article_sys_id: str, zip_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a single article to ZIP file.

        Args:
            article_sys_id: ServiceNow article sys_id
            zip_filename: Optional custom filename for ZIP

        Returns:
            Export result for this article
        """
        logger.info(f"Exporting single article: {article_sys_id}")

        result = {"article_sys_id": article_sys_id, "zip_created": False, "zip_path": None}

        try:
            # Fetch article data
            article_data = self._fetch_article_data(article_sys_id)

            # Create ZIP
            zip_path = self.zip_exporter.create_article_zip(
                article=article_data["article"],
                attachments=article_data["attachments"],
                html_content=article_data["html_content"],
            )

            result["zip_created"] = True
            result["zip_path"] = zip_path

            logger.info(f"✅ Article exported: {zip_path}")
            return result

        except Exception as e:
            logger.error(f"Export failed for article {article_sys_id}: {e}")
            result["error"] = str(e)
            return result

    def _fetch_all_articles(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all articles with full data from ServiceNow."""
        logger.info("Fetching all articles from ServiceNow (latest versions only)")

        # Pre-fetch categories for performance
        logger.info("Pre-fetching categories...")
        self.servicenow_kb.prefetch_all_categories()

        # Get latest version of articles only (filters out old versions)
        articles = self.servicenow_kb.get_latest_articles_only(query=query)
        logger.info(f"Found {len(articles)} articles (latest versions)")

        articles_data = []
        total = len(articles)

        for i, article in enumerate(articles, 1):
            try:
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{total} articles processed")

                article_data = self._fetch_article_data(article["sys_id"])
                articles_data.append(article_data)

            except Exception as e:
                logger.error(
                    f"Error fetching article {article.get('number', 'unknown')}: {e}"
                )
                # Continue with other articles

        logger.info(f"Successfully fetched {len(articles_data)} articles with data")
        return articles_data

    def _fetch_article_data(self, article_sys_id: str) -> Dict[str, Any]:
        """Fetch complete data for a single article."""
        # Get original article (NOT merged yet)
        original_article = self.servicenow_kb.get_article(article_sys_id)

        # Get category path
        article_with_cat = self.servicenow_kb.get_article_with_category_path(
            article_sys_id
        )
        original_article["category_path"] = article_with_cat.get("category_path", [])

        # Get translations
        translations = self.servicenow_kb._get_translations_for_article(article_sys_id)

        # Get all sys_ids for attachments
        all_sys_ids = [article_sys_id] + [t["sys_id"] for t in translations]

        # Get attachments from original AND all translations
        attachments = self.servicenow_kb.get_attachments_for_all_articles(
            all_sys_ids, download=True
        )

        logger.info(
            f"Fetched {len(attachments)} total attachments from original + {len(translations)} translations"
        )

        # Process iframes if enabled
        iframe_result = None
        downloaded_docs = []
        requires_special_handling = False
        flag_message = None
        html_content = None

        if self.process_iframes and self.iframe_processor:
            article_title = original_article.get("short_description", original_article.get("number", "document"))
            original_html = original_article.get("text", "")

            logger.info(f"Processing iframes in article: {article_title}")

            # Process iframes in original AND translations separately
            iframe_result = self.iframe_processor.process_article_with_translations(
                original_html=original_html,
                translations=translations,
                article_title=article_title,
            )

            if iframe_result["has_iframes"]:
                logger.info(
                    f"Iframe processing complete: "
                    f"{iframe_result['total_downloads']} total docs downloaded"
                )

                # Check if special handling is required
                requires_special_handling = iframe_result["requires_special_handling"]
                flag_message = iframe_result["flag_message"]

                if requires_special_handling:
                    logger.warning(f"⚠️  SPECIAL HANDLING REQUIRED: {flag_message}")

                    # Don't merge translations when we have Google Docs iframes
                    # Keep original and translations separate
                    html_content = iframe_result["original"]["html"]

                    # Add all downloaded docs as attachments (from original and translations)
                    for doc_path in iframe_result["original"]["downloaded_docs"]:
                        attachments.append({
                            "file_name": Path(doc_path).name,
                            "file_path": doc_path,
                            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "size_bytes": Path(doc_path).stat().st_size if Path(doc_path).exists() else 0,
                            "source": "google_docs_iframe_original",
                        })
                        downloaded_docs.append(doc_path)

                    # Add docs from translations
                    for trans in iframe_result["translations"]:
                        for doc_path in trans["downloaded_docs"]:
                            attachments.append({
                                "file_name": Path(doc_path).name,
                                "file_path": doc_path,
                                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "size_bytes": Path(doc_path).stat().st_size if Path(doc_path).exists() else 0,
                                "source": f"google_docs_iframe_{trans['language']}",
                                "language": trans["language"],
                            })
                            downloaded_docs.append(doc_path)

                    logger.info(f"Added {len(downloaded_docs)} downloaded Google Docs as attachments")

                else:
                    # No special handling needed - can merge normally
                    # Build merged HTML from processed original and translations
                    processed_original_html = iframe_result["original"]["html"]

                    # Create temporary processed translations list for merging
                    processed_translations = []
                    for i, trans_result in enumerate(iframe_result["translations"]):
                        trans_copy = translations[i].copy()
                        trans_copy["text"] = trans_result["html"]  # Use processed HTML
                        processed_translations.append(trans_copy)

                    # Now merge processed HTML
                    html_content = self.servicenow_kb._merge_article_html(
                        {"text": processed_original_html},
                        processed_translations
                    )

                    # Add downloaded docs as attachments
                    for doc_path in iframe_result["original"]["downloaded_docs"]:
                        attachments.append({
                            "file_name": Path(doc_path).name,
                            "file_path": doc_path,
                            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "size_bytes": Path(doc_path).stat().st_size if Path(doc_path).exists() else 0,
                            "source": "google_docs_iframe",
                        })
                        downloaded_docs.append(doc_path)

            else:
                # No iframes found - merge normally
                html_content = self.servicenow_kb._merge_article_html(
                    original_article,
                    translations
                )

        else:
            # Iframe processing disabled - merge normally
            html_content = self.servicenow_kb._merge_article_html(
                original_article,
                translations
            )

        # Prepare article data
        article = original_article.copy()
        article["translations"] = translations
        article["all_sys_ids"] = all_sys_ids
        article["merged_html"] = html_content

        return {
            "article": article,
            "html_content": html_content,
            "attachments": attachments,
            "category_path": article.get("category_path", []),
            "translations": translations,
            "iframe_result": iframe_result,
            "downloaded_google_docs": downloaded_docs,
            "requires_special_handling": requires_special_handling,
            "special_handling_flag": flag_message,
        }

    def get_export_summary(self) -> Dict[str, Any]:
        """
        Get summary of export operation.

        Returns:
            Dictionary with export summary information
        """
        return {
            "output_directory": str(self.output_dir),
            "zip_directory": str(self.output_dir / "zips"),
        }
