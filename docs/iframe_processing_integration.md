# Iframe Processing Integration Guide

This document explains how iframe processing is integrated into the complete ZIP export workflow.

## Overview

The iframe processor is fully integrated into the migration pipeline and will automatically:
- Detect Google Docs and Slides iframes in article HTML
- Download Google Docs as DOCX files
- Convert Google Slides iframes to anchor links
- Handle translated articles with iframes separately (no merging)
- Flag articles requiring special handling for manual review

## Architecture Flow

```
migration_example.py
    ↓
GoogleDocsBrowserExporter (optional)
    ↓
MigrationOrchestrator
    ↓
_fetch_article_data()
    ↓
IframeProcessor
    ↓
process_article_with_translations()
    ↓
ZIP Export with processed content
```

## How It Works

### 1. Initialization (migration_example.py)

When you run `python -m examples.migration_example`, the script:

1. Asks if you want to enable iframe processing
2. If yes, starts a browser and prompts you to log in to Google
3. Initializes `MigrationOrchestrator` with iframe processing enabled

```python
google_docs_exporter = GoogleDocsBrowserExporter(
    download_dir=Config.BROWSER_DOWNLOAD_DIR,
    browser_type=Config.BROWSER_TYPE,
    headless=Config.BROWSER_HEADLESS,
    timeout=Config.BROWSER_TIMEOUT,
)

migrator = MigrationOrchestrator(
    servicenow_kb=kb,
    output_dir=Config.MIGRATION_OUTPUT_DIR,
    google_docs_exporter=google_docs_exporter,
    process_iframes=True,
)
```

### 2. Article Processing (migrator.py)

For each article, the migrator's `_fetch_article_data()` method:

1. **Fetches original article** (NOT merged yet)
   ```python
   original_article = self.servicenow_kb.get_article(article_sys_id)
   ```

2. **Fetches translations separately**
   ```python
   translations = self.servicenow_kb._get_translations_for_article(article_sys_id)
   ```

3. **Processes iframes BEFORE merging** (if enabled)
   ```python
   if self.process_iframes and self.iframe_processor:
       iframe_result = self.iframe_processor.process_article_with_translations(
           original_html=original_html,
           translations=translations,
           article_title=article_title,
       )
   ```

4. **Handles two cases:**

   **Case A: Special Handling Required (Google Docs iframes detected)**
   - Downloads separate DOCX files for each language
   - Uses language suffixes: `article_ja.docx`, `article_en.docx`
   - **Does NOT merge** original and translations
   - Sets flag: `requires_special_handling = True`
   - Adds flag message for manual review

   **Case B: No Special Handling (Safe to merge)**
   - Processes iframes in original and translations
   - Merges the processed HTML
   - Downloads any embedded docs as attachments

### 3. Iframe Detection and Processing (iframe_processor.py)

The `process_article_with_translations()` method:

1. **Detects iframes** using regex patterns
2. **Checks if Google Docs iframes exist** in original OR translations
3. **If Google Docs found:**
   - Downloads each version separately with language tags
   - Returns `requires_special_handling: True`
   - Provides flag message for user

4. **If only Slides or other iframes:**
   - Converts to anchor links
   - Safe to merge translations
   - Returns `requires_special_handling: False`

### 4. Google Docs Download (google_docs_browser_exporter.py)

When a Google Docs iframe is detected:

1. Extracts file ID from iframe URL
2. Navigates to Google Doc in browser
3. Downloads as DOCX using `/export?format=docx` endpoint
4. Saves with language suffix if translation

## Special Handling for Translations

### Problem
When an article contains a Google Docs iframe and has translations, we cannot simply merge them because:
- Each language version may have a different Google Doc
- Merging would lose the separate documents
- Users need to import each language version separately in Notion

### Solution
The iframe processor detects this scenario and:

1. **Downloads all versions separately:**
   - Original: `article_name.docx`
   - Japanese: `article_name_ja.docx`
   - English: `article_name_en.docx`

2. **Does NOT merge translations**
   - Keeps original HTML only
   - Adds all downloaded docs as attachments

3. **Flags for manual review:**
   - Sets `requires_special_handling: True`
   - Provides message: "Google Docs iframes with translations require manual import in Notion"

## Usage

### Complete Export with Iframe Processing

```bash
python -m examples.migration_example
```

Interactive prompts will guide you through:
1. Enabling iframe processing (yes/no)
2. Browser login (if enabled)
3. Confirming export

### Iframe Analysis Only

To analyze iframes without exporting:

```bash
python -m examples.process_iframes
```

This provides a report of:
- Which articles contain iframes
- Google Docs vs. Slides count
- Iframe-only articles
- No downloads performed

### Article List Export (No Iframe Processing)

For metadata only (fast, no iframe processing):

```bash
python -m examples.export_article_list
```

## Configuration

Configure iframe processing in `.env`:

```bash
# Browser automation settings
BROWSER_DOWNLOAD_DIR=./google_docs_exports
BROWSER_HEADLESS=false              # Set to 'true' for headless mode
BROWSER_TYPE=chrome                 # chrome, firefox, or edge
BROWSER_TIMEOUT=30                  # seconds
```

## Output

### ZIP Structure

When iframe processing is enabled, the ZIP will contain:

```
notion_import_[timestamp].zip
├── article_1.html              # Processed HTML (iframes removed/converted)
├── article_1_attachment1.png   # Regular attachments
├── article_1_googledoc.docx    # Downloaded from iframe
├── article_2_ja.html           # Japanese version (with iframe)
├── article_2_ja_googledoc.docx # Japanese Google Doc
├── article_2_en.html           # English version (with iframe)
└── article_2_en_googledoc.docx # English Google Doc
```

### Special Handling Flags

Articles requiring special handling will have metadata in the export results:

```python
{
    "requires_special_handling": True,
    "special_handling_flag": "Google Docs iframes with translations require manual import in Notion",
    "downloaded_google_docs": [
        "./google_docs_exports/article_title.docx",
        "./google_docs_exports/article_title_ja.docx",
        "./google_docs_exports/article_title_en.docx"
    ]
}
```

## Verification

To verify iframe processing is working:

1. **Run complete export with iframe processing enabled:**
   ```bash
   python -m examples.migration_example
   ```

2. **Check the output:**
   - Look for "Iframe processor initialized" in logs
   - Check for "Processing iframes in article: [title]" messages
   - Verify DOCX files are downloaded to `BROWSER_DOWNLOAD_DIR`

3. **Inspect the ZIP:**
   - Open the generated ZIP file
   - Verify Google Docs are included as .docx attachments
   - Check that iframe HTML has been removed or converted

## Troubleshooting

### Browser fails to start
- Check ChromeDriver/GeckoDriver is installed
- Try different browser type in config
- Check browser version compatibility

### Google Docs not downloading
- Verify you logged into Google account in browser
- Check you have access to the documents
- Verify download directory permissions

### Iframes not detected
- Check article HTML contains iframe tags
- Verify iframe URLs match Google Docs/Slides patterns
- Enable debug logging to see detection details

## Technical Details

### Iframe Detection Patterns

Google Docs:
```regex
https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)
```

Google Slides:
```regex
https://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)
```

### Download URL Format

Google Docs download:
```
https://docs.google.com/document/d/{file_id}/export?format=docx
```

### Language Suffix Convention

- Original: `filename.docx`
- Japanese: `filename_ja.docx`
- English: `filename_en.docx`
- French: `filename_fr.docx`
- German: `filename_de.docx`
- Spanish: `filename_es.docx`

## Migration Flow Summary

1. **User runs**: `python -m examples.migration_example`
2. **Script asks**: Enable iframe processing?
3. **If yes**: Browser starts, user logs in
4. **Export begins**: Migrator processes each article
5. **For each article**:
   - Fetch original + translations
   - Process iframes (if any)
   - Download Google Docs (if any)
   - Merge or keep separate (depending on iframe type)
6. **Create ZIP**: All articles + attachments + Google Docs
7. **Browser closes**: Cleanup
8. **User imports**: ZIP file into Notion

## Conclusion

The iframe processor is fully integrated into the complete export workflow through the `MigrationOrchestrator`. When enabled, it automatically handles all iframe processing during the ZIP export process, ensuring Google Docs and Slides are properly handled for Notion import.

No additional steps are required - just enable iframe processing when prompted, and the system will handle everything automatically.
