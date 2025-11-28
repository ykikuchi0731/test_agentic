"""Article translation management and HTML merging."""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TranslationManager:
    """Manage article translations and HTML merging."""

    # Language code to display name mapping
    LANG_NAMES = {
        "ja": "Japanese",
        "en": "English",
        "zh": "Chinese",
        "ko": "Korean",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
    }

    # Standard fields to fetch for articles
    ARTICLE_FIELDS = [
        "sys_id",
        "number",
        "short_description",
        "text",
        "language",
        "sys_updated_on",
    ]

    def __init__(self, client):
        """
        Initialize translation manager.

        Args:
            client: ServiceNowClient instance
        """
        self.client = client

    def get_translations(self, article_sys_id: str) -> List[Dict[str, Any]]:
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
            query = f"parent={article_sys_id}^ORtranslated_from={article_sys_id}^workflow_state=published"

            translations = self.client.query_table(
                table="kb_knowledge",
                query=query,
                fields=self.ARTICLE_FIELDS,
            )

            # If no direct translations, check for sibling translations
            if not translations:
                translations = self.find_sibling_translations(article_sys_id)

            logger.info(f"Found {len(translations)} translations")
            return translations

        except Exception as e:
            logger.error(f"Error fetching translations: {e}")
            return []

    def find_sibling_translations(self, article_sys_id: str) -> List[Dict[str, Any]]:
        """
        Find sibling translations by checking if articles share the same parent.
        Handles cases where translations point to outdated versions.

        Args:
            article_sys_id: System ID of the article

        Returns:
            List of sibling translations
        """
        try:
            # Get current article
            current_article = self.client.get_record(
                table="kb_knowledge",
                sys_id=article_sys_id,
                fields=["sys_id", "number", "parent", "language"],
            )

            if not current_article:
                return []

            parent_sys_id = self._extract_parent_sys_id(current_article.get("parent", {}))

            # Case 0: No parent - check if other articles reference any version as parent
            if not parent_sys_id:
                return self._find_children_of_any_version(
                    current_article, current_article.get("number")
                )

            # Case 1 & 2: Has parent
            return self._find_translations_via_parent(current_article, parent_sys_id)

        except Exception as e:
            logger.error(f"Error finding sibling translations: {e}")
            return []

    def merge_html(
        self, original: Dict[str, Any], translations: List[Dict[str, Any]]
    ) -> str:
        """
        Merge original article and translations into single HTML.
        Japanese content first, then other languages.

        Args:
            original: Original article data
            translations: List of translated article data

        Returns:
            Merged HTML string
        """
        # Collect all articles with language
        all_articles = [(self._extract_language(original), original.get("text", ""))]

        # Add translations
        for translation in translations:
            lang = self._extract_language(translation)
            trans_html = translation.get("text", "")
            all_articles.append((lang, trans_html))

        # Sort by language: ja first, then en, then others
        all_articles.sort(key=self._lang_sort_key)

        # Create merged HTML
        merged_parts = []
        for i, (lang, html) in enumerate(all_articles):
            # Language should always be set (defaults to 'ja' in _extract_language)
            lang_code = lang if lang else "ja"
            lang_name = self.LANG_NAMES.get(lang_code, lang_code.upper())

            merged_parts.extend([
                f'<div class="article-section" data-language="{lang_code}">',
                f'<h2 class="language-header">{lang_name}</h2>',
                html,
                '</div>'
            ])

            # Add separator between sections
            if i < len(all_articles) - 1:
                merged_parts.append('<hr class="language-separator" />')

        return "\n".join(merged_parts)

    def _find_children_of_any_version(
        self, current_article: Dict[str, Any], current_kb_number: str
    ) -> List[Dict[str, Any]]:
        """Find articles that reference any version of this KB number as parent."""
        logger.info(
            f"Article {current_kb_number} has no parent, looking for articles that reference any version"
        )

        # Find all versions of this KB number
        all_versions = self.client.query_table(
            table="kb_knowledge", query=f"number={current_kb_number}", fields=["sys_id"]
        )

        if not all_versions:
            return []

        all_sys_ids = [v.get("sys_id") for v in all_versions]
        logger.info(f"Found {len(all_sys_ids)} versions of {current_kb_number}")

        # Find articles that have any of these versions as parent
        current_lang = self._extract_language(current_article)
        translations = []

        for sys_id in all_sys_ids:
            children = self._query_children(sys_id, current_article.get('sys_id'))
            translations.extend(
                self._filter_by_different_language(children, current_lang)
            )

        return translations

    def _find_translations_via_parent(
        self, current_article: Dict[str, Any], parent_sys_id: str
    ) -> List[Dict[str, Any]]:
        """Find translations via parent relationship."""
        # Get parent article
        parent_article = self.client.query_table(
            table="kb_knowledge",
            query=f"sys_id={parent_sys_id}",
            fields=["number", "workflow_state", "language"],
        )

        if not parent_article:
            return []

        # Only proceed if parent is outdated
        if parent_article[0].get("workflow_state") != "outdated":
            return []

        parent_kb_number = parent_article[0].get("number")
        logger.info(
            f"Parent article {parent_kb_number} is outdated, looking for latest version"
        )

        # Find latest published version
        latest_parent = self.client.query_table(
            table="kb_knowledge",
            query=f"number={parent_kb_number}^workflow_state=published",
            fields=["sys_id", "language"],
        )

        if not latest_parent:
            return []

        latest_parent_sys_id = latest_parent[0].get("sys_id")

        # Case 1: Current article IS the latest parent - find siblings
        if latest_parent_sys_id == current_article.get("sys_id"):
            return self._find_siblings_with_same_parent(current_article, parent_sys_id)

        # Case 2: Current article is a sibling - get latest parent as translation
        return self._get_latest_parent_as_translation(
            current_article, latest_parent[0], latest_parent_sys_id
        )

    def _find_siblings_with_same_parent(
        self, current_article: Dict[str, Any], parent_sys_id: str
    ) -> List[Dict[str, Any]]:
        """Find siblings that share the same parent."""
        logger.info("Current article is the latest version, looking for siblings")

        siblings = self._query_children(parent_sys_id, current_article.get('sys_id'))
        current_lang = self._extract_language(current_article)

        return self._filter_by_different_language(siblings, current_lang)

    def _get_latest_parent_as_translation(
        self, current_article: Dict[str, Any], latest_parent: Dict[str, Any],
        latest_parent_sys_id: str
    ) -> List[Dict[str, Any]]:
        """Get latest parent as translation if different language."""
        logger.info("Current article is a sibling, using latest parent as translation")

        current_lang = self._extract_language(current_article)
        latest_parent_lang = self._extract_language(latest_parent)

        # Only include if different language
        if current_lang == latest_parent_lang:
            return []

        # Fetch full latest parent article data
        latest_parent_full = self.client.query_table(
            table="kb_knowledge",
            query=f"sys_id={latest_parent_sys_id}",
            fields=self.ARTICLE_FIELDS,
        )

        if latest_parent_full:
            logger.info(
                f"Found translation: {latest_parent_full[0].get('number')} ({latest_parent_lang})"
            )
            return latest_parent_full

        return []

    def _query_children(self, parent_sys_id: str, exclude_sys_id: str) -> List[Dict[str, Any]]:
        """
        Query for child articles of a parent.

        Args:
            parent_sys_id: Parent article sys_id
            exclude_sys_id: Sys_id to exclude from results

        Returns:
            List of child articles
        """
        return self.client.query_table(
            table="kb_knowledge",
            query=f"parent={parent_sys_id}^workflow_state=published^sys_id!={exclude_sys_id}",
            fields=self.ARTICLE_FIELDS,
        )

    def _filter_by_different_language(
        self, articles: List[Dict[str, Any]], reference_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Filter articles to only include those with different language than reference.

        Args:
            articles: List of articles to filter
            reference_lang: Reference language to compare against

        Returns:
            Filtered list of articles
        """
        filtered = []
        for article in articles:
            article_lang = self._extract_language(article)
            if article_lang != reference_lang:
                logger.info(
                    f"Found translation: {article.get('number')} ({article_lang})"
                )
                filtered.append(article)
        return filtered

    @staticmethod
    def _extract_parent_sys_id(parent_ref: Any) -> str:
        """Extract parent sys_id from reference (dict or string)."""
        if isinstance(parent_ref, dict):
            return parent_ref.get("value", "")
        return str(parent_ref) if parent_ref else ""

    @staticmethod
    def _extract_language(article: Dict[str, Any]) -> str:
        """
        Extract language code from article.

        Returns:
            Language code (e.g., 'ja', 'en'). Defaults to 'ja' if not set.
        """
        lang = article.get("language", "")
        if isinstance(lang, dict):
            lang = lang.get("value", "")

        # Convert to string and strip whitespace
        lang = str(lang).strip() if lang else ""

        # Default to Japanese if language is not set
        return lang if lang else "ja"

    @staticmethod
    def _lang_sort_key(item: tuple) -> tuple:
        """Sort key for language ordering (ja before en)."""
        lang = item[0]
        if lang == "ja":
            return (0, lang)
        elif lang == "en":
            return (1, lang)
        else:
            return (2, lang)
