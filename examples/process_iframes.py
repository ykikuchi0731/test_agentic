"""Example: Process Google Docs and Slides iframes in ServiceNow articles."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from config import Config
from pre_processing import (
    ServiceNowClient,
    KnowledgeBase,
    IframeProcessor,
    GoogleDocsBrowserExporter,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Process iframes in ServiceNow knowledge articles.

    This script demonstrates:
    1. Detecting Google Docs and Slides iframes in articles
    2. Downloading Google Docs as DOCX
    3. Converting Google Slides iframes to anchor links
    4. Generating a report of iframe processing
    """

    print("=" * 80)
    print("ServiceNow Article Iframe Processor")
    print("=" * 80)

    # Get mode
    print("\nMode:")
    print("1. Analyze iframes (report only, no downloads)")
    print("2. Process iframes (download docs, convert slides)")
    mode = input("\nSelect mode (1 or 2): ").strip()

    if mode not in ["1", "2"]:
        print("Invalid mode. Exiting.")
        return

    analyze_only = mode == "1"

    # Initialize ServiceNow client
    print("\n" + "=" * 80)
    print("Connecting to ServiceNow...")
    print("=" * 80)

    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please check your .env file")
        return

    client = ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
    )

    kb = KnowledgeBase(client)
    print("✅ Connected to ServiceNow")

    # Get article selection
    print("\n" + "=" * 80)
    print("Article Selection:")
    print("=" * 80)
    print("1. Process all articles")
    print("2. Process specific article by number")

    selection = input("\nSelect option (1 or 2): ").strip()

    articles = []
    if selection == "1":
        # Get all articles
        print("\nFetching all articles...")
        articles = kb.get_latest_articles_only()
        print(f"Found {len(articles)} articles")

    elif selection == "2":
        # Get specific article
        article_number = input("\nEnter article number (e.g., KB0000001): ").strip()
        print(f"Fetching article {article_number}...")

        article = kb.get_article_by_number(article_number)
        if article:
            articles = [article]
            print(f"✅ Found article: {article.get('short_description', 'Untitled')}")
        else:
            print(f"❌ Article not found: {article_number}")
            return

    else:
        print("Invalid selection. Exiting.")
        return

    if not articles:
        print("No articles to process. Exiting.")
        return

    # Initialize iframe processor
    google_docs_exporter = None

    if not analyze_only:
        print("\n" + "=" * 80)
        print("Google Docs Export Setup")
        print("=" * 80)

        # Initialize browser exporter for Google Docs download
        google_docs_exporter = GoogleDocsBrowserExporter(
            download_dir=Config.BROWSER_DOWNLOAD_DIR,
            browser_type=Config.BROWSER_TYPE,
            headless=Config.BROWSER_HEADLESS,
            timeout=Config.BROWSER_TIMEOUT,
        )

        # Start browser and login
        if not google_docs_exporter.start_browser():
            print("❌ Failed to start browser")
            return

        print("✅ Browser started")

        # Manual login
        if not google_docs_exporter.manual_login_wait():
            print("⚠️  Login verification failed, but will continue...")

    iframe_processor = IframeProcessor(google_docs_exporter=google_docs_exporter)

    # Process articles
    print("\n" + "=" * 80)
    print(f"Processing {len(articles)} articles...")
    print("=" * 80)

    results = {
        "total_articles": len(articles),
        "articles_with_iframes": 0,
        "iframe_only_articles": 0,
        "total_iframes": 0,
        "google_docs_found": 0,
        "google_slides_found": 0,
        "google_docs_downloaded": 0,
        "google_slides_converted": 0,
        "errors": [],
    }

    article_reports = []

    for i, article in enumerate(articles, 1):
        article_number = article.get("number", "Unknown")
        article_title = article.get("short_description", "Untitled")

        print(f"\n[{i}/{len(articles)}] Processing: {article_number} - {article_title}")

        try:
            # Get article HTML
            html_content = article.get("text", "")

            if not html_content:
                print("  ⚠️  No HTML content")
                continue

            # Get iframe summary
            summary = iframe_processor.get_iframe_summary(html_content)

            if summary["total_iframes"] > 0:
                results["articles_with_iframes"] += 1
                results["total_iframes"] += summary["total_iframes"]
                results["google_docs_found"] += summary["google_docs_count"]
                results["google_slides_found"] += summary["google_slides_count"]

                if summary["is_iframe_only"]:
                    results["iframe_only_articles"] += 1

                print(f"  📊 Found {summary['total_iframes']} iframes:")
                print(f"     - Google Docs: {summary['google_docs_count']}")
                print(f"     - Google Slides: {summary['google_slides_count']}")
                print(f"     - Other: {summary['other_iframes_count']}")
                print(f"     - Iframe-only content: {summary['is_iframe_only']}")

                # Process iframes if not analyze-only mode
                if not analyze_only:
                    print("  🔄 Processing iframes...")

                    modified_html, process_summary = (
                        iframe_processor.process_html_iframes(
                            html_content=html_content,
                            article_title=article_title,
                            download_docs=True,
                            convert_slides=True,
                        )
                    )

                    results["google_docs_downloaded"] += len(
                        process_summary["docs_downloaded"]
                    )
                    results["google_slides_converted"] += len(
                        process_summary["slides_converted"]
                    )

                    if process_summary["docs_downloaded"]:
                        print(
                            f"  ✅ Downloaded {len(process_summary['docs_downloaded'])} Google Docs"
                        )

                    if process_summary["slides_converted"]:
                        print(
                            f"  ✅ Converted {len(process_summary['slides_converted'])} Google Slides"
                        )

                    if process_summary["errors"]:
                        for error in process_summary["errors"]:
                            print(f"  ❌ {error}")
                            results["errors"].append(f"{article_number}: {error}")

                # Store report
                article_reports.append(
                    {
                        "number": article_number,
                        "title": article_title,
                        "summary": summary,
                    }
                )

            else:
                print("  ℹ️  No iframes found")

        except Exception as e:
            logger.error(f"Error processing article {article_number}: {e}")
            print(f"  ❌ Error: {e}")
            results["errors"].append(f"{article_number}: {e}")

    # Stop browser if started
    if google_docs_exporter:
        print("\nStopping browser...")
        google_docs_exporter.stop_browser()

    # Print summary
    print("\n" + "=" * 80)
    print("Processing Summary")
    print("=" * 80)

    print(f"\n📊 Overall Statistics:")
    print(f"  Total articles processed: {results['total_articles']}")
    print(f"  Articles with iframes: {results['articles_with_iframes']}")
    print(f"  Iframe-only articles: {results['iframe_only_articles']}")
    print(f"  Total iframes found: {results['total_iframes']}")
    print(f"    - Google Docs: {results['google_docs_found']}")
    print(f"    - Google Slides: {results['google_slides_found']}")

    if not analyze_only:
        print(f"\n✅ Processing Results:")
        print(f"  Google Docs downloaded: {results['google_docs_downloaded']}")
        print(f"  Google Slides converted: {results['google_slides_converted']}")

    if results["errors"]:
        print(f"\n❌ Errors: {len(results['errors'])}")
        for error in results["errors"][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")

    # Print detailed report
    if article_reports:
        print("\n" + "=" * 80)
        print("Detailed Report")
        print("=" * 80)

        for report in article_reports:
            print(f"\n📄 {report['number']}: {report['title']}")
            summary = report["summary"]

            if summary["google_docs_urls"]:
                print("  Google Docs:")
                for url in summary["google_docs_urls"]:
                    print(f"    - {url}")

            if summary["google_slides_urls"]:
                print("  Google Slides:")
                for url in summary["google_slides_urls"]:
                    print(f"    - {url}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
