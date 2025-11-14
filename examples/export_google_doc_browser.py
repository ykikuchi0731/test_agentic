"""Example: Export Google Documents to DOCX format using browser automation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Export Google Documents to DOCX format using browser automation.

    Prerequisites:
        1. Chrome, Firefox, or Edge browser installed
        2. Google account with access to documents

    This script will:
        1. Start browser (Chrome by default)
        2. Prompt you to log in to Google account
        3. Export documents to DOCX format
        4. Save to output directory
    """

    print("=" * 80)
    print("Google Docs to DOCX Export (Browser Automation)")
    print("=" * 80)

    # Configuration
    print("\nConfiguration:")
    print("-" * 80)
    print(f"Output directory: {Config.BROWSER_DOWNLOAD_DIR}")
    print(f"Browser: {Config.BROWSER_TYPE}")
    print(f"Headless mode: {Config.BROWSER_HEADLESS}")
    print(f"Timeout: {Config.BROWSER_TIMEOUT}s")

    # Get export mode
    print("\n" + "=" * 80)
    print("Export Mode:")
    print("=" * 80)
    print("1. Single document")
    print("2. Multiple documents")
    mode = input("\nSelect mode (1 or 2): ").strip()

    if mode not in ["1", "2"]:
        print("Invalid mode. Exiting.")
        return

    # Initialize exporter
    exporter = GoogleDocsBrowserExporter(
        download_dir=Config.BROWSER_DOWNLOAD_DIR,
        browser_type=Config.BROWSER_TYPE,
        headless=Config.BROWSER_HEADLESS,
        timeout=Config.BROWSER_TIMEOUT,
    )

    try:
        # Start browser
        print("\n" + "=" * 80)
        print("Starting browser...")
        print("=" * 80)

        if not exporter.start_browser():
            print("❌ Failed to start browser")
            return

        print("✅ Browser started")

        # Manual login
        print("\n" + "=" * 80)
        print("Login to Google Account")
        print("=" * 80)

        if not exporter.manual_login_wait():
            print("⚠️  Login verification failed, but will continue...")
            print("If exports fail, please ensure you're logged in")

        # Single document mode
        if mode == "1":
            print("\n" + "=" * 80)
            print("Single Document Export")
            print("=" * 80)

            doc_input = input("\nEnter Google Doc URL or file ID: ").strip()
            if not doc_input:
                print("No input provided. Exiting.")
                return

            custom_filename = input(
                "Custom filename (optional, press Enter to use document title): "
            ).strip()
            if not custom_filename:
                custom_filename = None

            print("\n" + "=" * 80)
            print("Exporting document...")
            print("=" * 80)

            result = exporter.export_single_document(doc_input, custom_filename)

            print("\n" + "=" * 80)
            print("Export Result")
            print("=" * 80)

            if result["success"]:
                print(f"✅ Export successful!")
                print(f"\nDocument title: {result['title']}")
                print(f"Saved to: {result['file_path']}")
            else:
                print(f"❌ Export failed!")
                print(f"\nError: {result['error']}")
                print_troubleshooting()

        # Multiple documents mode
        else:
            print("\n" + "=" * 80)
            print("Multiple Documents Export")
            print("=" * 80)
            print("\nEnter Google Doc URLs or file IDs (one per line)")
            print("Press Enter twice when done:")
            print("-" * 80)

            urls = []
            while True:
                line = input().strip()
                if not line:
                    if urls:
                        break
                    else:
                        print("No URLs provided. Exiting.")
                        return
                urls.append(line)

            print(f"\n📋 Found {len(urls)} documents to export")
            response = input("Proceed with export? (yes/no): ")
            if response.lower() != "yes":
                print("Export cancelled.")
                return

            print("\n" + "=" * 80)
            print(f"Exporting {len(urls)} documents...")
            print("=" * 80)

            results = exporter.export_multiple_documents(urls)

            print("\n" + "=" * 80)
            print("Export Results")
            print("=" * 80)

            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful

            print(f"\n📊 Summary:")
            print(f"  Total: {len(results)}")
            print(f"  ✅ Successful: {successful}")
            print(f"  ❌ Failed: {failed}")

            print(f"\n📄 Details:")
            for i, result in enumerate(results, 1):
                if result["success"]:
                    print(f"  {i}. ✅ {result['title']}")
                    print(f"     → {result['file_path']}")
                else:
                    print(f"  {i}. ❌ Error: {result['error']}")

            if failed > 0:
                print()
                print_troubleshooting()

        print("\n" + "=" * 80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Export interrupted by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")

    finally:
        # Stop browser
        print("\nStopping browser...")
        exporter.stop_browser()
        print("✅ Browser stopped")


def print_troubleshooting():
    """Print troubleshooting tips."""
    print("\n💡 Troubleshooting:")
    print("  - Verify you're logged in to Google account")
    print("  - Check that you have access to the document")
    print("  - Ensure the URL/ID is correct")
    print("  - Try opening the document manually in browser first")
    print("  - Check browser console for errors (F12)")


def test_single_export():
    """
    Test function for quick single document export.

    Uncomment and modify the file_id to use this function.
    """
    exporter = GoogleDocsBrowserExporter(
        download_dir=Config.BROWSER_DOWNLOAD_DIR,
        browser_type=Config.BROWSER_TYPE,
        headless=Config.BROWSER_HEADLESS,
        timeout=Config.BROWSER_TIMEOUT,
    )

    try:
        # Start browser
        print("Starting browser...")
        exporter.start_browser()

        # Manual login
        print("Please log in to Google account...")
        exporter.manual_login_wait()

        # Export document
        file_id = "YOUR_DOCUMENT_ID_HERE"
        result = exporter.export_single_document(file_id)

        if result["success"]:
            print(f"✅ Export successful: {result['file_path']}")
        else:
            print(f"❌ Export failed: {result['error']}")

    finally:
        exporter.stop_browser()


def test_batch_export():
    """
    Test function for batch export with context manager.
    """
    urls = [
        "https://docs.google.com/document/d/DOC_ID_1/edit",
        "https://docs.google.com/document/d/DOC_ID_2/edit",
        "https://docs.google.com/document/d/DOC_ID_3/edit",
    ]

    # Using context manager (automatically starts/stops browser)
    with GoogleDocsBrowserExporter(
        download_dir=Config.BROWSER_DOWNLOAD_DIR,
        browser_type=Config.BROWSER_TYPE,
        headless=Config.BROWSER_HEADLESS,
        timeout=Config.BROWSER_TIMEOUT,
    ) as exporter:
        # Manual login
        print("Please log in to Google account...")
        exporter.manual_login_wait()

        # Export documents
        results = exporter.export_multiple_documents(urls)

        # Print results
        for result in results:
            if result["success"]:
                print(f"✅ {result['title']}: {result['file_path']}")
            else:
                print(f"❌ {result['error']}")


if __name__ == "__main__":
    # Uncomment to use test functions instead:
    # test_single_export()
    # test_batch_export()

    main()
