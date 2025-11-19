# Google Docs Export Naming Convention Update

## Overview

Updated the Google Docs export feature to include the article number in exported filenames, matching the HTML export naming convention.

## Changes Made

### 1. Updated Filename Pattern

**Before:**
- `{article_title}.docx`
- `{article_title}_ja.docx` (with translation)

**After:**
- `{article_number}-{article_title}.docx`
- `{article_number}-{article_title}_ja.docx` (with translation)

This matches the HTML export pattern: `ARTICLE_NUMBER-ARTICLE_NAME.html`

### 2. Files Modified

#### [`pre_processing/iframe_processor.py`](test_agentic/pre_processing/iframe_processor.py)

**Modified methods:**
- `process_google_docs_iframe()` - Added `article_number` parameter
- `process_html_iframes()` - Added `article_number` parameter
- `process_article_with_translations()` - Added `article_number` parameter
- `_process_translation_iframes()` - Added `article_number` parameter

**Key changes:**
- Lines 142-203: Added article number to filename generation
- Lines 285-291: Added article_number parameter to method signature
- Lines 347-349: Pass article_number to process_google_docs_iframe
- Lines 412-418: Added article_number parameter to process_article_with_translations
- Lines 483-489: Pass article_number to process_html_iframes
- Lines 551-557: Added article_number parameter to _process_translation_iframes
- Lines 597-602: Pass article_number to process_google_docs_iframe

#### [`pre_processing/migrator.py`](test_agentic/pre_processing/migrator.py)

**Modified section:**
- Lines 227-240: Extract article_number and pass to iframe processor

**Key changes:**
```python
article_number = original_article.get("number", "")
iframe_result = self.iframe_processor.process_article_with_translations(
    original_html=original_html,
    translations=translations,
    article_title=article_title,
    article_number=article_number,  # ← New parameter
)
```

#### [`examples/process_iframes.py`](test_agentic/examples/process_iframes.py)

**Modified section:**
- Lines 189-201: Pass article_number to process_html_iframes

**Key changes:**
```python
modified_html, process_summary = iframe_processor.process_html_iframes(
    html_content=html_content,
    article_title=article_title,
    download_docs=True,
    convert_slides=True,
    article_number=article_number,  # ← New parameter
)
```

### 3. Documentation Updated

#### [`docs/google_docs_setup.md`](test_agentic/docs/google_docs_setup.md)

Added new section: **File Naming Convention** (Lines 100-123)

Documents the naming pattern with examples:
```
KB0001-Getting_Started.html          ← HTML export
KB0001-Getting_Started.docx          ← Google Doc embedded in KB0001
KB0001-Getting_Started_ja.docx       ← Japanese translation of Google Doc
KB0001-Getting_Started_en.docx       ← English translation of Google Doc
```

## Benefits

1. **Consistency**: Google Docs now use the same naming pattern as HTML exports
2. **Easy Identification**: Filenames clearly show which article they belong to
3. **Better Organization**: Files can be sorted and grouped by article number
4. **Translation Clarity**: Language suffix added after article info maintains readability

## Example Filenames

### Without translations:
```
KB0001-Installation_Guide.html
KB0001-Installation_Guide.docx
```

### With translations:
```
KB0042-Security_Best_Practices.html
KB0042-Security_Best_Practices.docx      ← Original (English)
KB0042-Security_Best_Practices_ja.docx   ← Japanese translation
KB0042-Security_Best_Practices_zh.docx   ← Chinese translation
```

## Backward Compatibility

The changes are **backward compatible**:
- The `article_number` parameter is optional (defaults to empty string)
- If not provided, falls back to old naming pattern: `{article_title}.docx`
- Existing code without the parameter will continue to work

## Testing

Verified that:
- ✅ All Python files compile without syntax errors
- ✅ Filename sanitization works correctly
- ✅ Pattern matches HTML export naming convention
- ✅ Language suffixes are appended correctly

## Usage

The update is automatic when using the migration export:

```python
# Run full migration export
python -m examples.migration_example

# Google Docs will automatically be named: KB####-Article_Name.docx
```

Or in iframe processing mode:

```python
# Run iframe processing
python -m examples.process_iframes

# Select mode 2 (Process iframes - download docs, convert slides)
# Google Docs will be downloaded with article numbers in filenames
```

## Summary

This update ensures consistent file naming across all export formats (HTML and DOCX), making it easier to organize and identify files during the ServiceNow to Notion migration process.
