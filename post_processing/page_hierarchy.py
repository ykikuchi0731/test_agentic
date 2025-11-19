"""Manage page hierarchy in Notion - create parent-child (sub-item) relationships between database pages."""
import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class NotionPageHierarchy:
    """Manage parent-child (sub-item) relationships between Notion database pages.

    Note: This works with database pages that have the "Sub-items" feature enabled.
    Notion auto-creates a self-relation with "Parent item" and "Sub-items" properties.
    """

    def __init__(self, api_key: str):
        """
        Initialize Notion page hierarchy manager.

        Args:
            api_key: Notion integration API key

        Example:
            hierarchy = NotionPageHierarchy(api_key="secret_xxx")
            result = hierarchy.make_subitem(
                child_page_id="abc123",
                parent_page_id="def456"
            )
        """
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self._database_cache = {}  # Cache database schemas
        logger.info("Notion page hierarchy manager initialized")

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get page information from Notion.

        Args:
            page_id: Notion page ID

        Returns:
            Page object from Notion API

        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        logger.info(f"Fetching page info: {page_id}")

        response = requests.get(
            f"{self.base_url}/pages/{page_id}",
            headers=self.headers
        )
        response.raise_for_status()

        page = response.json()
        logger.debug(f"Page retrieved: {page.get('id')}")
        return page

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """
        Get database schema from Notion.

        Args:
            database_id: Notion database ID

        Returns:
            Database object from Notion API

        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        # Check cache first
        if database_id in self._database_cache:
            logger.debug(f"Using cached database schema for {database_id}")
            return self._database_cache[database_id]

        logger.info(f"Fetching database schema: {database_id}")

        response = requests.get(
            f"{self.base_url}/databases/{database_id}",
            headers=self.headers
        )
        response.raise_for_status()

        database = response.json()
        self._database_cache[database_id] = database
        logger.debug(f"Database retrieved: {database.get('id')}")
        return database

    def find_parent_item_property(self, database_id: str) -> Optional[str]:
        """
        Find the "Parent item" relation property ID in a database.

        When Sub-items feature is enabled, Notion creates a self-relation with
        two properties: "Parent item" and "Sub-items". We need the property ID
        of the "Parent item" relation to set sub-item relationships.

        Args:
            database_id: Notion database ID

        Returns:
            Property ID of the "Parent item" relation, or None if not found

        Example:
            property_id = hierarchy.find_parent_item_property(database_id)
            if property_id:
                # Use this to set parent-child relationships
        """
        logger.info(f"Finding 'Parent item' property in database {database_id}")

        try:
            database = self.get_database(database_id)
            properties = database.get("properties", {})

            # Look for a relation property that is a self-relation
            # and has a name like "Parent item" or "Parent"
            for prop_name, prop_config in properties.items():
                if prop_config.get("type") == "relation":
                    relation_config = prop_config.get("relation", {})

                    # Check if it's a self-relation (points to same database)
                    if relation_config.get("database_id") == database_id:
                        # Check if it's the parent property (usually has dual_property for sub-items)
                        # The "Parent item" property has a corresponding "Sub-items" property
                        if "Parent" in prop_name or prop_name == "Parent item":
                            property_id = prop_config.get("id")
                            logger.info(f"Found 'Parent item' property: {prop_name} (ID: {property_id})")
                            return property_id

            logger.warning("No 'Parent item' relation property found. Make sure Sub-items feature is enabled.")
            return None

        except Exception as e:
            logger.error(f"Error finding parent item property: {e}")
            return None

    def make_subitem(
        self,
        child_page_id: str,
        parent_page_id: str,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        Make a database page into a sub-item (child) of another page in the same database.

        This uses the database's "Parent item" self-relation property to create
        the parent-child relationship. Both pages must be in the same database
        that has the Sub-items feature enabled.

        Args:
            child_page_id: Page ID to become a sub-item
            parent_page_id: Page ID that will be the new parent
            verify: Whether to verify both pages exist before updating (default: True)

        Returns:
            Result dictionary with:
                {
                    'success': bool,
                    'child_page_id': str,
                    'parent_page_id': str,
                    'child_title': str (if available),
                    'parent_title': str (if available),
                    'database_id': str (if available),
                    'parent_property_id': str (if available),
                    'error': str (if failed)
                }

        Example:
            result = hierarchy.make_subitem(
                child_page_id="abc123",
                parent_page_id="def456"
            )

            if result['success']:
                print(f"✅ {result['child_title']} is now a sub-item of {result['parent_title']}")
            else:
                print(f"❌ Error: {result['error']}")

        Note:
            - Both pages must be in the same database
            - Database must have Sub-items feature enabled
            - Both pages must be accessible by the integration
            - The integration must have edit access to the child page
        """
        result = {
            "success": False,
            "child_page_id": child_page_id,
            "parent_page_id": parent_page_id,
            "child_title": None,
            "parent_title": None,
            "database_id": None,
            "parent_property_id": None,
            "error": None,
        }

        try:
            logger.info(f"Making page {child_page_id} a sub-item of {parent_page_id}")

            # Get child page to find database and title
            try:
                child_page = self.get_page(child_page_id)
                result["child_title"] = self._extract_page_title(child_page)
                logger.info(f"Child page found: {result['child_title']}")

                # Get database ID from child page's parent
                parent_info = child_page.get("parent", {})
                if parent_info.get("type") != "database_id":
                    result["error"] = "Child page is not in a database. Sub-items only work for database pages."
                    logger.error(result["error"])
                    return result

                database_id = parent_info.get("database_id")
                result["database_id"] = database_id
                logger.info(f"Child page is in database: {database_id}")

            except requests.exceptions.RequestException as e:
                result["error"] = f"Child page not found or inaccessible: {e}"
                logger.error(result["error"])
                return result

            # Verify parent page exists and is in same database
            if verify:
                try:
                    parent_page = self.get_page(parent_page_id)
                    result["parent_title"] = self._extract_page_title(parent_page)
                    logger.info(f"Parent page found: {result['parent_title']}")

                    # Verify parent is in same database
                    parent_db_info = parent_page.get("parent", {})
                    if parent_db_info.get("type") != "database_id":
                        result["error"] = "Parent page is not in a database."
                        logger.error(result["error"])
                        return result

                    parent_database_id = parent_db_info.get("database_id")
                    if parent_database_id != database_id:
                        result["error"] = f"Pages are in different databases. Child: {database_id}, Parent: {parent_database_id}"
                        logger.error(result["error"])
                        return result

                except requests.exceptions.RequestException as e:
                    result["error"] = f"Parent page not found or inaccessible: {e}"
                    logger.error(result["error"])
                    return result

            # Find the "Parent item" relation property in the database
            parent_property_id = self.find_parent_item_property(database_id)
            if not parent_property_id:
                result["error"] = (
                    "Could not find 'Parent item' property in database. "
                    "Make sure the Sub-items feature is enabled for this database. "
                    "To enable: Open database → click '...' → Turn on 'Sub-items'"
                )
                logger.error(result["error"])
                return result

            result["parent_property_id"] = parent_property_id
            logger.info(f"Using parent property ID: {parent_property_id}")

            # Update child page's "Parent item" relation property
            logger.info("Updating child page's 'Parent item' relation...")

            update_payload = {
                "properties": {
                    parent_property_id: {
                        "relation": [
                            {
                                "id": parent_page_id
                            }
                        ]
                    }
                }
            }

            logger.debug(f"Update payload: {update_payload}")

            response = requests.patch(
                f"{self.base_url}/pages/{child_page_id}",
                headers=self.headers,
                json=update_payload
            )
            response.raise_for_status()

            updated_page = response.json()
            result["success"] = True

            logger.info(
                f"✅ Successfully made '{result['child_title']}' a sub-item of '{result['parent_title']}'"
            )

            return result

        except requests.exceptions.RequestException as e:
            result["error"] = f"Failed to update page relation: {e}"
            logger.error(result["error"])

            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    result["error"] += f" - {error_detail.get('message', '')}"
                    logger.error(f"API Error detail: {error_detail}")
                except Exception:
                    result["error"] += f" - {e.response.text}"
                    logger.error(f"API Error response: {e.response.text}")

            return result

        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logger.error(result["error"], exc_info=True)
            return result

    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """
        Extract title from a Notion page object.

        Args:
            page: Notion page object from API

        Returns:
            Page title as string, or "Untitled" if no title found
        """
        try:
            # Try to get title from properties
            properties = page.get("properties", {})

            # Look for title property (could be "title" or "Title" or "Name")
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    if title_array and len(title_array) > 0:
                        return title_array[0].get("plain_text", "Untitled")

            # Fallback: try to get from page object itself
            if "title" in page:
                title_array = page.get("title", [])
                if title_array and len(title_array) > 0:
                    return title_array[0].get("plain_text", "Untitled")

            return "Untitled"

        except Exception as e:
            logger.warning(f"Could not extract page title: {e}")
            return "Untitled"

    def get_page_parent(self, page_id: str) -> Dict[str, Any]:
        """
        Get the parent information of a page.

        Args:
            page_id: Notion page ID

        Returns:
            Parent information dictionary:
                {
                    'type': str ('page_id', 'database_id', 'workspace', etc.),
                    'page_id': str (if type is 'page_id'),
                    'database_id': str (if type is 'database_id'),
                }

        Example:
            parent = hierarchy.get_page_parent("abc123")
            if parent['type'] == 'page_id':
                print(f"Parent page: {parent['page_id']}")
            elif parent['type'] == 'database_id':
                print(f"Parent database: {parent['database_id']}")
        """
        logger.info(f"Getting parent of page: {page_id}")

        page = self.get_page(page_id)
        parent = page.get("parent", {})

        logger.info(f"Parent type: {parent.get('type')}")
        return parent

    def verify_hierarchy(
        self,
        child_page_id: str,
        expected_parent_page_id: str
    ) -> bool:
        """
        Verify that a database page is a sub-item of the expected parent.

        This checks the "Parent item" relation property to verify the relationship.

        Args:
            child_page_id: Child page ID
            expected_parent_page_id: Expected parent page ID

        Returns:
            True if child's parent matches expected parent, False otherwise

        Example:
            is_subitem = hierarchy.verify_hierarchy(
                child_page_id="abc123",
                expected_parent_page_id="def456"
            )
            if is_subitem:
                print("✅ Hierarchy verified")
            else:
                print("❌ Not a sub-item of expected parent")
        """
        logger.info(
            f"Verifying {child_page_id} is a sub-item of {expected_parent_page_id}"
        )

        try:
            # Get child page
            child_page = self.get_page(child_page_id)

            # Check if it's a database page
            parent_info = child_page.get("parent", {})
            if parent_info.get("type") != "database_id":
                logger.info("Child page is not in a database")
                return False

            database_id = parent_info.get("database_id")

            # Find the parent item property
            parent_property_id = self.find_parent_item_property(database_id)
            if not parent_property_id:
                logger.info("Could not find 'Parent item' property")
                return False

            # Get the parent item relation value
            properties = child_page.get("properties", {})

            # Find the property by ID (need to iterate since properties are keyed by name)
            parent_relation = None
            for _prop_name, prop_value in properties.items():
                if prop_value.get("id") == parent_property_id:
                    parent_relation = prop_value
                    break

            if not parent_relation or parent_relation.get("type") != "relation":
                logger.info("Parent item relation not found in page properties")
                return False

            # Check if the relation includes the expected parent
            relations = parent_relation.get("relation", [])
            for relation in relations:
                if relation.get("id") == expected_parent_page_id:
                    logger.info("✅ Hierarchy verified")
                    return True

            logger.info("Expected parent not found in parent item relation")
            return False

        except Exception as e:
            logger.error(f"Error verifying hierarchy: {e}")
            return False
