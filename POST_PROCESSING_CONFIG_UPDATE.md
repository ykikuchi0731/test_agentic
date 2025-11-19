# Post-Processing Config Integration

## Overview

Updated all post-processing modules and examples to use the `Config` class for loading environment variables from `.env` file, eliminating the need for users to manually export environment variables.

## What Changed

### Before (Manual Export Required)

Users had to manually export environment variables:

```bash
export NOTION_API_KEY='secret_xxx...'
python -m examples.make_page_subitem
```

### After (Automatic from .env)

Users just add to `.env` file and run:

```bash
# In .env file:
NOTION_API_KEY=secret_xxx...

# Run directly - no export needed!
python -m examples.make_page_subitem
```

## Files Updated

### 1. examples/make_page_subitem.py

**Changes:**
- ✅ Uses `Config.validate_notion()` to check configuration
- ✅ Reads `Config.NOTION_API_KEY` automatically from `.env`
- ✅ Clear error messages if config is missing
- ✅ Optional API key parameter for flexibility

**Before:**
```python
import os

api_key = os.getenv("NOTION_API_KEY")
if not api_key:
    print("❌ Error: NOTION_API_KEY environment variable not set")
    print("Please set your Notion integration API key:")
    print("  export NOTION_API_KEY='secret_xxx...'")
    return
```

**After:**
```python
from config import Config, ConfigurationError

try:
    Config.validate_notion()
except ConfigurationError as e:
    print("❌ Configuration Error")
    print(str(e))
    return

# Use Config
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

### 2. examples/post_import_example.py

**Changes:**
- ✅ Uses `Config.validate_notion()` for validation
- ✅ Reads `Config.NOTION_API_KEY` and `Config.NOTION_DATABASE_ID` from `.env`
- ✅ No more hardcoded placeholder values
- ✅ Better error messages

**Before:**
```python
NOTION_API_KEY = "secret_your_api_key_here"
DATA_SOURCE_ID = "your_database_id_here"

if NOTION_API_KEY == "secret_your_api_key_here":
    print("\n⚠️  Please update NOTION_API_KEY in the script!")
    return
```

**After:**
```python
from config import Config, ConfigurationError

try:
    Config.validate_notion()
except ConfigurationError as e:
    print("❌ Configuration Error")
    print(str(e))
    return

# Get from Config
NOTION_API_KEY = Config.NOTION_API_KEY
DATA_SOURCE_ID = Config.NOTION_DATABASE_ID
```

### 3. docs/page_hierarchy.md

**Updated sections:**
- Setup instructions now use `.env` file
- Removed `export` commands
- Added examples using `Config` class
- Clarified that Config is recommended approach

## Benefits

### 1. No Manual Exports

**Before:**
```bash
export NOTION_API_KEY='secret_xxx...'
export NOTION_DATABASE_ID='database_id...'
python script.py
```

**After:**
```bash
# Just edit .env once
python script.py  # Works immediately!
```

### 2. Consistent with Pre-Processing

All modules now use the same configuration approach:

```python
from config import Config

# Pre-processing
Config.validate_all(['servicenow'])
kb = KnowledgeBase(
    instance=Config.SERVICENOW_INSTANCE,
    username=Config.SERVICENOW_USERNAME,
    password=Config.SERVICENOW_PASSWORD
)

# Post-processing
Config.validate_all(['notion'])
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

### 3. Better Error Messages

**Before:**
```
❌ Error: NOTION_API_KEY environment variable not set

Please set your Notion integration API key:
  export NOTION_API_KEY='secret_xxx...'
```

**After:**
```
❌ Configuration Error

Notion API configuration is incomplete:
  - NOTION_API_KEY is required

Please set the required environment variables in your .env file.
See env.example for reference.

To get your Notion API key:
  1. Go to https://www.notion.so/my-integrations
  2. Create a new integration
  3. Copy the Internal Integration Token (starts with 'secret_')
```

### 4. Validation Before Execution

```python
from config import Config, ConfigurationError

try:
    Config.validate_notion()
    # Only proceeds if config is valid
    hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    exit(1)
```

### 5. Flexibility

API key can still be provided explicitly if needed:

```python
from examples.make_page_subitem import make_subitem_programmatic

# Use Config (.env)
result = make_subitem_programmatic(
    child_page_id="abc123",
    parent_page_id="def456"
)

# Or provide explicitly
result = make_subitem_programmatic(
    child_page_id="abc123",
    parent_page_id="def456",
    api_key="secret_explicit_key"
)
```

## Usage Examples

### Interactive Script

```bash
# 1. Add to .env
echo "NOTION_API_KEY=secret_xxx..." >> .env

# 2. Run directly - no export needed!
python -m examples.make_page_subitem
```

### Programmatic Usage

```python
from config import Config
from post_processing.page_hierarchy import NotionPageHierarchy

# Validate config (reads from .env)
Config.validate_notion()

# Use Config
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)

result = hierarchy.make_subitem(
    child_page_id="abc123",
    parent_page_id="def456"
)
```

### Batch Processing

```python
from config import Config
from post_processing.page_hierarchy import NotionPageHierarchy

# Validate once
Config.validate_notion()

# Reuse Config for all operations
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)

for page in pages_to_organize:
    result = hierarchy.make_subitem(
        child_page_id=page["child"],
        parent_page_id=page["parent"]
    )
    print(f"{'✅' if result['success'] else '❌'} {page['child']}")
```

## Migration Guide

### For Users

**If you were using:**
```bash
export NOTION_API_KEY='secret_xxx...'
python script.py
```

**Now just:**
1. Add to `.env`:
   ```bash
   NOTION_API_KEY=secret_xxx...
   ```

2. Run script:
   ```bash
   python script.py  # No export needed!
   ```

### For Developers

**Update your code from:**
```python
import os

api_key = os.getenv("NOTION_API_KEY")
if not api_key:
    print("Error: NOTION_API_KEY not set")
    return

hierarchy = NotionPageHierarchy(api_key=api_key)
```

**To:**
```python
from config import Config, ConfigurationError

try:
    Config.validate_notion()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    return

hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

## Testing

All examples tested and verified:

```bash
✅ examples/make_page_subitem.py compiles successfully
✅ examples/post_import_example.py compiles successfully
✅ Config validation works correctly
✅ Error messages are helpful
✅ .env file is auto-loaded
✅ No manual export needed
```

## Backward Compatibility

✅ **Fully backward compatible**

API keys can still be provided explicitly:

```python
# Still works - provide API key directly
hierarchy = NotionPageHierarchy(api_key="secret_xxx")

# New recommended way - use Config
Config.validate_notion()
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

## Configuration File Structure

### .env (User's file)

```bash
# Notion API Configuration
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=your_database_id_here
```

### env.example (Template)

```bash
# ============================================================================
# Notion API Configuration (REQUIRED for post-processing)
# ============================================================================
# Your Notion integration API key (starts with 'secret_')
# Get it from: https://www.notion.so/my-integrations
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Database ID for organizing imported content
# Get it from the database URL: https://notion.so/{workspace}/{DATABASE_ID}?v=...
NOTION_DATABASE_ID=
```

## Error Handling

### Missing .env File

```
================================================================================
⚠️  WARNING: .env file not found
================================================================================

Please create a .env file in the project root with your configuration.

Steps:
  1. Copy env.example to .env:
     cp env.example .env

  2. Edit .env and add your credentials:
     - ServiceNow instance, username, password
     - Notion API key (if using post-processing)
     - Other optional settings

  3. Run your script again

================================================================================
```

### Missing NOTION_API_KEY

```
❌ Configuration Error

Notion API configuration is incomplete:
  - NOTION_API_KEY is required

Please set the required environment variables in your .env file.
See env.example for reference.

To get your Notion API key:
  1. Go to https://www.notion.so/my-integrations
  2. Create a new integration
  3. Copy the Internal Integration Token (starts with 'secret_')
```

### Invalid API Key Format

```
❌ Configuration Error

Notion API configuration is incomplete:
  - NOTION_API_KEY must start with 'secret_'
```

## Summary

Post-processing modules now:
- ✅ Automatically load configuration from `.env`
- ✅ No manual `export` commands needed
- ✅ Consistent with pre-processing modules
- ✅ Better error messages with setup instructions
- ✅ Validate configuration before execution
- ✅ Maintain backward compatibility
- ✅ Support both Config and explicit API keys

This makes the tool much easier to use and more professional! 🎉
