"""Run post-processing module: python -m post_processing

This allows running post-processing operations directly as a module.

Usage:
    python -m post_processing make-subitem --child <id> --parent <id>
    python -m post_processing get-imported-pages --parent-pages <id1>,<id2>
    python -m post_processing move-pages --database <id> --pages-csv <file>

Available commands:
    make-subitem        - Make a page a sub-item of another page
    get-imported-pages  - Get page IDs of imported KB pages
    move-pages          - Move pages to a target database
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_utils import CommonCLI
from config import Config, ConfigurationError
from post_processing.page_hierarchy import NotionPageHierarchy
from post_processing.get_imported_page_ids import main as get_imported_pages_main
from post_processing.move_pages_to_database import main as move_pages_main

import logging

logger = logging.getLogger(__name__)


def cmd_move_pages(args):
    """Move pages to a target database."""
    print("=" * 80)
    print("Move Pages to Database")
    print("=" * 80)

    # Setup logging with module-specific prefix
    CommonCLI.setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False),
        log_prefix='post_processing_move_pages'
    )

    # Validate configuration
    try:
        Config.validate_notion()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    logger.info(f"Target database ID: {args.database}")
    logger.info(f"Pages CSV: {args.pages_csv}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Max workers: {args.workers}")

    # Run main function
    try:
        results = move_pages_main(
            target_database_id=args.database,
            pages_csv=Path(args.pages_csv),
            api_key=Config.NOTION_API_KEY,
            output_dir=Path(args.output_dir),
            max_workers=args.workers,
            rate_limit_delay=args.rate_limit
        )

        # Calculate success/failure counts
        success_count = sum(1 for r in results if r.get("success", False))
        fail_count = len(results) - success_count

        print("\n" + "=" * 80)
        if fail_count == 0:
            print("✅ All operations completed successfully!")
        elif success_count == 0:
            print("❌ All operations failed!")
        else:
            print("⚠️  Operations completed with some failures")
        print("=" * 80)
        print(f"Total pages: {len(results)}")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")

        # Return non-zero exit code if there were failures
        return 1 if fail_count > 0 else 0
    except Exception as e:
        logger.error(f"Move operation failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def cmd_get_imported_pages(args):
    """Get page IDs of imported KB pages."""
    print("=" * 80)
    print("Get Imported Page IDs")
    print("=" * 80)

    # Setup logging with module-specific prefix
    CommonCLI.setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False),
        log_prefix='post_processing_get_imported_pages'
    )

    # Validate configuration
    try:
        Config.validate_notion()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    logger.info(f"Parent page IDs: {args.parent_pages}")
    logger.info(f"Filter prefix: {args.prefix}")
    logger.info(f"Output directory: {args.output_dir}")

    # Run main function
    output_path = get_imported_pages_main(
        parent_page_ids=args.parent_pages,
        api_key=Config.NOTION_API_KEY,
        output_dir=Path(args.output_dir),
        filter_prefix=args.prefix,
        max_workers=args.workers
    )

    print("\n" + "=" * 80)
    print("✅ Success!")
    print("=" * 80)
    print(f"Output file: {output_path}")
    return 0


def cmd_make_subitem(args):
    """Make a Notion page a sub-item of another page."""
    print("=" * 80)
    print("Make Notion Page a Sub-Item")
    print("=" * 80)

    # Setup logging with module-specific prefix
    CommonCLI.setup_logging(
        verbose=getattr(args, 'verbose', False),
        quiet=getattr(args, 'quiet', False),
        log_prefix='post_processing_make_subitem'
    )

    # Validate configuration
    try:
        Config.validate_notion()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
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
        print("\n" + "=" * 80)
        print("✅ Success!")
        print("=" * 80)
        print(f"Child: {result['child_title']}")
        print(f"Parent: {result['parent_title']}")
        print(f"Database: {result['database_id']}")
        print(f"Parent property ID: {result['parent_property_id']}")
        return 0
    else:
        print(f"\n❌ Error: {result['error']}")
        return 1


def main():
    """Run post-processing from command line."""
    parser = argparse.ArgumentParser(
        description="ServiceNow to Notion Migration - Post-processing\n\n"
                    "Organize and manage Notion pages after import.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Move pages command
    move_parser = subparsers.add_parser(
        'move-pages',
        help='Move pages to a target database',
        description='Move imported pages to a target Notion database'
    )
    move_parser.add_argument(
        '--database',
        required=True,
        metavar='DATABASE_ID',
        help='Target database ID'
    )
    move_parser.add_argument(
        '--pages-csv',
        required=True,
        metavar='FILE',
        help='CSV file with page_id column'
    )
    move_parser.add_argument(
        '--output-dir',
        default='./migration_output',
        metavar='DIR',
        help='Output directory for results log (default: ./migration_output)'
    )
    move_parser.add_argument(
        '--workers',
        type=int,
        default=4,
        metavar='N',
        help='Number of concurrent workers (default: 4)'
    )
    move_parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.1,
        metavar='SECONDS',
        help='Delay between requests in seconds (default: 0.1)'
    )
    move_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    move_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )
    move_parser.set_defaults(func=cmd_move_pages)

    # Get imported pages command
    imported_parser = subparsers.add_parser(
        'get-imported-pages',
        help='Get page IDs of imported KB pages',
        description='Retrieve page IDs and titles of pages imported from ServiceNow'
    )
    imported_parser.add_argument(
        '--parent-pages',
        required=True,
        metavar='PAGE_IDS',
        help='Comma-separated parent page IDs (e.g., "abc123,def456")'
    )
    imported_parser.add_argument(
        '--prefix',
        default='KB',
        metavar='PREFIX',
        help='Filter pages by title prefix (default: KB)'
    )
    imported_parser.add_argument(
        '--output-dir',
        default='./migration_output',
        metavar='DIR',
        help='Output directory for CSV file (default: ./migration_output)'
    )
    imported_parser.add_argument(
        '--workers',
        type=int,
        default=4,
        metavar='N',
        help='Number of concurrent workers (default: 4)'
    )
    imported_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    imported_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )
    imported_parser.set_defaults(func=cmd_get_imported_pages)

    # Make subitem command
    subitem_parser = subparsers.add_parser(
        'make-subitem',
        help='Make a page a sub-item of another',
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
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )
    subitem_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    subitem_parser.set_defaults(func=cmd_make_subitem)

    # Parse arguments
    args = parser.parse_args()

    # Note: Logging is setup by each command function with module-specific prefix

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
