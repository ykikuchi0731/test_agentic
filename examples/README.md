# Examples

This directory contains example scripts demonstrating how to use the ServiceNow to Notion migration tool.

## 📚 Available Examples

### 1. Quick Start (`quick_start.py`)
**Best for:** First-time users, testing setup

Minimal example that exports 5 articles for testing.

```bash
python examples/quick_start.py
```

**What it does:**
- Validates configuration
- Exports 5 articles (for quick testing)
- Creates ZIP file for Notion import
- No iframe processing (faster)

---

### 2. Full Migration (`full_migration.py`)
**Best for:** Production migration, complete export

Complete migration with all features enabled.

```bash
python examples/full_migration.py
```

**What it does:**
- Fetches ALL articles from ServiceNow
- Optional iframe processing (Google Docs, Slides)
- Generates category hierarchy
- Creates complete ZIP export
- Interactive prompts for confirmation

---

## 🚀 Recommended Usage

For most use cases, we recommend using the **CLI tool** instead of example scripts:

### Basic Migration (5 articles for testing)
```bash
python cli.py migrate --limit 5
```

### Filtered Migration
```bash
# Export only IT category articles
python cli.py migrate --filter "category:IT"

# Export specific article
python cli.py migrate --filter "number:KB0001"

# Combine multiple filters
python cli.py migrate --filter "category:IT" --filter "workflow_state:published" --limit 100
```

### With Iframe Processing
```bash
python cli.py migrate --process-iframes --limit 10
```

### Dry Run (see what would be exported)
```bash
python cli.py migrate --dry-run
```

---

## 📖 More Examples

### Export Article List Only (No Downloads)
```bash
# Get metadata of all articles as CSV
python cli.py export-list --format csv --output articles.csv

# With filters
python cli.py export-list --filter "category:IT" --limit 50
```

### Post-Processing (After Import to Notion)
```bash
# Make a page a sub-item of another
python cli.py make-subitem --child <page_id> --parent <page_id>
```

### Visualize Category Hierarchy
```bash
python cli.py visualize
```

---

## 🔧 Module Direct Execution

You can also run modules directly:

```bash
# Run pre-processing migration
python -m pre_processing --limit 10 --dry-run

# Run post-processing
python -m post_processing make-subitem --child <id> --parent <id>
```

---

## 📝 Common CLI Options

All commands support these options:

| Option | Description | Example |
|--------|-------------|---------|
| `--limit N` | Process only N items | `--limit 10` |
| `--offset N` | Skip first N items | `--offset 20` |
| `--filter KEY:VALUE` | Filter by criteria | `--filter "category:IT"` |
| `--dry-run` | Show what would be done | `--dry-run` |
| `--verbose` | Enable debug logging | `-v` or `--verbose` |
| `--quiet` | Minimal output | `-q` or `--quiet` |
| `--output PATH` | Output file path | `--output results.csv` |
| `--format json\|csv` | Output format | `--format csv` |

---

## 🎯 Use Cases

### Testing Setup
```bash
# Quick test with 5 articles
python examples/quick_start.py

# Or use CLI
python cli.py migrate --limit 5 --dry-run
```

### Incremental Migration
```bash
# Export IT category first
python cli.py migrate --filter "category:IT"

# Then HR category
python cli.py migrate --filter "category:HR"
```

### Large-Scale Migration
```bash
# Export everything with iframe processing
python examples/full_migration.py

# Or use CLI with specific limits
python cli.py migrate --process-iframes --limit 1000
```

### Planning Migration
```bash
# Get article list to plan migration
python cli.py export-list --format csv --output articles.csv

# Review the CSV file
# Then migrate specific articles
python cli.py migrate --filter "number:KB0001"
```

---

## 💡 Tips

1. **Start Small**: Use `--limit 5` for initial testing
2. **Use Filters**: Target specific categories or articles
3. **Dry Run First**: Always use `--dry-run` to preview
4. **Check Logs**: Use `--verbose` to see detailed progress
5. **Incremental Migration**: Migrate in batches by category

---

## 📚 Documentation

For complete documentation, see:
- [CLI Reference](../docs/cli_reference.md) - Complete command reference
- [README](../README.md) - Main project documentation
- [Quick Start](../QUICK_START.md) - Getting started guide

---

## ❓ Need Help?

```bash
# Get help for main CLI
python cli.py --help

# Get help for specific command
python cli.py migrate --help
python cli.py export-list --help
python cli.py make-subitem --help
```
