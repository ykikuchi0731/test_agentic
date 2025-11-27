"""Article data fetching with parallel processing and rate limiting."""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

logger = logging.getLogger(__name__)


class ArticleFetcher:
    """Fetch article data from ServiceNow with parallel processing support."""

    def __init__(
        self,
        knowledge_base,
        max_workers: int = 4,
        rate_limit_delay: float = 0.0,
        process_iframes: bool = False,
        iframe_processor=None,
    ):
        """
        Initialize article fetcher.

        Args:
            knowledge_base: ServiceNow KnowledgeBase instance
            max_workers: Maximum number of parallel workers
            rate_limit_delay: Delay in seconds between API requests
            process_iframes: Whether to process iframes
            iframe_processor: Optional IframeProcessor instance
        """
        self.kb = knowledge_base
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.process_iframes = process_iframes
        self.iframe_processor = iframe_processor
        self._rate_limit_lock = Lock()
        self._last_request_time = 0

    def fetch_all_articles(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        category_filter: Optional[str] = None,
        exclude_category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all articles with full data from ServiceNow.

        Args:
            query: ServiceNow query to filter articles
            limit: Maximum number of articles to fetch
            category_filter: Include only articles under this category
            exclude_category: Exclude articles under this category

        Returns:
            List of article data dictionaries
        """
        logger.info("Fetching articles from ServiceNow (latest versions only)")

        # Pre-fetch categories for performance
        logger.info("Pre-fetching categories...")
        self.kb.prefetch_all_categories()

        # Get latest version of articles only
        articles = self.kb.get_latest_articles_only(query=query)
        logger.info(f"Found {len(articles)} articles (latest versions)")

        # Apply category filters
        if category_filter or exclude_category:
            articles = self._filter_by_category(articles, category_filter, exclude_category)
            logger.info(f"After category filtering: {len(articles)} articles")

        # Apply limit
        if limit is not None and limit > 0:
            articles = articles[:limit]
            logger.info(f"Limited to {len(articles)} articles")

        # Fetch article data
        return self._fetch_articles_data(articles)

    def fetch_single_article(self, article_sys_id: str) -> Dict[str, Any]:
        """
        Fetch complete data for a single article.

        Args:
            article_sys_id: ServiceNow article sys_id

        Returns:
            Article data dictionary
        """
        return self._fetch_article_data(article_sys_id)

    def deduplicate_translation_pairs(
        self, articles_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate translation pairs to avoid exporting the same content twice.

        Args:
            articles_data: List of article data dictionaries

        Returns:
            Deduplicated list where translation pairs are merged
        """
        seen_sys_ids = set()
        deduplicated = []

        for article_data in articles_data:
            article = article_data["article"]
            article_sys_id = article.get("sys_id")

            if article_sys_id in seen_sys_ids:
                logger.debug(
                    f"Skipping {article.get('number')} - already processed as translation"
                )
                continue

            seen_sys_ids.add(article_sys_id)

            # Mark translation sys_ids as seen
            translations = article_data.get("translations", [])
            for trans in translations:
                if trans_sys_id := trans.get("sys_id"):
                    seen_sys_ids.add(trans_sys_id)

            deduplicated.append(article_data)

            if translations:
                logger.debug(
                    f"Keeping {article.get('number')} with {len(translations)} translation(s): "
                    f"{[t.get('number') for t in translations]}"
                )

        logger.info(f"Deduplication: {len(articles_data)} -> {len(deduplicated)} articles")
        return deduplicated

    def _filter_by_category(
        self,
        articles: List[Dict[str, Any]],
        category_filter: Optional[str],
        exclude_category: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Filter articles by category path."""
        filtered = []
        for article in articles:
            article_with_cat = self.kb.get_article_with_category_path(article["sys_id"])
            category_path = article_with_cat.get("category_path", [])
            category_path_str = " > ".join([cat.get("label", "") for cat in category_path])

            # Check include filter
            if category_filter and category_filter.lower() not in category_path_str.lower():
                continue

            # Check exclude filter
            if exclude_category and exclude_category.lower() in category_path_str.lower():
                logger.info(
                    f"Excluding article {article.get('number', '')} from category: {category_path_str}"
                )
                continue

            filtered.append(article)

        return filtered

    def _fetch_articles_data(
        self, articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch data for multiple articles with parallel or sequential processing."""
        total = len(articles)
        articles_data = []

        if self.max_workers > 1:
            articles_data = self._fetch_parallel(articles, total)
        else:
            articles_data = self._fetch_sequential(articles, total)

        logger.info(f"Successfully fetched {len(articles_data)} articles with data")
        return articles_data

    def _fetch_parallel(
        self, articles: List[Dict[str, Any]], total: int
    ) -> List[Dict[str, Any]]:
        """Fetch articles in parallel using ThreadPoolExecutor."""
        logger.info(f"Processing {total} articles with {self.max_workers} parallel workers")
        articles_data = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_article = {
                executor.submit(self._fetch_with_rate_limit, article["sys_id"]): article
                for article in articles
            }

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

        return articles_data

    def _fetch_sequential(
        self, articles: List[Dict[str, Any]], total: int
    ) -> List[Dict[str, Any]]:
        """Fetch articles sequentially."""
        logger.info(f"Processing {total} articles sequentially")
        articles_data = []

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

        return articles_data

    def _fetch_with_rate_limit(self, article_sys_id: str) -> Dict[str, Any]:
        """Fetch article data with rate limiting applied."""
        self._apply_rate_limit()
        return self._fetch_article_data(article_sys_id)

    def _apply_rate_limit(self):
        """Apply rate limiting to avoid API throttling."""
        if self.rate_limit_delay <= 0:
            return

        with self._rate_limit_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - time_since_last)

            self._last_request_time = time.time()

    def _fetch_article_data(self, article_sys_id: str) -> Dict[str, Any]:
        """Fetch complete data for a single article including translations and attachments."""
        # Get original article
        original_article = self.kb.get_article(article_sys_id)

        # Get category path
        article_with_cat = self.kb.get_article_with_category_path(article_sys_id)
        original_article["category_path"] = article_with_cat.get("category_path", [])

        # Get translations
        translations = self.kb._get_translations_for_article(article_sys_id)

        # Get all sys_ids for attachments
        all_sys_ids = [article_sys_id] + [t["sys_id"] for t in translations]

        # Get attachments from original and all translations
        attachments = self.kb.get_attachments_for_all_articles(all_sys_ids, download=True)
        logger.info(
            f"Fetched {len(attachments)} total attachments from original + {len(translations)} translations"
        )

        # Process iframes if enabled
        html_content, iframe_result, downloaded_docs, requires_special_handling, flag_message = (
            self._process_iframes(original_article, translations, attachments)
            if self.process_iframes and self.iframe_processor
            else (
                self.kb._merge_article_html(original_article, translations),
                None,
                [],
                False,
                None,
            )
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

    def _process_iframes(
        self,
        original_article: Dict[str, Any],
        translations: List[Dict[str, Any]],
        attachments: List[Dict[str, Any]],
    ) -> tuple:
        """
        Process iframes in article and translations.

        Returns:
            Tuple of (html_content, iframe_result, downloaded_docs, requires_special_handling, flag_message)
        """
        article_title = original_article.get(
            "short_description", original_article.get("number", "document")
        )
        article_number = original_article.get("number", "")
        original_html = original_article.get("text", "")

        logger.info(f"Processing iframes in article: {article_title}")

        iframe_result = self.iframe_processor.process_article_with_translations(
            original_html=original_html,
            translations=translations,
            article_title=article_title,
            article_number=article_number,
        )

        if not iframe_result["has_iframes"]:
            # No iframes - merge normally
            return (
                self.kb._merge_article_html(original_article, translations),
                iframe_result,
                [],
                False,
                None,
            )

        logger.info(
            f"Iframe processing complete: {iframe_result['total_downloads']} total docs downloaded"
        )

        requires_special_handling = iframe_result["requires_special_handling"]
        flag_message = iframe_result["flag_message"]
        downloaded_docs = []

        if requires_special_handling:
            logger.warning(f"⚠️  SPECIAL HANDLING REQUIRED: {flag_message}")

            # Keep original and translations separate
            html_content = iframe_result["original"]["html"]

            # Add downloaded docs from original
            for doc_path in iframe_result["original"]["downloaded_docs"]:
                attachments.append(self._create_attachment_entry(doc_path, "original"))
                downloaded_docs.append(doc_path)

            # Add downloaded docs from translations
            for trans in iframe_result["translations"]:
                for doc_path in trans["downloaded_docs"]:
                    attachments.append(
                        self._create_attachment_entry(doc_path, trans["language"])
                    )
                    downloaded_docs.append(doc_path)

            logger.info(f"Added {len(downloaded_docs)} downloaded Google Docs as attachments")

        else:
            # No special handling - merge processed HTML
            processed_original_html = iframe_result["original"]["html"]

            # Create processed translations for merging
            processed_translations = [
                {**translations[i], "text": trans_result["html"]}
                for i, trans_result in enumerate(iframe_result["translations"])
            ]

            html_content = self.kb._merge_article_html(
                {"text": processed_original_html}, processed_translations
            )

            # Add downloaded docs as attachments
            for doc_path in iframe_result["original"]["downloaded_docs"]:
                attachments.append(self._create_attachment_entry(doc_path))
                downloaded_docs.append(doc_path)

        return html_content, iframe_result, downloaded_docs, requires_special_handling, flag_message

    def _create_attachment_entry(
        self, doc_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create attachment entry dictionary for a downloaded document."""
        path_obj = Path(doc_path)
        entry = {
            "file_name": path_obj.name,
            "file_path": doc_path,
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size_bytes": path_obj.stat().st_size if path_obj.exists() else 0,
            "source": f"google_docs_iframe_{language}" if language else "google_docs_iframe",
        }
        if language:
            entry["language"] = language
        return entry
