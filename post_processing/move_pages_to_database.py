"""Move imported Notion pages to a target database.

This module moves pages from their current location to a target database using
Notion's page move API. All operations are logged for troubleshooting.

Usage:
    python -m post_processing move-pages --database <id> --pages-csv <file>
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import time

import requests

logger = logging.getLogger(__name__)


class PageMover:
    """Move pages to a target database using Notion's page move API."""

    def __init__(self, api_key: str):
        """
        Initialize page mover.

        Args:
            api_key: Notion integration API key
        """
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2025-09-03",
        }
        self._database_cache = {}
        logger.info("Page mover initialized")

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """
        Get database information including data_source_id.

        Args:
            database_id: Notion database ID

        Returns:
            Database object from Notion API

        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        # Check cache first
        if database_id in self._database_cache:
            logger.debug(f"Using cached database info for {database_id}")
            return self._database_cache[database_id]

        logger.info(f"Fetching database info: {database_id}")

        response = requests.get(
            f"{self.base_url}/databases/{database_id}",
            headers=self.headers
        )
        response.raise_for_status()

        database = response.json()
        self._database_cache[database_id] = database
        logger.debug(f"Database retrieved: {database.get('id')}")
        return database

    def get_data_source_id(self, database_id: str) -> str:
        """
        Get data_source_id from database_id.

        The page move API requires data_source_id (not database_id) when moving
        pages into a database.

        With Notion API 2025-09-03, the database response includes a data_sources
        array with data source information.

        Args:
            database_id: Notion database ID

        Returns:
            data_source_id from database response

        Raises:
            ValueError: If data_sources field is not in database response or is empty
        """
        database = self.get_database(database_id)

        # Get data_source_id from data_sources array
        # (Available in Notion API 2025-09-03+)
        if "data_sources" not in database:
            raise ValueError(
                f"Database {database_id} does not have data_sources field. "
                "Make sure you're using Notion API version 2025-09-03 or later."
            )

        data_sources = database["data_sources"]
        if not data_sources or len(data_sources) == 0:
            raise ValueError(
                f"Database {database_id} has empty data_sources array."
            )

        # Get the first data source ID
        data_source_id = data_sources[0]["id"]
        # Remove hyphens if present
        data_source_id = data_source_id.replace("-", "")
        logger.info(f"Got data_source_id from database response: {data_source_id}")
        return data_source_id

    def move_page_to_database(
        self,
        page_id: str,
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        Move a page to a database.

        Args:
            page_id: Page ID to move (can be with or without hyphens)
            data_source_id: Database data_source_id (can be with or without hyphens)

        Returns:
            Dict with keys:
                - success: bool
                - page_id: str
                - error: str (if success=False)
                - response: dict (if success=True)
        """
        # Remove hyphens from IDs if present
        page_id_clean = page_id.replace("-", "")
        data_source_id_clean = data_source_id.replace("-", "")

        logger.info(f"Moving page {page_id_clean} to database {data_source_id_clean}")

        try:
            # Build request body
            body = {
                "parent": {
                    "type": "data_source_id",
                    "data_source_id": data_source_id_clean
                }
            }

            # Call move API
            response = requests.post(
                f"{self.base_url}/pages/{page_id_clean}/move",
                headers=self.headers,
                json=body
            )

            # Check for errors
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except Exception:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to move page {page_id_clean}: {error_msg}")
                return {
                    "success": False,
                    "page_id": page_id_clean,
                    "error": error_msg
                }

            # Success
            try:
                result = response.json()
            except Exception as e:
                error_msg = f"Failed to parse success response: {str(e)}"
                logger.error(f"Failed to move page {page_id_clean}: {error_msg}")
                return {
                    "success": False,
                    "page_id": page_id_clean,
                    "error": error_msg
                }

            logger.info(f"✅ Successfully moved page {page_id_clean}")
            return {
                "success": True,
                "page_id": page_id_clean,
                "response": result
            }

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Request failed for page {page_id_clean}: {error_msg}")
            return {
                "success": False,
                "page_id": page_id_clean,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error moving page {page_id_clean}: {error_msg}")
            return {
                "success": False,
                "page_id": page_id_clean,
                "error": error_msg
            }

    def move_pages_batch(
        self,
        page_ids: List[str],
        data_source_id: str,
        max_workers: int = 4,
        rate_limit_delay: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Move multiple pages to database with threading.

        Args:
            page_ids: List of page IDs to move
            data_source_id: Target database data_source_id
            max_workers: Maximum concurrent workers
            rate_limit_delay: Delay between requests (seconds)

        Returns:
            List of result dicts from move_page_to_database
        """
        logger.info(f"Moving {len(page_ids)} pages with {max_workers} workers")

        results = []

        if max_workers == 1:
            # Sequential processing
            for page_id in page_ids:
                result = self.move_page_to_database(page_id, data_source_id)
                results.append(result)
                time.sleep(rate_limit_delay)
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_page = {
                    executor.submit(
                        self.move_page_to_database,
                        page_id,
                        data_source_id
                    ): page_id
                    for page_id in page_ids
                }

                # Collect results as they complete
                for future in as_completed(future_to_page):
                    page_id = future_to_page[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Exception moving page {page_id}: {e}")
                        results.append({
                            "success": False,
                            "page_id": page_id,
                            "error": str(e)
                        })

                    # Rate limiting
                    time.sleep(rate_limit_delay)

        # Log summary
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count
        logger.info(f"Move complete: {success_count} success, {fail_count} failed")

        return results


def read_page_ids_from_csv(csv_path: Path) -> List[str]:
    """
    Read page IDs from CSV file.

    Args:
        csv_path: Path to CSV file with 'page_id' column

    Returns:
        List of page IDs

    Raises:
        ValueError: If CSV doesn't have 'page_id' column
    """
    logger.info(f"Reading page IDs from: {csv_path}")

    page_ids = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Check for page_id column
        if "page_id" not in reader.fieldnames:
            raise ValueError(f"CSV must have 'page_id' column. Found: {reader.fieldnames}")

        for row in reader:
            page_id = row.get("page_id", "").strip()
            if page_id:
                page_ids.append(page_id)

    logger.info(f"Read {len(page_ids)} page IDs from CSV")
    return page_ids


def write_results_log(
    results: List[Dict[str, Any]],
    output_dir: Path
) -> Path:
    """
    Write move operation results to log file.

    Args:
        results: List of result dicts from move operations
        output_dir: Directory to save log file

    Returns:
        Path to log file
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"page_move_results_{timestamp}.log"
    log_path = output_dir / log_filename

    # Write log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"Page Move Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        f.write(f"Total pages: {len(results)}\n")
        f.write(f"Success: {success_count}\n")
        f.write(f"Failed: {fail_count}\n\n")

        f.write("=" * 80 + "\n")
        f.write("Detailed Results\n")
        f.write("=" * 80 + "\n\n")

        for i, result in enumerate(results, 1):
            page_id = result.get("page_id", "unknown")
            success = result.get("success", False)

            f.write(f"{i}. Page ID: {page_id}\n")
            if success:
                f.write("   Status: ✅ SUCCESS\n")
            else:
                error = result.get("error", "Unknown error")
                f.write(f"   Status: ❌ FAILED\n")
                f.write(f"   Error: {error}\n")
            f.write("\n")

    logger.info(f"Results log written to: {log_path}")
    return log_path


def main(
    target_database_id: str,
    pages_csv: Path,
    api_key: str,
    output_dir: Path,
    max_workers: int = 4,
    rate_limit_delay: float = 0.1
) -> List[Dict[str, Any]]:
    """
    Main function to move pages to database.

    Args:
        target_database_id: Target database ID
        pages_csv: Path to CSV file with page_id column
        api_key: Notion API key
        output_dir: Directory to save results log (unused, kept for compatibility)
        max_workers: Number of concurrent workers
        rate_limit_delay: Delay between requests (seconds)

    Returns:
        List of result dicts from move operations
    """
    # Initialize mover
    mover = PageMover(api_key=api_key)

    # Get data_source_id from database_id
    logger.info(f"Getting data_source_id for database: {target_database_id}")
    data_source_id = mover.get_data_source_id(target_database_id)

    # Read page IDs from CSV
    page_ids = read_page_ids_from_csv(pages_csv)

    # Move pages
    results = mover.move_pages_batch(
        page_ids=page_ids,
        data_source_id=data_source_id,
        max_workers=max_workers,
        rate_limit_delay=rate_limit_delay
    )

    return results
