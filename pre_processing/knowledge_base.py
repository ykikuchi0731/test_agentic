"""Knowledge base operations for ServiceNow knowledge portal."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import ServiceNowClient
from .parser import HTMLParser

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Handler for ServiceNow knowledge base operations."""

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
            enable_cache: Enable in-memory caching of categories (default: True)
        """
        self.client = client
        self.download_dir = Path(download_dir)
        self.parser = HTMLParser()

        # Category caching for performance
        self.enable_cache = enable_cache
        self._category_cache: Dict[str, Dict[str, Any]] = {}
        self._category_tree: Optional[Dict[str, Dict[str, Any]]] = None
        self._invalid_category_cache: set = set()  # Track 404/invalid category IDs

        # Create download directory if it doesn't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def list_articles(
        self,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List all HTML articles in knowledge portal.

        Args:
            query: Encoded query string to filter articles
            fields: List of fields to return (default: all common fields)
            limit: Maximum number of articles to return
            offset: Number of records to skip for pagination

        Returns:
            List of article records

        Example:
            # List all published articles
            articles = kb.list_articles(query='workflow_state=published')

            # List specific fields only
            articles = kb.list_articles(fields=['sys_id', 'short_description', 'number'])
        """
        if fields is None:
            fields = [
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

        logger.info(f"Listing knowledge articles with query: {query}")

        try:
            articles = self.client.query_table(
                table="kb_knowledge",
                query=query,
                fields=fields,
                limit=limit,
                offset=offset,
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
            fields: List of fields to return (default: all common fields)

        Returns:
            Article data including HTML content

        Example:
            article = kb.get_article('a1b2c3d4e5f6g7h8i9j0')
            html_content = article['text']
            title = article['short_description']
        """
        if fields is None:
            fields = [
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
                "meta",
                "meta_description",
                "version",
                "language",
                "parent",
                "translated_from",
            ]

        logger.info(f"Getting article {sys_id}")

        try:
            article = self.client.get_record(
                table="kb_knowledge", sys_id=sys_id, fields=fields
            )

            if not article:
                raise ValueError(f"Article {sys_id} not found")

            logger.info(f"Retrieved article: {article.get('number', sys_id)}")
            return article

        except Exception as e:
            logger.error(f"Error getting article {sys_id}: {e}")
            raise

    def get_article_attachments(
        self, article_sys_id: str, download: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get attached files within HTML article.

        Args:
            article_sys_id: System ID of the knowledge article
            download: If True, download attachment files to disk

        Returns:
            List of attachment metadata dictionaries

        Example:
            # Get attachment metadata only
            attachments = kb.get_article_attachments('a1b2c3d4e5f6g7h8i9j0')

            # Download all attachments
            attachments = kb.get_article_attachments('a1b2c3d4e5f6g7h8i9j0', download=True)
            for att in attachments:
                print(f"Downloaded: {att['file_path']}")
        """
        logger.info(f"Getting attachments for article {article_sys_id}")

        # Query attachments for this article
        query = f"table_name=kb_knowledge^table_sys_id={article_sys_id}"

        try:
            attachments = self.client.query_table(
                table="sys_attachment",
                query=query,
                fields=[
                    "sys_id",
                    "file_name",
                    "content_type",
                    "size_bytes",
                    "sys_created_on",
                    "download_link",
                ],
            )

            logger.info(f"Found {len(attachments)} attachments")

            # Download attachments if requested
            if download and attachments:
                self._download_attachments(article_sys_id, attachments)

            return attachments

        except Exception as e:
            logger.error(f"Error getting attachments for article {article_sys_id}: {e}")
            raise

    def get_attachments_for_all_articles(
        self, article_sys_ids: List[str], download: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get attachments from multiple articles (e.g., original + translations).

        Args:
            article_sys_ids: List of article system IDs
            download: If True, download attachment files to disk

        Returns:
            Combined list of attachment metadata from all articles

        Example:
            # Get attachments from original + translations
            all_sys_ids = ['original_sys_id', 'translation1_sys_id', 'translation2_sys_id']
            attachments = kb.get_attachments_for_all_articles(all_sys_ids, download=True)
        """
        logger.info(f"Getting attachments for {len(article_sys_ids)} articles")

        all_attachments = []

        for article_sys_id in article_sys_ids:
            try:
                attachments = self.get_article_attachments(article_sys_id, download=download)
                all_attachments.extend(attachments)
            except Exception as e:
                logger.error(f"Error getting attachments for {article_sys_id}: {e}")
                continue

        logger.info(f"Found total of {len(all_attachments)} attachments across all articles")
        return all_attachments

    def _download_attachments(
        self, article_sys_id: str, attachments: List[Dict[str, Any]]
    ) -> None:
        """
        Download attachment files to disk.

        Args:
            article_sys_id: System ID of the article
            attachments: List of attachment metadata
        """
        # Create article-specific directory
        article_dir = self.download_dir / article_sys_id
        article_dir.mkdir(parents=True, exist_ok=True)

        for attachment in attachments:
            sys_id = attachment["sys_id"]
            file_name = attachment["file_name"]

            try:
                logger.info(f"Downloading attachment: {file_name}")

                # Download file content
                content = self.client.get_attachment(sys_id)

                # Save to disk
                file_path = article_dir / file_name
                file_path.write_bytes(content)

                # Add local file path to attachment metadata
                attachment["file_path"] = str(file_path)

                logger.info(f"Saved attachment to {file_path}")

            except Exception as e:
                logger.error(f"Error downloading attachment {file_name}: {e}")
                attachment["download_error"] = str(e)

    def parse_article_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML content from article.

        Args:
            html_content: HTML content string from article

        Returns:
            Parsed content with text, images, links, etc.
        """
        return self.parser.parse_html(html_content)

    def get_all_articles_paginated(
        self, query: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all articles using pagination.

        Args:
            query: Encoded query string to filter articles
            page_size: Number of records per page

        Returns:
            List of all article records
        """
        all_articles = []
        offset = 0

        while True:
            logger.info(f"Fetching page at offset {offset}")
            articles = self.list_articles(query=query, limit=page_size, offset=offset)

            if not articles:
                break

            all_articles.extend(articles)
            offset += page_size

            # If we got fewer than page_size, we're done
            if len(articles) < page_size:
                break

        logger.info(f"Retrieved total of {len(all_articles)} articles")
        return all_articles

    def get_category(self, category_sys_id: str) -> Optional[Dict[str, Any]]:
        """
        Get category details by sys_id (with caching and 404 handling).

        Args:
            category_sys_id: System ID of the category

        Returns:
            Category details including label, parent_id, and other metadata
            Returns None if category doesn't exist (404) or is invalid

        Example:
            category = kb.get_category('a1b2c3d4e5f6g7h8i9j0')
            if category:
                print(f"Category: {category['label']}")
            else:
                print("Category not found or deleted")
        """
        # Check if we already know this category is invalid (avoid repeat 404 calls)
        if category_sys_id in self._invalid_category_cache:
            logger.debug(f"Skipping known invalid category {category_sys_id}")
            return None

        # Check cache first
        if self.enable_cache and category_sys_id in self._category_cache:
            logger.debug(f"Cache hit for category {category_sys_id}")
            return self._category_cache[category_sys_id]

        # Check pre-fetched tree
        if self._category_tree and category_sys_id in self._category_tree:
            logger.debug(f"Found category {category_sys_id} in pre-fetched tree")
            return self._category_tree[category_sys_id]

        logger.info(f"Fetching category {category_sys_id} from API")

        try:
            category = self.client.get_record(
                table="kb_category",
                sys_id=category_sys_id,
                fields=[
                    "sys_id",
                    "label",
                    "parent_id",
                    "sys_created_on",
                    "sys_updated_on",
                    "active",
                ],
            )

            if not category:
                # Category not found - cache as invalid to avoid repeat calls
                logger.warning(f"Category {category_sys_id} not found (404) - caching as invalid")
                self._invalid_category_cache.add(category_sys_id)
                return None

            # Store in cache
            if self.enable_cache:
                self._category_cache[category_sys_id] = category

            return category

        except Exception as e:
            # Check if it's a 404 error (category deleted/doesn't exist)
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                logger.warning(f"Category {category_sys_id} not found (404) - caching as invalid")
                self._invalid_category_cache.add(category_sys_id)
                return None
            else:
                # Other error - log and re-raise
                logger.error(f"Error getting category {category_sys_id}: {e}")
                raise

    def get_category_hierarchy(self, category_sys_id: str) -> List[Dict[str, Any]]:
        """
        Get full category hierarchy from root to the specified category.

        Args:
            category_sys_id: System ID of the category

        Returns:
            List of categories from root to specified category (ordered from parent to child)

        Example:
            hierarchy = kb.get_category_hierarchy('a1b2c3d4e5f6g7h8i9j0')
            for cat in hierarchy:
                print(f"  > {cat['label']}")
        """
        logger.info(f"Getting category hierarchy for {category_sys_id}")

        hierarchy = []
        current_sys_id = category_sys_id
        max_depth = 10  # Prevent infinite loops
        depth = 0

        try:
            while current_sys_id and depth < max_depth:
                category = self.get_category(current_sys_id)

                # If category doesn't exist (404), stop traversing
                if category is None:
                    logger.warning(f"Category {current_sys_id} not found - stopping hierarchy traversal")
                    break

                hierarchy.insert(
                    0, category
                )  # Insert at beginning to maintain order

                # Check if there's a parent
                parent_id = category.get("parent_id", {})
                if isinstance(parent_id, dict) and parent_id.get("value"):
                    current_sys_id = parent_id["value"]
                else:
                    # No parent - we've reached the root
                    break

                depth += 1

            return hierarchy

        except Exception as e:
            logger.error(f"Error getting category hierarchy: {e}")
            raise

    def get_article_with_category_path(self, sys_id: str) -> Dict[str, Any]:
        """
        Get article with full category hierarchy path.

        Args:
            sys_id: System ID of the knowledge article

        Returns:
            Article data with added 'category_path' field containing the hierarchy

        Example:
            article = kb.get_article_with_category_path('a1b2c3d4e5f6g7h8i9j0')
            print(f"Category Path: {' > '.join([c['label'] for c in article['category_path']])}")
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

    def get_latest_articles_only(
        self, query: Optional[str] = None, fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get only the latest version of each article (deduplicates by article number).

        Args:
            query: Additional encoded query string to filter articles
            fields: List of fields to return

        Returns:
            List of article records (latest version only)

        Example:
            # Get latest versions of all published articles
            articles = kb.get_latest_articles_only(query='workflow_state=published')
        """
        logger.info("Fetching latest version of articles only")

        # Build query to get published articles, ordered by update time descending
        base_query = "workflow_state=published^ORDERBYDESCsys_updated_on"
        if query:
            # If user provided query already has workflow_state, use it as-is
            if "workflow_state" in query:
                base_query = f"{query}^ORDERBYDESCsys_updated_on"
            else:
                base_query = f"{query}^{base_query}"

        if fields is None:
            fields = [
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

        # Get all articles
        all_articles = self.get_all_articles_paginated(query=base_query)

        # Deduplicate: keep only the latest version of each article number
        latest_articles = {}
        for article in all_articles:
            number = article.get("number")
            if number:
                # Keep first occurrence (already sorted by sys_updated_on DESC)
                if number not in latest_articles:
                    latest_articles[number] = article

        result = list(latest_articles.values())
        logger.info(
            f"Filtered to {len(result)} latest articles from {len(all_articles)} total versions"
        )

        return result

    def get_article_with_translations(self, sys_id: str) -> Dict[str, Any]:
        """
        Get article with all its translated versions merged into HTML.

        Args:
            sys_id: System ID of the original article

        Returns:
            Article data with 'merged_html' containing original + all translations

        Example:
            article = kb.get_article_with_translations('a1b2c3d4e5f6g7h8i9j0')
            merged_content = article['merged_html']
            print(f"Merged {len(article['translations'])} translations")
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
            original["all_sys_ids"] = [sys_id]  # Only original article
            logger.info(f"No translations found for article {original.get('number')}")
            return original

        # Merge original and translations into single HTML
        merged_html = self._merge_article_html(original, translations)

        original["merged_html"] = merged_html
        original["translations"] = translations

        # Store all sys_ids (original + translations) for attachment fetching
        original["all_sys_ids"] = [sys_id] + [t["sys_id"] for t in translations]

        logger.info(
            f"Merged {len(translations)} translations into article {original.get('number')}"
        )

        return original

    def _get_translations_for_article(
        self, article_sys_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all translated versions of an article.

        Args:
            article_sys_id: System ID of the original article

        Returns:
            List of translated article records
        """
        logger.info(f"Fetching translations for article {article_sys_id}")

        try:
            # Query for translations linked to this article
            # Try both 'parent' and 'translated_from' fields (depends on ServiceNow version)
            query = f"parent={article_sys_id}^ORtranslated_from={article_sys_id}^workflow_state=published"

            translations = self.client.query_table(
                table="kb_knowledge",
                query=query,
                fields=[
                    "sys_id",
                    "number",
                    "short_description",
                    "text",
                    "language",
                    "sys_updated_on",
                ],
            )

            logger.info(f"Found {len(translations)} translations")
            return translations

        except Exception as e:
            logger.error(f"Error fetching translations: {e}")
            return []

    def _merge_article_html(
        self, original: Dict[str, Any], translations: List[Dict[str, Any]]
    ) -> str:
        """
        Merge original article and translations into single HTML.

        Args:
            original: Original article data
            translations: List of translated article data

        Returns:
            Merged HTML string with original and all translations
        """
        # Start with original article
        original_html = original.get("text", "")
        original_lang = original.get("language", {})
        if isinstance(original_lang, dict):
            original_lang = original_lang.get("value", "Original")
        elif not original_lang:
            original_lang = "Original"

        # Create merged HTML structure
        merged_parts = []

        # Add original content with language section
        merged_parts.append(
            f'<div class="article-section" data-language="{original_lang}">'
        )
        merged_parts.append(
            f'<h2 class="language-header">Original ({original_lang})</h2>'
        )
        merged_parts.append(original_html)
        merged_parts.append("</div>")
        merged_parts.append('<hr class="language-separator" />')

        # Add each translation
        for translation in translations:
            lang = translation.get("language", {})
            if isinstance(lang, dict):
                lang = lang.get("value", "Unknown")
            elif not lang:
                lang = "Unknown"

            trans_html = translation.get("text", "")

            merged_parts.append(f'<div class="article-section" data-language="{lang}">')
            merged_parts.append(
                f'<h2 class="language-header">Translation ({lang})</h2>'
            )
            merged_parts.append(trans_html)
            merged_parts.append("</div>")
            merged_parts.append('<hr class="language-separator" />')

        # Remove last separator
        if merged_parts and merged_parts[-1].startswith("<hr"):
            merged_parts.pop()

        merged_html = "\n".join(merged_parts)

        return merged_html

    def prefetch_all_categories(self) -> int:
        """
        Pre-fetch all categories from ServiceNow and store in memory.
        This eliminates the need for individual API calls when traversing hierarchies.
        Recommended for bulk operations (migrating many articles).

        Returns:
            Number of categories fetched

        Example:
            kb = KnowledgeBase(client)
            count = kb.prefetch_all_categories()
            print(f"Loaded {count} categories into memory")

            # Now all get_category_hierarchy() calls use cached data
            # with ZERO additional API calls
        """
        logger.info("Pre-fetching all categories from ServiceNow...")

        try:
            # Fetch all categories in one API call
            all_categories = self.client.query_table(
                table="kb_category",
                fields=[
                    "sys_id",
                    "label",
                    "parent_id",
                    "sys_created_on",
                    "sys_updated_on",
                    "active",
                ],
            )

            # Build lookup dictionary
            self._category_tree = {cat["sys_id"]: cat for cat in all_categories}

            logger.info(f"Pre-fetched {len(all_categories)} categories")
            return len(all_categories)

        except Exception as e:
            logger.error(f"Error pre-fetching categories: {e}")
            raise

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about category cache usage and invalid categories.

        Returns:
            Dictionary with cache statistics including invalid category count

        Example:
            stats = kb.get_cache_stats()
            print(f"Cache size: {stats['cache_size']}")
            print(f"Pre-fetched: {stats['prefetched']}")
        """
        return {
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._category_cache),
            "prefetched": self._category_tree is not None,
            "prefetch_size": len(self._category_tree) if self._category_tree else 0,
            "invalid_categories": len(self._invalid_category_cache),
            "invalid_category_ids": list(self._invalid_category_cache) if self._invalid_category_cache else [],
        }

    def clear_cache(self):
        """Clear the category cache."""
        self._category_cache.clear()
        logger.info("Category cache cleared")

    def clear_prefetch(self):
        """Clear the pre-fetched category tree."""
        self._category_tree = None
        logger.info("Pre-fetched category tree cleared")
