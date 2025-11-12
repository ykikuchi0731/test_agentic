"""Export article list with metadata for migration planning (no file downloads)."""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArticleListExporter:
    """Export article metadata list without downloading HTML or attachments."""

    def __init__(self, servicenow_kb, output_dir: str = "./migration_output"):
        """
        Initialize article list exporter.

        Args:
            servicenow_kb: ServiceNow KnowledgeBase instance
            output_dir: Directory to save exported lists
        """
        self.servicenow_kb = servicenow_kb
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Article list exporter initialized")

    def collect_article_metadata(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        category_filter: Optional[str] = None,
        updated_after: Optional[str] = None,
        updated_before: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Collect metadata for articles without downloading files.

        Args:
            query: ServiceNow query to filter articles (will be combined with other filters)
            limit: Maximum number of articles to process (for quick sampling)
            category_filter: Filter by category label (partial match, case-insensitive)
            updated_after: Filter articles updated after this date (YYYY-MM-DD)
            updated_before: Filter articles updated before this date (YYYY-MM-DD)

        Returns:
            List of article metadata dictionaries

        Process:
            1. Fetch latest versions of articles
            2. Apply filters (limit, category, date range)
            3. Get translations for each article
            4. Get category hierarchy
            5. Compile metadata (no HTML/attachment downloads)

        Examples:
            # Get first 50 articles
            metadata = exporter.collect_article_metadata(limit=50)

            # Get articles from specific category
            metadata = exporter.collect_article_metadata(category_filter="Tokyo Office")

            # Get recent articles
            metadata = exporter.collect_article_metadata(updated_after="2024-01-01")

            # Combine filters
            metadata = exporter.collect_article_metadata(
                limit=100,
                category_filter="IT",
                updated_after="2024-01-01"
            )
        """
        logger.info("Collecting article metadata (no file downloads)")

        # Build ServiceNow query with date filters
        combined_query = self._build_query(query, updated_after, updated_before)

        # Pre-fetch categories for performance
        logger.info("Pre-fetching categories...")
        self.servicenow_kb.prefetch_all_categories()

        # Get latest version of articles only
        articles = self.servicenow_kb.get_latest_articles_only(query=combined_query)
        logger.info(f"Found {len(articles)} articles (latest versions)")

        # Apply limit if specified (for quick sampling)
        if limit and len(articles) > limit:
            logger.info(f"Limiting to first {limit} articles")
            articles = articles[:limit]

        article_metadata_list = []
        total = len(articles)

        for i, article in enumerate(articles, 1):
            try:
                if i % 10 == 0 or (limit and i == limit):
                    logger.info(f"Processing: {i}/{total} articles")

                metadata = self._collect_single_article_metadata(article)

                # Apply category filter if specified
                if category_filter:
                    category_path = metadata.get("category_path", "")
                    if category_filter.lower() not in category_path.lower():
                        continue  # Skip articles that don't match category filter

                article_metadata_list.append(metadata)

            except Exception as e:
                logger.error(
                    f"Error collecting metadata for article {article.get('number', 'unknown')}: {e}"
                )
                continue

        logger.info(
            f"Successfully collected metadata for {len(article_metadata_list)} articles"
        )
        return article_metadata_list

    def _build_query(
        self,
        base_query: Optional[str],
        updated_after: Optional[str],
        updated_before: Optional[str],
    ) -> Optional[str]:
        """
        Build ServiceNow query with date filters.

        Args:
            base_query: Base query string
            updated_after: Filter articles updated after this date (YYYY-MM-DD)
            updated_before: Filter articles updated before this date (YYYY-MM-DD)

        Returns:
            Combined query string
        """
        query_parts = []

        if base_query:
            query_parts.append(base_query)

        if updated_after:
            query_parts.append(f"sys_updated_on>={updated_after}")

        if updated_before:
            query_parts.append(f"sys_updated_on<={updated_before}")

        if query_parts:
            return "^".join(query_parts)

        return None

    def _collect_single_article_metadata(
        self, article: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect metadata for a single article.

        Args:
            article: Article record from ServiceNow

        Returns:
            Dictionary with article metadata
        """
        article_sys_id = article["sys_id"]
        article_number = article.get("number", "")

        # Get translations (without downloading)
        translations = self._get_translations_metadata(article_sys_id)

        # Get category path
        category_path = self._get_category_path(article_sys_id)

        # Extract author info
        author = article.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("display_value", "")
        else:
            author_name = str(author)

        # Extract language
        language = article.get("language", {})
        if isinstance(language, dict):
            language_code = language.get("value", "")
        else:
            language_code = str(language)

        # Compile metadata
        metadata = {
            # Basic info
            "article_number": article_number,
            "article_title": article.get("short_description", ""),
            "sys_id": article_sys_id,
            "article_type": article.get("article_type", ""),

            # Status
            "workflow_state": article.get("workflow_state", ""),
            "valid_to": article.get("valid_to", ""),

            # Dates
            "created_on": article.get("sys_created_on", ""),
            "updated_on": article.get("sys_updated_on", ""),

            # Language and version
            "language": language_code,
            "version": article.get("version", ""),

            # Author
            "author": author_name,

            # Category
            "category_path": " > ".join(category_path) if category_path else "",
            "category_depth": len(category_path),

            # Translations
            "has_translations": len(translations) > 0,
            "translation_count": len(translations),
            "translations": translations,
        }

        return metadata

    def _get_translations_metadata(
        self, article_sys_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get metadata for translations without downloading content.

        Args:
            article_sys_id: System ID of the original article

        Returns:
            List of translation metadata
        """
        try:
            # Query for translations
            query = f"parent={article_sys_id}^ORtranslated_from={article_sys_id}^workflow_state=published"

            translations = self.servicenow_kb.client.query_table(
                table="kb_knowledge",
                query=query,
                fields=[
                    "sys_id",
                    "number",
                    "short_description",
                    "language",
                    "sys_updated_on",
                ],
            )

            translation_list = []
            for trans in translations:
                lang = trans.get("language", {})
                if isinstance(lang, dict):
                    lang_code = lang.get("value", "Unknown")
                else:
                    lang_code = str(lang) if lang else "Unknown"

                translation_list.append(
                    {
                        "translation_sys_id": trans.get("sys_id", ""),
                        "translation_number": trans.get("number", ""),
                        "translation_title": trans.get("short_description", ""),
                        "translation_language": lang_code,
                        "translation_updated_on": trans.get("sys_updated_on", ""),
                    }
                )

            return translation_list

        except Exception as e:
            logger.error(f"Error fetching translation metadata: {e}")
            return []

    def _get_category_path(self, article_sys_id: str) -> List[str]:
        """
        Get category hierarchy path for an article.

        Args:
            article_sys_id: System ID of the article

        Returns:
            List of category names from root to leaf
        """
        try:
            article_with_cat = self.servicenow_kb.get_article_with_category_path(
                article_sys_id
            )
            category_path = article_with_cat.get("category_path", [])

            return [cat.get("label", "") for cat in category_path]

        except Exception as e:
            logger.error(f"Error getting category path: {e}")
            return []

    def _generate_timestamped_filename(self, base_filename: str) -> str:
        """
        Generate filename with timestamp to avoid overwriting.

        Args:
            base_filename: Base filename (e.g., "article_list.csv")

        Returns:
            Timestamped filename (e.g., "article_list_20241112_143025.csv")

        Examples:
            "article_list.csv" -> "article_list_20241112_143025.csv"
            "my_export.json" -> "my_export_20241112_143025.json"
        """
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Split filename into name and extension
        path = Path(base_filename)
        name = path.stem
        extension = path.suffix

        # Create timestamped filename
        timestamped_name = f"{name}_{timestamp}{extension}"

        return timestamped_name

    def export_to_csv(
        self,
        article_metadata_list: List[Dict[str, Any]],
        filename: str = "article_list.csv",
        add_timestamp: bool = True,
    ) -> str:
        """
        Export article metadata to CSV file with automatic timestamping.

        Args:
            article_metadata_list: List of article metadata
            filename: Output filename (default: "article_list.csv")
            add_timestamp: If True, add timestamp to filename to avoid overwriting (default: True)

        Returns:
            Path to created CSV file

        Examples:
            # With timestamp (default): article_list_20241112_143025.csv
            exporter.export_to_csv(metadata)

            # Without timestamp: article_list.csv (will overwrite)
            exporter.export_to_csv(metadata, add_timestamp=False)
        """
        # Add timestamp to filename if requested
        if add_timestamp:
            filename = self._generate_timestamped_filename(filename)

        output_path = self.output_dir / filename
        logger.info(f"Exporting article list to CSV: {output_path}")

        # Flatten translations for CSV
        csv_rows = []
        for article in article_metadata_list:
            base_row = {
                "article_number": article["article_number"],
                "article_title": article["article_title"],
                "sys_id": article["sys_id"],
                "article_type": article["article_type"],
                "workflow_state": article["workflow_state"],
                "valid_to": article["valid_to"],
                "created_on": article["created_on"],
                "updated_on": article["updated_on"],
                "language": article["language"],
                "version": article["version"],
                "author": article["author"],
                "category_path": article["category_path"],
                "category_depth": article["category_depth"],
                "has_translations": article["has_translations"],
                "translation_count": article["translation_count"],
            }

            # If no translations, add one row
            if not article["translations"]:
                csv_rows.append(base_row)
            else:
                # Add row for each translation
                for trans in article["translations"]:
                    row = base_row.copy()
                    row.update(trans)
                    csv_rows.append(row)

        # Write CSV
        if csv_rows:
            fieldnames = list(csv_rows[0].keys())
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)

            logger.info(f"✅ CSV exported: {output_path} ({len(csv_rows)} rows)")
        else:
            logger.warning("No data to export to CSV")

        return str(output_path)

    def export_to_json(
        self,
        article_metadata_list: List[Dict[str, Any]],
        filename: str = "article_list.json",
        add_timestamp: bool = True,
    ) -> str:
        """
        Export article metadata to JSON file with automatic timestamping.

        Args:
            article_metadata_list: List of article metadata
            filename: Output filename (default: "article_list.json")
            add_timestamp: If True, add timestamp to filename to avoid overwriting (default: True)

        Returns:
            Path to created JSON file

        Examples:
            # With timestamp (default): article_list_20241112_143025.json
            exporter.export_to_json(metadata)

            # Without timestamp: article_list.json (will overwrite)
            exporter.export_to_json(metadata, add_timestamp=False)
        """
        # Add timestamp to filename if requested
        if add_timestamp:
            filename = self._generate_timestamped_filename(filename)

        output_path = self.output_dir / filename
        logger.info(f"Exporting article list to JSON: {output_path}")

        # Add export timestamp to metadata
        export_info = {
            "source": "ServiceNow Knowledge Base",
            "includes_translations": True,
            "includes_categories": True,
            "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_articles": len(article_metadata_list),
                    "export_info": export_info,
                    "articles": article_metadata_list,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        logger.info(f"✅ JSON exported: {output_path} ({len(article_metadata_list)} articles)")
        return str(output_path)

    def export_summary(
        self, article_metadata_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics from article metadata.

        Args:
            article_metadata_list: List of article metadata

        Returns:
            Dictionary with summary statistics
        """
        total_articles = len(article_metadata_list)
        articles_with_translations = sum(
            1 for a in article_metadata_list if a["has_translations"]
        )
        total_translations = sum(a["translation_count"] for a in article_metadata_list)

        # Count by category
        categories = {}
        for article in article_metadata_list:
            cat_path = article["category_path"]
            if cat_path:
                categories[cat_path] = categories.get(cat_path, 0) + 1

        # Count by language
        languages = {}
        for article in article_metadata_list:
            lang = article["language"]
            languages[lang] = languages.get(lang, 0) + 1

        # Count by workflow state
        workflow_states = {}
        for article in article_metadata_list:
            state = article["workflow_state"]
            workflow_states[state] = workflow_states.get(state, 0) + 1

        summary = {
            "total_articles": total_articles,
            "articles_with_translations": articles_with_translations,
            "total_translations": total_translations,
            "unique_categories": len(categories),
            "top_categories": sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "languages": languages,
            "workflow_states": workflow_states,
        }

        return summary

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """
        Print summary statistics to console.

        Args:
            summary: Summary dictionary from export_summary()
        """
        print("\n" + "=" * 80)
        print("ARTICLE LIST EXPORT SUMMARY")
        print("=" * 80)
        print(f"\n📊 Statistics:")
        print(f"   Total articles: {summary['total_articles']}")
        print(f"   Articles with translations: {summary['articles_with_translations']}")
        print(f"   Total translations: {summary['total_translations']}")
        print(f"   Unique categories: {summary['unique_categories']}")

        print(f"\n🌍 Languages:")
        for lang, count in sorted(summary["languages"].items()):
            print(f"   {lang}: {count} articles")

        print(f"\n📋 Workflow States:")
        for state, count in sorted(summary["workflow_states"].items()):
            print(f"   {state}: {count} articles")

        if summary["top_categories"]:
            print(f"\n📁 Top 10 Categories:")
            for cat_path, count in summary["top_categories"]:
                print(f"   {count:3d} - {cat_path}")

        print("\n" + "=" * 80)
