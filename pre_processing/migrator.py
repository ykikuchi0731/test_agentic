"""Orchestrator for ServiceNow to Notion migration via ZIP export."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrate the migration process: extract from ServiceNow and create ZIP exports."""

    def __init__(self, servicenow_kb, output_dir: str = "./migration_output"):
        """
        Initialize migration orchestrator.

        Args:
            servicenow_kb: ServiceNow KnowledgeBase instance
            output_dir: Directory for migration artifacts (ZIPs, logs, etc.)
        """
        self.servicenow_kb = servicenow_kb
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ZIP exporter
        from .zip_exporter import ZipExporter

        self.zip_exporter = ZipExporter(str(self.output_dir / "zips"))

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
        # Get article with merged translations (includes original + translations)
        article = self.servicenow_kb.get_article_with_translations(article_sys_id)

        # Get category path
        article_with_cat = self.servicenow_kb.get_article_with_category_path(
            article_sys_id
        )
        article["category_path"] = article_with_cat.get("category_path", [])

        # Get attachments from original AND all translations
        all_sys_ids = article.get("all_sys_ids", [article_sys_id])
        attachments = self.servicenow_kb.get_attachments_for_all_articles(
            all_sys_ids, download=True
        )

        logger.info(
            f"Fetched {len(attachments)} total attachments from original + {len(all_sys_ids) - 1} translations"
        )

        # Use merged_html instead of text (includes translations if any)
        html_content = article.get("merged_html", article.get("text", ""))

        return {
            "article": article,
            "html_content": html_content,
            "attachments": attachments,
            "category_path": article.get("category_path", []),
            "translations": article.get("translations", []),
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
