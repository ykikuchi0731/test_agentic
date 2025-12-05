#!/usr/bin/env python3
"""Unified CLI tool for ServiceNow to Notion migration.

This CLI tool provides a unified interface to all migration functionality,
including pre-processing, post-processing, and utility commands.

Usage:
    python cli.py <command> [options]

Available commands:
    migrate            - Export articles from ServiceNow to ZIP
    export-list        - Export article list with metadata (CSV/JSON)
    export-categories  - Export category hierarchy (JSON/CSV)
    process-iframes    - Process iframes in article HTML
    convert-tables     - Convert tables with images to column blocks
    scan-invisible     - Scan HTML files for invisible elements
    make-subitem       - Make Notion page a sub-item of another
    organize-categories - Build category hierarchy in Notion database
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

from cli_utils import CommonCLI
from config import Config, ConfigurationError
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def init_servicenow_client():
    """Initialize and return ServiceNow client and knowledge base."""
    Config.validate_servicenow()
    logger.info(f"Connecting to ServiceNow: {Config.SERVICENOW_INSTANCE}")

    client = ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT,
    )
    kb = KnowledgeBase(client, download_dir=Config.DOWNLOAD_DIR)
    return client, kb


def print_separator(title=None, char="="):
    """Print a separator line with optional title."""
    if title:
        print(char * 80)
        print(title)
    print(char * 80)


def print_result_summary(result, success_msg, fail_msg):
    """Print standardized result summary."""
    if result and result.get('zip_created'):
        print(f"\n✅ {success_msg}")
        if result.get('zip_path'):
            print(f"Export ZIP: {result['zip_path']}")
        if result.get('csv_path'):
            print(f"Article list: {result['csv_path']}")
        print(f"Total articles exported: {result.get('total_articles', 0)}")
        return 0

    print(f"\n❌ {fail_msg}")
    if result and result.get('errors'):
        print(f"Errors: {result['errors']}")
    return 1


def flatten_hierarchy(nodes, rows=None):
    """Flatten category hierarchy tree into list of rows for CSV export."""
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


# ============================================================================
# Command Implementations
# ============================================================================

def cmd_migrate(args):
    """Run full migration to export articles as ZIP for Notion import."""
    from pre_processing.migrator import MigrationOrchestrator
    from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

    print_separator("ServiceNow Knowledge Base Export")

    # Validate configuration and initialize client
    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:

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

        # Initialize Google Docs exporter if requested
        google_docs_exporter = None
        if args.process_iframes:
            google_docs_exporter = GoogleDocsBrowserExporter(
                headless=not args.browser_gui if hasattr(args, 'browser_gui') else True
            )

        # Initialize migrator
        migrator = MigrationOrchestrator(
            servicenow_kb=kb,
            output_dir=Config.MIGRATION_OUTPUT_DIR,
            google_docs_exporter=google_docs_exporter,
            process_iframes=args.process_iframes,
            max_workers=args.workers if hasattr(args, 'workers') else 4,
            rate_limit_delay=args.rate_limit if hasattr(args, 'rate_limit') else 0.0,
            max_articles_per_zip=args.max_per_zip if hasattr(args, 'max_per_zip') else 300
        )

        # Show configuration
        print(f"Parallel workers: {args.workers}")
        if args.rate_limit > 0:
            print(f"Rate limit: {args.rate_limit}s delay between requests")
        if args.process_iframes:
            browser_mode = "GUI mode" if hasattr(args, 'browser_gui') and args.browser_gui else "headless mode"
            print(f"Iframe processing (Google Docs export): Enabled ({browser_mode})")
        else:
            print(f"Iframe processing (Google Docs export): Disabled")
        print(f"Max articles per ZIP: {args.max_per_zip}")

        if args.category:
            print(f"Including only articles under category: {args.category}")
        if args.exclude_category:
            print(f"Excluding articles under category: {args.exclude_category}")

        # Run migration
        result = migrator.export_all_to_zip(
            query=args.filter,
            zip_filename=None,
            limit=args.limit,
            category_filter=args.category if hasattr(args, 'category') else None,
            exclude_category=args.exclude_category if hasattr(args, 'exclude_category') else None
        )

        return print_result_summary(result, "Export completed successfully!", "Export failed!")


def cmd_export_list(args):
    """Export article list with metadata (no file downloads)."""
    from pre_processing.article_list_exporter import ArticleListExporter

    print_separator("Export Article List (Metadata Only)")

    # Validate configuration and initialize client
    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:

        # Initialize exporter
        exporter = ArticleListExporter(
            servicenow_kb=kb,
            output_dir=args.output or Config.MIGRATION_OUTPUT_DIR
        )

        # Parse filters
        filters = CommonCLI.parse_filters(args.filter)
        category_filter = filters.get('category') if filters else None

        if args.dry_run:
            print("\n[DRY RUN] Would export article list")
            print(f"  Limit: {args.limit if args.limit else 'all'}")
            print(f"  Category filter: {category_filter if category_filter else 'none'}")
            print(f"  Format: {args.format}")
            return 0

        # Collect metadata (this handles filtering and limiting internally)
        logger.info("Collecting article metadata...")
        article_metadata = exporter.collect_article_metadata(
            limit=args.limit,
            category_filter=category_filter
        )

        logger.info(f"Exporting {len(article_metadata)} articles")

        # Export based on format
        output_path = (exporter.export_to_csv(article_metadata) if args.format == 'csv'
                       else exporter.export_to_json(article_metadata))

        print(f"\n✅ Exported {len(article_metadata)} articles to: {output_path}")
        return 0


def cmd_process_iframes(args):
    """Process iframes in article HTML."""
    print_separator("Process iframes in Article HTML")

    if not args.article_number:
        logger.error("--article-number is required")
        return 1

    logger.info(f"Processing iframes for article: {args.article_number}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would process iframes for article {args.article_number}")
        return 0

    print("Note: Full implementation requires article HTML content")
    print("Use 'migrate' command with --process-iframes flag for full iframe processing")
    return 0


def cmd_convert_tables(args):
    """Convert tables with images to Notion column blocks."""
    from pre_processing.convert_table_column import main as convert_tables_main

    print_separator("Convert Tables to Column Blocks")

    # Setup logging
    CommonCLI.setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False)
    )

    directory = Path(args.directory)

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1

    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return 1

    logger.info(f"Directory: {directory}")
    logger.info(f"Recursive: {args.recursive}")
    logger.info(f"Dry run: {args.dry_run}")

    try:
        stats = convert_tables_main(
            directory=directory,
            recursive=args.recursive,
            dry_run=args.dry_run
        )

        print("\n" + "=" * 80)
        if args.dry_run:
            print("DRY RUN - No files were modified")
        elif stats['files_modified'] > 0:
            print("✅ Conversion completed!")
        else:
            print("No tables with images found")
        print("=" * 80)
        print(f"Files scanned:    {stats['files_scanned']}")
        print(f"Files modified:   {stats['files_modified']}")
        print(f"Tables converted: {stats['tables_converted']}")
        print(f"Tables skipped:   {stats['tables_skipped']}")

        return 0

    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_scan_invisible(args):
    """Scan HTML files for invisible elements."""
    from page_checks.scan_invisible_elements import main as scan_invisible_main
    from datetime import datetime

    print_separator("Scan Invisible Elements")

    # Setup logging
    CommonCLI.setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False),
        log_prefix='scan_invisible'
    )

    directory = Path(args.directory)

    # Use --output if provided, otherwise generate default filename in analysis_output
    if args.output:
        output_csv = Path(args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_csv = output_dir / f'invisible_elements_{timestamp}.csv'

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1

    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return 1

    logger.info(f"Directory: {directory}")
    logger.info(f"Output CSV: {output_csv}")
    logger.info(f"Recursive: {args.recursive}")

    try:
        stats = scan_invisible_main(
            directory=directory,
            output_csv=output_csv,
            recursive=args.recursive
        )

        print("\n" + "=" * 80)
        if stats['invisible_elements'] > 0:
            print("✅ Scan completed!")
        else:
            print("No invisible elements found")
        print("=" * 80)
        print(f"Files scanned:        {stats['files_scanned']}")
        print(f"Files with invisible: {stats['files_with_invisible']}")
        print(f"Invisible elements:   {stats['invisible_elements']}")
        print(f"\n📄 Report saved to: {output_csv}")

        return 0

    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_make_subitem(args):
    """Make a Notion page a sub-item of another page."""
    from post_processing.page_hierarchy import NotionPageHierarchy

    print_separator("Make Notion Page a Sub-Item")

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

    print(f"\n❌ Error: {result['error']}")
    return 1


def cmd_organize_categories(args):
    """Build category hierarchy in Notion database from article list CSV."""
    from post_processing.category_organizer import build_categories_from_csv

    print_separator("Organize Categories in Notion Database")

    try:
        Config.validate_notion()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Check CSV file exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {args.csv}")
        return 1

    # Get database ID (from args or config)
    database_id = args.database_id or Config.NOTION_DATABASE_ID
    if not database_id:
        logger.error("Database ID is required (use --database-id or set NOTION_DATABASE_ID in .env)")
        return 1

    logger.info(f"CSV file: {args.csv}")
    logger.info(f"Database ID: {database_id}")
    logger.info(f"Dry run: {args.dry_run}")

    if args.dry_run:
        print("\n[DRY RUN] Previewing category organization...")

    # Build category hierarchy
    result = build_categories_from_csv(
        api_key=Config.NOTION_API_KEY,
        database_id=database_id,
        csv_path=str(csv_path),
        dry_run=args.dry_run
    )

    # Display results
    print_separator("Results", "-")
    print(f"Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"Categories created: {result['categories_created']}")
    print(f"Relationships created: {result['relationships_created']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for i, error in enumerate(result['errors'][:10], 1):
            print(f"  {i}. {error}")
        if len(result['errors']) > 10:
            print(f"  ... and {len(result['errors']) - 10} more errors")

    # Export category mapping if requested
    if args.export_mapping and result['category_pages'] and not args.dry_run:
        from post_processing.category_organizer import CategoryOrganizer

        mapping_path = args.export_mapping
        logger.info(f"Exporting category mapping to {mapping_path}")

        organizer = CategoryOrganizer(
            api_key=Config.NOTION_API_KEY,
            database_id=database_id
        )
        organizer.category_pages = result['category_pages']
        organizer.export_category_mapping(mapping_path)

        print(f"\n✅ Category mapping exported to: {mapping_path}")

    print("=" * 80)

    return 0 if result['success'] else 1


def cmd_export_categories(args):
    """Export category hierarchy to JSON or CSV."""
    import json
    import csv
    from pre_processing.category_hierarchy import CategoryHierarchyBuilder

    print_separator("Export Category Hierarchy")

    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:

        # Get all articles with display values for human-readable category names
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only(display_value='all')
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
            rows = flatten_hierarchy(hierarchy)
            fieldnames = ['name', 'full_path', 'parent', 'ancestors', 'level',
                          'article_count', 'total_article_count']

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"✅ Exported hierarchy to CSV: {output_path}")

        # Show summary
        print_separator("Export Summary", "-")
        print(f"Total articles: {len(articles)}")
        print(f"Top-level categories: {len(hierarchy)}")
        print(f"Output file: {output_path}")
        print(f"Format: {args.format.upper()}")
        print()

        return 0


def cmd_visualize(args):
    """Visualize category hierarchy."""
    from pre_processing.category_hierarchy import CategoryHierarchyBuilder

    print_separator("Visualize Category Hierarchy")

    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:

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
        help='Export articles from ServiceNow to ZIP',
        description='Export ServiceNow Knowledge Base articles with attachments to ZIP'
    )
    CommonCLI.add_common_args(migrate_parser)
    migrate_parser.add_argument(
        '--category',
        metavar='NAME',
        help='Include only articles under this category (partial match, case-insensitive)'
    )
    migrate_parser.add_argument(
        '--exclude-category',
        metavar='NAME',
        help='Exclude articles under this category (partial match, case-insensitive)'
    )
    migrate_parser.add_argument(
        '--workers',
        type=int,
        default=4,
        metavar='N',
        help='Number of parallel workers for processing (default: 4, use 1 for sequential)'
    )
    migrate_parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.0,
        metavar='SECONDS',
        help='Delay in seconds between API requests to avoid throttling (default: 0.0)'
    )
    migrate_parser.add_argument(
        '--process-iframes',
        action='store_true',
        help='Enable iframe processing (Google Docs export)'
    )
    migrate_parser.add_argument(
        '--browser-gui',
        action='store_true',
        help='Show browser GUI when exporting Google Docs (default: headless mode)'
    )
    migrate_parser.add_argument(
        '--no-zip',
        action='store_true',
        help='Do not create ZIP file (keep extracted files)'
    )
    migrate_parser.add_argument(
        '--max-per-zip',
        type=int,
        default=300,
        metavar='N',
        help='Maximum number of articles per ZIP file (default: 300). '
             'Large exports will be split into multiple ZIPs.'
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
    # Convert tables command
    # =================================================================
    convert_parser = subparsers.add_parser(
        'convert-tables',
        help='Convert tables with images to Notion column blocks',
        description='Scan HTML files and convert tables containing images to column blocks'
    )
    CommonCLI.add_common_args(convert_parser)
    convert_parser.add_argument(
        '--directory',
        required=True,
        metavar='PATH',
        help='Directory containing HTML files to process'
    )
    convert_parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )
    convert_parser.set_defaults(func=cmd_convert_tables)

    # =================================================================
    # Scan invisible elements command
    # =================================================================
    scan_parser = subparsers.add_parser(
        'scan-invisible',
        help='Scan HTML files for invisible elements',
        description='Identify elements that are invisible due to CSS styles and report in CSV'
    )
    CommonCLI.add_common_args(scan_parser)
    scan_parser.add_argument(
        '--directory',
        required=True,
        metavar='PATH',
        help='Directory containing HTML files to scan'
    )
    scan_parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='Do not process subdirectories (recursive is default)'
    )
    scan_parser.set_defaults(func=cmd_scan_invisible, recursive=True)

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
    # Organize categories command
    # =================================================================
    organize_parser = subparsers.add_parser(
        'organize-categories',
        help='Build category hierarchy in Notion database',
        description='Create category pages and hierarchy in Notion from article list CSV'
    )
    organize_parser.add_argument(
        '--csv',
        required=True,
        metavar='PATH',
        help='Path to article list CSV file'
    )
    organize_parser.add_argument(
        '--database-id',
        metavar='ID',
        help='Notion database ID (overrides NOTION_DATABASE_ID from .env)'
    )
    organize_parser.add_argument(
        '--export-mapping',
        metavar='PATH',
        help='Export category path to page ID mapping as CSV'
    )
    organize_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview without creating pages'
    )
    organize_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    organize_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )
    organize_parser.set_defaults(func=cmd_organize_categories)

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
