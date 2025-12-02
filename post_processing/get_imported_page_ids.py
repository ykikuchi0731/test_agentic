"""Get page IDs of imported Notion pages that start with 'KB'.

This module retrieves page IDs and titles of pages that were imported from ServiceNow
Knowledge Base articles (which have KB numbers like KB0010400).

Usage:
    python -m post_processing get-imported-pages --parent-pages <id1>,<id2>
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import csv

import requests

logger = logging.getLogger(__name__)


class ImportedPageFetcher:
    """Fetch imported page IDs from Notion parent pages."""

    def __init__(self, api_key: str):
        """
        Initialize imported page fetcher.

        Args:
            api_key: Notion integration API key
        """
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        logger.info("Imported page fetcher initialized")

    def get_children_pages(
        self,
        parent_page_id: str,
        filter_prefix: str = "KB"
    ) -> List[Dict[str, str]]:
        """
        Get children pages of a parent page, filtered by title prefix.

        Uses pagination to retrieve all children pages.

        Args:
            parent_page_id: Parent page ID to get children from
            filter_prefix: Only include pages whose title starts with this prefix

        Returns:
            List of dicts with 'page_id' and 'page_title' keys
        """
        logger.info(f"Fetching children pages from parent: {parent_page_id}")

        all_pages = []
        start_cursor = None
        has_more = True
        page_count = 0

        while has_more:
            # Build request params
            params = {
                "page_size": 100  # Max allowed by Notion API
            }
            if start_cursor:
                params["start_cursor"] = start_cursor

            # Get children blocks (which includes child pages)
            response = requests.get(
                f"{self.base_url}/blocks/{parent_page_id}/children",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Filter for child_page blocks with KB prefix
            for block in results:
                if block.get("type") == "child_page":
                    page_id = block.get("id")
                    title = block.get("child_page", {}).get("title", "")

                    # Check if title starts with prefix
                    if title.startswith(filter_prefix):
                        # Remove hyphens from page_id
                        page_id_no_hyphens = page_id.replace("-", "")

                        all_pages.append({
                            "page_id": page_id_no_hyphens,
                            "page_title": title
                        })
                        page_count += 1

            # Check pagination
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            logger.debug(
                f"Retrieved {len(results)} blocks, "
                f"found {page_count} KB pages so far, "
                f"has_more: {has_more}"
            )

        logger.info(
            f"Found {len(all_pages)} pages starting with '{filter_prefix}' "
            f"under parent {parent_page_id}"
        )
        return all_pages

    def get_imported_pages_from_multiple_parents(
        self,
        parent_page_ids: List[str],
        filter_prefix: str = "KB"
    ) -> List[Dict[str, str]]:
        """
        Get children pages from multiple parent pages.

        Args:
            parent_page_ids: List of parent page IDs
            filter_prefix: Only include pages whose title starts with this prefix

        Returns:
            Combined list of all pages from all parents
        """
        all_pages = []

        for parent_id in parent_page_ids:
            try:
                pages = self.get_children_pages(parent_id, filter_prefix)
                all_pages.extend(pages)
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch children from {parent_id}: {e}")
                continue

        logger.info(
            f"Total pages found across {len(parent_page_ids)} parents: {len(all_pages)}"
        )
        return all_pages

    def save_to_csv(
        self,
        pages: List[Dict[str, str]],
        output_dir: Path
    ) -> Path:
        """
        Save page IDs to CSV file.

        Args:
            pages: List of page dicts with page_id and page_title
            output_dir: Directory to save the CSV file

        Returns:
            Path to created CSV file
        """
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"imported_page_ids_{timestamp}.csv"
        output_path = output_dir / filename

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["page_id", "page_title"])
            writer.writeheader()
            writer.writerows(pages)

        logger.info(f"Saved {len(pages)} page IDs to: {output_path}")
        return output_path


def parse_parent_page_ids(parent_pages_str: str) -> List[str]:
    """
    Parse comma-separated parent page IDs.

    Args:
        parent_pages_str: Comma-separated page IDs like "abc123,def456"

    Returns:
        List of page IDs
    """
    return [pid.strip() for pid in parent_pages_str.split(",") if pid.strip()]


def main(
    parent_page_ids: str,
    api_key: str,
    output_dir: Path,
    filter_prefix: str = "KB",
    max_workers: int = 4
) -> Path:
    """
    Main function to get imported page IDs.

    Args:
        parent_page_ids: Comma-separated parent page IDs
        api_key: Notion API key
        output_dir: Directory to save output CSV
        filter_prefix: Only include pages starting with this prefix
        max_workers: Number of concurrent workers (for future threading)

    Returns:
        Path to output CSV file
    """
    # Parse parent page IDs
    parent_ids = parse_parent_page_ids(parent_page_ids)
    logger.info(f"Processing {len(parent_ids)} parent page(s)")

    # Initialize fetcher
    fetcher = ImportedPageFetcher(api_key=api_key)

    # Get all pages
    pages = fetcher.get_imported_pages_from_multiple_parents(
        parent_page_ids=parent_ids,
        filter_prefix=filter_prefix
    )

    # Save to CSV
    output_path = fetcher.save_to_csv(pages, output_dir)

    return output_path
