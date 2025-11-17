# Iframe Analysis CSV Export - Quick Guide

## What's New

The `process_iframes` example now **automatically creates a CSV report** when analyzing or processing iframes!

## How It Works

### Analysis Mode (No Downloads)

```bash
python -m examples.process_iframes
# Select: 1 (Analyze iframes - report only, no downloads)
```

**You Get:**
- 📊 Console summary
- 📄 CSV report: `migration_output/iframe_report_analysis_YYYYMMDD_HHMMSS.csv`

### Processing Mode (Download & Convert)

```bash
python -m examples.process_iframes
# Select: 2 (Process iframes - download docs, convert slides)
```

**You Get:**
- 📊 Console summary
- 📦 Downloaded Google Docs (DOCX files)
- 📄 CSV report: `migration_output/iframe_report_processed_YYYYMMDD_HHMMSS.csv`

## CSV Contents

### In Both Modes

| Column | What It Shows |
|--------|---------------|
| `article_number` | KB number |
| `article_title` | Article title |
| `has_iframes` | Yes/No |
| `total_iframes` | Total count |
| `google_docs_count` | How many Google Docs |
| `google_slides_count` | How many Slides |
| `is_iframe_only` | Article is only iframe? |
| `google_docs_urls` | List of Doc URLs |
| `google_slides_urls` | List of Slide URLs |

### Additional in Processing Mode

| Column | What It Shows |
|--------|---------------|
| `docs_downloaded_count` | Successfully downloaded |
| `slides_converted_count` | Successfully converted |

## Why This Is Useful

### 1. **Understand Your Content**
Before migration, see exactly what embedded content exists:
- How many articles have iframes?
- Google Docs vs Slides distribution
- Which articles are iframe-only?

### 2. **Verify Processing**
After processing, confirm everything downloaded:
```python
import pandas as pd
df = pd.read_csv('iframe_report_processed_20240320.csv')

# Check if all docs downloaded successfully
df['success'] = df['google_docs_count'] == df['docs_downloaded_count']
print(df[df['success'] == False])  # Show any failures
```

### 3. **Extract URLs**
Get a list of all embedded content for review:
```python
df = pd.read_csv('iframe_report_analysis_20240320.csv')

# All Google Docs URLs
all_urls = []
for urls in df['google_docs_urls'].dropna():
    all_urls.extend(urls.split('; '))

print(f"Total embedded Google Docs: {len(all_urls)}")
```

### 4. **Plan Migration**
Identify articles needing special attention:
- Iframe-only articles (may need different approach)
- Articles with multiple embedded docs
- Articles with Slides (need manual review)

## Example Output

```
================================================================================
Processing Summary
================================================================================

📊 Overall Statistics:
  Total articles processed: 150
  Articles with iframes: 25
  Iframe-only articles: 5
  Total iframes found: 30
    - Google Docs: 20
    - Google Slides: 10

✅ Processing Results:
  Google Docs downloaded: 20
  Google Slides converted: 10

================================================================================
Generating CSV Report
================================================================================

📊 CSV report saved to: ./migration_output/iframe_report_processed_20240320_143000.csv
You can open this file in Excel or Google Sheets for analysis

================================================================================
```

## Quick Analysis Examples

### In Excel/Google Sheets

1. Open the CSV file
2. Use filters to analyze:
   - Filter `has_iframes` = "Yes" → See all articles with embedded content
   - Filter `is_iframe_only` = "Yes" → See articles that are only iframes
   - Sort by `google_docs_count` → See articles with most embedded docs

### In Python

```python
import pandas as pd

df = pd.read_csv('iframe_report_analysis_20240320.csv')

# Quick stats
print(f"Total articles: {len(df)}")
print(f"With iframes: {df['has_iframes'].value_counts()}")
print(f"Iframe-only: {df[df['is_iframe_only'] == 'Yes'].shape[0]}")

# Distribution
print(f"\nTotal embedded content:")
print(f"  Google Docs: {df['google_docs_count'].sum()}")
print(f"  Google Slides: {df['google_slides_count'].sum()}")
```

## Comparison: Two Types of CSV Reports

### Iframe Analysis CSV (`process_iframes`)
- **Focus:** Iframe-specific details
- **When:** Before/during iframe analysis
- **Contains:** URLs, types, iframe-only status
- **Best for:** Understanding embedded content

### Full Migration CSV (`migration_example`)
- **Focus:** Complete export summary
- **When:** After full migration
- **Contains:** All articles, translations, attachments, special handling
- **Best for:** Tracking complete export

Both are useful for different purposes!

## Workflow Recommendation

1. **Run iframe analysis first:**
   ```bash
   python -m examples.process_iframes  # Mode 1: Analyze
   ```

2. **Review the CSV:**
   - See what embedded content exists
   - Plan how to handle it
   - Identify potential issues

3. **Run full processing:**
   ```bash
   python -m examples.process_iframes  # Mode 2: Process
   ```

4. **Verify success:**
   - Check CSV: `docs_downloaded_count` matches `google_docs_count`
   - Review any errors

5. **Run complete migration:**
   ```bash
   python -m examples.migration_example
   ```

## No Configuration Needed

The CSV export is:
- ✅ Automatically enabled
- ✅ Works in both modes (analyze and process)
- ✅ Saved to `migration_output/` directory
- ✅ Timestamped filename
- ✅ UTF-8 encoded (supports all languages)

## Documentation

For detailed information and analysis examples, see:
- [docs/iframe_csv_export.md](docs/iframe_csv_export.md)

## Summary

**Answer to your question:** Yes! The `process_iframes` script now creates a CSV report in both analysis and processing modes.

**What you get:**
- Analysis mode: CSV with iframe detection results
- Processing mode: CSV with detection + download/conversion results

**No changes needed** - just run the script as usual and you'll automatically get a CSV report! 🎉
