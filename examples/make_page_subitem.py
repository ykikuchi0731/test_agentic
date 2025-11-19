"""Example: Make a Notion page a sub-item of another page."""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, ConfigurationError
from post_processing.page_hierarchy import NotionPageHierarchy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Make a page a sub-item of another page."""
    print("=" * 80)
    print("Make Notion Page a Sub-Item")
    print("=" * 80)
    print()

    # Validate Notion configuration
    try:
        Config.validate_notion()
    except ConfigurationError as e:
        print("❌ Configuration Error")
        print()
        print(str(e))
        print()
        return

    # Initialize hierarchy manager using Config
    hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
    print("✅ Notion hierarchy manager initialized")
    print()

    # Get page IDs from user
    print("Enter the page IDs:")
    print()

    child_page_id = input("Child page ID (page to become sub-item): ").strip()
    if not child_page_id:
        print("❌ Child page ID is required")
        return

    parent_page_id = input("Parent page ID (page to be the parent): ").strip()
    if not parent_page_id:
        print("❌ Parent page ID is required")
        return

    print()
    print("-" * 80)
    print()

    # Confirm action
    print("About to make the following change:")
    print(f"  Child page:  {child_page_id}")
    print(f"  Parent page: {parent_page_id}")
    print()
    confirm = input("Proceed? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ Cancelled")
        return

    print()
    print("Processing...")
    print()

    # Make the page a sub-item
    result = hierarchy.make_subitem(
        child_page_id=child_page_id,
        parent_page_id=parent_page_id,
        verify=True
    )

    # Display result
    print("-" * 80)
    print()

    if result["success"]:
        print("✅ SUCCESS!")
        print()
        print(f"Child page:  {result['child_title'] or child_page_id}")
        print(f"Parent page: {result['parent_title'] or parent_page_id}")
        print()
        print(f"'{result['child_title']}' is now a sub-item of '{result['parent_title']}'")
        print()
        print("You can verify this in Notion - the child page should now appear")
        print("nested under the parent page.")
    else:
        print("❌ FAILED")
        print()
        print(f"Error: {result['error']}")
        print()
        print("Common issues:")
        print("  - Page IDs might be incorrect")
        print("  - Integration might not have access to the pages")
        print("  - Pages might not exist")
        print("  - Integration might not have edit permission")

    print()
    print("=" * 80)


def make_subitem_programmatic(child_page_id: str, parent_page_id: str, api_key: str = None):
    """
    Programmatic example of making a page a sub-item.

    Args:
        child_page_id: Page ID to become a sub-item
        parent_page_id: Page ID to be the parent
        api_key: Notion API key (optional, uses Config.NOTION_API_KEY if not provided)

    Returns:
        Result dictionary

    Example:
        from examples.make_page_subitem import make_subitem_programmatic

        # Use API key from Config (.env file)
        result = make_subitem_programmatic(
            child_page_id="abc123",
            parent_page_id="def456"
        )

        # Or provide API key explicitly
        result = make_subitem_programmatic(
            child_page_id="abc123",
            parent_page_id="def456",
            api_key="secret_xxx"
        )

        if result['success']:
            print(f"✅ {result['child_title']} is now under {result['parent_title']}")
    """
    # Use Config if API key not provided
    if api_key is None:
        Config.validate_notion()
        api_key = Config.NOTION_API_KEY

    hierarchy = NotionPageHierarchy(api_key=api_key)

    result = hierarchy.make_subitem(
        child_page_id=child_page_id,
        parent_page_id=parent_page_id,
        verify=True
    )

    return result


if __name__ == "__main__":
    main()
