"""Run pre-processing module: python -m pre_processing

This allows running the migration directly as a module without needing
to use the examples directory.

Usage:
    python -m pre_processing [options]

This is equivalent to running:
    python cli.py migrate [options]
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_utils import CommonCLI, create_base_parser
from config import Config, ConfigurationError
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from pre_processing.migrator import MigrationOrchestrator
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

import logging

logger = logging.getLogger(__name__)


def main():
    """Run pre-processing (migration) from command line."""
    parser = create_base_parser(
        description="ServiceNow to Notion Migration - Pre-processing\n\n"
                    "Export ServiceNow knowledge base articles as ZIP for Notion import."
    )

    # Add common CLI arguments
    CommonCLI.add_common_args(parser)

    # Add module-specific arguments
    parser.add_argument(
        '--process-iframes',
        action='store_true',
        help='Enable iframe processing (download Google Docs, Slides, etc.)'
    )
    parser.add_argument(
        '--no-zip',
        action='store_true',
        help='Do not create ZIP file (keep extracted files only)'
    )

    args = parser.parse_args()

    # Setup logging
    CommonCLI.setup_logging(verbose=args.verbose, quiet=args.quiet)

    print("=" * 80)
    print("ServiceNow to Notion Migration - Pre-processing")
    print("=" * 80)

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

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

        # Get all articles (latest versions only)
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()
        logger.info(f"Found {len(articles)} articles")

        # Apply filters
        filters = CommonCLI.parse_filters(args.filter)
        if filters or args.kb_base:
            articles = CommonCLI.filter_articles(articles, filters, args.kb_base)
            logger.info(f"Filtered to {len(articles)} articles")

        # Apply limit and offset
        articles = CommonCLI.apply_limit_offset(articles, args.limit, args.offset)
        logger.info(f"Processing {len(articles)} articles (offset: {args.offset})")

        if args.dry_run:
            print("\n[DRY RUN] Would process the following articles:")
            CommonCLI.print_summary(
                "Articles to Process",
                articles,
                ['number', 'short_description', 'kb_category'],
                max_items=20
            )
            return 0

        # Initialize iframe processor if requested
        iframe_processor = None
        if args.process_iframes:
            logger.info("Iframe processing enabled")
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
            create_zip=not args.no_zip
        )

        if result:
            print("\n" + "=" * 80)
            print("✅ Migration completed successfully!")
            print("=" * 80)
            if 'export_path' in result:
                print(f"Export path: {result['export_path']}")
            if 'zip_path' in result:
                print(f"ZIP file: {result['zip_path']}")
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1


if __name__ == '__main__':
    sys.exit(main())
