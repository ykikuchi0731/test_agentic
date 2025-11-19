# Page Hierarchy Feature - Quick Reference

## Overview

New module to create parent-child relationships between Notion pages, making it easy to organize imported content into hierarchical structures.

## What It Does

Allows you to make any Notion page a **sub-item** (child) of another page, creating nested page structures.

## Quick Start

### 1. Set API Key

```bash
export NOTION_API_KEY='secret_xxx...'
```

### 2. Share Pages with Integration

In Notion, for both pages:
1. Click "..." menu
2. Click "Add connections"
3. Select your integration

### 3. Run Interactive Script

```bash
python -m examples.make_page_subitem
```

Enter the page IDs when prompted, and the script will:
- Verify both pages exist
- Make the child page a sub-item of the parent
- Display the result with page titles

### 4. Or Use Programmatically

```python
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key="secret_xxx")

result = hierarchy.make_subitem(
    child_page_id="abc123",
    parent_page_id="def456"
)

if result['success']:
    print(f"✅ {result['child_title']} → {result['parent_title']}")
```

## Files Created

### Module: [`post_processing/page_hierarchy.py`](test_agentic/post_processing/page_hierarchy.py)

Main class: **`NotionPageHierarchy`**

**Key Methods:**
- `make_subitem(child_page_id, parent_page_id, verify=True)` - Make a page a sub-item
- `get_page_parent(page_id)` - Get parent information
- `verify_hierarchy(child_page_id, expected_parent_page_id)` - Verify relationship
- `get_page(page_id)` - Get page information

### Example: [`examples/make_page_subitem.py`](test_agentic/examples/make_page_subitem.py)

Interactive script with:
- User-friendly prompts for page IDs
- Page verification before making changes
- Clear success/error messages
- Programmatic function for batch use

### Documentation: [`docs/page_hierarchy.md`](test_agentic/docs/page_hierarchy.md)

Complete documentation including:
- Setup instructions
- API reference
- Usage examples (interactive, programmatic, batch)
- How to get page IDs
- Common use cases
- Troubleshooting guide
- Advanced usage patterns

## Use Cases

### 1. Organize Imported Articles

```python
# After migration, organize articles under a main page
hierarchy = NotionPageHierarchy(api_key="secret_xxx")

main_kb_page = "xyz789"
imported_articles = ["page1", "page2", "page3"]

for article_id in imported_articles:
    hierarchy.make_subitem(article_id, main_kb_page)
```

**Result:**
```
📄 Knowledge Base
  ├─ 📄 Getting Started
  ├─ 📄 Installation Guide
  └─ 📄 Troubleshooting
```

### 2. Create Category Structure

```python
# Build nested hierarchy
kb_root = "root_id"
it_section = "it_id"
apps_category = "apps_id"

# Level 1: IT under KB
hierarchy.make_subitem(it_section, kb_root)

# Level 2: Applications under IT
hierarchy.make_subitem(apps_category, it_section)

# Level 3: Articles under Applications
hierarchy.make_subitem("figma_guide_id", apps_category)
hierarchy.make_subitem("slack_guide_id", apps_category)
```

**Result:**
```
📄 Knowledge Base
  └─ 📄 IT
      └─ 📄 Applications
          ├─ 📄 Figma Guide
          └─ 📄 Slack Guide
```

### 3. Batch Processing

```python
pages_to_organize = [
    {"child": "page_1", "parent": "main_page"},
    {"child": "page_2", "parent": "main_page"},
    {"child": "page_3", "parent": "main_page"},
]

for item in pages_to_organize:
    result = hierarchy.make_subitem(item["child"], item["parent"])
    print(f"{'✅' if result['success'] else '❌'} {result.get('child_title', 'Page')}")
```

## API Reference

### `make_subitem(child_page_id, parent_page_id, verify=True)`

Make a page a sub-item of another page.

**Parameters:**
- `child_page_id` (str): Page to become a sub-item
- `parent_page_id` (str): Page to be the parent
- `verify` (bool): Verify pages exist before moving (default: True)

**Returns:**
```python
{
    'success': bool,
    'child_page_id': str,
    'parent_page_id': str,
    'child_title': str,      # Page title (if verify=True)
    'parent_title': str,     # Page title (if verify=True)
    'error': str             # Error message (if failed)
}
```

**Example:**
```python
result = hierarchy.make_subitem(
    child_page_id="abc123",
    parent_page_id="def456"
)
```

### `get_page_parent(page_id)`

Get parent information of a page.

**Returns:**
```python
{
    'type': str,           # 'page_id', 'database_id', 'workspace'
    'page_id': str,        # if type is 'page_id'
    'database_id': str,    # if type is 'database_id'
}
```

### `verify_hierarchy(child_page_id, expected_parent_page_id)`

Verify a page is a sub-item of expected parent.

**Returns:** `bool`

## How to Get Page IDs

### From URL

Page URL:
```
https://www.notion.so/My-Page-abc123def456
```

Page ID: `abc123def456`

### Format Page ID

Some APIs require UUID format with hyphens:
```
abc123de-f456-ghi7-89jk-l012mno34567
```

Add hyphens at positions: 8, 12, 16, 20

## Example Output

### Interactive Script

```
================================================================================
Make Notion Page a Sub-Item
================================================================================

✅ Notion hierarchy manager initialized

Enter the page IDs:

Child page ID (page to become sub-item): abc123
Parent page ID (page to be the parent): def456

--------------------------------------------------------------------------------

✅ SUCCESS!

Child page:  Getting Started Guide
Parent page: Knowledge Base

'Getting Started Guide' is now a sub-item of 'Knowledge Base'

================================================================================
```

### Programmatic

```python
result = hierarchy.make_subitem("abc123", "def456")

# Output:
# {
#     'success': True,
#     'child_page_id': 'abc123',
#     'parent_page_id': 'def456',
#     'child_title': 'Getting Started Guide',
#     'parent_title': 'Knowledge Base',
#     'error': None
# }
```

## Common Errors

### "Page not found or inaccessible"
- Verify page ID is correct
- Share page with integration

### "Integration does not have access"
- Open page → "..." → "Add connections" → Select integration

### "Invalid page_id"
- Check format (UUID with or without hyphens)
- Use only the ID part (not full URL)

## Integration with Migration Tool

Combine with ServiceNow migration:

```python
from pre_processing.migrator import MigrationOrchestrator
from post_processing.page_hierarchy import NotionPageHierarchy

# 1. Export from ServiceNow
migrator = MigrationOrchestrator(servicenow_kb)
results = migrator.export_all_to_zip()

# 2. Import ZIP to Notion (manually)
# Get imported page IDs

# 3. Organize in Notion
hierarchy = NotionPageHierarchy(api_key="secret_xxx")

for article in imported_articles:
    hierarchy.make_subitem(
        child_page_id=article["notion_page_id"],
        parent_page_id=main_kb_page_id
    )
```

## Features

✅ **Simple API** - Just two page IDs needed
✅ **Verification** - Optional page existence check
✅ **Error Handling** - Clear error messages
✅ **Page Titles** - Displays titles for confirmation
✅ **Batch Support** - Process multiple pages
✅ **Interactive Mode** - User-friendly CLI
✅ **Programmatic Mode** - For automation

## Testing

Compiled successfully:
```bash
python3 -m py_compile post_processing/page_hierarchy.py
python3 -m py_compile examples/make_page_subitem.py
```

## Next Steps

1. **Try it out**: Run `python -m examples.make_page_subitem`
2. **Organize imports**: Use after migrating from ServiceNow
3. **Build hierarchies**: Create nested structures programmatically
4. **Database organization**: See `NotionPostImport` for database-based organization

## Documentation

Full documentation: [`docs/page_hierarchy.md`](test_agentic/docs/page_hierarchy.md)

- Complete API reference
- Advanced usage patterns
- Troubleshooting guide
- Rate limiting strategies
- Error handling examples
