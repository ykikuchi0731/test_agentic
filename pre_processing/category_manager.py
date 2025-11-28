"""Category hierarchy management with caching and prefetching."""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CategoryManager:
    """Manage category operations with caching for performance."""

    def __init__(self, client, enable_cache: bool = True):
        """
        Initialize category manager.

        Args:
            client: ServiceNowClient instance
            enable_cache: Enable in-memory caching of categories
        """
        self.client = client
        self.enable_cache = enable_cache
        self._category_cache: Dict[str, Dict[str, Any]] = {}
        self._category_tree: Optional[Dict[str, Dict[str, Any]]] = None
        self._invalid_category_cache: set = set()

    def get_category(self, category_sys_id: str) -> Optional[Dict[str, Any]]:
        """
        Get category details by sys_id with caching and 404 handling.

        Args:
            category_sys_id: System ID of the category

        Returns:
            Category details or None if not found
        """
        # Check invalid cache
        if category_sys_id in self._invalid_category_cache:
            logger.debug(f"Skipping known invalid category {category_sys_id}")
            return None

        # Check cache
        if self.enable_cache and category_sys_id in self._category_cache:
            logger.debug(f"Cache hit for category {category_sys_id}")
            return self._category_cache[category_sys_id]

        # Check pre-fetched tree
        if self._category_tree and category_sys_id in self._category_tree:
            logger.debug(f"Found category {category_sys_id} in pre-fetched tree")
            return self._category_tree[category_sys_id]

        logger.info(f"Fetching category {category_sys_id} from API")

        try:
            category = self.client.get_record(
                table="kb_category",
                sys_id=category_sys_id,
                fields=["sys_id", "label", "parent_id", "sys_created_on", "sys_updated_on", "active"],
            )

            if not category:
                logger.warning(f"Category {category_sys_id} not found (404) - caching as invalid")
                self._invalid_category_cache.add(category_sys_id)
                return None

            # Store in cache
            if self.enable_cache:
                self._category_cache[category_sys_id] = category

            return category

        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                logger.warning(f"Category {category_sys_id} not found (404) - caching as invalid")
                self._invalid_category_cache.add(category_sys_id)
                return None
            else:
                logger.error(f"Error getting category {category_sys_id}: {e}")
                raise

    def get_hierarchy(self, category_sys_id: str) -> List[Dict[str, Any]]:
        """
        Get full category hierarchy from root to specified category.

        Args:
            category_sys_id: System ID of the category

        Returns:
            List of categories from root to child (ordered parent to child)
        """
        logger.info(f"Getting category hierarchy for {category_sys_id}")

        hierarchy = []
        current_sys_id = category_sys_id
        max_depth = 10
        depth = 0

        try:
            while current_sys_id and depth < max_depth:
                category = self.get_category(current_sys_id)

                if category is None:
                    logger.warning(
                        f"Category {current_sys_id} not found - stopping hierarchy traversal"
                    )
                    break

                hierarchy.insert(0, category)

                # Check parent
                parent_id = category.get("parent_id", {})
                if isinstance(parent_id, dict) and parent_id.get("value"):
                    current_sys_id = parent_id["value"]
                else:
                    break

                depth += 1

            return hierarchy

        except Exception as e:
            logger.error(f"Error getting category hierarchy: {e}")
            raise

    def prefetch_all(self) -> int:
        """
        Pre-fetch all categories from ServiceNow and store in memory.
        Eliminates individual API calls when traversing hierarchies.

        Returns:
            Number of categories fetched
        """
        logger.info("Pre-fetching all categories from ServiceNow...")

        try:
            all_categories = self.client.query_table(
                table="kb_category",
                fields=["sys_id", "label", "parent_id", "sys_created_on", "sys_updated_on", "active"],
            )

            # Build lookup dictionary
            self._category_tree = {}
            for cat in all_categories:
                sys_id = cat["sys_id"]
                if isinstance(sys_id, dict):
                    sys_id = sys_id.get("value", sys_id.get("display_value", ""))
                if sys_id:
                    self._category_tree[sys_id] = cat

            logger.info(f"Pre-fetched {len(all_categories)} categories")
            return len(all_categories)

        except Exception as e:
            logger.error(f"Error pre-fetching categories: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about category cache usage."""
        return {
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._category_cache),
            "prefetched": self._category_tree is not None,
            "prefetch_size": len(self._category_tree) if self._category_tree else 0,
            "invalid_categories": len(self._invalid_category_cache),
            "invalid_category_ids": list(self._invalid_category_cache)
            if self._invalid_category_cache
            else [],
        }

    def clear_cache(self):
        """Clear the category cache."""
        self._category_cache.clear()
        logger.info("Category cache cleared")

    def clear_prefetch(self):
        """Clear the pre-fetched category tree."""
        self._category_tree = None
        logger.info("Pre-fetched category tree cleared")
