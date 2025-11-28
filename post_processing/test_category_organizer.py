"""Test script for category organizer module."""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from post_processing.category_organizer import CategoryOrganizer, build_categories_from_csv


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('category_organizer_test.log')
        ]
    )


def test_extract_and_parse(csv_path: str):
    """Test extracting and parsing category paths from CSV."""
    print("=" * 80)
    print("Test: Extract and Parse Category Paths")
    print("=" * 80)

    organizer = CategoryOrganizer(
        api_key="test_key",  # Not needed for extraction
        database_id="test_db",
        csv_path=csv_path,
        dry_run=True
    )

    # Extract category paths
    paths = organizer.extract_category_paths_from_csv()

    print(f"\nFound {len(paths)} unique category paths:")
    print("-" * 80)
    for path in paths[:20]:  # Show first 20
        print(f"  {path}")

    if len(paths) > 20:
        print(f"  ... and {len(paths) - 20} more")

    # Parse into tree
    print("\n" + "=" * 80)
    print("Parsing Category Tree")
    print("=" * 80)

    tree = organizer.parse_category_tree(paths)

    # Show tree structure
    root_categories = [p for p in paths if ' > ' not in p]

    print(f"\nFound {len(root_categories)} root categories:")
    print("-" * 80)

    for root in root_categories:
        print(f"\n{root}")
        children = tree[root]['children']

        for child_path in children:
            child_name = tree[child_path]['name']
            print(f"  └─ {child_name}")

            # Show grandchildren
            grandchildren = tree[child_path]['children']
            for i, gc_path in enumerate(grandchildren):
                gc_name = tree[gc_path]['name']
                prefix = "  │  └─" if i == len(grandchildren) - 1 else "  │  ├─"
                print(f"{prefix} {gc_name}")

    print("\n" + "=" * 80)
    print(f"Total categories in tree: {len(tree)}")
    print("=" * 80)

    return organizer, paths, tree


def test_dry_run(csv_path: str, api_key: str, database_id: str):
    """Test building category hierarchy in dry-run mode."""
    print("\n\n" + "=" * 80)
    print("Test: Build Category Hierarchy (DRY RUN)")
    print("=" * 80)

    result = build_categories_from_csv(
        api_key=api_key,
        database_id=database_id,
        csv_path=csv_path,
        dry_run=True
    )

    print("\n" + "=" * 80)
    print("DRY RUN Results:")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Categories would be created: {result['categories_created']}")
    print(f"Relationships would be created: {result['relationships_created']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")

    return result


def test_actual_build(csv_path: str, api_key: str, database_id: str):
    """Test actual building of category hierarchy (requires valid Notion credentials)."""
    print("\n\n" + "=" * 80)
    print("Test: Build Category Hierarchy (ACTUAL)")
    print("=" * 80)
    print("WARNING: This will create pages in your Notion database!")
    print("=" * 80)

    response = input("\nProceed with actual build? (yes/no): ")
    if response.lower() != 'yes':
        print("Skipped actual build.")
        return None

    result = build_categories_from_csv(
        api_key=api_key,
        database_id=database_id,
        csv_path=csv_path,
        dry_run=False
    )

    print("\n" + "=" * 80)
    print("ACTUAL Build Results:")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Categories created: {result['categories_created']}")
    print(f"Relationships created: {result['relationships_created']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")

    # Export category mapping
    if result['category_pages']:
        output_path = 'category_mapping.csv'
        organizer = CategoryOrganizer(
            api_key=api_key,
            database_id=database_id
        )
        organizer.category_pages = result['category_pages']
        organizer.export_category_mapping(output_path)
        print(f"\nCategory mapping exported to: {output_path}")

    return result


if __name__ == '__main__':
    setup_logging()

    # Configuration
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'migration_output/article_list_20251119_065308.csv'

    print("Category Organizer Test Suite")
    print("=" * 80)
    print(f"CSV Path: {csv_path}")
    print("=" * 80)

    # Verify CSV exists
    if not Path(csv_path).exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        print("\nUsage:")
        print(f"  python {__file__} <path_to_article_list.csv>")
        sys.exit(1)

    # Test 1: Extract and parse
    organizer, paths, tree = test_extract_and_parse(csv_path)

    # Test 2: Dry run (doesn't require actual API key)
    test_dry_run(
        csv_path=csv_path,
        api_key="test_key",
        database_id="test_database_id"
    )

    # Test 3: Actual build (requires valid credentials)
    print("\n\n" + "=" * 80)
    print("Actual Build Test")
    print("=" * 80)

    try:
        Config.validate_all(['notion'])
        print("Notion configuration found.")

        test_actual_build(
            csv_path=csv_path,
            api_key=Config.NOTION_API_KEY,
            database_id=Config.NOTION_DATABASE_ID
        )

    except Exception as e:
        print(f"Notion configuration not available: {e}")
        print("Skipping actual build test.")
        print("\nTo run actual build test:")
        print("  1. Set NOTION_API_KEY in .env")
        print("  2. Set NOTION_DATABASE_ID in .env")
        print("  3. Run this script again")

    print("\n" + "=" * 80)
    print("All Tests Complete")
    print("=" * 80)
