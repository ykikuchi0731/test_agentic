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
    scan-div-accshow   - Scan HTML files for invisible div.accshow elements
    scan-empty-wrappers - Scan HTML files for empty list wrapper elements
    gdoc-mapping       - Extract Google Docs mapping from migration log
    rename-gdoc        - Rename Google Docs files based on article names
    remove-toc         - Remove div.mce-toc elements from HTML files
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
        print(f"{char * 80}\n{title}")
    print(char * 80)


def print_result_summary(result, success_msg, fail_msg):
    """Print standardized result summary."""
    if result and result.get('zip_created'):
        print(f"\n✅ {success_msg}")
        if zip_path := result.get('zip_path'):
            print(f"Export ZIP: {zip_path}")
        if csv_path := result.get('csv_path'):
            print(f"Article list: {csv_path}")
        print(f"Total articles exported: {result.get('total_articles', 0)}")
        return 0
    print(f"\n❌ {fail_msg}")
    if result and (errors := result.get('errors')):
        print(f"Errors: {errors}")
    return 1


def flatten_hierarchy(nodes, rows=None):
    """Flatten category hierarchy tree into list of rows for CSV export."""
    rows = rows or []
    for node in nodes:
        rows.append({'name': node['name'], 'full_path': node['full_path'],
                    'parent': node['parent'] or '(root)',
                    'ancestors': ' > '.join(node['ancestors']) if node['ancestors'] else '(none)',
                    'level': node['level'], 'article_count': node['article_count'],
                    'total_article_count': node['total_article_count']})
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
    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()

        filters = CommonCLI.parse_filters(args.filter)
        if filters or args.kb_base:
            articles = CommonCLI.filter_articles(articles, filters, args.kb_base)
            logger.info(f"Filtered to {len(articles)} articles")

        articles = CommonCLI.apply_limit_offset(articles, args.limit, args.offset)
        logger.info(f"Processing {len(articles)} articles (offset: {args.offset})")

        if args.dry_run:
            print("\n[DRY RUN] Would process the following articles:")
            CommonCLI.print_summary("Articles to Process", articles, ['number', 'short_description', 'kb_category'])
            return 0

        google_docs_exporter = (GoogleDocsBrowserExporter(headless=not getattr(args, 'browser_gui', False))
                               if args.process_iframes else None)

        migrator = MigrationOrchestrator(servicenow_kb=kb, output_dir=Config.MIGRATION_OUTPUT_DIR,
            google_docs_exporter=google_docs_exporter, process_iframes=args.process_iframes,
            max_workers=getattr(args, 'workers', 4), rate_limit_delay=getattr(args, 'rate_limit', 0.0),
            max_articles_per_zip=getattr(args, 'max_per_zip', 300))

        print(f"Parallel workers: {args.workers}")
        if args.rate_limit > 0:
            print(f"Rate limit: {args.rate_limit}s delay between requests")
        browser_mode = "GUI mode" if getattr(args, 'browser_gui', False) else "headless mode"
        status = f"Enabled ({browser_mode})" if args.process_iframes else "Disabled"
        print(f"Iframe processing (Google Docs export): {status}")
        print(f"Max articles per ZIP: {args.max_per_zip}")
        if args.category:
            print(f"Including only articles under category: {args.category}")
        if args.exclude_category:
            print(f"Excluding articles under category: {args.exclude_category}")

        result = migrator.export_all_to_zip(query=args.filter, zip_filename=None, limit=args.limit,
            category_filter=getattr(args, 'category', None), exclude_category=getattr(args, 'exclude_category', None))
        return print_result_summary(result, "Export completed successfully!", "Export failed!")


def cmd_export_list(args):
    """Export article list with metadata (no file downloads)."""
    from pre_processing.article_list_exporter import ArticleListExporter

    print_separator("Export Article List (Metadata Only)")
    try:
        sn_client, kb = init_servicenow_client()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    with sn_client:
        exporter = ArticleListExporter(servicenow_kb=kb, output_dir=args.output or Config.MIGRATION_OUTPUT_DIR)
        filters = CommonCLI.parse_filters(args.filter)
        category_filter = filters.get('category') if filters else None

        if args.dry_run:
            print(f"\n[DRY RUN] Would export article list\n  Limit: {args.limit or 'all'}\n"
                  f"  Category filter: {category_filter or 'none'}\n  Format: {args.format}")
            return 0

        logger.info("Collecting article metadata...")
        article_metadata = exporter.collect_article_metadata(limit=args.limit, category_filter=category_filter)
        logger.info(f"Exporting {len(article_metadata)} articles")

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
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False))

    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1
    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return 1

    logger.info(f"Directory: {directory}\nRecursive: {args.recursive}\nDry run: {args.dry_run}")

    try:
        stats = convert_tables_main(directory=directory, recursive=args.recursive, dry_run=args.dry_run)
        print(f"\n{'=' * 80}")
        msg = "DRY RUN - No files were modified" if args.dry_run else (
              "✅ Conversion completed!" if stats['files_modified'] > 0 else "No tables with images found")
        print(f"{msg}\n{'=' * 80}\nFiles scanned:    {stats['files_scanned']}\n"
              f"Files modified:   {stats['files_modified']}\nTables converted: {stats['tables_converted']}\n"
              f"Tables skipped:   {stats['tables_skipped']}")
        return 0
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_scan_invisible(args):
    """Scan HTML files for invisible div.accshow elements."""
    from page_checks.scan_div_accshow import main as scan_invisible_main
    from datetime import datetime

    print_separator("Scan Invisible Elements")
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False),
                           log_prefix='scan_invisible')

    directory = Path(args.directory)
    if args.output:
        output_csv = Path(args.output)
    else:
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_csv = output_dir / f"div_accshow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1
    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return 1

    logger.info(f"Directory: {directory}\nOutput CSV: {output_csv}\nRecursive: {args.recursive}")

    try:
        stats = scan_invisible_main(directory=directory, output_csv=output_csv, recursive=args.recursive)
        msg = "✅ Scan completed!" if stats['invisible_elements'] > 0 else "No invisible elements found"
        print(f"\n{'=' * 80}\n{msg}\n{'=' * 80}\nFiles scanned:        {stats['files_scanned']}\n"
              f"Files with invisible: {stats['files_with_invisible']}\nInvisible elements:   {stats['invisible_elements']}\n"
              f"\n📄 Report saved to: {output_csv}")
        return 0
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_scan_empty_wrappers(args):
    """Scan HTML files for empty list wrapper elements."""
    from page_checks.scan_empty_list_wrappers import main as scan_wrappers_main
    from datetime import datetime

    print_separator("Scan Empty List Wrappers")
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False),
                           log_prefix='scan_empty_wrappers')

    directory = Path(args.directory)
    if args.output:
        output_csv = Path(args.output)
    else:
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_csv = output_dir / f"empty_list_wrappers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1
    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return 1

    logger.info(f"Directory: {directory}\nOutput CSV: {output_csv}\nRecursive: {args.recursive}\n"
               f"Min nesting depth: {args.min_depth}\nMin wrapper count: {args.min_count}")

    try:
        stats = scan_wrappers_main(directory=directory, output_csv=output_csv, recursive=args.recursive,
                                   min_nesting_depth=args.min_depth, min_wrapper_count=args.min_count)
        msg = "✅ Scan completed!" if stats['total_empty_wrappers'] > 0 else "No empty list wrappers found"
        print(f"\n{'=' * 80}\n{msg}\n{'=' * 80}\nFiles scanned:        {stats['files_scanned']}\n"
              f"Files with wrappers:  {stats['files_with_wrappers']}\nWrapper chains:       {stats['total_wrapper_chains']}\n"
              f"Total empty wrappers: {stats['total_empty_wrappers']}\n\n📄 Report saved to: {output_csv}")
        return 0
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_gdoc_mapping(args):
    """Extract Google Docs mapping from migration log and tracking files."""
    from pre_processing.gdoc_article_mapping import main as gdoc_mapping_main

    print_separator("Extract Google Docs Mapping")
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False),
                           log_prefix='gdoc_mapping')

    log_file = Path(args.log_file)
    download_dir = getattr(args, 'download_dir', 'download')

    if not log_file.exists():
        logger.error(f"Log file not found: {log_file}")
        print(f"\n❌ Error: Log file not found: {log_file}")
        return 1

    logger.info(f"Log file: {log_file}\nDownload directory: {download_dir}\nOutput: {args.output or 'auto-generated'}")

    try:
        result = gdoc_mapping_main(log_file=str(log_file), output_file=args.output, download_dir=download_dir)
        msg = "✅ Successfully extracted Google Docs mappings" if result['success'] else f"❌ {result['error']}"
        print(f"\n{'=' * 80}\n{msg}\n{'=' * 80}\nTotal mappings:   {result['count']}")
        if result['success']:
            print(f"  From tracking:  {result.get('tracking_file_count', 0)} (deterministic)\n"
                  f"  From log:       {result.get('log_only_count', 0)} (failed downloads)\n"
                  f"  Success:        {result['success_count']}\n  Failed:         {result['failed_count']}\n"
                  f"\n📄 CSV saved to: {result['csv_path']}")
        return 0 if result['success'] else 1
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_rename_gdoc(args):
    """Rename Google Docs files based on article names."""
    from pre_processing.rename_gdoc import main as rename_gdoc_main

    print_separator("Rename Google Docs Files")
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False),
                           log_prefix='rename_gdoc')

    mapping_file, input_folder = Path(args.mapping_file), Path(args.input_folder)

    if not mapping_file.exists():
        logger.error(f"Mapping file not found: {mapping_file}")
        print(f"\n❌ Error: Mapping file not found: {mapping_file}")
        return 1
    if not input_folder.exists():
        logger.error(f"Input folder not found: {input_folder}")
        print(f"\n❌ Error: Input folder not found: {input_folder}")
        return 1
    if not input_folder.is_dir():
        logger.error(f"Path is not a directory: {input_folder}")
        print(f"\n❌ Error: Path is not a directory: {input_folder}")
        return 1

    logger.info(f"Mapping file: {mapping_file}\nInput folder: {input_folder}\nOutput: {args.output or 'auto-generated'}")

    try:
        result = rename_gdoc_main(mapping_file_path=str(mapping_file), input_folder=str(input_folder),
                                 output_file=args.output)
        stats = result['stats']
        print(f"\n{'=' * 80}\n✅ Google Docs Renaming Complete\n{'=' * 80}\nTotal files:      {stats['total']}\n"
              f"Renamed:          {stats['renamed']}\nNot found:        {stats['not_found']}\n"
              f"Failed:           {stats['failed']}\n\n📄 Report saved to: {result['csv_path']}")
        return 0
    except Exception as e:
        logger.error(f"Renaming failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_remove_toc(args):
    """Remove div.mce-toc elements from HTML files."""
    from pre_processing.remove_toc import main as remove_toc_main

    print_separator("Remove TOC Elements")
    CommonCLI.setup_logging(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False),
                           log_prefix='remove_toc')

    input_folder = Path(args.input_folder)
    if not input_folder.exists():
        logger.error(f"Folder not found: {input_folder}")
        print(f"\n❌ Error: Folder not found: {input_folder}")
        return 1
    if not input_folder.is_dir():
        logger.error(f"Path is not a directory: {input_folder}")
        print(f"\n❌ Error: Path is not a directory: {input_folder}")
        return 1

    logger.info(f"Input folder: {input_folder}\nRecursive: {args.recursive}\nOutput: {args.output or 'auto-generated'}")

    try:
        result = remove_toc_main(input_folder=str(input_folder), output_file=args.output, recursive=args.recursive)
        stats = result['stats']
        print(f"\n{'=' * 80}\n✅ TOC Removal Complete\n{'=' * 80}\nTotal HTML files:     {stats['total_files']}\n"
              f"Files with mce-toc:   {stats['files_with_toc']}\nTotal TOC removed:    {stats['total_toc_removed']}\n"
              f"Errors:               {stats['errors']}")
        if csv_path := result['csv_path']:
            print(f"\n📄 Report saved to: {csv_path}")
        else:
            print("\nNo mce-toc elements found in any files.")
        return 0
    except Exception as e:
        logger.error(f"TOC removal failed: {e}", exc_info=True)
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

    logger.info(f"Child page ID: {args.child}\nParent page ID: {args.parent}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would make page {args.child} a sub-item of {args.parent}")
        return 0

    hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
    result = hierarchy.make_subitem(child_page_id=args.child, parent_page_id=args.parent, verify=not args.no_verify)

    if result['success']:
        print(f"\n✅ Successfully made '{result['child_title']}' a sub-item of '{result['parent_title']}'\n"
              f"Database: {result['database_id']}\nParent property ID: {result['parent_property_id']}")
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

    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {args.csv}")
        return 1

    database_id = args.database_id or Config.NOTION_DATABASE_ID
    if not database_id:
        logger.error("Database ID is required (use --database-id or set NOTION_DATABASE_ID in .env)")
        return 1

    logger.info(f"CSV file: {args.csv}\nDatabase ID: {database_id}\nDry run: {args.dry_run}")
    if args.dry_run:
        print("\n[DRY RUN] Previewing category organization...")

    result = build_categories_from_csv(api_key=Config.NOTION_API_KEY, database_id=database_id,
                                      csv_path=str(csv_path), dry_run=args.dry_run)

    print_separator("Results", "-")
    print(f"Success: {'✅ Yes' if result['success'] else '❌ No'}\nCategories created: {result['categories_created']}\n"
          f"Relationships created: {result['relationships_created']}\nErrors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for i, error in enumerate(result['errors'][:10], 1):
            print(f"  {i}. {error}")
        if len(result['errors']) > 10:
            print(f"  ... and {len(result['errors']) - 10} more errors")

    if args.export_mapping and result['category_pages'] and not args.dry_run:
        from post_processing.category_organizer import CategoryOrganizer
        logger.info(f"Exporting category mapping to {args.export_mapping}")
        organizer = CategoryOrganizer(api_key=Config.NOTION_API_KEY, database_id=database_id)
        organizer.category_pages = result['category_pages']
        organizer.export_category_mapping(args.export_mapping)
        print(f"\n✅ Category mapping exported to: {args.export_mapping}")

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
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only(display_value='all')
        logger.info(f"Found {len(articles)} articles")

        logger.info("Building category hierarchy...")
        builder = CategoryHierarchyBuilder()
        hierarchy = builder.build_hierarchy_from_articles(articles)
        logger.info(f"Found {len(hierarchy)} top-level categories")

        if args.dry_run:
            print(f"\n[DRY RUN] Would export category hierarchy:\n  - Top-level categories: {len(hierarchy)}\n"
                  f"  - Output format: {args.format}\n  - Output path: {args.output or 'category_hierarchy.' + args.format}")
            return 0

        output_path = Path(args.output) if args.output else Path(f"category_hierarchy.{args.format}")

        if args.format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(hierarchy, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Exported hierarchy to JSON: {output_path}")
        elif args.format == 'csv':
            rows = flatten_hierarchy(hierarchy)
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'full_path', 'parent', 'ancestors', 'level',
                                                       'article_count', 'total_article_count'])
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"✅ Exported hierarchy to CSV: {output_path}")

        print_separator("Export Summary", "-")
        print(f"Total articles: {len(articles)}\nTop-level categories: {len(hierarchy)}\n"
              f"Output file: {output_path}\nFormat: {args.format.upper()}\n")
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
        logger.info("Fetching articles from ServiceNow...")
        articles = kb.get_latest_articles_only()
        builder = CategoryHierarchyBuilder()
        hierarchy = builder.build_hierarchy_from_articles(articles)

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
    # Scan div.accshow elements command
    # =================================================================
    scan_parser = subparsers.add_parser(
        'scan-div-accshow',
        help='Scan HTML files for invisible div.accshow elements',
        description='Identify <div class="accshow"> elements that are invisible due to CSS rules'
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
    # Scan empty list wrappers command
    # =================================================================
    wrappers_parser = subparsers.add_parser(
        'scan-empty-wrappers',
        help='Scan HTML files for empty list wrapper elements',
        description='Identify nested <li> wrapper elements that cause blank lines in Notion'
    )
    CommonCLI.add_common_args(wrappers_parser)
    wrappers_parser.add_argument(
        '--directory',
        required=True,
        metavar='PATH',
        help='Directory containing HTML files to scan'
    )
    wrappers_parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='Do not process subdirectories (recursive is default)'
    )
    wrappers_parser.add_argument(
        '--min-depth',
        type=int,
        default=2,
        metavar='N',
        help='Minimum nesting depth to report (default: 2)'
    )
    wrappers_parser.add_argument(
        '--min-count',
        type=int,
        default=3,
        metavar='N',
        help='Minimum empty wrappers per file to report (default: 3)'
    )
    wrappers_parser.set_defaults(func=cmd_scan_empty_wrappers, recursive=True)

    # =================================================================
    # Google Docs mapping command
    # =================================================================
    gdoc_parser = subparsers.add_parser(
        'gdoc-mapping',
        help='Extract Google Docs mapping from migration log and tracking files',
        description='Parse migration log and tracking files to create CSV mapping of Google Docs to articles'
    )
    CommonCLI.add_common_args(gdoc_parser)
    gdoc_parser.add_argument(
        'log_file',
        metavar='LOG_FILE',
        help='Path to migration log file (e.g., logs/migration_20251210_103001.log)'
    )
    gdoc_parser.add_argument(
        '--download-dir',
        default='download',
        help='Directory containing downloaded files and tracking files (default: download)'
    )
    gdoc_parser.set_defaults(func=cmd_gdoc_mapping)

    # =================================================================
    # Rename Google Docs command
    # =================================================================
    rename_gdoc_parser = subparsers.add_parser(
        'rename-gdoc',
        help='Rename Google Docs files based on article names',
        description='Rename .docx files using article names from mapping CSV'
    )
    CommonCLI.add_common_args(rename_gdoc_parser)
    rename_gdoc_parser.add_argument(
        'mapping_file',
        metavar='MAPPING_FILE',
        help='Path to mapping CSV file (e.g., analysis_output/gdoc_article_mapping_*.csv)'
    )
    rename_gdoc_parser.add_argument(
        'input_folder',
        metavar='INPUT_FOLDER',
        help='Path to folder containing .docx files to rename'
    )
    rename_gdoc_parser.set_defaults(func=cmd_rename_gdoc)

    # =================================================================
    # Remove TOC command
    # =================================================================
    toc_parser = subparsers.add_parser(
        'remove-toc',
        help='Remove div.mce-toc elements from HTML files',
        description='Remove table of contents div elements from HTML files'
    )
    CommonCLI.add_common_args(toc_parser)
    toc_parser.add_argument(
        'input_folder',
        metavar='FOLDER',
        help='Path to folder containing HTML files'
    )
    toc_parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='Do not process subdirectories (recursive is default)'
    )
    toc_parser.set_defaults(func=cmd_remove_toc, recursive=True)

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
