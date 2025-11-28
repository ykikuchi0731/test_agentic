"""Create category hierarchy in Notion database based on article list."""
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from post_processing.page_hierarchy import NotionPageHierarchy

logger = logging.getLogger(__name__)


class CategoryOrganizer:
    """
    Build category hierarchy in Notion database from article list CSV.

    Process:
    1. Read article list CSV and extract unique category paths
    2. Build category tree structure from paths (e.g., "IT > FAQ" -> parent-child)
    3. Create blank Notion pages for each category
    4. Establish parent-child relationships using Sub-items feature

    Performance optimizations:
    - Cache parent property ID (fetch once, reuse for all relationships)
    - Cache created page IDs immediately after creation
    - Bulk operations with minimal API calls

    Example:
        organizer = CategoryOrganizer(
            api_key="secret_xxx",
            database_id="abc123",
            csv_path="article_list.csv"
        )

        result = organizer.build_category_hierarchy()
        print(f"Created {result['categories_created']} category pages")
    """

    def __init__(
        self,
        api_key: str,
        database_id: str,
        csv_path: Optional[str] = None,
        dry_run: bool = False,
        output_dir: str = "./migration_output"
    ):
        """
        Initialize category organizer.

        Args:
            api_key: Notion integration API key
            database_id: Target Notion database ID
            csv_path: Path to article list CSV file (optional)
            dry_run: If True, preview operations without creating pages
            output_dir: Directory to save output CSV files
        """
        self.api_key = api_key
        self.database_id = database_id
        self.csv_path = csv_path
        self.dry_run = dry_run
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.hierarchy = NotionPageHierarchy(api_key)
        self.category_pages: Dict[str, str] = {}  # category_path -> page_id

        # Performance optimization: cache parent property ID
        self._parent_property_id: Optional[str] = None

        logger.info(f"Category organizer initialized (dry_run={dry_run})")

    def _get_parent_property_id(self) -> Optional[str]:
        """
        Get parent property ID with caching.
        Fetch once from database, then reuse for all subsequent operations.

        Returns:
            Parent property ID or None if not found
        """
        if self._parent_property_id is None:
            logger.info("Fetching parent property ID (first time only)")
            self._parent_property_id = self.hierarchy.find_parent_item_property(self.database_id)

            if self._parent_property_id:
                logger.info(f"✅ Cached parent property ID: {self._parent_property_id}")
            else:
                logger.warning("⚠️  Parent property not found - Sub-items feature may not be enabled")

        return self._parent_property_id

    def extract_category_paths_from_csv(
        self,
        csv_path: Optional[str] = None
    ) -> List[str]:
        """
        Extract unique category paths from article list CSV.

        Args:
            csv_path: Path to CSV file (uses self.csv_path if not provided)

        Returns:
            List of unique category paths sorted by depth (parent categories first)
        """
        csv_path = csv_path or self.csv_path
        if not csv_path:
            raise ValueError("csv_path must be provided either in __init__ or method call")

        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        logger.info(f"Reading category paths from {csv_path}")

        category_paths = set()

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                category_path = row.get('category_path', '').strip()
                if category_path:
                    # Normalize: remove extra spaces around separators
                    normalized_path = ' > '.join([p.strip() for p in category_path.split(' > ')])
                    category_paths.add(normalized_path)

        # Sort by depth (number of separators) to ensure parents are created first
        sorted_paths = sorted(
            category_paths,
            key=lambda p: (p.count(' > '), p)
        )

        logger.info(f"Found {len(sorted_paths)} unique category paths")
        return sorted_paths

    def parse_category_tree(
        self,
        category_paths: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Parse category paths into a tree structure.

        Args:
            category_paths: List of category paths (e.g., ["IT > FAQ", "IT > 使い方"])

        Returns:
            Dictionary representing category tree with metadata
        """
        logger.info("Parsing category tree structure")

        tree = {}

        for path in category_paths:
            parts = [p.strip() for p in path.split(' > ')]

            # Build each level of the path
            for i in range(len(parts)):
                current_path = ' > '.join(parts[:i+1])

                if current_path not in tree:
                    parent_path = ' > '.join(parts[:i]) if i > 0 else None

                    tree[current_path] = {
                        'full_path': current_path,
                        'name': parts[i],
                        'parent_path': parent_path,
                        'depth': i,
                        'children': []
                    }

                    # Add to parent's children list
                    if parent_path and parent_path in tree:
                        if current_path not in tree[parent_path]['children']:
                            tree[parent_path]['children'].append(current_path)

        logger.info(f"Built tree with {len(tree)} category nodes")
        return tree

    def create_category_page(
        self,
        category_name: str,
        category_path: str
    ) -> Optional[str]:
        """
        Create a blank Notion page for a category in the database.

        Args:
            category_name: Display name for the category (e.g., "FAQ")
            category_path: Full path for uniqueness (e.g., "IT > FAQ")

        Returns:
            Page ID of created page, or None if dry_run or error
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create category page: {category_name} ({category_path})")
            return f"dry_run_page_{hash(category_path)}"

        logger.info(f"Creating category page: {category_name}")

        try:
            import requests

            url = "https://api.notion.com/v1/pages"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }

            payload = {
                "parent": {
                    "database_id": self.database_id
                },
                "properties": {
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": category_name
                                }
                            }
                        ]
                    }
                }
            }

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            page = response.json()
            page_id = page.get('id')

            logger.info(f"✅ Created category page '{category_name}' (ID: {page_id})")

            # Cache immediately after creation
            self.category_pages[category_path] = page_id

            return page_id

        except Exception as e:
            logger.error(f"Failed to create category page '{category_name}': {e}")
            return None

    def build_category_hierarchy(
        self,
        csv_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build complete category hierarchy in Notion database with performance optimizations.

        This is the main method that:
        1. Extracts category paths from CSV
        2. Parses them into a tree structure
        3. Creates Notion pages for each category
        4. Establishes parent-child relationships (optimized with property caching)

        Args:
            csv_path: Path to article list CSV (uses self.csv_path if not provided)

        Returns:
            Result dictionary with created categories and CSV export path
        """
        logger.info("=" * 80)
        logger.info("Building category hierarchy in Notion")
        logger.info("=" * 80)

        result = {
            'success': False,
            'categories_created': 0,
            'relationships_created': 0,
            'category_pages': {},
            'csv_export_path': None,
            'errors': [],
            'tree': {}
        }

        try:
            # Step 1: Extract category paths from CSV
            logger.info("Step 1: Extracting category paths from CSV")
            category_paths = self.extract_category_paths_from_csv(csv_path)

            if not category_paths:
                logger.warning("No category paths found in CSV")
                result['success'] = True
                return result

            logger.info(f"Found {len(category_paths)} unique categories")

            # Step 2: Parse into tree structure
            logger.info("Step 2: Parsing category tree structure")
            tree = self.parse_category_tree(category_paths)
            result['tree'] = tree

            # Step 3: Cache parent property ID (PERFORMANCE OPTIMIZATION)
            logger.info("Step 3: Caching database parent property ID")
            parent_property_id = self._get_parent_property_id()
            if not parent_property_id and not self.dry_run:
                logger.warning("⚠️  Could not find parent property - relationships may fail")

            # Step 4: Create Notion pages for each category
            logger.info("Step 4: Creating Notion pages for categories")
            logger.info("-" * 80)

            # Sort tree paths by depth to ensure parents are created first
            all_tree_paths = sorted(
                tree.keys(),
                key=lambda p: (p.count(' > '), p)
            )

            for i, category_path in enumerate(all_tree_paths, 1):
                category_info = tree[category_path]
                category_name = category_info['name']

                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(all_tree_paths)} categories created")

                page_id = self.create_category_page(category_name, category_path)

                if page_id:
                    result['categories_created'] += 1
                else:
                    error_msg = f"Failed to create page for category: {category_path}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

            logger.info("-" * 80)
            logger.info(f"Created {result['categories_created']} category pages")

            # Step 5: Establish parent-child relationships (OPTIMIZED)
            logger.info("Step 5: Establishing parent-child relationships")
            logger.info("-" * 80)

            for i, category_path in enumerate(all_tree_paths, 1):
                category_info = tree[category_path]
                parent_path = category_info['parent_path']

                if not parent_path:
                    logger.debug(f"Root category: {category_path}")
                    continue

                child_page_id = self.category_pages.get(category_path)
                parent_page_id = self.category_pages.get(parent_path)

                if not child_page_id or not parent_page_id:
                    error_msg = f"Missing page IDs for relationship: {category_path} -> {parent_path}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    continue

                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(all_tree_paths)} relationships processed")

                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would make '{category_path}' "
                        f"a sub-item of '{parent_path}'"
                    )
                    result['relationships_created'] += 1
                else:
                    # Create parent-child relationship with optimized call
                    logger.debug(f"Making '{category_path}' a sub-item of '{parent_path}'")

                    # PERFORMANCE: Use pre-cached property ID
                    relation_result = self.hierarchy.make_subitem_optimized(
                        child_page_id=child_page_id,
                        parent_page_id=parent_page_id,
                        parent_property_id=parent_property_id,
                        verify=False
                    )

                    if relation_result['success']:
                        result['relationships_created'] += 1
                    else:
                        error_msg = (
                            f"Failed to create relationship {category_path} -> {parent_path}: "
                            f"{relation_result.get('error')}"
                        )
                        logger.error(error_msg)
                        result['errors'].append(error_msg)

            logger.info("-" * 80)
            logger.info(f"Established {result['relationships_created']} parent-child relationships")

            # Step 6: Export to CSV
            logger.info("Step 6: Exporting category hierarchy to CSV")
            csv_export_path = self.export_category_hierarchy_csv(tree)
            result['csv_export_path'] = csv_export_path
            logger.info(f"✅ CSV exported to: {csv_export_path}")

            # Store category page mapping in result
            result['category_pages'] = self.category_pages.copy()

            # Final summary
            logger.info("=" * 80)
            logger.info("Category Hierarchy Build Complete")
            logger.info("=" * 80)
            logger.info(f"Categories created:     {result['categories_created']}")
            logger.info(f"Relationships created:  {result['relationships_created']}")
            logger.info(f"CSV export:             {csv_export_path}")
            logger.info(f"Errors encountered:     {len(result['errors'])}")
            logger.info("=" * 80)

            result['success'] = len(result['errors']) == 0

            return result

        except Exception as e:
            error_msg = f"Unexpected error building category hierarchy: {e}"
            logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)
            return result

    def export_category_hierarchy_csv(self, tree: Dict[str, Dict[str, Any]]) -> str:
        """
        Export category hierarchy to CSV with page IDs and structure information.

        Args:
            tree: Parsed category tree structure

        Returns:
            Path to created CSV file

        CSV Format:
            category_name, full_path, depth, parent_path, page_id, children_count
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"category_hierarchy_{timestamp}.csv"
        csv_path = self.output_dir / csv_filename

        logger.info(f"Exporting category hierarchy to {csv_path}")

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'category_name',
                'full_path',
                'depth',
                'parent_path',
                'page_id',
                'children_count'
            ])

            # Sort by depth for readability
            sorted_paths = sorted(
                tree.keys(),
                key=lambda p: (p.count(' > '), p)
            )

            for category_path in sorted_paths:
                category_info = tree[category_path]
                page_id = self.category_pages.get(category_path, '')

                writer.writerow([
                    category_info['name'],
                    category_info['full_path'],
                    category_info['depth'],
                    category_info['parent_path'] or '',
                    page_id,
                    len(category_info['children'])
                ])

        logger.info(f"Exported {len(tree)} categories to CSV")
        return str(csv_path)

    def get_category_page_id(self, category_path: str) -> Optional[str]:
        """Get Notion page ID for a category path."""
        return self.category_pages.get(category_path)

    def export_category_mapping(self, output_path: str):
        """
        Export simple category path to page ID mapping as CSV.

        Args:
            output_path: Path to output CSV file
        """
        logger.info(f"Exporting category mapping to {output_path}")

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['category_path', 'page_id'])

            for category_path, page_id in sorted(self.category_pages.items()):
                writer.writerow([category_path, page_id])

        logger.info(f"Exported {len(self.category_pages)} category mappings")


def build_categories_from_csv(
    api_key: str,
    database_id: str,
    csv_path: str,
    dry_run: bool = False,
    output_dir: str = "./migration_output"
) -> Dict[str, Any]:
    """
    Convenience function to build category hierarchy from CSV.

    Args:
        api_key: Notion integration API key
        database_id: Target Notion database ID
        csv_path: Path to article list CSV
        dry_run: If True, preview without creating pages
        output_dir: Directory to save output CSV files

    Returns:
        Result dictionary from CategoryOrganizer.build_category_hierarchy()
    """
    organizer = CategoryOrganizer(
        api_key=api_key,
        database_id=database_id,
        csv_path=csv_path,
        dry_run=dry_run,
        output_dir=output_dir
    )

    return organizer.build_category_hierarchy()
