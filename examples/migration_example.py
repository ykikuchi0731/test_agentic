"""Example: Export ServiceNow articles to ZIP for Notion import."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing.migrator import MigrationOrchestrator
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

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

        # Ask if iframe processing should be enabled
        print("\n" + "=" * 80)
        print("Iframe Processing Setup:")
        print("=" * 80)
        print("Do you want to enable iframe processing?")
        print("This will:")
        print("  - Detect Google Docs and Slides iframes in articles")
        print("  - Download Google Docs as DOCX files")
        print("  - Convert Google Slides iframes to anchor links")
        print("  - Handle translations separately when iframes are present")
        print()

        enable_iframes = input("Enable iframe processing? (yes/no): ").strip().lower()

        google_docs_exporter = None
        if enable_iframes == "yes":
            print("\n" + "=" * 80)
            print("Google Docs Browser Setup")
            print("=" * 80)
            print("Starting browser for Google Docs export...")
            print()

            # Initialize browser exporter
            google_docs_exporter = GoogleDocsBrowserExporter(
                download_dir=Config.BROWSER_DOWNLOAD_DIR,
                browser_type=Config.BROWSER_TYPE,
                headless=Config.BROWSER_HEADLESS,
                timeout=Config.BROWSER_TIMEOUT,
            )

            # Start browser
            if not google_docs_exporter.start_browser():
                print("❌ Failed to start browser")
                print("Continuing without iframe processing...")
                google_docs_exporter = None
            else:
                print("✅ Browser started")
                print()
                print("Please log in to your Google account in the browser window.")
                print("After logging in, press Enter to continue...")

                # Wait for manual login
                if not google_docs_exporter.manual_login_wait():
                    print("⚠️  Login verification failed")
                    print("Continuing anyway - iframe processing may fail if not logged in...")
                else:
                    print("✅ Google login verified")

        # Initialize migrator with iframe processing
        migrator = MigrationOrchestrator(
            servicenow_kb=kb,
            output_dir=Config.MIGRATION_OUTPUT_DIR,
            google_docs_exporter=google_docs_exporter,
            process_iframes=(google_docs_exporter is not None),
        )

        # Display export options
        print("\n" + "=" * 80)
        print("Export Options:")
        print("=" * 80)
        print(f"Output directory: {Config.MIGRATION_OUTPUT_DIR}")
        print(f"Query: workflow_state=published (latest versions only)")
        print(f"Features: Version filtering + Translation merging")
        print(f"Iframe processing: {'Enabled' if google_docs_exporter else 'Disabled'}")
        print()

        # Get user confirmation
        response = input("Proceed with ZIP export? (yes/no): ")
        if response.lower() != "yes":
            print("Export cancelled.")
            if google_docs_exporter:
                google_docs_exporter.stop_browser()
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
            print(f"\n📦 ZIP file: {results['zip_path']}")

        if results.get("csv_path"):
            print(f"📊 CSV report: {results['csv_path']}")

        if results["zip_path"]:
            print()
            print("✅ Export complete!")
            print()
            print("Next steps:")
            print("1. Review the CSV report for export summary")
            print("2. Open Notion and navigate to the page where you want to import")
            print("3. Click '...' menu → Import")
            print("4. Select 'HTML' as import format")
            print(f"5. Upload the ZIP file: {results['zip_path']}")
            print("6. Notion will automatically create pages from the HTML files")

        if results["errors"]:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results["errors"][:10]:  # Show first 10
                print(f"  - {error}")
            if len(results["errors"]) > 10:
                print(f"  ... and {len(results['errors']) - 10} more errors")

        # Stop browser if it was started
        if google_docs_exporter:
            print("\nStopping browser...")
            google_docs_exporter.stop_browser()
            print("✅ Browser stopped")

        print("\n" + "=" * 80)
        print("Export complete!")
        print("=" * 80)

        # Display summary
        summary = migrator.get_export_summary()
        print(f"\nOutput directory: {summary['output_directory']}")
        print(f"ZIP directory: {summary['zip_directory']}")


if __name__ == "__main__":
    main()
