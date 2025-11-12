"""Example: Post-import organization of Notion pages into database structure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging

from post_processing.post_import import NotionPostImport

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Organize imported Notion pages into an existing database with category hierarchy.

    Prerequisites:
        1. Already exported from ServiceNow to ZIP
        2. Already imported ZIP to Notion (creates pages)
        3. Have Notion API key
        4. **Have an existing Notion database with the required schema**
        5. Have the database ID from the URL
        6. Have collected page IDs and titles from imported pages

    Required Database Schema:
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

    This script will:
        1. Build category hierarchy as pages in the existing database
        2. Move imported article pages into the database
        3. Link articles to categories via Parent Task relation
    """

    print("=" * 80)
    print("Notion Post-Import Organization")
    print("=" * 80)

    # =========================================================================
    # CONFIGURATION - Update these values
    # =========================================================================

    NOTION_API_KEY = "secret_your_api_key_here"
    DATA_SOURCE_ID = "your_database_id_here"  # Database data_source_id (same as database_id)

    # Example: Imported article pages (you'll need to provide these)
    # After importing ZIP to Notion, collect the page IDs and titles
    imported_articles = [
        {
            "page_id": "page_id_1",
            "title": "How to use Figma",
            "article_number": "KB0001",
            "category_path": ["IT", "Applications", "Figma"],
        },
        {
            "page_id": "page_id_2",
            "title": "Slack best practices",
            "article_number": "KB0002",
            "category_path": ["IT", "Applications", "Slack"],
        },
        {
            "page_id": "page_id_3",
            "title": "Tokyo office access",
            "article_number": "KB0003",
            "category_path": ["Office", "Tokyo", "Access"],
        },
    ]

    # =========================================================================
    # Alternative: Load from JSON file
    # =========================================================================
    # If you have a JSON file with article data:
    # with open('imported_articles.json', 'r') as f:
    #     imported_articles = json.load(f)

    # =========================================================================
    # EXECUTION
    # =========================================================================

    if NOTION_API_KEY == "secret_your_api_key_here":
        print("\n⚠️  Please update NOTION_API_KEY in the script!")
        print("Get your API key from: https://www.notion.so/my-integrations")
        return

    if DATA_SOURCE_ID == "your_database_id_here":
        print("\n⚠️  Please update DATA_SOURCE_ID in the script!")
        print("Copy the database ID from your Notion database URL")
        print("Format: https://www.notion.so/{database_id}?v=...")
        print("Note: data_source_id is typically the same as database_id")
        return

    if not imported_articles or imported_articles[0]["page_id"] == "page_id_1":
        print("\n⚠️  Please update imported_articles list in the script!")
        print("Collect page IDs from Notion after importing the ZIP")
        print("\nYou can:")
        print("1. Manually collect page IDs from Notion URLs")
        print("2. Use Notion API to search for imported pages")
        print("3. Create a JSON file with article data")
        return

    print(f"\nConfiguration:")
    print(f"  API Key: {NOTION_API_KEY[:10]}...")
    print(f"  Data Source ID: {DATA_SOURCE_ID}")
    print(f"  Articles to organize: {len(imported_articles)}")

    response = input("\nProceed with post-import organization? (yes/no): ")
    if response.lower() != "yes":
        print("Organization cancelled.")
        return

    # Initialize organizer
    organizer = NotionPostImport(api_key=NOTION_API_KEY)

    # Step 1: Build category hierarchy
    print("\n" + "=" * 80)
    print("Step 1: Building Category Hierarchy")
    print("=" * 80)

    # Extract unique category paths
    category_paths = []
    for article in imported_articles:
        category_path = article.get("category_path", [])
        if category_path and category_path not in category_paths:
            category_paths.append(category_path)

    print(f"Found {len(category_paths)} unique category paths")

    category_map = organizer.build_category_hierarchy(
        database_id=DATA_SOURCE_ID, category_paths=category_paths
    )

    print(f"\n✅ Category hierarchy created:")
    for path, page_id in sorted(category_map.items()):
        print(f"  {path} → {page_id}")

    # Step 2: Move articles to database
    print("\n" + "=" * 80)
    print("Step 2: Moving Articles to Database")
    print("=" * 80)

    results = organizer.organize_imported_articles(
        data_source_id=DATA_SOURCE_ID, articles=imported_articles, category_map=category_map
    )

    # Display results
    print("\n" + "=" * 80)
    print("Organization Complete!")
    print("=" * 80)
    print(f"✅ Successfully organized: {results['success']} articles")
    print(f"❌ Failed: {results['failed']} articles")

    if results["errors"]:
        print(f"\nErrors:")
        for error in results["errors"][:10]:
            print(f"  - {error}")

    print(f"\n📊 Final Structure:")
    print(f"  Database ID: {DATA_SOURCE_ID}")
    print(f"  Categories: {len(category_map)}")
    print(f"  Articles: {results['success']}")
    print(f"\n🔗 View your organized knowledge base:")
    print(f"  https://www.notion.so/{DATA_SOURCE_ID.replace('-', '')}")


def create_article_mapping_template():
    """
    Helper function to create a template for article mapping.

    Run this to generate a JSON template that you can fill in with
    page IDs after importing to Notion.
    """
    template = [
        {
            "page_id": "REPLACE_WITH_NOTION_PAGE_ID",
            "title": "Article Title from ServiceNow",
            "article_number": "KB0001",
            "category_path": ["Category", "Subcategory"],
        }
    ]

    with open("article_mapping_template.json", "w") as f:
        json.dump(template, f, indent=2)

    print("✅ Template created: article_mapping_template.json")
    print("\nSteps to use:")
    print("1. Import ZIP to Notion")
    print("2. Collect page IDs from imported pages")
    print("3. Fill in the template with actual page IDs")
    print("4. Update the script to load from this file")


if __name__ == "__main__":
    # Uncomment to create template:
    # create_article_mapping_template()

    main()

