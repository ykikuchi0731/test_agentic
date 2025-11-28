"""Run post-processing module: python -m post_processing

This allows running post-processing operations directly as a module.

Usage:
    python -m post_processing make-subitem --child <id> --parent <id>

Available commands:
    make-subitem    - Make a page a sub-item of another page
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_utils import CommonCLI
from config import Config, ConfigurationError
from post_processing.page_hierarchy import NotionPageHierarchy

import logging

logger = logging.getLogger(__name__)


def cmd_make_subitem(args):
    """Make a Notion page a sub-item of another page."""
    print("=" * 80)
    print("Make Notion Page a Sub-Item")
    print("=" * 80)

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
