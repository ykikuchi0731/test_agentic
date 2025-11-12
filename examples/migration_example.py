"""Example: Export ServiceNow articles to ZIP for Notion import."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing.migrator import MigrationOrchestrator
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Export ServiceNow articles to ZIP for Notion's built-in importer."""

    print("=" * 80)
    print("ServiceNow to Notion Migration - ZIP Export")
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

        # Initialize migrator
        migrator = MigrationOrchestrator(
            servicenow_kb=kb, output_dir=Config.MIGRATION_OUTPUT_DIR
        )

        # Display export options
        print("\n" + "=" * 80)
        print("Export Options:")
        print("=" * 80)
        print(f"Output directory: {Config.MIGRATION_OUTPUT_DIR}")
        print(f"Query: workflow_state=published (latest versions only)")
        print(f"Features: Version filtering + Translation merging")
        print()

        # Get user confirmation
        response = input("Proceed with ZIP export? (yes/no): ")
        if response.lower() != "yes":
            print("Export cancelled.")
            return

        logger.info("\n" + "=" * 80)
        logger.info("Starting export...")
        logger.info("=" * 80)

        # Execute export
        results = migrator.export_all_to_zip(
            query="workflow_state=published",  # Only published articles
        )

        # Display results
        print("\n" + "=" * 80)
        print("Export Results")
        print("=" * 80)
        print(f"Total articles: {results['total_articles']}")
        print(f"ZIP created: {results['zip_created']}")
        if results["zip_path"]:
            print(f"ZIP file: {results['zip_path']}")
            print()
            print("✅ Export complete!")
            print()
            print("Next steps:")
            print("1. Open Notion and navigate to the page where you want to import")
            print("2. Click '...' menu → Import")
            print("3. Select 'HTML' as import format")
            print(f"4. Upload the ZIP file: {results['zip_path']}")
            print("5. Notion will automatically create pages from the HTML files")

        if results["errors"]:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results["errors"][:10]:  # Show first 10
                print(f"  - {error}")

        print("\n" + "=" * 80)
        print("Export complete!")
        print("=" * 80)

        # Display summary
        summary = migrator.get_export_summary()
        print(f"\nOutput directory: {summary['output_directory']}")
        print(f"ZIP directory: {summary['zip_directory']}")


if __name__ == "__main__":
    main()
