# CSV Export Format Documentation

## Overview

When you run the complete migration export, a CSV report is automatically generated alongside the ZIP file. This CSV provides a detailed summary of all exported articles and their processing status.

## CSV Location

The CSV report is saved in the same directory as the ZIP file:

```
./migration_output/
├── zips/
│   └── notion_import_YYYYMMDD_HHMMSS.zip          # ZIP for Notion import
└── notion_import_YYYYMMDD_HHMMSS_report.csv       # CSV report
```

## CSV Columns

### Article Information

| Column | Description | Example |
|--------|-------------|---------|
| `article_number` | ServiceNow article number | KB0000123 |
| `article_title` | Article title/short description | "How to reset password" |
| `sys_id` | ServiceNow system ID (unique identifier) | abc123def456... |
| `workflow_state` | Article workflow state | published, draft |
| `language` | Primary language of article | en, ja, fr |
| `created_on` | Article creation timestamp | 2024-01-15 10:30:00 |
| `updated_on` | Last update timestamp | 2024-03-20 14:45:00 |
| `author` | Article author name | John Smith |

### Translation Information

| Column | Description | Example |
|--------|-------------|---------|
| `has_translations` | Whether article has translations | Yes, No |
| `translation_count` | Number of translations | 2 |

### Content Information

| Column | Description | Example |
|--------|-------------|---------|
| `category_path` | Full category hierarchy | IT Services > Security > Authentication |
| `attachments_count` | Number of attachments (images, files) | 5 |

### Iframe Processing

| Column | Description | Example |
|--------|-------------|---------|
| `has_iframes` | Whether article contains iframes | Yes, No |
| `google_docs_downloaded` | Number of Google Docs downloaded | 2 |
| `google_slides_converted` | Number of Google Slides converted to links | 1 |

### Special Handling

| Column | Description | Example |
|--------|-------------|---------|
| `requires_special_handling` | Whether manual review needed | Yes, No |
| `special_handling_flag` | Reason for special handling | "Article contains Google Docs iframe with 2 translation(s)..." |

## Use Cases

### 1. Quick Summary

Open the CSV in Excel/Sheets to get a quick overview of:
- Total articles exported
- Which articles have translations
- Which articles have iframes
- Which articles need special handling

### 2. Filter Articles Requiring Attention

Filter by `requires_special_handling = "Yes"` to see which articles need manual review in Notion after import.

**Common reasons for special handling:**
- Articles with Google Docs iframes AND translations
- These require separate import per language version

### 3. Verify Export Completeness

Check that all expected articles are included:
```python
import pandas as pd

df = pd.read_csv('notion_import_20240320_report.csv')
print(f"Total articles: {len(df)}")
print(f"With translations: {df['has_translations'].value_counts()}")
print(f"With iframes: {df['has_iframes'].value_counts()}")
```

### 4. Identify Iframe Processing Results

See which articles had Google Docs or Slides processed:
```python
# Articles with downloaded Google Docs
docs_downloaded = df[df['google_docs_downloaded'] > 0]
print(f"{len(docs_downloaded)} articles had Google Docs downloaded")

# Articles with converted Slides
slides_converted = df[df['google_slides_converted'] > 0]
print(f"{len(slides_converted)} articles had Slides converted")
```

### 5. Category Analysis

Analyze article distribution by category:
```python
# Group by top-level category
df['top_category'] = df['category_path'].str.split(' > ').str[0]
category_counts = df['top_category'].value_counts()
print(category_counts)
```

## Example CSV Content

```csv
article_number,article_title,sys_id,workflow_state,language,has_translations,translation_count,category_path,attachments_count,has_iframes,google_docs_downloaded,google_slides_converted,requires_special_handling,special_handling_flag,created_on,updated_on,author
KB0000001,Password Reset Guide,abc123,published,en,Yes,2,IT Services > Security,3,Yes,2,0,Yes,"Article contains Google Docs iframe with 2 translation(s). Downloaded 3 separate DOCX files instead of merging.",2024-01-15 10:30:00,2024-03-20 14:45:00,John Smith
KB0000002,VPN Setup Instructions,def456,published,en,No,0,IT Services > Network,5,No,0,0,No,,2024-02-01 09:00:00,2024-02-15 11:20:00,Jane Doe
KB0000003,Training Presentation,ghi789,published,en,Yes,1,Training > Onboarding,2,Yes,0,1,No,,2024-03-01 14:00:00,2024-03-10 16:30:00,Bob Wilson
```

## Opening the CSV

### Excel
1. Open Excel
2. File → Open
3. Select the CSV file
4. Data loads automatically with proper formatting

### Google Sheets
1. Open Google Sheets
2. File → Import
3. Upload → Select the CSV file
4. Choose "Import location: Replace current sheet"
5. Click "Import data"

### Python (pandas)
```python
import pandas as pd

df = pd.read_csv('notion_import_20240320_report.csv')
print(df.head())

# Get summary statistics
print(df.describe())

# Filter specific columns
important_cols = ['article_number', 'article_title', 'has_translations', 'requires_special_handling']
print(df[important_cols])
```

## CSV vs Standard Output

**Standard Output (Terminal):**
- Real-time progress updates
- Error messages
- Interactive prompts
- Final summary

**CSV Report:**
- Permanent record of export
- Detailed per-article information
- Easy to analyze and filter
- Can be shared with team
- Useful for tracking and auditing

## Tips

### 1. Save the CSV Report
Keep the CSV file alongside your ZIP export for future reference:
```
project_exports/
├── 2024-03-20_export/
│   ├── notion_import_20240320_143000.zip
│   └── notion_import_20240320_143000_report.csv
```

### 2. Check Special Handling First
Before importing to Notion, review articles marked with `requires_special_handling = "Yes"`:
- Read the `special_handling_flag` message
- Plan how to import these articles manually
- Usually involves importing language versions separately

### 3. Verify Counts
Cross-reference the CSV row count with the terminal output:
- Terminal shows: "Total articles: 150"
- CSV should have 150 data rows (plus 1 header row)

### 4. Track Export History
Use the CSV to maintain a history of exports:
```python
import glob
import pandas as pd

# Load all CSV reports
csv_files = glob.glob('migration_output/*_report.csv')
all_exports = []

for file in csv_files:
    df = pd.read_csv(file)
    df['export_date'] = file.split('_')[2]  # Extract date from filename
    all_exports.append(df)

combined = pd.concat(all_exports, ignore_index=True)
print(f"Total exports tracked: {len(csv_files)}")
print(f"Total articles across all exports: {len(combined)}")
```

## Troubleshooting

### CSV not created
**Problem:** ZIP file exists but no CSV file

**Solution:** Check the terminal output for error messages. The CSV is created after the ZIP, so if the export failed partway through, you may have a ZIP but no CSV.

### CSV has fewer rows than expected
**Problem:** CSV row count doesn't match "Total articles" in terminal

**Solution:** Check for errors in the terminal output. Some articles may have failed to export due to API errors or permission issues.

### Special characters garbled
**Problem:** Article titles with special characters (Japanese, Chinese, etc.) show as �����

**Solution:** Open CSV with UTF-8 encoding:
- Excel: Data → Get Data → From Text/CSV → File Origin: "65001: Unicode (UTF-8)"
- Google Sheets: Automatically handles UTF-8
- Python: `pd.read_csv('file.csv', encoding='utf-8')`

## Summary

The CSV export provides a comprehensive, permanent record of your migration export that complements the ZIP file. Use it to:
- ✅ Verify export completeness
- ✅ Identify articles requiring special handling
- ✅ Analyze content distribution
- ✅ Track iframe processing results
- ✅ Maintain export history
- ✅ Share export summary with team

The CSV is automatically generated with every export - no additional configuration needed!
