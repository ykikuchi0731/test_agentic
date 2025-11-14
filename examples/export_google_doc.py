"""Example: Export a single Google Document to DOCX format."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing.google_docs_exporter import GoogleDocsExporter

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Export a single Google Document to DOCX format.

    Prerequisites:
        1. Google Cloud Project with Drive API and Docs API enabled
        2. OAuth2 credentials downloaded as JSON file
        3. Credentials file path set in .env (GOOGLE_CREDENTIALS_FILE)

    This script will:
        1. Prompt for Google Doc URL or file ID
        2. Authenticate with Google (opens browser on first run)
        3. Export document to DOCX format
        4. Save to output directory
    """

    print("=" * 80)
    print("Google Docs to DOCX Export")
    print("=" * 80)

    # Initialize exporter
    exporter = GoogleDocsExporter(
        credentials_file=Config.GOOGLE_CREDENTIALS_FILE,
        token_file=Config.GOOGLE_TOKEN_FILE,
        scopes=Config.GOOGLE_SCOPES,
        output_dir=Config.GOOGLE_DOCS_OUTPUT_DIR,
    )

    # Check authentication status
    auth_status = exporter.get_authentication_status()
    print("\nAuthentication Status:")
    print("-" * 80)
    print(f"Credentials file exists: {auth_status['credentials_file_exists']}")
    print(f"  Path: {Config.GOOGLE_CREDENTIALS_FILE}")
    print(f"Token file exists: {auth_status['token_file_exists']}")
    print(f"  Path: {Config.GOOGLE_TOKEN_FILE}")
    print(f"Authenticated: {auth_status['authenticated']}")

    if not auth_status["credentials_file_exists"]:
        print("\n⚠️  Credentials file not found!")
        print("\nSetup instructions:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a project (or select existing)")
        print("3. Enable Google Drive API and Google Docs API")
        print("4. Create OAuth2 credentials (Desktop app)")
        print("5. Download credentials JSON file")
        print(f"6. Save as: {Config.GOOGLE_CREDENTIALS_FILE}")
        print("\nFor detailed instructions, see: docs/google_docs_setup.md")
        return

    # Get Google Doc URL or file ID
    print("\n" + "=" * 80)
    print("Export Settings:")
    print("=" * 80)
    print(f"Output directory: {Config.GOOGLE_DOCS_OUTPUT_DIR}")
    print()

    doc_input = input("Enter Google Doc URL or file ID: ").strip()
    if not doc_input:
        print("No input provided. Exiting.")
        return

    # Optional: custom filename
    custom_filename = input(
        "Custom filename (optional, press Enter to use document title): "
    ).strip()
    if not custom_filename:
        custom_filename = None

    # Display settings
    print("\n" + "=" * 80)
    print("Export Configuration:")
    print("=" * 80)
    print(f"Document: {doc_input}")
    if custom_filename:
        print(f"Output filename: {custom_filename}")
    else:
        print("Output filename: [Document title].docx")
    print()

    # Get user confirmation
    response = input("Proceed with export? (yes/no): ")
    if response.lower() != "yes":
        print("Export cancelled.")
        return

    print("\n" + "=" * 80)
    print("Starting export...")
    print("=" * 80)

    # Authenticate (will open browser on first run)
    if not auth_status["authenticated"]:
        print("\n⚠️  First-time authentication required")
        print("A browser window will open for you to grant permissions")
        print("Please sign in and authorize the application")
        print()

    # Export document
    result = exporter.export_single_document(doc_input, custom_filename)

    # Display results
    print("\n" + "=" * 80)
    print("Export Results")
    print("=" * 80)

    if result["success"]:
        print(f"✅ Export successful!")
        print(f"\nDocument title: {result['title']}")
        print(f"Saved to: {result['file_path']}")
        print(f"\n💡 The exported DOCX file is ready to use")
    else:
        print(f"❌ Export failed!")
        print(f"\nError: {result['error']}")
        print(f"\nTroubleshooting:")
        print(f"- Verify the document URL or file ID is correct")
        print(f"- Ensure you have permission to access the document")
        print(f"- Check that the document is a Google Doc (not Sheets or Slides)")
        print(f"- Review authentication status above")

    print("\n" + "=" * 80)


def test_export():
    """
    Test function for quick exports without interactive prompts.

    Uncomment and modify the file_id to use this function.
    """
    exporter = GoogleDocsExporter(
        credentials_file=Config.GOOGLE_CREDENTIALS_FILE,
        token_file=Config.GOOGLE_TOKEN_FILE,
        scopes=Config.GOOGLE_SCOPES,
        output_dir=Config.GOOGLE_DOCS_OUTPUT_DIR,
    )

    # Replace with your test document ID
    file_id = "YOUR_DOCUMENT_ID_HERE"

    result = exporter.export_single_document(file_id)

    if result["success"]:
        print(f"✅ Export successful: {result['file_path']}")
    else:
        print(f"❌ Export failed: {result['error']}")


if __name__ == "__main__":
    # Uncomment to use test function instead:
    # test_export()

    main()
