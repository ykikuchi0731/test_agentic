# Changelog - Version Filtering & Translation Merging

## Date: 2025-11-06

## Summary

Added two major features to the ServiceNow to Notion migration tool:

1. **Version Filtering**: Automatically migrate only the newest version of articles
2. **Translation Merging**: Merge original and translated articles into single HTML

---

## Changes Made

### 1. ServiceNow Knowledge Base Module (`servicenow/knowledge_base.py`)

#### Updated Fields
Added new fields to article retrieval:
- `version` - article version number
- `language` - article language
- `parent` - parent article reference (for translations)
- `translated_from` - original article reference (for translations)

#### New Methods

**`get_latest_articles_only(query, fields)`**
- Filters articles to return only the newest version of each article
- Deduplicates by article number
- Orders by `sys_updated_on` descending
- Returns latest version only

**`get_article_with_translations(sys_id)`**
- Gets article with all translated versions
- Merges original and translations into single HTML
- Returns article with `merged_html` field
- Includes `translations` list

**`_get_translations_for_article(article_sys_id)`** (private)
- Queries ServiceNow for all translations of an article
- Checks both `parent` and `translated_from` fields
- Returns list of translated article records

**`_merge_article_html(original, translations)`** (private)
- Merges original and translation HTML into single document
- Adds language section headers
- Adds separators between sections
- Returns combined HTML string

#### Merged HTML Structure
```html
<div class="article-section" data-language="en">
  <h2 class="language-header">Original (en)</h2>
  [Original content]
</div>
<hr class="language-separator" />
<div class="article-section" data-language="ja">
  <h2 class="language-header">Translation (ja)</h2>
  [Translation content]
</div>
```

---

### 2. Migration Orchestrator (`notion/migrator.py`)

#### Updated Methods

**`_fetch_all_articles(query)`**
- Changed from `get_all_articles_paginated()` to `get_latest_articles_only()`
- Now fetches only latest versions
- Added logging to indicate version filtering

**`_fetch_article_data(article_sys_id)`**
- Changed from `get_article_with_category_path()` to `get_article_with_translations()`
- Uses `merged_html` instead of `text` field
- Adds `translations` list to returned data
- Combines category path separately

---

### 3. Documentation Updates

#### README.md
- Added "Version Filtering (NEW!)" section
- Added "Translation Merging (NEW!)" section
- Updated usage examples
- Updated API reference
- Updated migration workflow
- Updated testing section

#### New Test Script
Created `/app/test_agentic/tests/test_version_and_translation.py`:
- Tests version filtering functionality
- Tests translation merging functionality
- Demonstrates complete workflow
- Shows before/after comparisons

---

## Usage Examples

### Get Latest Versions Only

```python
from servicenow.client import ServiceNowClient
from servicenow.knowledge_base import KnowledgeBase

with ServiceNowClient(...) as client:
    kb = KnowledgeBase(client)
    
    # Get only latest versions (filters out old versions)
    articles = kb.get_latest_articles_only(query='workflow_state=published')
    
    print(f"Found {len(articles)} unique articles (latest versions only)")
```

### Get Article with Translations Merged

```python
# Get article with all translations merged into single HTML
article = kb.get_article_with_translations('article_sys_id')

# Access merged HTML
merged_html = article['merged_html']

# Check translations
translations = article['translations']
print(f"Merged {len(translations)} translations into article")
```

### Complete Migration Workflow

```python
kb = KnowledgeBase(client)
kb.prefetch_all_categories()

# Get latest versions only
articles = kb.get_latest_articles_only(query='workflow_state=published')

for article in articles:
    # Get with merged translations
    full_article = kb.get_article_with_translations(article['sys_id'])
    
    # Get category path
    article_with_cat = kb.get_article_with_category_path(article['sys_id'])
    full_article['category_path'] = article_with_cat['category_path']
    
    # Use merged_html (includes translations)
    html_content = full_article['merged_html']
    
    # Parse and migrate
    parsed = kb.parse_article_html(html_content)
    attachments = kb.get_article_attachments(article['sys_id'], download=True)
    
    # Migrate to Notion
    migrate_to_notion(full_article, parsed, attachments)
```

---

## Testing

Run the new test script:

```bash
cd /app/test_agentic
python tests/test_version_and_translation.py
```

This will:
1. Fetch all articles (showing all versions)
2. Fetch latest versions only (showing deduplication)
3. Test translation merging on sample articles
4. Demonstrate complete workflow

---

## Benefits

### Version Filtering
- ✅ Avoids migrating duplicate content
- ✅ Ensures only current information is migrated
- ✅ Reduces data volume
- ✅ Faster migration process

### Translation Merging
- ✅ Keeps related content together
- ✅ Maintains context between languages
- ✅ Single page in Notion per article (all languages)
- ✅ Easier to manage and maintain

---

## Backward Compatibility

All existing functionality remains unchanged:
- `list_articles()` - Still works (now includes new fields)
- `get_article()` - Still works (now includes new fields)
- `get_all_articles_paginated()` - Still works (returns all versions)
- `get_article_with_category_path()` - Still works

New methods are additions, not replacements. You can choose whether to use:
- `get_all_articles_paginated()` or `get_latest_articles_only()`
- `get_article()` or `get_article_with_translations()`

---

## Migration from Old Code

If you have existing migration scripts, update them:

### Before:
```python
articles = kb.get_all_articles_paginated(query='workflow_state=published')
for article in articles:
    full_article = kb.get_article_with_category_path(article['sys_id'])
    html_content = full_article['text']
```

### After:
```python
articles = kb.get_latest_articles_only(query='workflow_state=published')
for article in articles:
    full_article = kb.get_article_with_translations(article['sys_id'])
    article_with_cat = kb.get_article_with_category_path(article['sys_id'])
    full_article['category_path'] = article_with_cat['category_path']
    html_content = full_article['merged_html']
```

---

## Files Modified

1. `/app/test_agentic/servicenow/knowledge_base.py` - Added new methods
2. `/app/test_agentic/notion/migrator.py` - Updated to use new methods
3. `/app/test_agentic/README.md` - Updated documentation
4. `/app/test_agentic/tests/test_version_and_translation.py` - New test script

---

## Known Limitations

1. **ServiceNow Field Names**: The `parent` and `translated_from` fields may vary by ServiceNow version. The code checks both.

2. **Language Detection**: Language is read from the `language` field. If this field is not populated in your ServiceNow instance, it will show as "Original" or "Unknown".

3. **Merged HTML Size**: If articles have many translations with large content, the merged HTML can be very large.

---

## Future Enhancements

Potential improvements for the future:

1. **Language Tabs**: Add JavaScript to create interactive language tabs in Notion
2. **Translation Status**: Track which articles have translations
3. **Language Statistics**: Report on language coverage
4. **Selective Translation**: Option to include only specific languages

---

## Questions or Issues?

If you encounter any issues with the new features:

1. Check that your ServiceNow instance has `version`, `language`, and `parent`/`translated_from` fields
2. Run the test script to verify functionality
3. Check logs for detailed information about what's happening
4. Review the examples in README.md

---

**All tests passing ✅**
**Ready for production use ✅**

