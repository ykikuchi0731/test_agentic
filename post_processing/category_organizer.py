"""Create category hierarchy in Notion database based on article list."""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

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
        dry_run: bool = False
    ):
        """
        Initialize category organizer.

        Args:
            api_key: Notion integration API key
            database_id: Target Notion database ID
            csv_path: Path to article list CSV file (optional)
            dry_run: If True, preview operations without creating pages
        """
        self.api_key = api_key
        self.database_id = database_id
        self.csv_path = csv_path
        self.dry_run = dry_run

        self.hierarchy = NotionPageHierarchy(api_key)
        self.category_pages: Dict[str, str] = {}  # category_path -> page_id

        logger.info(f"Category organizer initialized (dry_run={dry_run})")

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

        Example:
            paths = organizer.extract_category_paths_from_csv("article_list.csv")
            # Returns: ["IT", "IT > FAQ", "IT > トラブルシューティング", ...]
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
            Dictionary representing category tree:
            {
                "IT": {
                    "full_path": "IT",
                    "name": "IT",
                    "parent_path": None,
                    "children": ["IT > FAQ", "IT > 使い方"]
                },
                "IT > FAQ": {
                    "full_path": "IT > FAQ",
                    "name": "FAQ",
                    "parent_path": "IT",
                    "children": []
                }
            }
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

        Note:
            This creates a page with just the title. The page hierarchy
            (parent-child relationships) is established separately.
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

            # Create page payload
            # We assume the database has a "Name" or "Title" property
            payload = {
                "parent": {
                    "database_id": self.database_id
                },
                "properties": {
                    "Name": {  # This might need to be adjusted based on actual database schema
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
            return page_id

        except Exception as e:
            logger.error(f"Failed to create category page '{category_name}': {e}")
            return None

    def build_category_hierarchy(
        self,
        csv_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build complete category hierarchy in Notion database.

        This is the main method that:
        1. Extracts category paths from CSV
        2. Parses them into a tree structure
        3. Creates Notion pages for each category
        4. Establishes parent-child relationships

        Args:
            csv_path: Path to article list CSV (uses self.csv_path if not provided)

        Returns:
            Result dictionary:
            {
                'success': bool,
                'categories_created': int,
                'relationships_created': int,
                'category_pages': dict,  # category_path -> page_id mapping
                'errors': list,
                'tree': dict  # The parsed category tree structure
            }

        Example:
            result = organizer.build_category_hierarchy("article_list.csv")

            if result['success']:
                print(f"Created {result['categories_created']} categories")
                print(f"Established {result['relationships_created']} relationships")

                # Access mapping for later use
                it_faq_page_id = result['category_pages']['IT > FAQ']
        """
        logger.info("=" * 80)
        logger.info("Building category hierarchy in Notion")
        logger.info("=" * 80)

        result = {
            'success': False,
            'categories_created': 0,
            'relationships_created': 0,
            'category_pages': {},
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

            # Step 3: Create Notion pages for each category
            # Important: Create pages for ALL nodes in tree (including auto-generated parents)
            logger.info("Step 3: Creating Notion pages for categories")
            logger.info("-" * 80)

            # Sort tree paths by depth to ensure parents are created first
            all_tree_paths = sorted(
                tree.keys(),
                key=lambda p: (p.count(' > '), p)
            )

            for category_path in all_tree_paths:
                category_info = tree[category_path]
                category_name = category_info['name']

                page_id = self.create_category_page(category_name, category_path)

                if page_id:
                    self.category_pages[category_path] = page_id
                    result['categories_created'] += 1
                else:
                    error_msg = f"Failed to create page for category: {category_path}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

            logger.info("-" * 80)
            logger.info(f"Created {result['categories_created']} category pages")

            # Step 4: Establish parent-child relationships
            logger.info("Step 4: Establishing parent-child relationships")
            logger.info("-" * 80)

            for category_path in all_tree_paths:
                category_info = tree[category_path]
                parent_path = category_info['parent_path']

                if not parent_path:
                    # This is a root category (no parent)
                    logger.info(f"Root category: {category_path}")
                    continue

                child_page_id = self.category_pages.get(category_path)
                parent_page_id = self.category_pages.get(parent_path)

                if not child_page_id or not parent_page_id:
                    error_msg = f"Missing page IDs for relationship: {category_path} -> {parent_path}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    continue

                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would make '{category_path}' "
                        f"a sub-item of '{parent_path}'"
                    )
                    result['relationships_created'] += 1
                else:
                    # Create parent-child relationship
                    logger.info(f"Making '{category_path}' a sub-item of '{parent_path}'")

                    relation_result = self.hierarchy.make_subitem(
                        child_page_id=child_page_id,
                        parent_page_id=parent_page_id,
                        verify=False  # Skip verification for performance
                    )

                    if relation_result['success']:
                        result['relationships_created'] += 1
                        logger.info(f"✅ Relationship created")
                    else:
                        error_msg = (
                            f"Failed to create relationship {category_path} -> {parent_path}: "
                            f"{relation_result.get('error')}"
                        )
                        logger.error(error_msg)
                        result['errors'].append(error_msg)

            logger.info("-" * 80)
            logger.info(f"Established {result['relationships_created']} parent-child relationships")

            # Store category page mapping in result
            result['category_pages'] = self.category_pages.copy()

            # Final summary
            logger.info("=" * 80)
            logger.info("Category Hierarchy Build Complete")
            logger.info("=" * 80)
            logger.info(f"Categories created:     {result['categories_created']}")
            logger.info(f"Relationships created:  {result['relationships_created']}")
            logger.info(f"Errors encountered:     {len(result['errors'])}")
            logger.info("=" * 80)

            result['success'] = len(result['errors']) == 0

            return result

        except Exception as e:
            error_msg = f"Unexpected error building category hierarchy: {e}"
            logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)
            return result

    def get_category_page_id(self, category_path: str) -> Optional[str]:
        """
        Get Notion page ID for a category path.

        Args:
            category_path: Full category path (e.g., "IT > FAQ")

        Returns:
            Page ID if found, None otherwise
        """
        return self.category_pages.get(category_path)

    def export_category_mapping(self, output_path: str):
        """
        Export category path to page ID mapping as CSV.

        Args:
            output_path: Path to output CSV file

        Example:
            organizer.export_category_mapping("category_mapping.csv")
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
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to build category hierarchy from CSV.

    Args:
        api_key: Notion integration API key
        database_id: Target Notion database ID
        csv_path: Path to article list CSV
        dry_run: If True, preview without creating pages

    Returns:
        Result dictionary from CategoryOrganizer.build_category_hierarchy()

    Example:
        from config import Config

        result = build_categories_from_csv(
            api_key=Config.NOTION_API_KEY,
            database_id=Config.NOTION_DATABASE_ID,
            csv_path="migration_output/article_list.csv",
            dry_run=False
        )

        if result['success']:
            print(f"Created {result['categories_created']} categories")
    """
    organizer = CategoryOrganizer(
        api_key=api_key,
        database_id=database_id,
        csv_path=csv_path,
        dry_run=dry_run
    )

    return organizer.build_category_hierarchy()
