"""Categorize imported pages by moving them under category pages as sub-items."""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from post_processing.page_hierarchy import NotionPageHierarchy

logger = logging.getLogger(__name__)


class PageCategorizer:
    """
    Categorize imported Notion pages by making them sub-items of category pages.

    Process:
    1. Read page list CSV (page_id, category_path)
    2. Read category list CSV (full_path, page_id as category_page_id)
    3. Match pages to categories via category_path
    4. Make each page a sub-item of its category page
    """

    def __init__(
        self,
        api_key: str,
        max_workers: int = 4,
        rate_limit_delay: float = 0.1
    ):
        """
        Initialize page categorizer.

        Args:
            api_key: Notion integration API key
            max_workers: Number of concurrent workers for threading
            rate_limit_delay: Delay between requests (seconds)
        """
        self.api_key = api_key
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.hierarchy = NotionPageHierarchy(api_key)

        logger.info(f"Page categorizer initialized (max_workers={max_workers})")

    def read_page_list_csv(self, csv_path: Path) -> List[Dict[str, str]]:
        """
        Read page list CSV with page_id and category_path columns.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of dicts with page_id and category_path

        Raises:
            ValueError: If required columns are missing
            FileNotFoundError: If CSV file not found
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"Page list CSV not found: {csv_path}")

        logger.info(f"Reading page list from {csv_path}")

        pages = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate required columns
            if "page_id" not in reader.fieldnames or "category_path" not in reader.fieldnames:
                raise ValueError(
                    f"CSV must have 'page_id' and 'category_path' columns. "
                    f"Found: {reader.fieldnames}"
                )

            for row in reader:
                page_id = row.get("page_id", "").strip()
                category_path = row.get("category_path", "").strip()

                if page_id and category_path:
                    pages.append({
                        "page_id": page_id,
                        "category_path": category_path
                    })

        logger.info(f"Read {len(pages)} pages from CSV")
        return pages

    def read_category_list_csv(self, csv_path: Path) -> Dict[str, str]:
        """
        Read category list CSV and build category_path -> category_page_id mapping.

        Args:
            csv_path: Path to CSV file

        Returns:
            Dict mapping category_path (full_path) to category_page_id

        Raises:
            ValueError: If required columns are missing
            FileNotFoundError: If CSV file not found
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"Category list CSV not found: {csv_path}")

        logger.info(f"Reading category list from {csv_path}")

        category_map = {}
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate required columns
            if "full_path" not in reader.fieldnames or "page_id" not in reader.fieldnames:
                raise ValueError(
                    f"CSV must have 'full_path' and 'page_id' columns. "
                    f"Found: {reader.fieldnames}"
                )

            for row in reader:
                full_path = row.get("full_path", "").strip()
                page_id = row.get("page_id", "").strip()

                if full_path and page_id:
                    category_map[full_path] = page_id

        logger.info(f"Read {len(category_map)} categories from CSV")
        return category_map

    def categorize_single_page(
        self,
        page_id: str,
        category_page_id: str,
        category_path: str,
        parent_property_id: str
    ) -> Dict[str, Any]:
        """
        Categorize a single page by making it a sub-item of category page.

        Args:
            page_id: Page ID to categorize
            category_page_id: Category page ID (parent)
            category_path: Category path for logging
            parent_property_id: Pre-cached parent property ID

        Returns:
            Result dict with success status
        """
        logger.debug(f"Categorizing page {page_id} under category '{category_path}'")

        try:
            result = self.hierarchy.make_subitem_optimized(
                child_page_id=page_id,
                parent_page_id=category_page_id,
                parent_property_id=parent_property_id,
                verify=False
            )

            if result["success"]:
                logger.info(f"✅ Page {page_id} categorized under '{category_path}'")
            else:
                logger.error(
                    f"Failed to categorize page {page_id}: {result.get('error')}"
                )

            return {
                "page_id": page_id,
                "category_path": category_path,
                "category_page_id": category_page_id,
                "success": result["success"],
                "error": result.get("error")
            }

        except Exception as e:
            error_msg = f"Exception categorizing page {page_id}: {e}"
            logger.error(error_msg)
            return {
                "page_id": page_id,
                "category_path": category_path,
                "category_page_id": category_page_id,
                "success": False,
                "error": str(e)
            }

    def categorize_pages_batch(
        self,
        pages: List[Dict[str, str]],
        category_map: Dict[str, str],
        database_id: str
    ) -> List[Dict[str, Any]]:
        """
        Categorize multiple pages with threading.

        Args:
            pages: List of page dicts with page_id and category_path
            category_map: Dict mapping category_path to category_page_id
            database_id: Database ID to get parent property

        Returns:
            List of result dicts
        """
        logger.info("=" * 80)
        logger.info(f"Categorizing {len(pages)} pages")
        logger.info("=" * 80)

        # Get parent property ID once (performance optimization)
        logger.info("Fetching parent property ID from database")
        parent_property_id = self.hierarchy.find_parent_item_property(database_id)

        if not parent_property_id:
            raise ValueError(
                f"Could not find 'Parent item' property in database {database_id}. "
                "Make sure Sub-items feature is enabled."
            )

        logger.info(f"✅ Using parent property ID: {parent_property_id}")

        # Build list of categorization tasks
        tasks = []
        skipped = 0

        for page in pages:
            page_id = page["page_id"]
            category_path = page["category_path"]

            # Find category page ID
            category_page_id = category_map.get(category_path)

            if not category_page_id:
                logger.warning(
                    f"Category '{category_path}' not found in category list. "
                    f"Skipping page {page_id}"
                )
                skipped += 1
                continue

            tasks.append({
                "page_id": page_id,
                "category_page_id": category_page_id,
                "category_path": category_path,
                "parent_property_id": parent_property_id
            })

        if skipped > 0:
            logger.warning(f"Skipped {skipped} pages with unknown categories")

        logger.info(f"Categorizing {len(tasks)} pages with {self.max_workers} workers")

        # Execute with threading
        results = []

        if self.max_workers == 1:
            # Sequential processing
            for i, task in enumerate(tasks, 1):
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(tasks)} pages categorized")

                result = self.categorize_single_page(**task)
                results.append(result)
                time.sleep(self.rate_limit_delay)
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self.categorize_single_page, **task): task
                    for task in tasks
                }

                completed = 0
                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1

                        if completed % 10 == 0 or completed == len(tasks):
                            logger.info(f"Progress: {completed}/{len(tasks)} pages processed")

                    except Exception as e:
                        logger.error(f"Exception processing page {task['page_id']}: {e}")
                        results.append({
                            "page_id": task["page_id"],
                            "category_path": task["category_path"],
                            "category_page_id": task["category_page_id"],
                            "success": False,
                            "error": str(e)
                        })

                    # Rate limiting
                    time.sleep(self.rate_limit_delay)

        # Summary
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        logger.info("=" * 80)
        logger.info("Categorization Complete")
        logger.info("=" * 80)
        logger.info(f"Total pages: {len(results)}")
        logger.info(f"Success: {success_count}")
        logger.info(f"Failed: {fail_count}")
        logger.info(f"Skipped (no category match): {skipped}")
        logger.info("=" * 80)

        return results

    def categorize_pages(
        self,
        page_list_csv: Path,
        category_list_csv: Path,
        database_id: str
    ) -> List[Dict[str, Any]]:
        """
        Main function to categorize pages.

        Args:
            page_list_csv: Path to page list CSV (page_id, category_path)
            category_list_csv: Path to category list CSV (full_path, page_id)
            database_id: Database ID where pages and categories exist

        Returns:
            List of result dicts
        """
        # Read CSVs
        pages = self.read_page_list_csv(page_list_csv)
        category_map = self.read_category_list_csv(category_list_csv)

        # Categorize pages
        results = self.categorize_pages_batch(pages, category_map, database_id)

        return results


def main(
    page_list_csv: Path,
    category_list_csv: Path,
    database_id: str,
    api_key: str,
    max_workers: int = 4,
    rate_limit_delay: float = 0.1
) -> List[Dict[str, Any]]:
    """
    Main function to categorize pages.

    Args:
        page_list_csv: Path to page list CSV (page_id, category_path)
        category_list_csv: Path to category list CSV (full_path, page_id)
        database_id: Database ID where pages and categories exist
        api_key: Notion API key
        max_workers: Number of concurrent workers
        rate_limit_delay: Delay between requests (seconds)

    Returns:
        List of result dicts
    """
    categorizer = PageCategorizer(
        api_key=api_key,
        max_workers=max_workers,
        rate_limit_delay=rate_limit_delay
    )

    return categorizer.categorize_pages(
        page_list_csv=page_list_csv,
        category_list_csv=category_list_csv,
        database_id=database_id
    )
