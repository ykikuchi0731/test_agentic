#!/usr/bin/env python3
"""Unified CLI tool for ServiceNow to Notion migration.

This CLI tool provides a unified interface to all migration functionality,
including pre-processing, post-processing, and utility commands.

Usage:
    python cli.py <command> [options]

Available commands:
    migrate            - Run full migration (export articles to ZIP)
    export-list        - Export article list with metadata (CSV/JSON)
    export-categories  - Export category hierarchy (JSON/CSV)
    process-iframes    - Process iframes in article HTML
    make-subitem       - Make Notion page a sub-item of another
    visualize          - Visualize category hierarchy

For help on a specific command:
    python cli.py <command> --help
"""
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cli_utils import CommonCLI, create_base_parser
from config import Config, ConfigurationError

logger = logging.getLogger(__name__)


def cmd_migrate(args):
    """Run full migration to export articles as ZIP for Notion import."""
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.migrator import MigrationOrchestrator
    from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

    print("=" * 80)
    print("ServiceNow to Notion Migration - Full Export")
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

        # Get all articles
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()

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
                ['number', 'short_description', 'kb_category']
            )
            return 0

        # Initialize iframe processor if requested
        iframe_processor = None
        if args.process_iframes:
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
            print("\n✅ Migration completed successfully!")
            if 'export_path' in result:
                print(f"Export path: {result['export_path']}")
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1


def cmd_export_list(args):
    """Export article list with metadata (no file downloads)."""
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.article_list_exporter import ArticleListExporter

    print("=" * 80)
    print("Export Article List (Metadata Only)")
    print("=" * 80)

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Initialize ServiceNow client
    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        # Initialize knowledge base handler
        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Get all articles
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()

        # Apply filters
        filters = CommonCLI.parse_filters(args.filter)
        if filters or args.kb_base:
            articles = CommonCLI.filter_articles(articles, filters, args.kb_base)
            logger.info(f"Filtered to {len(articles)} articles")

        # Apply limit and offset
        articles = CommonCLI.apply_limit_offset(articles, args.limit, args.offset)
        logger.info(f"Exporting {len(articles)} articles")

        if args.dry_run:
            print("\n[DRY RUN] Would export the following articles:")
            CommonCLI.print_summary(
                "Articles to Export",
                articles,
                ['number', 'short_description', 'kb_category']
            )
            return 0

        # Initialize exporter
        exporter = ArticleListExporter(
            kb=kb,
            output_dir=args.output or Config.MIGRATION_OUTPUT_DIR
        )

        # Export based on format
        if args.format == 'csv':
            output_path = exporter.export_to_csv(articles)
        else:
            output_path = exporter.export_to_json(articles)

        print(f"\n✅ Exported {len(articles)} articles to: {output_path}")
        return 0


def cmd_process_iframes(args):
    """Process iframes in article HTML."""
    from pre_processing.iframe_processor import IframeProcessor

    print("=" * 80)
    print("Process iframes in Article HTML")
    print("=" * 80)

    if not args.article_number:
        logger.error("--article-number is required")
        return 1

    # Initialize iframe processor
    processor = IframeProcessor()

    # This is a simplified version - full implementation would fetch article from ServiceNow
    logger.info(f"Processing iframes for article: {args.article_number}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would process iframes for article {args.article_number}")
        return 0

    print("Note: Full implementation requires article HTML content")
    print("Use 'migrate' command with --process-iframes flag for full iframe processing")
    return 0


def cmd_make_subitem(args):
    """Make a Notion page a sub-item of another page."""
    from post_processing.page_hierarchy import NotionPageHierarchy

    print("=" * 80)
    print("Make Notion Page a Sub-Item")
    print("=" * 80)

    # Validate configuration
    try:
        Config.validate_notion()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    if not args.child or not args.parent:
        logger.error("Both --child and --parent page IDs are required")
        return 1

    logger.info(f"Child page ID: {args.child}")
    logger.info(f"Parent page ID: {args.parent}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would make page {args.child} a sub-item of {args.parent}")
        return 0

    # Initialize hierarchy manager
    hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)

    # Make sub-item
    result = hierarchy.make_subitem(
        child_page_id=args.child,
        parent_page_id=args.parent,
        verify=not args.no_verify
    )

    if result['success']:
        print(f"\n✅ Successfully made '{result['child_title']}' a sub-item of '{result['parent_title']}'")
        print(f"Database: {result['database_id']}")
        print(f"Parent property ID: {result['parent_property_id']}")
        return 0
    else:
        print(f"\n❌ Error: {result['error']}")
        return 1


def cmd_export_categories(args):
    """Export category hierarchy to JSON or CSV."""
    import json
    import csv
    from pathlib import Path
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.category_hierarchy import CategoryHierarchyBuilder

    print("=" * 80)
    print("Export Category Hierarchy")
    print("=" * 80)

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Initialize ServiceNow client
    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        # Initialize knowledge base handler
        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Get all articles
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()
        logger.info(f"Found {len(articles)} articles")

        # Build hierarchy
        logger.info("Building category hierarchy...")
        builder = CategoryHierarchyBuilder()
        hierarchy = builder.build_hierarchy_from_articles(articles)
        logger.info(f"Found {len(hierarchy)} top-level categories")

        if args.dry_run:
            print("\n[DRY RUN] Would export category hierarchy:")
            print(f"  - Top-level categories: {len(hierarchy)}")
            print(f"  - Output format: {args.format}")
            print(f"  - Output path: {args.output or 'category_hierarchy.' + args.format}")
            return 0

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(f"category_hierarchy.{args.format}")

        # Export based on format
        if args.format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(hierarchy, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Exported hierarchy to JSON: {output_path}")

        elif args.format == 'csv':
            # Flatten hierarchy for CSV
            def flatten_hierarchy(nodes, rows=None):
                if rows is None:
                    rows = []

                for node in nodes:
                    rows.append({
                        'name': node['name'],
                        'full_path': node['full_path'],
                        'parent': node['parent'] or '(root)',
                        'ancestors': ' > '.join(node['ancestors']) if node['ancestors'] else '(none)',
                        'level': node['level'],
                        'article_count': node['article_count'],
                        'total_article_count': node['total_article_count']
                    })

                    if node.get('children'):
                        flatten_hierarchy(node['children'], rows)

                return rows

            rows = flatten_hierarchy(hierarchy)

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'full_path', 'parent', 'ancestors', 'level', 'article_count', 'total_article_count'])
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"✅ Exported hierarchy to CSV: {output_path}")

        # Show summary
        print()
        print("=" * 80)
        print("Export Summary")
        print("=" * 80)
        print(f"Total articles: {len(articles)}")
        print(f"Top-level categories: {len(hierarchy)}")
        print(f"Output file: {output_path}")
        print(f"Format: {args.format.upper()}")
        print()

        return 0


def cmd_visualize(args):
    """Visualize category hierarchy."""
    from pre_processing.client import ServiceNowClient
    from pre_processing.knowledge_base import KnowledgeBase
    from pre_processing.category_hierarchy import CategoryHierarchyBuilder

    print("=" * 80)
    print("Visualize Category Hierarchy")
    print("=" * 80)

    # Validate configuration
    try:
        Config.validate_servicenow()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Initialize ServiceNow client
    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    ) as sn_client:

        # Initialize knowledge base handler
        kb = KnowledgeBase(sn_client, download_dir=Config.DOWNLOAD_DIR)

        # Get all articles
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()

        # Build hierarchy
        builder = CategoryHierarchyBuilder()
        hierarchy = builder.build_hierarchy_from_articles(articles)

        # Visualize
        def print_tree(nodes, indent=0):
            for node in nodes:
                print("  " * indent + f"├─ {node['label']} ({node.get('count', 0)} articles)")
                if node.get('children'):
                    print_tree(node['children'], indent + 1)

        print(f"\nFound {len(hierarchy)} top-level categories:")
        print_tree(hierarchy)

        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # =================================================================
    # Migrate command
    # =================================================================
    migrate_parser = subparsers.add_parser(
        'migrate',
        help='Run full migration (export articles to ZIP)',
        description='Export ServiceNow articles as ZIP file for Notion import'
    )
    CommonCLI.add_common_args(migrate_parser)
    migrate_parser.add_argument(
        '--process-iframes',
        action='store_true',
        help='Enable iframe processing (Google Docs export)'
    )
    migrate_parser.add_argument(
        '--no-zip',
        action='store_true',
        help='Do not create ZIP file (keep extracted files)'
    )
    migrate_parser.set_defaults(func=cmd_migrate)

    # =================================================================
    # Export list command
    # =================================================================
    export_parser = subparsers.add_parser(
        'export-list',
        help='Export article list with metadata',
        description='Export article metadata to CSV or JSON (no file downloads)'
    )
    CommonCLI.add_common_args(export_parser)
    export_parser.set_defaults(func=cmd_export_list)

    # =================================================================
    # Process iframes command
    # =================================================================
    iframe_parser = subparsers.add_parser(
        'process-iframes',
        help='Process iframes in article HTML',
        description='Download and process embedded content (Google Docs, Slides, etc.)'
    )
    CommonCLI.add_common_args(iframe_parser)
    iframe_parser.add_argument(
        '--article-number',
        required=True,
        help='Article number to process (e.g., KB0001)'
    )
    iframe_parser.set_defaults(func=cmd_process_iframes)

    # =================================================================
    # Make subitem command
    # =================================================================
    subitem_parser = subparsers.add_parser(
        'make-subitem',
        help='Make Notion page a sub-item of another',
        description='Create parent-child relationship between database pages'
    )
    subitem_parser.add_argument(
        '--child',
        required=True,
        metavar='PAGE_ID',
        help='Child page ID'
    )
    subitem_parser.add_argument(
        '--parent',
        required=True,
        metavar='PAGE_ID',
        help='Parent page ID'
    )
    subitem_parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip verification that pages exist'
    )
    subitem_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    subitem_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    subitem_parser.set_defaults(func=cmd_make_subitem)

    # =================================================================
    # Export categories command
    # =================================================================
    export_cat_parser = subparsers.add_parser(
        'export-categories',
        help='Export category hierarchy to JSON or CSV',
        description='Export complete category hierarchy from ServiceNow Knowledge Base'
    )
    export_cat_parser.add_argument(
        '--format',
        choices=['json', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    export_cat_parser.add_argument(
        '--output',
        metavar='PATH',
        help='Output file path (default: category_hierarchy.{format})'
    )
    export_cat_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be exported without executing'
    )
    export_cat_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    export_cat_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )
    export_cat_parser.set_defaults(func=cmd_export_categories)

    # =================================================================
    # Visualize command
    # =================================================================
    visualize_parser = subparsers.add_parser(
        'visualize',
        help='Visualize category hierarchy',
        description='Display category hierarchy tree from ServiceNow'
    )
    visualize_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    visualize_parser.set_defaults(func=cmd_visualize)

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    verbose = getattr(args, 'verbose', False)
    quiet = getattr(args, 'quiet', False)
    CommonCLI.setup_logging(verbose=verbose, quiet=quiet)

    # Run command
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
