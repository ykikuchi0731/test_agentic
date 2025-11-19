"""Full Migration Example - Complete migration with all features enabled.

This script demonstrates a complete migration workflow including:
  - Fetching all articles from ServiceNow
  - Processing embedded content (iframes, Google Docs)
  - Generating category hierarchy
  - Creating ZIP export for Notion import

Usage:
    python examples/full_migration.py

This is equivalent to:
    python cli.py migrate --process-iframes

For production use, we recommend using the CLI tool directly with filters:
    python cli.py migrate --filter "category:IT" --limit 100
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from config import Config, ConfigurationError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Full migration with all features enabled."""
    print("=" * 80)
    print("ServiceNow to Notion Migration - Full Migration")
    print("=" * 80)
    print()
    print("This will perform a complete migration:")
    print("  ✓ Fetch all articles from ServiceNow")
    print("  ✓ Download attachments")
    print("  ✓ Process embedded content (iframes, Google Docs)")
    print("  ✓ Generate category hierarchy")
    print("  ✓ Create ZIP file for Notion import")
    print()
    print("⚠️  This may take a while depending on the number of articles!")
    print()

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        print("\n❌ Configuration Error")
        print(str(e))
        return 1

    # Check if iframe processing should be enabled
    print("=" * 80)
    print("Iframe Processing (Optional)")
    print("=" * 80)
    print()
    print("Iframe processing will:")
    print("  - Download embedded Google Docs as DOCX files")
    print("  - Convert Google Slides to images")
    print("  - Process other embedded content")
    print()
    print("⚠️  This requires browser automation and may take additional time")
    print()

    enable_iframes = input("Enable iframe processing? [y/N]: ").strip().lower()
    process_iframes = enable_iframes in ('y', 'yes')

    print()
    print("=" * 80)
    response = input("Start full migration? [y/N]: ").strip().lower()

    if response not in ('y', 'yes'):
        print("Cancelled.")
        return 0

    print()
    print("Starting full migration...")
    print()

    # Run full migration
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.migrator import MigrationOrchestrator
    from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Get all articles (latest versions only)
        logger.info("Fetching all articles from ServiceNow...")
        articles = kb.get_latest_articles_only()
        logger.info(f"Found {len(articles)} articles")

        # Initialize iframe processor if enabled
        iframe_processor = None
        if process_iframes:
            logger.info("Initializing iframe processor...")
            iframe_processor = GoogleDocsBrowserExporter()

        # Initialize migrator
        migrator = MigrationOrchestrator(
            kb=kb,
            output_dir=Config.MIGRATION_OUTPUT_DIR,
            iframe_processor=iframe_processor
        )

        # Run migration
        result = migrator.export_for_notion_import(
            articles=articles,
            create_zip=True
        )

        if result:
            print()
            print("=" * 80)
            print("✅ Full Migration Completed Successfully!")
            print("=" * 80)
            print()
            print(f"Articles processed: {len(articles)}")
            if 'export_path' in result:
                print(f"Export directory: {result['export_path']}")
            if 'zip_path' in result:
                print(f"ZIP file: {result['zip_path']}")
            print()
            print("Next steps:")
            print("  1. Review the generated ZIP file")
            print("  2. Import to Notion:")
            print("     - Open Notion → Settings → Import")
            print("     - Select 'HTML' as import type")
            print("     - Upload the ZIP file")
            print("  3. After import, use post-processing tools:")
            print("     - python cli.py make-subitem (organize pages)")
            print()
            return 0
        else:
            print()
            print("=" * 80)
            print("❌ Migration Failed")
            print("=" * 80)
            print()
            print("Please check the logs for errors")
            return 1


if __name__ == '__main__':
    sys.exit(main())
