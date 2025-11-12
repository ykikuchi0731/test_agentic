"""Post-import organization: Move pages into database with category hierarchy."""
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class NotionPostImport:
    """Handle post-import organization of Notion pages into an existing database structure."""

    def __init__(self, api_key: str):
        """
        Initialize Notion post-import organizer.

        Args:
            api_key: Notion integration API key

        Note:
            This class assumes you already have a database created in Notion.
            The database should have the following properties:
            - Title (title)
            - Type (select: Category/Article)
            - Article Number (rich_text)
            - Category Path (rich_text)
            - Parent Task (relation to same database)
            - Sub-tasks (relation to same database)
            - Original Page ID (rich_text)
            - Status (select: Published/Draft/Archived)
            - Created Date (date)
            - Updated Date (date)
        """
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        logger.info("Notion post-import organizer initialized")

    def create_category_page(
        self,
        database_id: str,
        category_name: str,
        category_path: List[str],
        parent_page_id: Optional[str] = None,
    ) -> str:
        """
        Create a category page in the database.

        Args:
            database_id: Target database ID
            category_name: Name of the category
            category_path: Full path as list (e.g., ['IT', 'Applications', 'Figma'])
            parent_page_id: Parent category page ID (for Sub-tasks relation)

        Returns:
            Created page ID
        """
        logger.info(f"Creating category page: {category_name}")

        properties = {
            "Title": {"title": [{"text": {"content": category_name}}]},
            "Type": {"select": {"name": "Category"}},
            "Category Path": {"rich_text": [{"text": {"content": " > ".join(category_path)}}]},
            "Status": {"select": {"name": "Published"}},
        }

        # Add parent relation if provided
        if parent_page_id:
            properties["Parent Task"] = {"relation": [{"id": parent_page_id}]}

        payload = {"parent": {"database_id": database_id}, "properties": properties}

        response = requests.post(
            f"{self.base_url}/pages", headers=self.headers, json=payload
        )
        response.raise_for_status()
        page = response.json()
        page_id = page["id"]

        logger.info(f"✅ Category page created: {page_id}")
        return page_id

    def build_category_hierarchy(
        self, database_id: str, category_paths: List[List[str]]
    ) -> Dict[str, str]:
        """
        Build complete category hierarchy in database.

        Args:
            database_id: Target database ID
            category_paths: List of category paths, e.g.:
                [['IT', 'Applications', 'Figma'],
                 ['IT', 'Applications', 'Slack'],
                 ['Office', 'Tokyo']]

        Returns:
            Dictionary mapping category path (joined with '>') to page ID
        """
        logger.info(f"Building category hierarchy with {len(category_paths)} paths")

        # Collect all unique categories at each level
        all_categories = set()
        for path in category_paths:
            for i in range(1, len(path) + 1):
                all_categories.add(tuple(path[:i]))

        # Sort by depth (root categories first)
        sorted_categories = sorted(all_categories, key=len)

        category_map = {}

        for category_path in sorted_categories:
            path_key = " > ".join(category_path)

            if path_key in category_map:
                continue  # Already created

            category_name = category_path[-1]

            # Find parent
            parent_page_id = None
            if len(category_path) > 1:
                parent_path = category_path[:-1]
                parent_key = " > ".join(parent_path)
                parent_page_id = category_map.get(parent_key)

            # Create category page
            page_id = self.create_category_page(
                database_id=database_id,
                category_name=category_name,
                category_path=list(category_path),
                parent_page_id=parent_page_id,
            )

            category_map[path_key] = page_id

        logger.info(f"✅ Created {len(category_map)} category pages")
        return category_map

    def move_page_to_database(
        self,
        page_id: str,
        data_source_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        """
        Move a page into a database using the Move Page API.

        Args:
            page_id: Page ID to move
            data_source_id: Database data_source_id (typically the same as database_id)
            properties: Properties to set on the page after moving

        Returns:
            Success status

        Note: This uses the Move Page API documented at:
        https://dev.notion.so/notion/Move-page-299b35e6e67f81578c33c1d8d7f79f9d

        The API requires:
        - Endpoint: POST /v1/pages/{page_id}/move
        - Parent must use data_source_id (not database_id)
        """
        logger.info(f"Moving page {page_id} to database {data_source_id}")

        # Use correct move endpoint
        move_url = f"{self.base_url}/pages/{page_id}/move"

        # Correct payload structure according to API documentation
        payload = {
            "parent": {
                "type": "data_source_id",
                "data_source_id": data_source_id,
            }
        }

        try:
            # First, move the page to the database
            response = requests.post(move_url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info(f"✅ Page moved to database successfully: {page_id}")

            # Then, update the page properties
            if properties:
                update_url = f"{self.base_url}/pages/{page_id}"
                update_payload = {"properties": properties}

                update_response = requests.patch(
                    update_url,
                    headers=self.headers,
                    json=update_payload
                )
                update_response.raise_for_status()
                logger.info(f"✅ Page properties updated successfully: {page_id}")

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to move page {page_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False

    def organize_imported_articles(
        self,
        data_source_id: str,
        articles: List[Dict[str, Any]],
        category_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Organize imported articles into database with proper hierarchy.

        Args:
            data_source_id: Target database data_source_id (typically the same as database_id)
            articles: List of article info with:
                - page_id: Imported Notion page ID
                - title: Article title
                - article_number: KB number (optional)
                - category_path: List of category names (optional)
            category_map: Dictionary mapping category path to page ID (optional)
                If not provided, articles will be added without category linking

        Returns:
            Results summary

        Process:
            1. For each article, find its parent category (if category_map provided)
            2. Move page to database
            3. Set properties (title, article number, category, parent task)
            4. Link to parent category via Parent Task relation (if category exists)
        """
        logger.info(f"Organizing {len(articles)} imported articles into database {data_source_id}")

        results = {"success": 0, "failed": 0, "errors": []}
        category_map = category_map or {}

        for i, article in enumerate(articles, 1):
            try:
                page_id = article["page_id"]
                title = article["title"]
                article_number = article.get("article_number", "")
                category_path = article.get("category_path", [])

                logger.info(f"Processing {i}/{len(articles)}: {article_number}")

                # Find parent category
                parent_page_id = None
                category_path_str = ""
                if category_path:
                    category_path_str = " > ".join(category_path)
                    parent_page_id = category_map.get(category_path_str)

                # Prepare properties
                properties = {
                    "Title": {"title": [{"text": {"content": title}}]},
                    "Type": {"select": {"name": "Article"}},
                    "Article Number": {
                        "rich_text": [{"text": {"content": article_number}}]
                    },
                    "Category Path": {
                        "rich_text": [{"text": {"content": category_path_str}}]
                    },
                    "Status": {"select": {"name": "Published"}},
                    "Original Page ID": {"rich_text": [{"text": {"content": page_id}}]},
                }

                # Add parent relation if category exists
                if parent_page_id:
                    properties["Parent Task"] = {"relation": [{"id": parent_page_id}]}

                # Move page to database
                success = self.move_page_to_database(
                    page_id=page_id,
                    data_source_id=data_source_id,
                    properties=properties,
                )

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to move {article_number}")

            except Exception as e:
                logger.error(f"Error organizing article {article.get('title', 'unknown')}: {e}")
                results["failed"] += 1
                results["errors"].append(str(e))

        logger.info(
            f"✅ Organization complete: {results['success']} success, {results['failed']} failed"
        )
        return results

    def get_page_info(self, page_id: str) -> Dict[str, Any]:
        """
        Get page information from Notion.

        Args:
            page_id: Notion page ID

        Returns:
            Page information including title and properties
        """
        response = requests.get(
            f"{self.base_url}/pages/{page_id}", headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_pages_in_parent(self, parent_page_id: str) -> List[Dict[str, Any]]:
        """
        List all pages under a parent page (useful after Notion import).

        Args:
            parent_page_id: Parent page ID

        Returns:
            List of page information

        Note: This requires searching, as there's no direct API for this.
        You'll need to manually collect page IDs after import.
        """
        # This is a placeholder - Notion API doesn't directly support listing children
        # Users will need to provide page IDs manually or via export
        logger.warning(
            "Notion API doesn't support listing page children directly. "
            "You'll need to collect page IDs manually after import."
        )
        return []

