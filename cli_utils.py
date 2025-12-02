"""Common CLI utilities for all modules.

This module provides shared CLI argument parsing, filtering, and utility functions
that can be used across all command-line scripts in the migration tool.
"""
import argparse
import logging
from typing import Dict, Any, Optional, List, Callable


class CommonCLI:
    """Common CLI argument parser and utilities for all modules."""

    @staticmethod
    def add_common_args(parser: argparse.ArgumentParser) -> None:
        """
        Add common arguments to any argument parser.

        Args:
            parser: ArgumentParser instance to add arguments to

        Common arguments added:
            --limit: Limit number of items to process (for testing)
            --offset: Skip N items before processing
            --filter: Filter criteria (key:value format, can be repeated)
            --kb-base: Knowledge base ID filter
            --dry-run: Show what would be done without executing
            -v/--verbose: Enable verbose logging
            -q/--quiet: Minimal output (errors only)
            --output: Output file path
            --format: Output format (json or csv)
        """
        # Data limiting
        parser.add_argument(
            '--limit',
            type=int,
            metavar='N',
            help='Limit number of items to process (useful for testing)'
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            metavar='N',
            help='Skip N items before processing (default: 0)'
        )

        # Filtering
        parser.add_argument(
            '--filter',
            action='append',
            metavar='KEY:VALUE',
            help='Filter items by criteria (e.g., "category:IT", "number:KB0001"). Can be used multiple times.'
        )
        parser.add_argument(
            '--kb-base',
            metavar='ID',
            help='Filter by knowledge base ID'
        )

        # Execution mode
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually executing'
        )
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose output (DEBUG level logging)'
        )
        parser.add_argument(
            '-q', '--quiet',
            action='store_true',
            help='Minimal output (only errors)'
        )

        # Output settings
        parser.add_argument(
            '--output',
            metavar='PATH',
            help='Output file path'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'csv'],
            default='json',
            help='Output format (default: json)'
        )

    @staticmethod
    def parse_filters(filter_args: Optional[List[str]]) -> Dict[str, str]:
        """
        Parse filter arguments into a dictionary.

        Args:
            filter_args: List of filter strings in "key:value" format

        Returns:
            Dictionary mapping filter keys to values

        Example:
            >>> parse_filters(['category:IT', 'number:KB0001'])
            {'category': 'IT', 'number': 'KB0001'}
        """
        if not filter_args:
            return {}

        filters = {}
        for f in filter_args:
            if ':' in f:
                key, value = f.split(':', 1)
                filters[key.strip()] = value.strip()
            else:
                logging.warning(f"Invalid filter format (expected 'key:value'): {f}")

        return filters

    @staticmethod
    def setup_logging(verbose: bool = False, quiet: bool = False, log_prefix: str = 'migration') -> None:
        """
        Setup logging configuration based on verbosity flags.

        Args:
            verbose: Enable DEBUG level logging
            quiet: Enable ERROR level logging only
            log_prefix: Prefix for log filename (e.g., 'migration', 'post_processing')
        """
        from pathlib import Path
        from datetime import datetime

        if quiet:
            level = logging.ERROR
        elif verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO

        # Create logs directory
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)

        # Create log file path with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'{log_prefix}_{timestamp}.log'

        # Configure logging to both file and console
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        # Log the file location
        logging.getLogger(__name__).info(f"Logging to: {log_file}")

    @staticmethod
    def apply_limit_offset(items: List[Any], limit: Optional[int] = None, offset: int = 0) -> List[Any]:
        """
        Apply limit and offset to a list of items.

        Args:
            items: List of items to slice
            limit: Maximum number of items to return (None = no limit)
            offset: Number of items to skip from beginning

        Returns:
            Sliced list of items

        Example:
            >>> items = [1, 2, 3, 4, 5]
            >>> apply_limit_offset(items, limit=2, offset=1)
            [2, 3]
        """
        if offset > 0:
            items = items[offset:]

        if limit is not None and limit > 0:
            items = items[:limit]

        return items

    @staticmethod
    def filter_articles(
        articles: List[Dict[str, Any]],
        filters: Dict[str, str],
        kb_base: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter articles based on criteria.

        Args:
            articles: List of article dictionaries
            filters: Filter criteria (key-value pairs)
            kb_base: Knowledge base ID to filter by

        Returns:
            Filtered list of articles

        Supported filter keys:
            - category: Article category (partial match)
            - number: Article number (exact match)
            - workflow_state: Workflow state (exact match)
            - language: Language code (exact match)

        Example:
            >>> articles = [{'number': 'KB0001', 'category': 'IT'}]
            >>> filter_articles(articles, {'category': 'IT'})
            [{'number': 'KB0001', 'category': 'IT'}]
        """
        filtered = articles

        # Apply kb_base filter
        if kb_base:
            filtered = [a for a in filtered if a.get('kb_knowledge_base') == kb_base]

        # Apply custom filters
        for key, value in filters.items():
            if key == 'category':
                # Category partial match (case-insensitive)
                filtered = [
                    a for a in filtered
                    if value.lower() in a.get('kb_category', '').lower()
                ]
            elif key == 'number':
                # Number exact match
                filtered = [
                    a for a in filtered
                    if a.get('number', '') == value
                ]
            elif key == 'workflow_state':
                # Workflow state exact match
                filtered = [
                    a for a in filtered
                    if a.get('workflow_state', '') == value
                ]
            elif key == 'language':
                # Language exact match
                filtered = [
                    a for a in filtered
                    if a.get('language', '') == value
                ]
            else:
                logging.warning(f"Unknown filter key: {key}")

        return filtered

    @staticmethod
    def confirm_action(message: str, default: bool = False) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Confirmation message
            default: Default response if user just presses Enter

        Returns:
            True if user confirmed, False otherwise

        Example:
            >>> if confirm_action("Delete all files?", default=False):
            ...     delete_files()
        """
        if default:
            prompt = f"{message} [Y/n]: "
        else:
            prompt = f"{message} [y/N]: "

        while True:
            response = input(prompt).strip().lower()

            if response == '':
                return default
            elif response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Please answer 'y' or 'n'")

    @staticmethod
    def print_summary(
        title: str,
        items: List[Dict[str, Any]],
        key_fields: List[str],
        max_items: int = 10
    ) -> None:
        """
        Print a summary of items with key fields.

        Args:
            title: Summary title
            items: List of item dictionaries
            key_fields: Fields to display for each item
            max_items: Maximum number of items to display

        Example:
            >>> items = [{'number': 'KB0001', 'title': 'Test'}]
            >>> print_summary("Articles", items, ['number', 'title'])
        """
        print()
        print("=" * 80)
        print(title)
        print("=" * 80)
        print(f"Total items: {len(items)}")
        print()

        if not items:
            print("No items to display")
            return

        # Display up to max_items
        display_items = items[:max_items]

        for i, item in enumerate(display_items, 1):
            fields = []
            for field in key_fields:
                value = item.get(field, 'N/A')
                # Truncate long values
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + '...'
                fields.append(f"{field}: {value}")

            print(f"{i}. {' | '.join(fields)}")

        if len(items) > max_items:
            print(f"\n... and {len(items) - max_items} more items")

        print()


def create_base_parser(description: str) -> argparse.ArgumentParser:
    """
    Create a base argument parser with common settings.

    Args:
        description: Description of the command

    Returns:
        Configured ArgumentParser instance

    Example:
        >>> parser = create_base_parser("Export articles")
        >>> parser.add_argument('--custom', help='Custom argument')
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    return parser
