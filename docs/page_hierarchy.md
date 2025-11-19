# Notion Page Hierarchy Management

This module provides tools to create and manage parent-child relationships between Notion pages.

## Overview

The `NotionPageHierarchy` class allows you to:
- Make a page a sub-item (child) of another page
- Verify parent-child relationships
- Get parent information for any page

## Use Cases

### 1. Organize Imported Pages

After importing pages from ServiceNow, you may want to create a hierarchical structure:

```
📄 Knowledge Base (parent)
  ├─ 📄 Getting Started (sub-item)
  ├─ 📄 Installation Guide (sub-item)
  └─ 📄 Troubleshooting (sub-item)
```

### 2. Restructure Content

Move pages around to create better organization:

```
📄 IT Department
  └─ 📄 Applications
      ├─ 📄 Figma Guide
      └─ 📄 Slack Guide
```

### 3. Create Documentation Hierarchies

Build nested documentation structures:

```
📄 API Documentation
  ├─ 📄 Authentication
  ├─ 📄 Endpoints
  │   ├─ 📄 Users API
  │   └─ 📄 Articles API
  └─ 📄 Examples
```

---

## Setup

### 1. Install Dependencies

```bash
pip install requests
```

### 2. Get Notion API Key

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Name it (e.g., "Page Hierarchy Manager")
4. Select the workspace
5. Click **"Submit"**
6. Copy the **Internal Integration Token** (starts with `secret_`)

### 3. Share Pages with Integration

**Important**: The integration must have access to both pages.

For each page you want to manage:
1. Open the page in Notion
2. Click the **"..."** menu (top right)
3. Click **"Add connections"**
4. Select your integration
5. Click **"Confirm"**

### 4. Add to .env File

Add your Notion API key to `.env`:

```bash
# Add to .env file
NOTION_API_KEY=secret_xxx...
```

**No need to export!** The script automatically loads from `.env` file.

---

## Usage

### Method 1: Interactive Script

Run the interactive example:

```bash
python -m examples.make_page_subitem
```

The script will:
1. Prompt for child page ID
2. Prompt for parent page ID
3. Verify both pages exist
4. Make the child page a sub-item of the parent
5. Display the result

**Example Session:**

```
================================================================================
Make Notion Page a Sub-Item
================================================================================

✅ Notion hierarchy manager initialized

Enter the page IDs:

Child page ID (page to become sub-item): abc123def456
Parent page ID (page to be the parent): xyz789ghi012

--------------------------------------------------------------------------------

About to make the following change:
  Child page:  abc123def456
  Parent page: xyz789ghi012

Proceed? (y/n): y

Processing...

--------------------------------------------------------------------------------

✅ SUCCESS!

Child page:  Getting Started Guide
Parent page: Knowledge Base

'Getting Started Guide' is now a sub-item of 'Knowledge Base'

You can verify this in Notion - the child page should now appear
nested under the parent page.

================================================================================
```

### Method 2: Programmatic Usage

**Option A: Use Config (Recommended)**

```python
from config import Config
from post_processing.page_hierarchy import NotionPageHierarchy

# Validate configuration (reads from .env)
Config.validate_notion()

# Initialize using Config
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)

# Make a page a sub-item
result = hierarchy.make_subitem(
    child_page_id="abc123def456",
    parent_page_id="xyz789ghi012",
    verify=True
)

# Check result
if result['success']:
    print(f"✅ {result['child_title']} is now a sub-item of {result['parent_title']}")
else:
    print(f"❌ Error: {result['error']}")
```

**Option B: Provide API key directly**

```python
from post_processing.page_hierarchy import NotionPageHierarchy

# Initialize with API key
hierarchy = NotionPageHierarchy(api_key="secret_xxx")

# Make a page a sub-item
result = hierarchy.make_subitem(
    child_page_id="abc123def456",
    parent_page_id="xyz789ghi012",
    verify=True
)
```

### Method 3: Batch Processing

Make multiple pages sub-items:

```python
from config import Config
from post_processing.page_hierarchy import NotionPageHierarchy

# Validate configuration
Config.validate_notion()

# Initialize using Config
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)

# List of pages to organize
pages_to_organize = [
    {"child": "page_id_1", "parent": "parent_id"},
    {"child": "page_id_2", "parent": "parent_id"},
    {"child": "page_id_3", "parent": "parent_id"},
]

# Process each page
for item in pages_to_organize:
    result = hierarchy.make_subitem(
        child_page_id=item["child"],
        parent_page_id=item["parent"]
    )

    if result['success']:
        print(f"✅ {result['child_title']}")
    else:
        print(f"❌ Failed: {result['error']}")
```

---

## API Reference

### `NotionPageHierarchy`

Main class for managing page hierarchy.

#### `__init__(api_key: str)`

Initialize the hierarchy manager.

**Args:**
- `api_key` (str): Notion integration API key

**Example:**
```python
hierarchy = NotionPageHierarchy(api_key="secret_xxx")
```

---

#### `make_subitem(child_page_id: str, parent_page_id: str, verify: bool = True)`

Make a page a sub-item of another page.

**Args:**
- `child_page_id` (str): Page ID to become a sub-item
- `parent_page_id` (str): Page ID that will be the new parent
- `verify` (bool): Whether to verify both pages exist before moving (default: True)

**Returns:**
- `dict`: Result dictionary:
  ```python
  {
      'success': bool,
      'child_page_id': str,
      'parent_page_id': str,
      'child_title': str,  # or None
      'parent_title': str,  # or None
      'error': str  # or None
  }
  ```

**Example:**
```python
result = hierarchy.make_subitem(
    child_page_id="abc123",
    parent_page_id="def456"
)
```

---

#### `get_page_parent(page_id: str)`

Get the parent information of a page.

**Args:**
- `page_id` (str): Notion page ID

**Returns:**
- `dict`: Parent information:
  ```python
  {
      'type': str,  # 'page_id', 'database_id', 'workspace', etc.
      'page_id': str,  # if type is 'page_id'
      'database_id': str,  # if type is 'database_id'
  }
  ```

**Example:**
```python
parent = hierarchy.get_page_parent("abc123")

if parent['type'] == 'page_id':
    print(f"Parent page: {parent['page_id']}")
elif parent['type'] == 'database_id':
    print(f"Parent database: {parent['database_id']}")
```

---

#### `verify_hierarchy(child_page_id: str, expected_parent_page_id: str)`

Verify that a page is a sub-item of the expected parent.

**Args:**
- `child_page_id` (str): Child page ID
- `expected_parent_page_id` (str): Expected parent page ID

**Returns:**
- `bool`: True if child's parent matches expected parent, False otherwise

**Example:**
```python
is_subitem = hierarchy.verify_hierarchy(
    child_page_id="abc123",
    expected_parent_page_id="def456"
)

if is_subitem:
    print("✅ Hierarchy verified")
else:
    print("❌ Not a sub-item of expected parent")
```

---

#### `get_page(page_id: str)`

Get page information from Notion.

**Args:**
- `page_id` (str): Notion page ID

**Returns:**
- `dict`: Full page object from Notion API

**Example:**
```python
page = hierarchy.get_page("abc123")
print(f"Page ID: {page['id']}")
```

---

## How to Get Page IDs

### Method 1: From Page URL

When you open a page in Notion, the URL looks like:
```
https://www.notion.so/My-Page-Title-abc123def456ghi789jkl012
```

The page ID is the last part: `abc123def456ghi789jkl012`

**Note**: You may need to add hyphens every 8, 12, 16, and 20 characters:
```
abc123de-f456-ghi7-89jk-l012mno34567
```

### Method 2: Copy Link

1. Open the page in Notion
2. Click the **"..."** menu (top right)
3. Click **"Copy link"**
4. Extract the ID from the URL

### Method 3: Via API (Advanced)

Use the Notion Search API to find pages by title:

```python
import requests

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Search for pages
response = requests.post(
    "https://api.notion.com/v1/search",
    headers=headers,
    json={
        "query": "Getting Started",
        "filter": {"property": "object", "value": "page"}
    }
)

results = response.json()
for page in results.get("results", []):
    print(f"Page: {page['id']}")
```

---

## Common Use Cases

### 1. Organize Imported Articles

After using the migration tool to import articles from ServiceNow:

```python
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key="secret_xxx")

# Create main container
main_page_id = "xyz789"  # Your "Knowledge Base" page

# Import resulted in these page IDs
imported_articles = [
    {"page_id": "page1", "title": "Getting Started"},
    {"page_id": "page2", "title": "Installation"},
    {"page_id": "page3", "title": "FAQ"},
]

# Make them all sub-items of the main page
for article in imported_articles:
    result = hierarchy.make_subitem(
        child_page_id=article["page_id"],
        parent_page_id=main_page_id
    )
    print(f"{'✅' if result['success'] else '❌'} {article['title']}")
```

### 2. Create Nested Structure

Build a multi-level hierarchy:

```python
# Level 1: Main sections
main_sections = {
    "IT": "section_it_id",
    "Office": "section_office_id",
    "HR": "section_hr_id",
}

# Level 2: Subsections under IT
it_subsections = {
    "Applications": "subsection_apps_id",
    "Infrastructure": "subsection_infra_id",
}

# Level 3: Articles under Applications
app_articles = [
    "article_figma_id",
    "article_slack_id",
    "article_zoom_id",
]

# Create hierarchy
kb_root = "kb_root_id"

# Attach main sections to root
for section_name, section_id in main_sections.items():
    hierarchy.make_subitem(section_id, kb_root)

# Attach subsections to IT
for subsection_name, subsection_id in it_subsections.items():
    hierarchy.make_subitem(subsection_id, main_sections["IT"])

# Attach articles to Applications
for article_id in app_articles:
    hierarchy.make_subitem(article_id, it_subsections["Applications"])
```

### 3. Move Page to Different Parent

Change the parent of a page:

```python
# Current structure:
#   Old Parent
#     └─ My Page

# Desired structure:
#   New Parent
#     └─ My Page

result = hierarchy.make_subitem(
    child_page_id="my_page_id",
    parent_page_id="new_parent_id"
)

# The page is now under the new parent
```

---

## Troubleshooting

### Error: "Page not found or inaccessible"

**Solutions:**
1. Verify the page ID is correct
2. Check that the integration has access to the page:
   - Open page in Notion
   - Click "..." → "Add connections"
   - Select your integration
3. Ensure the page hasn't been deleted

### Error: "Integration does not have access"

**Solution:**
Share the page with your integration:
1. Open page in Notion
2. Click "..." menu (top right)
3. Click "Add connections"
4. Select your integration
5. Click "Confirm"

### Error: "Invalid page_id"

**Solutions:**
1. Check page ID format (should be UUID-like)
2. Remove any URL parts (use only the ID)
3. Add hyphens if needed: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Page appears in wrong location

**Check:**
1. Verify you're using the correct parent page ID
2. Use `verify_hierarchy()` to confirm the relationship
3. Check Notion workspace - refresh the page

### Batch processing is slow

**Tips:**
1. Remove `verify=True` for faster processing (skips verification step)
2. Process in smaller batches
3. Add error handling to continue on failures:

```python
for item in items:
    try:
        result = hierarchy.make_subitem(item["child"], item["parent"], verify=False)
    except Exception as e:
        print(f"Skipping {item['child']}: {e}")
        continue
```

---

## Limitations

1. **Notion API Rate Limits**:
   - 3 requests per second average
   - For bulk operations, add delays between requests

2. **Page Must Allow Children**:
   - Some page types might not support children
   - Database pages work differently (see database organization)

3. **Integration Permissions**:
   - Integration must have edit access to child page
   - Integration must have read access to parent page

4. **No Automatic Undo**:
   - Once a page is moved, you need to manually move it back
   - Keep track of original parent IDs if you need to revert

---

## Advanced Usage

### Rate Limiting for Bulk Operations

```python
import time
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key="secret_xxx")

pages = [...]  # Large list of pages

for i, page in enumerate(pages):
    result = hierarchy.make_subitem(page["child"], page["parent"])

    # Add delay every 3 requests
    if (i + 1) % 3 == 0:
        time.sleep(1)
```

### Error Handling and Logging

```python
import logging

logging.basicConfig(level=logging.INFO)

hierarchy = NotionPageHierarchy(api_key="secret_xxx")

results = {"success": 0, "failed": 0, "errors": []}

for item in items:
    try:
        result = hierarchy.make_subitem(item["child"], item["parent"])

        if result["success"]:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "page": item["child"],
                "error": result["error"]
            })
    except Exception as e:
        results["failed"] += 1
        results["errors"].append({
            "page": item["child"],
            "error": str(e)
        })

print(f"✅ Success: {results['success']}")
print(f"❌ Failed: {results['failed']}")
```

---

## Next Steps

- **Database Organization**: Use `NotionPostImport` class for organizing pages into databases with properties
- **Bulk Import**: Combine with migration tools to automatically organize imported content
- **Category Hierarchy**: Build complete category structures programmatically

For more advanced organization with databases, see [`docs/post_import.md`](post_import.md).
