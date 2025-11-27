"""Knowledge base operations for ServiceNow knowledge portal."""
import logging
from typing import Any, Dict, List, Optional

from .attachment_manager import AttachmentManager
from .category_manager import CategoryManager
from .client import ServiceNowClient
from .parser import HTMLParser
from .translation_manager import TranslationManager

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Handler for ServiceNow knowledge base operations."""

    # Default fields for article queries
    DEFAULT_ARTICLE_FIELDS = [
        "sys_id",
        "number",
        "short_description",
        "text",
        "workflow_state",
        "kb_knowledge_base",
        "kb_category",
        "category",
        "author",
        "sys_created_on",
        "sys_updated_on",
        "valid_to",
        "article_type",
        "version",
        "language",
        "parent",
        "translated_from",
    ]

    def __init__(
        self,
        client: ServiceNowClient,
        download_dir: str = "./downloads",
        enable_cache: bool = True,
    ):
        """
        Initialize knowledge base handler.

        Args:
            client: ServiceNowClient instance
            download_dir: Directory to save downloaded files
            enable_cache: Enable in-memory caching of categories
        """
        self.client = client
        self.parser = HTMLParser()

        # Initialize managers
        self.category_mgr = CategoryManager(client, enable_cache)
        self.translation_mgr = TranslationManager(client)
        self.attachment_mgr = AttachmentManager(client, download_dir)

    # =========================================================================
    # Article Operations
    # =========================================================================

    def list_articles(
        self,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        display_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all HTML articles in knowledge portal.

        Args:
            query: Encoded query string to filter articles
            fields: List of fields to return
            limit: Maximum number of articles to return
            offset: Number of records to skip for pagination
            display_value: Display value option

        Returns:
            List of article records
        """
        if fields is None:
            fields = self.DEFAULT_ARTICLE_FIELDS

        logger.info(f"Listing knowledge articles with query: {query}")

        try:
            articles = self.client.query_table(
                table="kb_knowledge",
                query=query,
                fields=fields,
                limit=limit,
                offset=offset,
                display_value=display_value,
            )

            logger.info(f"Retrieved {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"Error listing articles: {e}")
            raise

    def get_article(
        self, sys_id: str, fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get article data in HTML format by sys_id.

        Args:
            sys_id: System ID of the knowledge article
            fields: List of fields to return

        Returns:
            Article data including HTML content
        """
        # Handle sys_id as dict (when sysparm_display_value=all)
        if isinstance(sys_id, dict):
            sys_id = sys_id.get("value", sys_id.get("display_value", ""))

        if fields is None:
            fields = self.DEFAULT_ARTICLE_FIELDS + ["meta", "meta_description"]

        logger.info(f"Getting article {sys_id}")

        try:
            article = self.client.get_record(table="kb_knowledge", sys_id=sys_id, fields=fields)

            if not article:
                raise ValueError(f"Article {sys_id} not found")

            logger.info(f"Retrieved article: {article.get('number', sys_id)}")
            return article

        except Exception as e:
            logger.error(f"Error getting article {sys_id}: {e}")
            raise

    def get_all_articles_paginated(
        self,
        query: Optional[str] = None,
        page_size: int = 100,
        display_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all articles using pagination.

        Args:
            query: Encoded query string to filter articles
            page_size: Number of records per page
            display_value: Display value option

        Returns:
            List of all article records
        """
        all_articles = []
        offset = 0

        while True:
            logger.info(f"Fetching page at offset {offset}")
            articles = self.list_articles(
                query=query, limit=page_size, offset=offset, display_value=display_value
            )

            if not articles:
                break

            all_articles.extend(articles)
            offset += page_size

            if len(articles) < page_size:
                break

        logger.info(f"Retrieved total of {len(all_articles)} articles")
        return all_articles

    def get_latest_articles_only(
        self,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        display_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get only the latest version of each article (deduplicates by article number).

        Args:
            query: Additional encoded query string to filter articles
            fields: List of fields to return
            display_value: Display value option

        Returns:
            List of article records (latest version only)
        """
        logger.info("Fetching latest version of articles only")

        # Build query with ORDER BY
        base_query = "workflow_state=published^ORDERBYDESCsys_updated_on"
        if query:
            if "workflow_state" in query:
                base_query = f"{query}^ORDERBYDESCsys_updated_on"
            else:
                base_query = f"{query}^{base_query}"

        if fields is None:
            fields = self.DEFAULT_ARTICLE_FIELDS

        # Get all articles
        all_articles = self.get_all_articles_paginated(
            query=base_query, display_value=display_value
        )

        # Deduplicate: keep only latest version of each article number
        latest_articles = {}
        for article in all_articles:
            number = article.get("number")

            # Handle number as dict
            if isinstance(number, dict):
                number = number.get("value", number.get("display_value", ""))

            if number and number not in latest_articles:
                latest_articles[number] = article

        result = list(latest_articles.values())
        logger.info(
            f"Filtered to {len(result)} latest articles from {len(all_articles)} total versions"
        )

        return result

    # =========================================================================
    # Category Operations (delegated to CategoryManager)
    # =========================================================================

    def get_category(self, category_sys_id: str) -> Optional[Dict[str, Any]]:
        """Get category details by sys_id."""
        return self.category_mgr.get_category(category_sys_id)

    def get_category_hierarchy(self, category_sys_id: str) -> List[Dict[str, Any]]:
        """Get full category hierarchy from root to specified category."""
        return self.category_mgr.get_hierarchy(category_sys_id)

    def get_article_with_category_path(self, sys_id: str) -> Dict[str, Any]:
        """
        Get article with full category hierarchy path.

        Args:
            sys_id: System ID of the knowledge article

        Returns:
            Article data with added 'category_path' field
        """
        article = self.get_article(sys_id)

        # Get category hierarchy if article has a category
        kb_category = article.get("kb_category", {})
        if isinstance(kb_category, dict) and kb_category.get("value"):
            category_sys_id = kb_category["value"]
            article["category_path"] = self.get_category_hierarchy(category_sys_id)
        else:
            article["category_path"] = []

        return article

    def prefetch_all_categories(self) -> int:
        """
        Pre-fetch all categories from ServiceNow and store in memory.
        Recommended for bulk operations.

        Returns:
            Number of categories fetched
        """
        return self.category_mgr.prefetch_all()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about category cache usage."""
        return self.category_mgr.get_stats()

    def clear_cache(self):
        """Clear the category cache."""
        self.category_mgr.clear_cache()

    def clear_prefetch(self):
        """Clear the pre-fetched category tree."""
        self.category_mgr.clear_prefetch()

    # =========================================================================
    # Attachment Operations (delegated to AttachmentManager)
    # =========================================================================

    def get_article_attachments(
        self, article_sys_id: str, download: bool = False
    ) -> List[Dict[str, Any]]:
        """Get attached files for an article."""
        return self.attachment_mgr.get_attachments(article_sys_id, download)

    def get_attachments_for_all_articles(
        self, article_sys_ids: List[str], download: bool = False
    ) -> List[Dict[str, Any]]:
        """Get attachments from multiple articles."""
        return self.attachment_mgr.get_attachments_for_multiple(article_sys_ids, download)

    # =========================================================================
    # Translation Operations (delegated to TranslationManager)
    # =========================================================================

    def get_article_with_translations(self, sys_id: str) -> Dict[str, Any]:
        """
        Get article with all its translated versions merged into HTML.

        Args:
            sys_id: System ID of the original article

        Returns:
            Article data with 'merged_html' containing original + all translations
        """
        logger.info(f"Getting article with translations: {sys_id}")

        # Get the original article
        original = self.get_article(sys_id)

        # Get all translated versions
        translations = self._get_translations_for_article(sys_id)

        if not translations:
            # No translations, just return original HTML
            original["merged_html"] = original.get("text", "")
            original["translations"] = []
            original["all_sys_ids"] = [sys_id]
            logger.info(f"No translations found for article {original.get('number')}")
            return original

        # Merge original and translations into single HTML
        merged_html = self._merge_article_html(original, translations)

        original["merged_html"] = merged_html
        original["translations"] = translations
        original["all_sys_ids"] = [sys_id] + [t["sys_id"] for t in translations]

        logger.info(f"Merged {len(translations)} translations into article {original.get('number')}")

        return original

    def _get_translations_for_article(self, article_sys_id: str) -> List[Dict[str, Any]]:
        """Get all translated versions of an article."""
        return self.translation_mgr.get_translations(article_sys_id)

    def _merge_article_html(
        self, original: Dict[str, Any], translations: List[Dict[str, Any]]
    ) -> str:
        """Merge original article and translations into single HTML."""
        return self.translation_mgr.merge_html(original, translations)

    # =========================================================================
    # HTML Parsing (delegated to HTMLParser)
    # =========================================================================

    def parse_article_html(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML content from article."""
        return self.parser.parse_html(html_content)
