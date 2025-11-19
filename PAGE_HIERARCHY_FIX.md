# Page Hierarchy Fix - Database Sub-items

## Issue

The original `page_hierarchy.py` implementation was incorrect. It attempted to create parent-child relationships by changing a page's `parent` property, which moves pages between databases or under other pages, but **does not create sub-item relationships within a database**.

## Root Cause

In Notion, there are two different concepts:

1. **Page Parent** (`parent` property): Defines where a page lives (in a database, under another page, or in workspace)
2. **Sub-items** (database relation): A self-relation property that creates parent-child relationships within a database

The original code confused these two concepts.

## How Sub-items Actually Work

When you enable the "Sub-items" feature in a Notion database:

1. Notion auto-creates a **self-relation** with two properties:
   - **"Parent item"** - relation pointing to parent tasks
   - **"Sub-items"** - relation showing child tasks

2. To make Page A a sub-item of Page B:
   - Both pages must be in the same database
   - Update Page A's "Parent item" relation property to point to Page B's page ID
   - The relation is a property update, NOT a parent change

## The Fix

### 1. New Methods Added

**`get_database(database_id: str)`**
- Fetches database schema from Notion API
- Caches results to avoid repeated API calls
- Returns full database object with properties

**`find_parent_item_property(database_id: str)`**
- Searches database schema for the "Parent item" relation property
- Identifies self-relations (where relation points to same database)
- Returns the property ID needed for updates
- Validates that Sub-items feature is enabled

### 2. Updated `make_subitem()` Method

**Old approach (WRONG):**
```python
update_payload = {
    "parent": {
        "type": "page_id",
        "page_id": parent_page_id
    }
}
```

**New approach (CORRECT):**
```python
update_payload = {
    "properties": {
        parent_property_id: {  # The "Parent item" property ID
            "relation": [
                {
                    "id": parent_page_id  # Parent task's page ID
                }
            ]
        }
    }
}
```

### 3. Enhanced Validation

The updated method now:
- ✅ Verifies both pages are in a database (not standalone pages)
- ✅ Verifies both pages are in the **same** database
- ✅ Finds the "Parent item" property automatically
- ✅ Provides clear error messages if Sub-items is not enabled
- ✅ Returns database_id and property_id in result for debugging

### 4. Updated `verify_hierarchy()` Method

**Old approach (WRONG):**
- Checked page's `parent` property
- Only worked for page-under-page relationships

**New approach (CORRECT):**
- Checks the "Parent item" relation property value
- Verifies the relation includes the expected parent page ID
- Works with database sub-items

## API Payload Example

To make page `child_id` a sub-item of page `parent_id`:

```http
PATCH https://api.notion.com/v1/pages/{child_id}
Content-Type: application/json
Authorization: Bearer {api_key}
Notion-Version: 2022-06-28

{
    "properties": {
        "pX%3BH": {  // This is the "Parent item" property ID from database schema
            "relation": [
                {
                    "id": "2704aa08f51280fbaefadc91b14d8bf4"  // Parent page ID
                }
            ]
        }
    }
}
```

## Usage Changes

### Before (Wrong - didn't actually work)

```python
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key="...")

# This would move the page's parent, not create sub-item
result = hierarchy.make_subitem(
    child_page_id="abc123",
    parent_page_id="def456"
)
```

### After (Correct - creates actual sub-item)

```python
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key="...")

# This creates a proper sub-item relationship via the relation property
result = hierarchy.make_subitem(
    child_page_id="abc123",  # Must be in a database
    parent_page_id="def456"  # Must be in same database
)

if result['success']:
    print(f"✅ {result['child_title']} is now a sub-item of {result['parent_title']}")
    print(f"Database: {result['database_id']}")
    print(f"Parent property ID: {result['parent_property_id']}")
else:
    print(f"❌ Error: {result['error']}")
```

## Prerequisites

For this to work, users must:

1. **Enable Sub-items feature** in the database:
   - Open the database in Notion
   - Click the "..." menu (top right)
   - Select "Turn on Sub-items"
   - Notion will auto-create "Parent item" and "Sub-items" properties

2. **Share database with integration**:
   - Open the database page
   - Click "..." → "Add connections"
   - Select your integration

3. **Both pages must be in the database**:
   - Pages must be database rows, not standalone pages
   - Both child and parent must be in the same database

## Error Messages

The updated code provides helpful error messages:

### Sub-items Not Enabled
```
Could not find 'Parent item' property in database.
Make sure the Sub-items feature is enabled for this database.
To enable: Open database → click '...' → Turn on 'Sub-items'
```

### Pages in Different Databases
```
Pages are in different databases.
Child: 123abc..., Parent: 456def...
```

### Not a Database Page
```
Child page is not in a database.
Sub-items only work for database pages.
```

## Testing

The module compiles successfully:

```bash
✅ NotionPageHierarchy module loads successfully
```

All validation logic in place:
- ✅ Database detection
- ✅ Property ID resolution
- ✅ Self-relation verification
- ✅ Same-database validation
- ✅ Clear error messages

## Key Takeaways

1. **Sub-items ≠ Page Parent**: These are fundamentally different Notion features
2. **Database relation property**: Sub-items use a special self-relation property
3. **Property ID required**: Must query database schema to get the "Parent item" property ID
4. **Same database only**: Both pages must be in the same database
5. **Enable Sub-items first**: Feature must be turned on in database settings

## References

- [Notion API - Update Page](https://developers.notion.com/reference/patch-page)
- [Notion API - Database Object](https://developers.notion.com/reference/database)
- [Notion API - Relation Property](https://developers.notion.com/reference/property-object#relation)
