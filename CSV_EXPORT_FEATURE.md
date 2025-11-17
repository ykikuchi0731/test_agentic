# CSV Export Feature - Quick Guide

## What's New

The migration export now **automatically creates a CSV report** alongside the ZIP file!

## What You Get

When you run:
```bash
python -m examples.migration_example
```

You'll get **two files**:

1. **ZIP file** - For Notion import
   ```
   migration_output/zips/notion_import_20240320_143000.zip
   ```

2. **CSV report** - For analysis and review ⭐ NEW!
   ```
   migration_output/notion_import_20240320_143000_report.csv
   ```

## CSV Contents

The CSV includes detailed information about every exported article:

### Key Columns

| Column | What It Shows |
|--------|---------------|
| `article_number` | KB number (e.g., KB0000123) |
| `article_title` | Article title |
| `has_translations` | Yes/No |
| `translation_count` | Number of translations |
| `category_path` | Full category hierarchy |
| `attachments_count` | Number of attachments |
| `has_iframes` | Contains Google Docs/Slides? |
| `google_docs_downloaded` | How many Docs were downloaded |
| `google_slides_converted` | How many Slides were converted |
| `requires_special_handling` | Needs manual review? |
| `special_handling_flag` | Why it needs review |

## Why This Is Useful

### 1. **Quick Summary**
Open in Excel/Sheets to see at a glance:
- How many articles were exported
- Which have translations
- Which have iframes
- Which need special attention

### 2. **Identify Issues**
Filter by `requires_special_handling = "Yes"` to see articles that need manual review before/after Notion import.

### 3. **Track Progress**
Keep CSV files to maintain a history of your exports.

### 4. **Share with Team**
Easy to share the CSV summary with stakeholders without sharing the full ZIP.

## Example Output

Terminal output now shows both files:
```
================================================================================
Export Results
================================================================================
Total articles: 150
ZIP created: True

📦 ZIP file: ./migration_output/zips/notion_import_20240320_143000.zip
📊 CSV report: ./migration_output/notion_import_20240320_143000_report.csv

✅ Export complete!

Next steps:
1. Review the CSV report for export summary
2. Open Notion and navigate to the page where you want to import
3. Click '...' menu → Import
4. Select 'HTML' as import format
5. Upload the ZIP file: ./migration_output/zips/notion_import_20240320_143000.zip
6. Notion will automatically create pages from the HTML files
```

## Quick Analysis

### In Excel/Google Sheets

1. Open the CSV file
2. Use filters to analyze:
   - Filter `has_translations` = "Yes" → See translated articles
   - Filter `requires_special_handling` = "Yes" → See articles needing attention
   - Sort by `google_docs_downloaded` → See iframe processing results

### In Python

```python
import pandas as pd

# Load the CSV
df = pd.read_csv('notion_import_20240320_143000_report.csv')

# Quick summary
print(f"Total articles: {len(df)}")
print(f"With translations: {df[df['has_translations'] == 'Yes'].shape[0]}")
print(f"With iframes: {df[df['has_iframes'] == 'Yes'].shape[0]}")
print(f"Needing special handling: {df[df['requires_special_handling'] == 'Yes'].shape[0]}")

# Articles with Google Docs
docs = df[df['google_docs_downloaded'] > 0]
print(f"\nArticles with Google Docs: {len(docs)}")
print(docs[['article_number', 'article_title', 'google_docs_downloaded']])
```

## Special Handling Articles

Articles marked with `requires_special_handling = "Yes"` typically means:

**Reason:** Article has Google Docs iframes AND translations

**What happened:**
- Downloaded separate DOCX files for each language
- Files named: `article_title.docx`, `article_title_ja.docx`, `article_title_en.docx`
- All included in ZIP as attachments

**What to do:**
1. Import the ZIP to Notion normally
2. Review these specific articles in Notion
3. The DOCX files will be attached to the page
4. You may want to organize them into separate pages per language

## Technical Details

### File Format
- **Encoding:** UTF-8 (supports all languages)
- **Delimiter:** Comma (,)
- **Headers:** Yes (first row)
- **Format:** Standard CSV

### Generation
- **When:** Automatically after ZIP creation
- **Location:** Same directory as ZIP (migration_output/)
- **Naming:** `{zip_filename}_report.csv`
- **Performance:** Negligible overhead (< 1 second for 1000 articles)

## No Configuration Needed

The CSV export is:
- ✅ Automatically enabled
- ✅ No setup required
- ✅ No performance impact
- ✅ Always created with every export

## Documentation

For detailed information about CSV columns and analysis examples, see:
- [docs/csv_export_format.md](docs/csv_export_format.md)

## Summary

**Before:**
- ✅ ZIP file created
- ❌ Export details only in terminal (lost after closing)
- ❌ Hard to analyze or share results

**After:**
- ✅ ZIP file created
- ✅ CSV report created
- ✅ Permanent record of export
- ✅ Easy to analyze and share
- ✅ Track special handling requirements
- ✅ Monitor iframe processing results

**No changes needed to your workflow** - just run the export as usual and you'll automatically get both files! 🎉
