# CLI Reference

Complete command-line interface reference for the ServiceNow to Notion migration tool.

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Global Options](#global-options)
- [Commands](#commands)
  - [migrate](#migrate)
  - [export-list](#export-list)
  - [export-categories](#export-categories)
  - [process-iframes](#process-iframes)
  - [make-subitem](#make-subitem)
  - [visualize](#visualize)
- [Filtering](#filtering)
- [Examples](#examples)
- [Module Execution](#module-execution)

---

## Installation

No installation required. The CLI tool is included in the project.

**Prerequisites:**
1. Python 3.8+
2. Configured `.env` file (copy from `env.example`)

---

## Quick Start

```bash
# Show all available commands
python cli.py --help

# Run migration with 5 articles (test)
python cli.py migrate --limit 5

# Export article list as CSV
python cli.py export-list --format csv --output articles.csv

# Make a Notion page a sub-item
python cli.py make-subitem --child <page_id> --parent <page_id>
```

---

## Global Options

These options are available for most commands:

### Data Limiting

| Option | Description | Example |
|--------|-------------|---------|
| `--limit N` | Process only N items | `--limit 10` |
| `--offset N` | Skip first N items before processing | `--offset 20` |

### Filtering

| Option | Description | Example |
|--------|-------------|---------|
| `--filter KEY:VALUE` | Filter items (can be used multiple times) | `--filter "category:IT"` |
| `--kb-base ID` | Filter by knowledge base ID | `--kb-base abc123` |

### Execution Mode

| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Show what would be done without executing | `--dry-run` |
| `-v, --verbose` | Enable verbose output (DEBUG logging) | `-v` |
| `-q, --quiet` | Minimal output (errors only) | `-q` |

### Output Settings

| Option | Description | Example |
|--------|-------------|---------|
| `--output PATH` | Output file path | `--output results.csv` |
| `--format {json,csv}` | Output format | `--format csv` |

---

## Commands

### migrate

Export ServiceNow knowledge base articles as ZIP file for Notion import.

**Usage:**
```bash
python cli.py migrate [OPTIONS]
```

**Options:**
- All [global options](#global-options)
- `--process-iframes` - Enable iframe processing (Google Docs, Slides)
- `--no-zip` - Don't create ZIP file (keep extracted files only)

**Examples:**
```bash
# Basic migration (all articles)
python cli.py migrate

# Test with 5 articles
python cli.py migrate --limit 5

# Migrate IT category only
python cli.py migrate --filter "category:IT"

# With iframe processing
python cli.py migrate --process-iframes --limit 10

# Dry run to see what would be migrated
python cli.py migrate --filter "category:IT" --dry-run

# Skip first 50 articles, process next 10
python cli.py migrate --offset 50 --limit 10
```

**Output:**
- Creates directory: `migration_output/servicenow_kb_export_YYYYMMDD_HHMMSS/`
- Contains:
  - `articles/` - HTML files and attachments
  - `category_hierarchy.json` - Category structure
  - `metadata.json` - Export metadata
  - `servicenow_kb_export_YYYYMMDD_HHMMSS.zip` - ZIP for Notion import

---

### export-list

Export article list with metadata (no file downloads).

**Usage:**
```bash
python cli.py export-list [OPTIONS]
```

**Options:**
- All [global options](#global-options)

**Examples:**
```bash
# Export all articles as CSV
python cli.py export-list --format csv --output articles.csv

# Export IT category as JSON
python cli.py export-list --filter "category:IT" --format json

# First 100 articles
python cli.py export-list --limit 100

# See what would be exported
python cli.py export-list --filter "category:HR" --dry-run
```

**Output:**
- CSV file with columns:
  - number, short_description, kb_category, workflow_state, language, etc.
- JSON file with complete article metadata

---

### export-categories

Export complete category hierarchy from ServiceNow Knowledge Base.

**Usage:**
```bash
python cli.py export-categories [OPTIONS]
```

**Options:**
- `--format {json,csv}` - Output format (default: json)
- `--output PATH` - Output file path (default: category_hierarchy.{format})
- `--dry-run` - Show what would be exported without executing
- `-v, --verbose` - Enable verbose output
- `-q, --quiet` - Minimal output (errors only)

**Examples:**
```bash
# Export as JSON (default)
python cli.py export-categories

# Export as CSV
python cli.py export-categories --format csv

# Custom output path
python cli.py export-categories --output my_categories.json

# CSV with custom path
python cli.py export-categories --format csv --output categories.csv

# Dry run to preview
python cli.py export-categories --dry-run

# Verbose output
python cli.py export-categories -v
```

**Output Formats:**

**JSON format** - Hierarchical structure:
```json
[
  {
    "name": "IT",
    "full_path": "IT",
    "parent": null,
    "ancestors": [],
    "level": 0,
    "article_count": 25,
    "total_article_count": 150,
    "children": [
      {
        "name": "Applications",
        "full_path": "IT > Applications",
        "parent": "IT",
        "ancestors": ["IT"],
        "level": 1,
        "article_count": 10,
        "total_article_count": 50,
        "children": [
          {
            "name": "Figma",
            "full_path": "IT > Applications > Figma",
            "parent": "IT > Applications",
            "ancestors": ["IT", "IT > Applications"],
            "level": 2,
            "article_count": 10,
            "total_article_count": 10,
            "children": []
          }
        ]
      }
    ]
  }
]
```

**Field definitions:**
- `name` - Category name (without parent path)
- `full_path` - Complete category path
- `parent` - Direct parent category path (null for root)
- `ancestors` - List of all ancestor paths (empty for root)
- `level` - Hierarchy depth (0 = root)
- `article_count` - Articles directly in this category
- `total_article_count` - Articles including all descendants
- `children` - Nested child categories

**CSV format** - Flattened structure:
```csv
name,full_path,parent,ancestors,level,article_count,total_article_count
IT,IT,(root),(none),0,25,150
Applications,IT > Applications,IT,IT,1,10,50
Figma,IT > Applications > Figma,IT > Applications,IT > IT > Applications,2,10,10
```

**Use cases:**
- Planning migration structure
- Understanding knowledge base organization
- Creating category mapping for import
- Analyzing content distribution

---

### process-iframes

Process iframes in article HTML (download Google Docs, convert Slides, etc.).

**Usage:**
```bash
python cli.py process-iframes --article-number ARTICLE_NUMBER [OPTIONS]
```

**Options:**
- All [global options](#global-options)
- `--article-number` (required) - Article number to process (e.g., KB0001)

**Examples:**
```bash
# Process iframes for specific article
python cli.py process-iframes --article-number KB0001

# Dry run
python cli.py process-iframes --article-number KB0001 --dry-run
```

**Note:** For full iframe processing during migration, use `migrate --process-iframes` instead.

---

### make-subitem

Make a Notion page a sub-item (child) of another page.

**Usage:**
```bash
python cli.py make-subitem --child PAGE_ID --parent PAGE_ID [OPTIONS]
```

**Options:**
- `--child` (required) - Child page ID
- `--parent` (required) - Parent page ID
- `--no-verify` - Skip verification that pages exist
- `-v, --verbose` - Enable verbose output
- `--dry-run` - Show what would be done

**Examples:**
```bash
# Make page A a sub-item of page B
python cli.py make-subitem --child abc123 --parent def456

# Dry run
python cli.py make-subitem --child abc123 --parent def456 --dry-run

# With verbose output
python cli.py make-subitem --child abc123 --parent def456 -v
```

**Requirements:**
- Both pages must be in the same Notion database
- Database must have "Sub-items" feature enabled
- Notion API key configured in `.env`

---

### visualize

Visualize category hierarchy from ServiceNow.

**Usage:**
```bash
python cli.py visualize [OPTIONS]
```

**Options:**
- `-v, --verbose` - Enable verbose output

**Examples:**
```bash
# Show category hierarchy
python cli.py visualize

# With verbose logging
python cli.py visualize -v
```

**Output:**
```
├─ IT (150 articles)
  ├─ Applications (50 articles)
    ├─ Figma (10 articles)
    ├─ Slack (15 articles)
  ├─ Hardware (30 articles)
├─ HR (80 articles)
  ├─ Benefits (25 articles)
  ├─ Policies (20 articles)
```

---

## Filtering

The `--filter` option accepts `KEY:VALUE` pairs and can be used multiple times.

### Supported Filter Keys

| Key | Description | Example |
|-----|-------------|---------|
| `category` | Article category (partial match, case-insensitive) | `--filter "category:IT"` |
| `number` | Article number (exact match) | `--filter "number:KB0001"` |
| `workflow_state` | Workflow state (exact match) | `--filter "workflow_state:published"` |
| `language` | Language code (exact match) | `--filter "language:en"` |

### Filter Examples

```bash
# Single filter
python cli.py migrate --filter "category:IT"

# Multiple filters (AND logic)
python cli.py migrate --filter "category:IT" --filter "workflow_state:published"

# Specific article
python cli.py migrate --filter "number:KB0001"

# IT category in English
python cli.py migrate --filter "category:IT" --filter "language:en"
```

---

## Examples

### Testing & Development

```bash
# Quick test with 5 articles
python cli.py migrate --limit 5 --dry-run

# Test IT category only
python cli.py migrate --filter "category:IT" --limit 10

# Verbose output for debugging
python cli.py migrate --limit 3 -v
```

### Planning Migration

```bash
# Export article list to CSV for review
python cli.py export-list --format csv --output articles.csv

# Visualize category structure
python cli.py visualize

# Dry run to see what would be migrated
python cli.py migrate --filter "category:IT" --dry-run
```

### Incremental Migration

```bash
# Migrate IT category
python cli.py migrate --filter "category:IT" --output it_export

# Then migrate HR category
python cli.py migrate --filter "category:HR" --output hr_export

# Migrate in batches of 100
python cli.py migrate --limit 100 --output batch_1
python cli.py migrate --offset 100 --limit 100 --output batch_2
```

### Production Migration

```bash
# Full migration with iframe processing
python cli.py migrate --process-iframes

# Large-scale migration with logging
python cli.py migrate --process-iframes -v 2>&1 | tee migration.log

# Migrate everything except drafts
python cli.py migrate --filter "workflow_state:published"
```

### Post-Processing

```bash
# After importing to Notion, organize pages
python cli.py make-subitem --child <page_id> --parent <page_id>

# Batch organization (use script)
for child in $(cat child_ids.txt); do
  python cli.py make-subitem --child $child --parent <parent_id>
done
```

---

## Module Execution

You can run modules directly using `python -m`:

### Pre-processing (Migration)

```bash
# Run migration module directly
python -m pre_processing --limit 10

# With all options
python -m pre_processing --filter "category:IT" --limit 50 --dry-run

# Enable iframe processing
python -m pre_processing --process-iframes --limit 10
```

### Post-processing

```bash
# Make sub-item
python -m post_processing make-subitem --child <id> --parent <id>

# With dry run
python -m post_processing make-subitem --child <id> --parent <id> --dry-run
```

**Advantages of module execution:**
- Shorter commands
- Direct access to module functionality
- Can be used in scripts

---

## Tips & Best Practices

### 1. Start Small
```bash
# Always test with --limit first
python cli.py migrate --limit 5
```

### 2. Use Dry Run
```bash
# Preview before executing
python cli.py migrate --filter "category:IT" --dry-run
```

### 3. Filter Strategically
```bash
# Migrate by category for better organization
python cli.py migrate --filter "category:IT"
python cli.py migrate --filter "category:HR"
```

### 4. Monitor Progress
```bash
# Use verbose logging and save to file
python cli.py migrate -v 2>&1 | tee migration.log
```

### 5. Incremental Processing
```bash
# Process in batches to avoid timeouts
python cli.py migrate --limit 100
python cli.py migrate --offset 100 --limit 100
```

---

## Troubleshooting

### Command not found
```bash
# Make sure you're in the project directory
cd /path/to/test_agentic

# Run with python explicitly
python cli.py --help
```

### Configuration errors
```bash
# Validate configuration
python -c "from config import Config; Config.validate_servicenow()"

# Check .env file exists
ls -la .env
```

### Permission errors
```bash
# Make CLI executable (optional)
chmod +x cli.py

# Run directly
./cli.py --help
```

### Import errors
```bash
# Ensure you're running from project root
pwd  # Should show /path/to/test_agentic

# Check Python path
python -c "import sys; print(sys.path)"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (configuration, execution, etc.) |
| 130 | Interrupted by user (Ctrl+C) |

---

## See Also

- [Quick Start Guide](../QUICK_START.md)
- [README](../README.md)
- [Examples](../examples/README.md)
- [Configuration Guide](./configuration.md)

---

## Need More Help?

```bash
# Show help for main CLI
python cli.py --help

# Show help for specific command
python cli.py migrate --help
python cli.py export-list --help
python cli.py make-subitem --help
```
