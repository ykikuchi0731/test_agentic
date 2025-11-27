"""Orchestrator for ServiceNow to Notion migration via ZIP export."""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

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
        """
        self.servicenow_kb = servicenow_kb
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process_iframes = process_iframes
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self._rate_limit_lock = Lock()
        self._last_request_time = 0

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
        exclude_category: Optional[str] = None
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
            "articles_data": [],  # Store article data for CSV export
        }

        try:
            # Fetch articles with full data
            logger.info("Fetching articles from ServiceNow")
            articles_data = self._fetch_all_articles(
                query,
                limit=limit,
                category_filter=category_filter,
                exclude_category=exclude_category
            )

            # Deduplicate translation pairs
            logger.info(f"Deduplicating {len(articles_data)} articles")
            articles_data = self._deduplicate_translation_pairs(articles_data)
            logger.info(f"After deduplication: {len(articles_data)} unique articles/pairs")

            results["total_articles"] = len(articles_data)
            results["articles_data"] = articles_data  # Store for CSV export

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

            # Create CSV report
            logger.info("Generating CSV export report")
            csv_path = self._create_export_report_csv(articles_data, zip_path)
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

    def _apply_rate_limit(self):
        """Apply rate limiting to avoid API throttling."""
        if self.rate_limit_delay <= 0:
            return

        with self._rate_limit_lock:
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time

            if time_since_last_request < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last_request
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _deduplicate_translation_pairs(self, articles_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate translation pairs to avoid exporting the same content twice.

        When two articles are translations of each other (e.g., KB0010101 and KB0010544),
        we only want to export them once with a combined filename.

        Args:
            articles_data: List of article data dictionaries

        Returns:
            Deduplicated list where translation pairs are merged into single entries
        """
        seen_sys_ids = set()
        deduplicated = []

        for article_data in articles_data:
            article = article_data["article"]
            article_sys_id = article.get("sys_id")

            # Skip if we've already processed this article as part of a translation pair
            if article_sys_id in seen_sys_ids:
                logger.debug(f"Skipping {article.get('number')} - already processed as translation")
                continue

            # Mark this article as seen
            seen_sys_ids.add(article_sys_id)

            # Mark all translation sys_ids as seen too
            translations = article_data.get("translations", [])
            for trans in translations:
                trans_sys_id = trans.get("sys_id")
                if trans_sys_id:
                    seen_sys_ids.add(trans_sys_id)

            # Add this article data to deduplicated list
            deduplicated.append(article_data)

            if translations:
                logger.debug(
                    f"Keeping {article.get('number')} with {len(translations)} translation(s): "
                    f"{[t.get('number') for t in translations]}"
                )

        logger.info(f"Deduplication: {len(articles_data)} -> {len(deduplicated)} articles")
        return deduplicated

    def _fetch_all_articles(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        category_filter: Optional[str] = None,
        exclude_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all articles with full data from ServiceNow."""
        logger.info("Fetching all articles from ServiceNow (latest versions only)")

        # Pre-fetch categories for performance
        logger.info("Pre-fetching categories...")
        self.servicenow_kb.prefetch_all_categories()

        # Get latest version of articles only (filters out old versions)
        articles = self.servicenow_kb.get_latest_articles_only(query=query)
        logger.info(f"Found {len(articles)} articles (latest versions)")

        # Apply category filters if specified
        if category_filter or exclude_category:
            filtered_articles = []
            for article in articles:
                article_sys_id = article["sys_id"]
                article_with_cat = self.servicenow_kb.get_article_with_category_path(article_sys_id)
                category_path = article_with_cat.get("category_path", [])
                category_path_str = " > ".join([cat.get("label", "") for cat in category_path])

                # Check include filter
                if category_filter:
                    if category_filter.lower() not in category_path_str.lower():
                        continue

                # Check exclude filter
                if exclude_category:
                    if exclude_category.lower() in category_path_str.lower():
                        logger.info(f"Excluding article {article.get('number', '')} from category: {category_path_str}")
                        continue

                filtered_articles.append(article)

            articles = filtered_articles
            logger.info(f"After category filtering: {len(articles)} articles")

        # Apply limit if specified
        if limit is not None and limit > 0:
            articles = articles[:limit]
            logger.info(f"Limited to {len(articles)} articles")

        total = len(articles)
        articles_data = []

        if self.max_workers > 1:
            # Parallel processing
            logger.info(f"Processing {total} articles with {self.max_workers} parallel workers")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_article = {
                    executor.submit(self._fetch_article_data_with_rate_limit, article["sys_id"]): article
                    for article in articles
                }

                # Process completed tasks
                completed = 0
                for future in as_completed(future_to_article):
                    article = future_to_article[future]
                    try:
                        article_data = future.result()
                        articles_data.append(article_data)
                        completed += 1

                        if completed % 10 == 0 or completed == total:
                            logger.info(f"Progress: {completed}/{total} articles processed")

                    except Exception as e:
                        logger.error(
                            f"Error fetching article {article.get('number', 'unknown')}: {e}"
                        )
                        # Continue with other articles
        else:
            # Sequential processing
            logger.info(f"Processing {total} articles sequentially")

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

    def _fetch_article_data_with_rate_limit(self, article_sys_id: str) -> Dict[str, Any]:
        """Fetch article data with rate limiting applied."""
        self._apply_rate_limit()
        return self._fetch_article_data(article_sys_id)

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
            article_number = original_article.get("number", "")
            original_html = original_article.get("text", "")

            logger.info(f"Processing iframes in article: {article_title}")

            # Process iframes in original AND translations separately
            iframe_result = self.iframe_processor.process_article_with_translations(
                original_html=original_html,
                translations=translations,
                article_title=article_title,
                article_number=article_number,
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

    def _create_export_report_csv(
        self, articles_data: List[Dict[str, Any]], zip_path: str
    ) -> str:
        """
        Create CSV report of exported articles.

        Args:
            articles_data: List of article data dictionaries
            zip_path: Path to the created ZIP file

        Returns:
            Path to created CSV file
        """
        import csv
        from datetime import datetime

        # Generate CSV filename based on ZIP filename
        csv_filename = Path(zip_path).stem + "_report.csv"
        csv_path = self.output_dir / csv_filename

        # Define CSV columns
        fieldnames = [
            "article_number",
            "article_title",
            "sys_id",
            "workflow_state",
            "language",
            "has_translations",
            "translation_count",
            "category_path",
            "attachments_count",
            "has_iframes",
            "google_docs_downloaded",
            "google_slides_converted",
            "requires_special_handling",
            "special_handling_flag",
            "created_on",
            "updated_on",
            "author",
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for article_data in articles_data:
                article = article_data["article"]
                translations = article_data.get("translations", [])
                attachments = article_data.get("attachments", [])
                iframe_result = article_data.get("iframe_result")
                category_path = article_data.get("category_path", [])

                # Count Google Docs downloaded
                google_docs_count = 0
                google_slides_count = 0
                if iframe_result and iframe_result.get("has_iframes"):
                    # Count from original
                    if iframe_result["original"].get("summary"):
                        google_docs_count += len(
                            iframe_result["original"]["summary"].get("docs_downloaded", [])
                        )
                        google_slides_count += len(
                            iframe_result["original"]["summary"].get("slides_converted", [])
                        )

                    # Count from translations
                    for trans in iframe_result.get("translations", []):
                        if trans.get("summary"):
                            google_docs_count += len(
                                trans["summary"].get("docs_downloaded", [])
                            )
                            google_slides_count += len(
                                trans["summary"].get("slides_converted", [])
                            )

                # Extract category labels from category path
                category_labels = []
                if category_path:
                    for cat in category_path:
                        if isinstance(cat, dict):
                            category_labels.append(cat.get("label", ""))
                        else:
                            category_labels.append(str(cat))

                # Create combined article number and title if there are translations
                if translations:
                    # Sort by language (ja before en) to match filename format
                    article_lang = article.get("language", {})
                    if isinstance(article_lang, dict):
                        article_lang = article_lang.get("value", "")

                    articles_by_lang = [(article_lang, article.get("number", ""), article.get("short_description", ""))]
                    for trans in translations:
                        trans_lang = trans.get("language", {})
                        if isinstance(trans_lang, dict):
                            trans_lang = trans_lang.get("value", "")
                        articles_by_lang.append((trans_lang, trans.get("number", ""), trans.get("short_description", "")))

                    # Sort by language (ja before en)
                    def lang_sort_key(item):
                        lang = item[0]
                        if lang == 'ja':
                            return (0, lang)
                        elif lang == 'en':
                            return (1, lang)
                        else:
                            return (2, lang)

                    articles_by_lang.sort(key=lang_sort_key)

                    combined_number = " / ".join([num for _, num, _ in articles_by_lang])
                    combined_title = " / ".join([title for _, _, title in articles_by_lang])
                    combined_lang = " / ".join([lang for lang, _, _ in articles_by_lang])
                else:
                    combined_number = article.get("number", "")
                    combined_title = article.get("short_description", "")
                    combined_lang = article.get("language", "")

                row = {
                    "article_number": combined_number,
                    "article_title": combined_title,
                    "sys_id": article.get("sys_id", ""),
                    "workflow_state": article.get("workflow_state", ""),
                    "language": combined_lang,
                    "has_translations": "Yes" if translations else "No",
                    "translation_count": len(translations),
                    "category_path": " > ".join(category_labels) if category_labels else "",
                    "attachments_count": len(attachments),
                    "has_iframes": "Yes"
                    if (iframe_result and iframe_result.get("has_iframes"))
                    else "No",
                    "google_docs_downloaded": google_docs_count,
                    "google_slides_converted": google_slides_count,
                    "requires_special_handling": "Yes"
                    if article_data.get("requires_special_handling")
                    else "No",
                    "special_handling_flag": article_data.get("special_handling_flag", ""),
                    "created_on": article.get("sys_created_on", ""),
                    "updated_on": article.get("sys_updated_on", ""),
                    "author": article.get("author", {}).get("display_value", "")
                    if isinstance(article.get("author"), dict)
                    else article.get("author", ""),
                }

                writer.writerow(row)

        logger.info(f"CSV report saved to: {csv_path}")
        return str(csv_path)
