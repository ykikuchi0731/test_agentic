"""CSV export report generation for migration exports."""
import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ExportReporter:
    """Generate CSV reports for exported articles."""

    @staticmethod
    def create_csv_report(
        articles_data: List[Dict[str, Any]], zip_path: str, output_dir: Path
    ) -> str:
        """
        Create CSV report of exported articles.

        Args:
            articles_data: List of article data dictionaries
            zip_path: Path to the created ZIP file
            output_dir: Directory to save CSV report

        Returns:
            Path to created CSV file
        """
        csv_filename = Path(zip_path).stem + "_report.csv"
        csv_path = output_dir / csv_filename

        fieldnames = ExportReporter._get_csv_fieldnames()

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for article_data in articles_data:
                row = ExportReporter._create_csv_row(article_data)
                writer.writerow(row)

        logger.info(f"CSV report saved to: {csv_path}")
        return str(csv_path)

    @staticmethod
    def _get_csv_fieldnames() -> List[str]:
        """Get CSV column names."""
        return [
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

    @staticmethod
    def _create_csv_row(article_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a CSV row from article data."""
        article = article_data["article"]
        translations = article_data.get("translations", [])
        attachments = article_data.get("attachments", [])
        iframe_result = article_data.get("iframe_result")
        category_path = article_data.get("category_path", [])

        # Count Google Docs downloaded
        google_docs_count, google_slides_count = ExportReporter._count_google_docs(
            iframe_result
        )

        # Extract category labels
        category_labels = ExportReporter._extract_category_labels(category_path)

        # Create combined article number and title if there are translations
        combined_number, combined_title, combined_lang = (
            ExportReporter._create_combined_fields(article, translations)
        )

        return {
            "article_number": combined_number,
            "article_title": combined_title,
            "sys_id": article.get("sys_id", ""),
            "workflow_state": article.get("workflow_state", ""),
            "language": combined_lang,
            "has_translations": "Yes" if translations else "No",
            "translation_count": len(translations),
            "category_path": " > ".join(category_labels) if category_labels else "",
            "attachments_count": len(attachments),
            "has_iframes": "Yes" if (iframe_result and iframe_result.get("has_iframes")) else "No",
            "google_docs_downloaded": google_docs_count,
            "google_slides_converted": google_slides_count,
            "requires_special_handling": "Yes"
            if article_data.get("requires_special_handling")
            else "No",
            "special_handling_flag": article_data.get("special_handling_flag", ""),
            "created_on": article.get("sys_created_on", ""),
            "updated_on": article.get("sys_updated_on", ""),
            "author": ExportReporter._extract_author(article),
        }

    @staticmethod
    def _count_google_docs(iframe_result: Dict[str, Any]) -> tuple:
        """Count Google Docs and Slides downloaded."""
        if not iframe_result or not iframe_result.get("has_iframes"):
            return 0, 0

        docs_count = 0
        slides_count = 0

        # Count from original
        if original_summary := iframe_result["original"].get("summary"):
            docs_count += len(original_summary.get("docs_downloaded", []))
            slides_count += len(original_summary.get("slides_converted", []))

        # Count from translations
        for trans in iframe_result.get("translations", []):
            if trans_summary := trans.get("summary"):
                docs_count += len(trans_summary.get("docs_downloaded", []))
                slides_count += len(trans_summary.get("slides_converted", []))

        return docs_count, slides_count

    @staticmethod
    def _extract_category_labels(category_path: List) -> List[str]:
        """Extract category labels from category path."""
        labels = []
        for cat in category_path:
            if isinstance(cat, dict):
                labels.append(cat.get("label", ""))
            else:
                labels.append(str(cat))
        return labels

    @staticmethod
    def _create_combined_fields(
        article: Dict[str, Any], translations: List[Dict[str, Any]]
    ) -> tuple:
        """Create combined article number, title, and language fields."""
        if not translations:
            return (
                article.get("number", ""),
                article.get("short_description", ""),
                ExportReporter._extract_language(article),
            )

        # Combine original and translations
        articles_by_lang = [
            (
                ExportReporter._extract_language(article),
                article.get("number", ""),
                article.get("short_description", ""),
            )
        ]

        for trans in translations:
            articles_by_lang.append(
                (
                    ExportReporter._extract_language(trans),
                    trans.get("number", ""),
                    trans.get("short_description", ""),
                )
            )

        # Sort by language (ja before en)
        articles_by_lang.sort(key=ExportReporter._lang_sort_key)

        combined_number = " / ".join([num for _, num, _ in articles_by_lang])
        combined_title = " / ".join([title for _, _, title in articles_by_lang])
        combined_lang = " / ".join([lang for lang, _, _ in articles_by_lang])

        return combined_number, combined_title, combined_lang

    @staticmethod
    def _extract_language(article: Dict[str, Any]) -> str:
        """Extract language from article."""
        lang = article.get("language", "")
        if isinstance(lang, dict):
            return lang.get("value", "")
        return str(lang)

    @staticmethod
    def _extract_author(article: Dict[str, Any]) -> str:
        """Extract author from article."""
        author = article.get("author", "")
        if isinstance(author, dict):
            return author.get("display_value", "")
        return str(author)

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
