"""Build category hierarchy from ServiceNow knowledge base articles.

This module provides functionality to construct a hierarchical tree structure
of categories from article metadata, useful for understanding the knowledge base
organization and planning migrations.
"""
import logging
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class CategoryHierarchyBuilder:
    """Build hierarchical category tree from article metadata."""

    def __init__(self):
        """Initialize the category hierarchy builder."""
        self.category_counts = defaultdict(int)
        logger.debug("CategoryHierarchyBuilder initialized")

    @staticmethod
    def _extract_category(article: Dict[str, Any]) -> str:
        """
        Extract category string from article data.

        ServiceNow may return kb_category as:
        - A string: "IT > Applications > Figma"
        - A dict/reference: {"value": "...", "display_value": "..."}

        Args:
            article: Article dictionary

        Returns:
            Category path as string, or empty string if not found
        """
        category_value = article.get('kb_category', '')

        # Handle if kb_category is a dict (ServiceNow reference field)
        if isinstance(category_value, dict):
            # Prefer display_value (human-readable) over value (sys_id)
            category = category_value.get('display_value', '') or category_value.get('value', '')
        else:
            category = category_value

        # Convert to string and strip whitespace
        return str(category).strip() if category else ''

    def build_hierarchy_from_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build category hierarchy from a list of articles.

        Args:
            articles: List of article dictionaries with 'kb_category' field

        Returns:
            Hierarchical tree structure as list of category nodes

        Example:
            >>> builder = CategoryHierarchyBuilder()
            >>> articles = [
            ...     {'kb_category': 'IT > Applications > Figma'},
            ...     {'kb_category': 'IT > Applications > Slack'},
            ...     {'kb_category': 'IT > Hardware'},
            ... ]
            >>> hierarchy = builder.build_hierarchy_from_articles(articles)
            >>> # Returns:
            >>> # [
            >>> #   {
            >>> #     'name': 'IT',
            >>> #     'full_path': 'IT',
            >>> #     'parent': None,
            >>> #     'ancestors': [],
            >>> #     'level': 0,
            >>> #     'article_count': 3,
            >>> #     'children': [...]
            >>> #   }
            >>> # ]
        """
        logger.info(f"Building category hierarchy from {len(articles)} articles")

        # Count articles per category path (only direct articles, not including descendants)
        category_article_counts = defaultdict(int)

        for article in articles:
            category = self._extract_category(article)

            if category:
                # Count only for the exact category path
                category_article_counts[category] += 1

        # Collect all unique category paths (including parent paths)
        all_category_paths = set()
        for category in category_article_counts.keys():
            parts = category.split(' > ')
            for i in range(1, len(parts) + 1):
                path = ' > '.join(parts[:i])
                all_category_paths.add(path)

        logger.debug(f"Found {len(all_category_paths)} unique category paths")

        # Build tree structure
        hierarchy = self._build_tree(all_category_paths, category_article_counts)

        logger.info(f"Built hierarchy with {len(hierarchy)} top-level categories")
        return hierarchy

    def _build_tree(self, category_paths: set, category_article_counts: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Build hierarchical tree from flat category paths.

        Args:
            category_paths: Set of all category paths
            category_article_counts: Dictionary mapping category paths to direct article counts

        Returns:
            List of top-level category nodes with nested children
        """
        # Organize categories by level
        tree = []
        category_nodes = {}

        # Sort paths to process parents before children
        sorted_paths = sorted(category_paths, key=lambda x: x.count(' > '))

        for path in sorted_paths:
            parts = path.split(' > ')
            level = len(parts) - 1
            name = parts[-1]

            # Get parent path and ancestors
            parent_path = ' > '.join(parts[:-1]) if level > 0 else None
            ancestors = [' > '.join(parts[:i]) for i in range(1, len(parts))] if level > 0 else []

            # Create node
            node = {
                'name': name,
                'full_path': path,
                'parent': parent_path,
                'ancestors': ancestors,
                'level': level,
                'article_count': category_article_counts.get(path, 0),  # Direct articles only
                'total_article_count': 0,  # Will be calculated later (includes descendants)
                'children': []
            }

            # Store node for parent-child linking
            category_nodes[path] = node

            if level == 0:
                # Top-level category
                tree.append(node)
            else:
                # Find parent and add as child
                if parent_path in category_nodes:
                    category_nodes[parent_path]['children'].append(node)
                else:
                    # Parent doesn't exist, create it
                    logger.warning(f"Parent path not found: {parent_path}")
                    tree.append(node)

        # Update total counts to include children
        self._update_total_counts(tree)

        return tree

    def _update_total_counts(self, nodes: List[Dict[str, Any]]) -> int:
        """
        Update total article counts to include all descendants.

        Args:
            nodes: List of category nodes

        Returns:
            Total count including all descendants
        """
        total = 0

        for node in nodes:
            # Start with node's direct article count
            node_total = node.get('article_count', 0)

            # Add children's total counts
            if node.get('children'):
                children_total = self._update_total_counts(node['children'])
                node_total += children_total

            # Update node's total count
            node['total_article_count'] = node_total
            total += node_total

        return total

    def get_flat_categories(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get flat list of all categories with metadata.

        Args:
            articles: List of article dictionaries

        Returns:
            List of category dictionaries with full metadata

        Example:
            >>> builder = CategoryHierarchyBuilder()
            >>> categories = builder.get_flat_categories(articles)
            >>> # Returns:
            >>> # [
            >>> #   {
            >>> #     'name': 'IT',
            >>> #     'full_path': 'IT',
            >>> #     'parent': None,
            >>> #     'ancestors': [],
            >>> #     'level': 0,
            >>> #     'article_count': 25,
            >>> #     'total_article_count': 150
            >>> #   },
            >>> #   ...
            >>> # ]
        """
        # Count articles per category path (only direct articles)
        category_article_counts = defaultdict(int)

        for article in articles:
            category = self._extract_category(article)

            if category:
                category_article_counts[category] += 1

        # Collect all unique category paths
        all_category_paths = set()
        for category in category_article_counts.keys():
            parts = category.split(' > ')
            for i in range(1, len(parts) + 1):
                path = ' > '.join(parts[:i])
                all_category_paths.add(path)

        # Build complete category information
        categories = []
        for path in sorted(all_category_paths):
            parts = path.split(' > ')
            level = len(parts) - 1
            name = parts[-1]
            parent = ' > '.join(parts[:-1]) if level > 0 else None
            ancestors = [' > '.join(parts[:i]) for i in range(1, len(parts))] if level > 0 else []

            # Calculate total count (direct + all descendants)
            total_count = 0
            for cat_path, count in category_article_counts.items():
                if cat_path == path or cat_path.startswith(path + ' > '):
                    total_count += count

            categories.append({
                'name': name,
                'full_path': path,
                'parent': parent,
                'ancestors': ancestors,
                'level': level,
                'article_count': category_article_counts.get(path, 0),
                'total_article_count': total_count
            })

        return categories

    def get_category_stats(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about categories.

        Args:
            articles: List of article dictionaries

        Returns:
            Dictionary with category statistics

        Example:
            >>> stats = builder.get_category_stats(articles)
            >>> print(stats['total_categories'])
            >>> print(stats['max_depth'])
            >>> print(stats['top_categories'])
        """
        categories = self.get_flat_categories(articles)

        if not categories:
            return {
                'total_categories': 0,
                'max_depth': 0,
                'top_categories': [],
                'articles_with_category': 0,
                'articles_without_category': len(articles)
            }

        # Calculate stats
        max_depth = max(cat['level'] for cat in categories) + 1 if categories else 0
        top_categories = [cat for cat in categories if cat['level'] == 0]

        # Count articles with/without categories
        articles_with_category = sum(1 for a in articles if a.get('kb_category'))
        articles_without_category = len(articles) - articles_with_category

        return {
            'total_categories': len(categories),
            'max_depth': max_depth,
            'top_categories': sorted(top_categories, key=lambda x: x['count'], reverse=True),
            'articles_with_category': articles_with_category,
            'articles_without_category': articles_without_category,
            'all_categories': categories
        }
