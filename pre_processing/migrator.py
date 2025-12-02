"""Orchestrator for ServiceNow to Notion migration via ZIP export."""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .article_fetcher import ArticleFetcher
from .export_reporter import ExportReporter

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrate the migration process: extract from ServiceNow and create ZIP exports."""

    def __init__(
        self,
        servicenow_kb,
        output_dir: str = "./migration_output",
        google_docs_exporter=None,
        process_iframes: bool = True,
        max_workers: int = 4,
        rate_limit_delay: float = 0.0,
        max_articles_per_zip: int = 300,
    ):
        """
        Initialize migration orchestrator.

        Args:
            servicenow_kb: ServiceNow KnowledgeBase instance
            output_dir: Directory for migration artifacts (ZIPs, logs, etc.)
            google_docs_exporter: Optional GoogleDocsBrowserExporter instance for iframe processing
            process_iframes: Whether to process Google Docs/Slides iframes (default: True)
            max_workers: Maximum number of parallel workers (default: 4)
            rate_limit_delay: Delay in seconds between API requests to avoid throttling (default: 0.0)
            max_articles_per_zip: Maximum articles per ZIP file (default: 300)
        """
        self.servicenow_kb = servicenow_kb
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_articles_per_zip = max_articles_per_zip

        # Initialize ZIP exporter
        from .zip_exporter import ZipExporter

        self.zip_exporter = ZipExporter(str(self.output_dir / "zips"))

        # Initialize iframe processor if enabled
        iframe_processor = None
        if process_iframes:
            from .iframe_processor import IframeProcessor

            iframe_processor = IframeProcessor(google_docs_exporter=google_docs_exporter)
            logger.info("Iframe processor initialized")

        # Initialize article fetcher
        self.article_fetcher = ArticleFetcher(
            knowledge_base=servicenow_kb,
            max_workers=max_workers,
            rate_limit_delay=rate_limit_delay,
            process_iframes=process_iframes,
            iframe_processor=iframe_processor,
        )

        logger.info(
            f"Migration orchestrator initialized (ZIP export mode, "
            f"max_workers={max_workers}, rate_limit_delay={rate_limit_delay}s)"
        )

    def export_all_to_zip(
        self,
        query: Optional[str] = None,
        zip_filename: Optional[str] = None,
        limit: Optional[int] = None,
        category_filter: Optional[str] = None,
        exclude_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export all articles to a ZIP file for Notion import.

        Args:
            query: ServiceNow query to filter articles
            zip_filename: Optional custom filename for ZIP
            limit: Maximum number of articles to export
            category_filter: Include only articles under this category (partial match, case-insensitive)
            exclude_category: Exclude articles under this category (partial match, case-insensitive)

        Returns:
            Export results summary

        Process:
            1. Fetch latest versions of articles from ServiceNow
            2. Filter by category if specified
            3. Get merged translations for each article
            4. Download attachments
            5. Create ZIP export with all data
            6. Generate CSV report
        """
        logger.info("Starting ZIP export process")

        results = {
            "total_articles": 0,
            "zip_created": False,
            "zip_path": None,
            "csv_path": None,
            "errors": [],
            "articles_data": [],
        }

        try:
            # Fetch articles with full data
            # Note: Deduplication now happens inside fetch_all_articles (deduplicate_first=True)
            # to prevent downloading the same Google Docs twice for translation pairs
            logger.info("Fetching articles from ServiceNow")
            articles_data = self.article_fetcher.fetch_all_articles(
                query=query,
                limit=limit,
                category_filter=category_filter,
                exclude_category=exclude_category,
                deduplicate_first=True,  # Deduplicate BEFORE processing iframes
            )
            logger.info(f"Fetched {len(articles_data)} unique articles/pairs")

            results["total_articles"] = len(articles_data)
            results["articles_data"] = articles_data

            if not articles_data:
                logger.warning("No articles found")
                return results

            # Create ZIP export
            logger.info(f"Creating ZIP export with {len(articles_data)} articles")
            zip_path = self.zip_exporter.create_bulk_zip(
                articles_data,
                max_articles_per_zip=self.max_articles_per_zip
            )

            # Rename if custom filename provided
            if zip_filename:
                zip_path = self._rename_zip(zip_path, zip_filename)

            results["zip_created"] = True
            results["zip_path"] = zip_path

            # Create CSV report
            logger.info("Generating CSV export report")
            csv_path = ExportReporter.create_csv_report(
                articles_data, zip_path, self.output_dir
            )
            results["csv_path"] = csv_path
            logger.info(f"✅ CSV report created: {csv_path}")

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
            article_data = self.article_fetcher.fetch_single_article(article_sys_id)

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

    def _rename_zip(self, zip_path: str, new_filename: str) -> str:
        """Rename ZIP file to custom filename."""
        import shutil

        zip_path_obj = Path(zip_path)
        new_path = zip_path_obj.parent / new_filename
        shutil.move(str(zip_path), str(new_path))
        logger.info(f"Renamed ZIP to: {new_filename}")
        return str(new_path)
