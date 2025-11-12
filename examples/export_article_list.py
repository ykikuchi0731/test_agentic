"""Example: Export article list with metadata (no file downloads)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing.article_list_exporter import ArticleListExporter
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Export article list with metadata for migration planning.

    This script:
    1. Fetches article metadata (no HTML/attachment downloads)
    2. Includes translations information
    3. Includes category hierarchy
    4. Exports to CSV and JSON formats
    5. Shows summary statistics
    """

    print("=" * 80)
    print("ServiceNow Article List Export (Metadata Only)")
    print("=" * 80)

    # Validate ServiceNow configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"ServiceNow configuration error: {e}")
        return

    # Initialize ServiceNow client
    logger.info(f"Connecting to ServiceNow: {Config.SERVICENOW_INSTANCE}")

    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        # Initialize knowledge base handler
        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Initialize article list exporter
        exporter = ArticleListExporter(
            servicenow_kb=kb, output_dir=Config.MIGRATION_OUTPUT_DIR
        )

        # Display export options
        print("\n" + "=" * 80)
        print("Export Options:")
        print("=" * 80)
        print(f"Output directory: {Config.MIGRATION_OUTPUT_DIR}")
        print(f"Base query: workflow_state=published (latest versions only)")
        print(f"Includes: Translations, Categories, Metadata")
        print(f"Downloads: NONE (metadata only)")
        print()

        # Ask for filtering options
        print("Filter Options (press Enter to skip):")
        print("-" * 80)

        limit_input = input("Limit (e.g., 50 for first 50 articles): ").strip()
        limit = int(limit_input) if limit_input else None

        category_filter = input("Category filter (e.g., 'Tokyo Office', 'IT'): ").strip()
        if not category_filter:
            category_filter = None

        updated_after = input("Updated after date (YYYY-MM-DD, e.g., 2024-01-01): ").strip()
        if not updated_after:
            updated_after = None

        updated_before = input("Updated before date (YYYY-MM-DD, e.g., 2024-12-31): ").strip()
        if not updated_before:
            updated_before = None

        # Display selected filters
        print("\n" + "=" * 80)
        print("Selected Filters:")
        print("=" * 80)
        if limit:
            print(f"  Limit: {limit} articles")
        else:
            print(f"  Limit: None (all articles)")
        if category_filter:
            print(f"  Category filter: '{category_filter}'")
        if updated_after:
            print(f"  Updated after: {updated_after}")
        if updated_before:
            print(f"  Updated before: {updated_before}")
        print()

        # Get user confirmation
        response = input("Proceed with article list export? (yes/no): ")
        if response.lower() != "yes":
            print("Export cancelled.")
            return

        logger.info("\n" + "=" * 80)
        logger.info("Starting metadata collection...")
        logger.info("=" * 80)

        # Collect article metadata (no downloads) with filters
        article_metadata = exporter.collect_article_metadata(
            query="workflow_state=published",
            limit=limit,
            category_filter=category_filter,
            updated_after=updated_after,
            updated_before=updated_before,
        )

        if not article_metadata:
            print("\n⚠️  No articles found!")
            return

        # Generate summary
        summary = exporter.export_summary(article_metadata)

        # Display summary
        exporter.print_summary(summary)

        # Export to files
        print("\n" + "=" * 80)
        print("Exporting to files...")
        print("=" * 80)

        csv_path = exporter.export_to_csv(article_metadata, "article_list.csv")
        json_path = exporter.export_to_json(article_metadata, "article_list.json")

        print(f"\n✅ Export complete!")
        print(f"\n📄 Files created:")
        print(f"   CSV:  {csv_path}")
        print(f"   JSON: {json_path}")

        print(f"\n📋 CSV Format:")
        print(f"   - One row per article (+ one row per translation)")
        print(f"   - Easy to open in Excel/Google Sheets")
        print(f"   - Good for filtering and sorting")

        print(f"\n📋 JSON Format:")
        print(f"   - Hierarchical structure")
        print(f"   - Includes all metadata")
        print(f"   - Good for programmatic access")

        print(f"\n💡 Next steps:")
        print(f"   1. Review the exported list")
        print(f"   2. Plan your Notion database structure")
        print(f"   3. Run migration_example.py to export HTML + attachments")
        print(f"   4. Import ZIP to Notion")
        print(f"   5. Run post_import_example.py to organize")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
