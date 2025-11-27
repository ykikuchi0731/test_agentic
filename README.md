# ServiceNow to Notion Migration Tool

A Python project for migrating knowledge portal articles from ServiceNow to Notion.

## Features

- ✅ List all HTML articles in ServiceNow knowledge portal
- ✅ Extract article data with HTML content
- ✅ Download and handle attached files
- ✅ Parse category hierarchy (with 99% API call reduction!)
- ✅ Parse HTML content (text, images, links, tables, etc.)
- ✅ Performance optimized with caching and pre-fetching
- ✅ **NEW: Filter to latest version only (ignore old article versions)**
- ✅ **NEW: Merge translated articles into single HTML**

## Project Structure

```
test_agentic/
├── README.md                       # This file
├── INDEX.md                        # Project index
├── cli.py                          # Unified CLI interface
├── cli_utils.py                    # CLI utilities
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── env.example                     # Environment variables template
├── .gitignore                      # Git ignore rules
│
├── pre_processing/                 # Phase 1: Extract from ServiceNow → ZIP
│   ├── __init__.py
│   ├── client.py                   # ServiceNow API client
│   ├── knowledge_base.py           # Knowledge base operations
│   ├── parser.py                   # HTML parsing utilities
│   ├── migrator.py                 # Migration orchestrator
│   ├── zip_exporter.py             # ZIP file creation
│   └── ...                         # Other exporters and processors
│
├── post_processing/                # Phase 2: Organize in Notion after import
│   ├── __init__.py
│   ├── post_import.py              # Database organization
│   ├── category_organizer.py       # Category hierarchy builder
│   └── page_hierarchy.py           # Page relationship manager
│
├── examples/                       # Example scripts
│   ├── quick_start.py              # Quick start example
│   ├── full_migration.py           # Full migration workflow
│   └── ...                         # Other examples
│
├── tests/                          # Test scripts
│   ├── test_list_articles.py
│   ├── test_categories.py
│   ├── test_optimization.py
│   └── ...                         # Other tests
│
├── docs/                           # Documentation
│   ├── QUICK_START.md              # Quick start guide
│   ├── PROJECT_ORGANIZATION.md     # Project organization details
│   ├── CLI_IMPLEMENTATION_SUMMARY.md
│   ├── EXPORT_CATEGORIES_FEATURE.md
│   ├── OPTIMIZATION_OPTIONS.md
│   └── ...                         # Other documentation
│
├── output/                         # Generated files (gitignored)
├── downloads/                      # Downloaded attachments (gitignored)
├── migration_output/               # Migration artifacts (gitignored)
└── logs/                           # Log files (gitignored)
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy `env.example` to `.env` and fill in your ServiceNow credentials:

```bash
cp env.example .env
# Edit .env with your credentials
```

### 3. Run Migration

**Using CLI (Recommended):**

```bash
# Quick test with 5 articles
python cli.py migrate --limit 5

# Full migration
python cli.py migrate

# With filters
python cli.py migrate --filter "category:IT" --limit 100

# See all options
python cli.py --help
```

**Using examples:**

```bash
# Quick start example (5 articles)
python examples/quick_start.py

# Full migration with interactive prompts
python examples/full_migration.py
```

**See [CLI Reference](docs/cli_reference.md) for complete command documentation.**

## CLI Commands

The migration tool provides a unified CLI interface for all operations:

### Main Commands

```bash
# Migrate articles (export as ZIP for Notion import)
python cli.py migrate [--limit N] [--filter "key:value"] [--process-iframes]

# Export article list (metadata only, CSV/JSON)
python cli.py export-list [--format csv] [--output path]

# Export category hierarchy (JSON/CSV)
python cli.py export-categories [--format csv] [--output path]

# Make Notion page a sub-item (post-processing)
python cli.py make-subitem --child <id> --parent <id>

# Visualize category hierarchy
python cli.py visualize
```

### Common Options

All commands support these options:

- `--limit N` - Process only N items (for testing)
- `--offset N` - Skip first N items
- `--filter "key:value"` - Filter by criteria (category, number, etc.)
- `--dry-run` - Show what would be done without executing
- `-v, --verbose` - Enable debug logging
- `-q, --quiet` - Minimal output

### Examples

```bash
# Test with 5 articles
python cli.py migrate --limit 5

# Migrate IT category only
python cli.py migrate --filter "category:IT"

# Export article list as CSV
python cli.py export-list --format csv --output articles.csv

# Export category hierarchy as JSON
python cli.py export-categories

# Export category hierarchy as CSV
python cli.py export-categories --format csv --output categories.csv

# Dry run to preview
python cli.py migrate --filter "category:HR" --dry-run

# Full migration with iframe processing
python cli.py migrate --process-iframes
```

### Module Direct Execution

You can also run modules directly:

```bash
# Run pre-processing (migration)
python -m pre_processing --limit 10 --dry-run

# Run post-processing
python -m post_processing make-subitem --child <id> --parent <id>
```

For complete CLI documentation, see [CLI Reference](docs/cli_reference.md).

## Usage Examples (Python API)

### Basic: List Articles

```python
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from config import Config

with ServiceNowClient(
    instance=Config.SERVICENOW_INSTANCE,
    username=Config.SERVICENOW_USERNAME,
    password=Config.SERVICENOW_PASSWORD
) as client:
    kb = KnowledgeBase(client)

    # List articles
    articles = kb.list_articles(limit=10)

    for article in articles:
        print(f"{article['number']}: {article['short_description']}")
```

### Get Article with HTML Content

```python
# Get specific article with full HTML content
article = kb.get_article('article_sys_id')

print(f"Title: {article['short_description']}")
print(f"HTML: {article['text']}")
print(f"Created: {article['sys_created_on']}")
```

### Get Attachments

```python
# Get and download attachments
attachments = kb.get_article_attachments(
    article_sys_id='abc123',
    download=True  # Downloads files to disk
)

for att in attachments:
    print(f"Downloaded: {att['file_name']} ({att['size_bytes']} bytes)")
```

### Get Category Hierarchy

```python
# Get article with full category path
article = kb.get_article_with_category_path('article_sys_id')

if article['category_path']:
    path = ' > '.join([c['label'] for c in article['category_path']])
    print(f"Category: {path}")
```

### Optimized: Bulk Migration (RECOMMENDED)

```python
# For migrating many articles - use pre-fetching!
kb = KnowledgeBase(client)

# ONE-TIME: Load all categories (1 API call)
kb.prefetch_all_categories()

# Get latest versions only (NEW: filters out old versions)
articles = kb.get_latest_articles_only(query='workflow_state=published')

for article in articles:
    # Get article with merged translations (NEW: includes original + translations)
    article_data = kb.get_article_with_translations(article['sys_id'])
    
    # Get category path
    article_with_cat = kb.get_article_with_category_path(article['sys_id'])
    article_data['category_path'] = article_with_cat['category_path']
    
    # Use merged_html instead of text (includes translations)
    html_content = article_data['merged_html']
    
    # Your migration logic here
    migrate_to_notion(article_data, html_content)
```

## Key Features

### 1. Version Filtering (NEW!)

ServiceNow articles can have multiple versions. The migration tool now automatically filters to only the **latest version** of each article:

```python
# Get only latest versions (filters out old versions automatically)
articles = kb.get_latest_articles_only(query='workflow_state=published')
```

**How it works:**
- Fetches all articles ordered by update time
- Deduplicates by article number
- Returns only the most recent version of each article

### 2. Translation Merging (NEW!)

Articles with translations are automatically merged into a single HTML document:

```python
# Get article with all translations merged
article = kb.get_article_with_translations('article_sys_id')

# Access merged HTML (includes original + all translations)
merged_html = article['merged_html']

# Check how many translations were found
translations_count = len(article['translations'])
```

**Merged HTML structure:**
```html
<div class="article-section" data-language="en">
  <h2 class="language-header">Original (en)</h2>
  <!-- Original article content -->
</div>
<hr class="language-separator" />
<div class="article-section" data-language="ja">
  <h2 class="language-header">Translation (ja)</h2>
  <!-- Japanese translation content -->
</div>
```

### 3. Category Hierarchy Support

Articles are organized in a hierarchical category structure. The tool automatically traverses the hierarchy:

```
Root Category
└─ Parent Category
   └─ Child Category
      └─ Article
```

Example output:
```
Article: KB0011256
Category Path: オフィス > 東京オフィス > イベント
```

### 4. Performance Optimization

**Problem:** Recursive category traversal = many API calls

**Solution:** Pre-fetching reduces API calls by 99%!

```python
# Without optimization: ~3,500 API calls for 1000 articles
# With pre-fetching: 1 API call total!

kb.prefetch_all_categories()  # Add this one line
```

See `docs/API_OPTIMIZATION_SUMMARY.md` for details.

### 5. HTML Parsing

Parse HTML content into structured data:

```python
parsed = kb.parse_article_html(html_content)

print(f"Text: {parsed['text']}")
print(f"Images: {len(parsed['images'])}")
print(f"Links: {len(parsed['links'])}")
print(f"Tables: {len(parsed['tables'])}")
```

## API Reference

### ServiceNowClient

```python
client = ServiceNowClient(instance, username, password, timeout=30)
client.query_table(table, query, fields, limit, offset)
client.get_record(table, sys_id, fields)
client.get_attachment(sys_id)
```

### KnowledgeBase

```python
kb = KnowledgeBase(client, download_dir='./downloads', enable_cache=True)

# Article operations
kb.list_articles(query, fields, limit, offset)
kb.get_article(sys_id, fields)
kb.get_all_articles_paginated(query, page_size)
kb.get_latest_articles_only(query, fields)  # NEW: Latest versions only
kb.get_article_with_translations(sys_id)    # NEW: Merge translations

# Category operations
kb.get_category(category_sys_id)
kb.get_category_hierarchy(category_sys_id)
kb.get_article_with_category_path(sys_id)

# Attachments
kb.get_article_attachments(article_sys_id, download=False)

# Optimization
kb.prefetch_all_categories()  # Highly recommended!
kb.get_cache_stats()
kb.clear_cache()
```

### HTMLParser

```python
parser = HTMLParser()
parsed = parser.parse_html(html_content)
markdown = parser.html_to_markdown(html_content)
```

## Documentation

- **[OPTIMIZATION_OPTIONS.md](docs/OPTIMIZATION_OPTIONS.md)** - Compare 6 optimization strategies
- **[API_OPTIMIZATION_SUMMARY.md](docs/API_OPTIMIZATION_SUMMARY.md)** - Quick optimization guide with code
- **[CATEGORY_HIERARCHY_EXPLANATION.md](docs/CATEGORY_HIERARCHY_EXPLANATION.md)** - Detailed algorithm explanation
- **[ALGORITHM_SUMMARY.txt](docs/ALGORITHM_SUMMARY.txt)** - Quick algorithm reference
- **[OPTIMIZATION_VISUAL.txt](docs/OPTIMIZATION_VISUAL.txt)** - Visual comparison diagrams

## Testing

Run individual test scripts:

```bash
# Test article listing
python tests/test_list_articles.py

# Test category functionality
python tests/test_categories.py
python tests/test_category_hierarchy.py

# Test performance optimization
python tests/test_optimization.py

# Test version filtering and translation merging (NEW!)
python tests/test_version_and_translation.py

# Test ZIP export
python tests/test_zip_export.py
```

## Performance

Based on real data from a ServiceNow instance with 593 categories:

| Operation | Without Optimization | With Pre-fetching |
|-----------|---------------------|-------------------|
| Setup | 0 calls | 1 call (2.34s) |
| 1000 articles | ~3,500 calls | 0 calls |
| Total Time | ~25-30 min | ~3-5 min |
| **Improvement** | **Baseline** | **99% fewer calls** |

## Migration Workflow

Complete workflow for ServiceNow → Notion migration with proper organization:

### Step 1: Export from ServiceNow to ZIP

```python
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from pre_processing.migrator import MigrationOrchestrator
from config import Config

# Initialize
with ServiceNowClient(...) as client:
    kb = KnowledgeBase(client)
    migrator = MigrationOrchestrator(kb, output_dir='./migration_output')

    # Export all articles to ZIP (includes latest versions + merged translations)
    results = migrator.export_all_to_zip(query='workflow_state=published')

    print(f"✅ Exported {results['total_articles']} articles")
    print(f"📦 ZIP file: {results['zip_path']}")
```

### Step 2: Import ZIP to Notion

1. Open Notion and navigate to the page where you want to import
2. Click the `...` menu → **Import**
3. Select **HTML** as import format
4. Upload the ZIP file created in Step 1
5. Notion will automatically create pages from the HTML files

**Result:** All articles are imported as individual Notion pages.

### Step 3: Post-Import Organization (Optional but Recommended)

After importing, organize pages into a database with proper category hierarchy:

**Prerequisites:**
- **Create a Notion database manually** with the required schema (see below)
- Get the database ID from the URL (example: `https://notion.so/workspace/DATABASE_ID?v=...`)
  - Note: The `data_source_id` is typically the same as the `database_id`
- Get your Notion API integration key

**Required Database Schema:**
Your database must have these properties:
- **Title** (title)
- **Type** (select: Category/Article)
- **Article Number** (rich_text)
- **Category Path** (rich_text)
- **Parent Task** (relation to same database)
- **Sub-tasks** (relation to same database)
- **Original Page ID** (rich_text)
- **Status** (select: Published/Draft/Archived)
- **Created Date** (date)
- **Updated Date** (date)

```python
from post_processing.post_import import NotionPostImport

# Initialize with Notion API key
organizer = NotionPostImport(api_key="your_notion_api_key")

# Specify your existing database ID (data_source_id is typically the same)
DATA_SOURCE_ID = "your_database_id_here"

# 1. Build category hierarchy in the database
category_paths = [
    ['IT', 'Applications', 'Figma'],
    ['IT', 'Applications', 'Slack'],
    ['Office', 'Tokyo', 'Access']
]
category_map = organizer.build_category_hierarchy(DATA_SOURCE_ID, category_paths)

# 2. Move imported articles to database
articles = [
    {
        'page_id': 'imported_page_id_1',
        'title': 'How to use Figma',
        'article_number': 'KB0001',
        'category_path': ['IT', 'Applications', 'Figma']
    },
    # ... more articles
]
results = organizer.organize_imported_articles(DATA_SOURCE_ID, articles, category_map)
```

**Result:** Articles organized in database with:
- Category hierarchy (task-subtask relations)
- Articles linked to categories
- Proper parent-child structure
- All metadata preserved

## Notion Database Structure

The post-import process requires an existing self-referencing database with the following schema:

### Database Properties

| Property | Type | Description |
|----------|------|-------------|
| **Title** | Title | Article or category name |
| **Type** | Select | "Category" or "Article" |
| **Article Number** | Rich Text | KB number from ServiceNow (e.g., KB0001) |
| **Category Path** | Rich Text | Full path (e.g., "IT > Applications > Figma") |
| **Parent Task** | Relation | Link to parent category/article (for hierarchy) |
| **Sub-tasks** | Relation | Links to child items (automatically populated) |
| **Original Page ID** | Rich Text | Reference to imported Notion page |
| **Status** | Select | Published / Draft / Archived |
| **Created Date** | Date | Original creation date |
| **Updated Date** | Date | Last update date |

### Hierarchy Structure

The category-subcategory-article structure is represented using **task-subtask relations**:

```
Database (Self-referencing)
├── IT (Category)
│   └── Parent Task: (none)
│   └── Sub-tasks: [Applications]
│   
├── Applications (Category)
│   └── Parent Task: [IT]
│   └── Sub-tasks: [Figma, Slack]
│   
├── Figma (Category)
│   └── Parent Task: [Applications]
│   └── Sub-tasks: [How to use Figma, Figma shortcuts]
│   
├── How to use Figma (Article)
│   └── Parent Task: [Figma]
│   └── Sub-tasks: (none)
│
└── Figma shortcuts (Article)
    └── Parent Task: [Figma]
    └── Sub-tasks: (none)
```

**Benefits of this structure:**
- ✅ Navigate hierarchy using Notion's built-in relation views
- ✅ Filter by category using database views
- ✅ See parent-child relationships clearly
- ✅ Maintain same structure as ServiceNow knowledge portal
- ✅ Easy to reorganize if needed

### Advanced: Custom Processing

If you need custom processing before export:

```python
kb = KnowledgeBase(client)
kb.prefetch_all_categories()

# Get latest versions only
articles = kb.get_latest_articles_only(query='workflow_state=published')

# Process each article
for article in articles:
    # Get article with merged translations
    full_article = kb.get_article_with_translations(article['sys_id'])
    
    # Get category path
    article_with_cat = kb.get_article_with_category_path(article['sys_id'])
    full_article['category_path'] = article_with_cat['category_path']
    
    # Use merged_html (includes translations if any)
    html_content = full_article['merged_html']
    
    # Custom processing here...
    # e.g., modify HTML, filter content, etc.
    
    # Get attachments
    attachments = kb.get_article_attachments(article['sys_id'], download=True)
```

## Requirements

- Python 3.8+
- requests
- beautifulsoup4
- lxml
- python-dotenv

## License

This project is for internal use in migrating ServiceNow knowledge base to Notion.

## Contributing

When adding new features:
1. Add core code to `servicenow/`
2. Add examples to `examples/`
3. Add tests to `tests/`
4. Add documentation to `docs/`

## Next Steps

Complete migration process:
1. ✅ Extract articles from ServiceNow (latest versions)
2. ✅ Merge translations into single HTML
3. ✅ Parse and clean HTML content
4. ✅ Download and organize attachments
5. ✅ Export to ZIP format
6. ⬜ Import ZIP to Notion (use Notion's built-in HTML importer)
7. ✅ Create database with category hierarchy (post-import module)
8. ✅ Move pages to database with proper organization (post-import module)
9. ⬜ Customize database views and properties as needed
