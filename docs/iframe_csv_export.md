# Iframe Analysis CSV Export

## Overview

The `process_iframes` example now automatically generates a CSV report of iframe analysis and processing results.

## Usage

### Analysis Mode (Report Only)

```bash
python -m examples.process_iframes
# Select mode: 1 (Analyze iframes - report only, no downloads)
```

**Output:**
- Console report with statistics
- CSV file: `migration_output/iframe_report_analysis_YYYYMMDD_HHMMSS.csv`

### Processing Mode (Download & Convert)

```bash
python -m examples.process_iframes
# Select mode: 2 (Process iframes - download docs, convert slides)
```

**Output:**
- Console report with statistics
- Downloaded Google Docs (DOCX files)
- CSV file: `migration_output/iframe_report_processed_YYYYMMDD_HHMMSS.csv`

## CSV Columns

### Analysis Mode CSV

| Column | Description | Example |
|--------|-------------|---------|
| `article_number` | ServiceNow article number | KB0000123 |
| `article_title` | Article title | "User Guide" |
| `has_iframes` | Contains iframes? | Yes, No |
| `total_iframes` | Total iframe count | 3 |
| `google_docs_count` | Number of Google Docs iframes | 2 |
| `google_slides_count` | Number of Google Slides iframes | 1 |
| `other_iframes_count` | Other iframe types | 0 |
| `is_iframe_only` | Article is iframe-only? | Yes, No |
| `google_docs_urls` | List of Google Docs URLs (semicolon-separated) | https://docs.google.com/document/d/abc123; https://docs.google.com/document/d/def456 |
| `google_slides_urls` | List of Google Slides URLs (semicolon-separated) | https://docs.google.com/presentation/d/xyz789 |

### Processing Mode CSV (Additional Columns)

In processing mode, the CSV includes two additional columns:

| Column | Description | Example |
|--------|-------------|---------|
| `docs_downloaded_count` | Number of docs successfully downloaded | 2 |
| `slides_converted_count` | Number of slides converted to links | 1 |

## Use Cases

### 1. Identify Articles with Embedded Content

Filter the CSV to find articles that rely heavily on embedded content:

```python
import pandas as pd

df = pd.read_csv('iframe_report_analysis_20240320.csv')

# Articles with iframes
with_iframes = df[df['has_iframes'] == 'Yes']
print(f"Articles with iframes: {len(with_iframes)}")

# Articles that are iframe-only (no other content)
iframe_only = df[df['is_iframe_only'] == 'Yes']
print(f"Iframe-only articles: {len(iframe_only)}")
```

### 2. Count Google Docs vs Slides

Analyze the distribution of embedded content types:

```python
# Total embedded Google Docs across all articles
total_docs = df['google_docs_count'].sum()
print(f"Total Google Docs embedded: {total_docs}")

# Total embedded Google Slides
total_slides = df['google_slides_count'].sum()
print(f"Total Google Slides embedded: {total_slides}")

# Articles by content type
docs_articles = df[df['google_docs_count'] > 0]
slides_articles = df[df['google_slides_count'] > 0]
print(f"Articles with Google Docs: {len(docs_articles)}")
print(f"Articles with Google Slides: {len(slides_articles)}")
```

### 3. Verify Processing Success

In processing mode, check that downloads succeeded:

```python
df = pd.read_csv('iframe_report_processed_20240320.csv')

# Should match: google_docs_count == docs_downloaded_count
df['download_success'] = df['google_docs_count'] == df['docs_downloaded_count']
failed = df[df['download_success'] == False]

if len(failed) > 0:
    print(f"⚠️  {len(failed)} articles had download issues:")
    print(failed[['article_number', 'article_title', 'google_docs_count', 'docs_downloaded_count']])
else:
    print("✅ All downloads successful!")
```

### 4. Extract URLs for Manual Review

Get a list of all embedded Google Docs for review:

```python
# Get all unique Google Docs URLs
all_urls = []
for urls in df['google_docs_urls'].dropna():
    if urls:  # Skip empty cells
        all_urls.extend(urls.split('; '))

unique_urls = set(all_urls)
print(f"Unique Google Docs found: {len(unique_urls)}")

# Save to text file for review
with open('google_docs_inventory.txt', 'w') as f:
    for url in sorted(unique_urls):
        f.write(url + '\n')
```

### 5. Plan Migration Strategy

Identify which articles need special attention:

```python
# Articles that are iframe-only (may need different migration approach)
iframe_only = df[df['is_iframe_only'] == 'Yes']

# Articles with multiple embedded docs (may need reorganization)
multiple_docs = df[df['google_docs_count'] > 1]

print(f"Articles needing special handling:")
print(f"  - Iframe-only: {len(iframe_only)}")
print(f"  - Multiple docs: {len(multiple_docs)}")
```

## Example CSV Content

### Analysis Mode

```csv
article_number,article_title,has_iframes,total_iframes,google_docs_count,google_slides_count,other_iframes_count,is_iframe_only,google_docs_urls,google_slides_urls
KB0000001,User Guide,Yes,2,2,0,0,Yes,https://docs.google.com/document/d/abc123; https://docs.google.com/document/d/def456,
KB0000002,Training Material,Yes,1,0,1,0,No,,https://docs.google.com/presentation/d/xyz789
KB0000003,FAQ,No,0,0,0,0,No,,
```

### Processing Mode

```csv
article_number,article_title,has_iframes,total_iframes,google_docs_count,google_slides_count,other_iframes_count,is_iframe_only,google_docs_urls,google_slides_urls,docs_downloaded_count,slides_converted_count
KB0000001,User Guide,Yes,2,2,0,0,Yes,https://docs.google.com/document/d/abc123; https://docs.google.com/document/d/def456,,2,0
KB0000002,Training Material,Yes,1,0,1,0,No,,https://docs.google.com/presentation/d/xyz789,0,1
KB0000003,FAQ,No,0,0,0,0,No,,,0,0
```

## Comparison with Full Migration CSV

### `process_iframes` CSV
- **Purpose:** Analyze iframe content specifically
- **Scope:** Only articles with iframes (or all if analyzing)
- **Focus:** Iframe detection and processing details
- **When to use:** Before full migration, to understand iframe content

### Full Migration CSV (`migration_example`)
- **Purpose:** Complete export summary
- **Scope:** All exported articles
- **Focus:** Overall export status, translations, attachments, special handling
- **When to use:** After full migration, to track complete export

## File Location

CSV files are saved to:
```
./migration_output/
├── iframe_report_analysis_20240320_143000.csv
└── iframe_report_processed_20240320_150000.csv
```

## Tips

### 1. Run Analysis First
Before doing a full processing run, use analysis mode to understand the scope:

```bash
# First: Analyze
python -m examples.process_iframes
# Select: 1 (Analyze)

# Review the CSV to see what you'll be processing

# Then: Process
python -m examples.process_iframes
# Select: 2 (Process)
```

### 2. Filter Before Opening in Excel
For large datasets, pre-filter the CSV before opening:

```python
import pandas as pd

df = pd.read_csv('iframe_report_analysis_20240320.csv')

# Save only articles with iframes
with_iframes = df[df['has_iframes'] == 'Yes']
with_iframes.to_csv('iframes_only.csv', index=False)

# Now open iframes_only.csv in Excel (much smaller file)
```

### 3. Compare Multiple Runs
Track changes over time:

```python
import pandas as pd

before = pd.read_csv('iframe_report_analysis_20240301.csv')
after = pd.read_csv('iframe_report_analysis_20240320.csv')

# Compare iframe counts
print(f"Before: {before['has_iframes'].value_counts()}")
print(f"After: {after['has_iframes'].value_counts()}")
```

## Summary

The iframe processing script now provides:

✅ **Automatic CSV generation** - No configuration needed
✅ **Two modes** - Analysis (report only) or Processing (download & convert)
✅ **Detailed iframe data** - URLs, counts, types
✅ **Processing verification** - Track download success
✅ **Easy analysis** - Open in Excel/Sheets/Python

This makes it easy to:
- Understand what embedded content exists
- Plan migration strategy
- Verify processing success
- Track iframe inventory
