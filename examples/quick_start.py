"""Quick Start Example - Minimal configuration for first-time users.

This script demonstrates the simplest way to export a few articles
from ServiceNow for testing the migration tool.

Usage:
    python examples/quick_start.py

This is equivalent to:
    python cli.py migrate --limit 5 --dry-run
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from config import Config, ConfigurationError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Quick start migration example."""
    print("=" * 80)
    print("ServiceNow to Notion Migration - Quick Start")
    print("=" * 80)
    print()
    print("This example will:")
    print("  1. Connect to ServiceNow")
    print("  2. Fetch 5 articles (for testing)")
    print("  3. Export them as ZIP for Notion import")
    print()

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        print("\n❌ Configuration Error")
        print(str(e))
        print("\nPlease set up your .env file first:")
        print("  1. Copy env.example to .env")
        print("  2. Add your ServiceNow credentials")
        print("  3. Run this script again")
        return 1

    # Ask for confirmation
    print("=" * 80)
    response = input("Continue with quick start? [y/N]: ").strip().lower()

    if response not in ('y', 'yes'):
        print("Cancelled.")
        return 0

    print()
    print("Starting migration...")
    print("(This will export only 5 articles for testing)")
    print()

    # Run migration with limit
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.migrator import MigrationOrchestrator

    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Get articles (limited to 5)
        logger.info("Fetching articles...")
        all_articles = kb.get_latest_articles_only()
        articles = all_articles[:5]  # Limit to 5 articles

        logger.info(f"Processing {len(articles)} articles")

        # Initialize migrator (without iframe processing for speed)
        migrator = MigrationOrchestrator(
            kb=kb,
            output_dir=Config.MIGRATION_OUTPUT_DIR,
            iframe_processor=None  # Disable iframe processing for quick start
        )

        # Run migration
        result = migrator.export_for_notion_import(
            articles=articles,
            create_zip=True
        )

        if result:
            print()
            print("=" * 80)
            print("✅ Quick Start Migration Completed!")
            print("=" * 80)
            print(f"\nExport path: {result.get('export_path', 'N/A')}")
            if 'zip_path' in result:
                print(f"ZIP file: {result['zip_path']}")
            print()
            print("Next steps:")
            print("  1. Review the exported files")
            print("  2. Import the ZIP file to Notion")
            print("  3. Run full migration with: python cli.py migrate")
            print()
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1


if __name__ == '__main__':
    sys.exit(main())
