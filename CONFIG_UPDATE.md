# Configuration System Update

## Overview

Updated the configuration system to enforce required environment variables and added comprehensive Notion API support with module-specific validation.

## What Changed

### 1. Enhanced config.py

**New Features:**
- ✅ **Notion API configuration** - `NOTION_API_KEY` and `NOTION_DATABASE_ID`
- ✅ **Module-specific validation** - Validate only what you're using
- ✅ **ConfigurationError exception** - Clear error messages
- ✅ **Auto .env file check** - Warns if .env is missing
- ✅ **Config summary printer** - Debug configuration with secrets masked
- ✅ **Flexible validation** - Choose to raise errors or return bool

**New Configuration Variables:**
```python
NOTION_API_KEY = os.getenv('NOTION_API_KEY', '').strip()
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '').strip()
```

**New Validation Methods:**
```python
Config.validate_servicenow()      # Validate ServiceNow config
Config.validate_notion()           # Validate Notion config
Config.validate_google_browser()   # Validate browser config
Config.validate_all(['notion'])    # Validate specific modules
Config.check_env_file()            # Check if .env exists
Config.print_config_summary()      # Print config for debugging
```

### 2. Updated env.example

**New sections added:**
- Notion API Configuration with instructions
- Detailed comments for each variable
- Security warnings for sensitive credentials
- Instructions on how to get API keys

**Structure:**
```
============================================================================
ServiceNow Configuration (REQUIRED for pre-processing)
============================================================================
SERVICENOW_INSTANCE=...
SERVICENOW_USERNAME=...
SERVICENOW_PASSWORD=...

============================================================================
Notion API Configuration (REQUIRED for post-processing)
============================================================================
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...

[... and more sections ...]
```

### 3. New Documentation

Created [docs/configuration.md](test_agentic/docs/configuration.md) with:
- Complete configuration guide
- How to get Notion API keys
- Validation examples
- Troubleshooting guide
- Security best practices
- Reference table of all variables

## Usage Examples

### Basic Validation

```python
from config import Config, ConfigurationError

# Validate ServiceNow (for pre-processing)
try:
    Config.validate_servicenow()
    print("✅ ServiceNow config valid")
except ConfigurationError as e:
    print(f"❌ Configuration Error: {e}")
```

### Module-Specific Validation

```python
from config import Config

# Validate only what you need
Config.validate_all(['servicenow'])                      # Pre-processing only
Config.validate_all(['notion'])                          # Post-processing only
Config.validate_all(['servicenow', 'notion'])            # Full migration
Config.validate_all(['servicenow', 'google_browser'])    # With Google Docs
```

### Using in Scripts

**Pre-Processing (ServiceNow → ZIP):**
```python
from config import Config

# Validate required config
Config.validate_all(['servicenow'])

# Safe to use
kb = KnowledgeBase(
    instance=Config.SERVICENOW_INSTANCE,
    username=Config.SERVICENOW_USERNAME,
    password=Config.SERVICENOW_PASSWORD
)
```

**Post-Processing (Notion organization):**
```python
from config import Config

# Validate required config
Config.validate_all(['notion'])

# Safe to use
hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

### Debug Configuration

```python
from config import Config

# Check if .env exists
if not Config.check_env_file():
    exit(1)

# Print configuration summary (secrets masked)
Config.print_config_summary()
```

**Output:**
```
================================================================================
Configuration Summary
================================================================================

ServiceNow:
  Instance:  your-instance.service-now.com
  Username:  your-username
  Password:  your****

Notion:
  API Key:   secr****
  Database:  (not set)

Directories:
  Downloads: ./downloads
  Exports:   ./migration_output
  Google:    ./google_docs_exports

Browser Automation:
  Type:      chrome
  Headless:  False
  Timeout:   30s

================================================================================
```

## Error Messages

### Missing ServiceNow Config

```
ConfigurationError: ServiceNow configuration is incomplete:
  - SERVICENOW_INSTANCE is required
  - SERVICENOW_USERNAME is required
  - SERVICENOW_PASSWORD is required

Please set the required environment variables in your .env file.
See env.example for reference.
```

### Missing Notion Config

```
ConfigurationError: Notion API configuration is incomplete:
  - NOTION_API_KEY is required
  - NOTION_DATABASE_ID is required (optional for some operations)

Please set the required environment variables in your .env file.
See env.example for reference.

To get your Notion API key:
  1. Go to https://www.notion.so/my-integrations
  2. Create a new integration
  3. Copy the Internal Integration Token (starts with 'secret_')
```

### Invalid Notion API Key

```
ConfigurationError: Notion API configuration is incomplete:
  - NOTION_API_KEY must start with 'secret_'
```

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

## Breaking Changes

### None for Existing Code

The update is **backward compatible**:

- ✅ `Config.validate()` still works (validates ServiceNow only)
- ✅ Raises `ValueError` for backward compatibility
- ✅ All existing config variables unchanged
- ✅ New validation is opt-in via `validate_all()`

### Recommended Migration

Update your scripts to use new validation:

**Before:**
```python
from config import Config

Config.validate()  # Old method
```

**After:**
```python
from config import Config

# More explicit about what's being validated
Config.validate_all(['servicenow'])

# Or validate multiple modules
Config.validate_all(['servicenow', 'notion'])
```

## Setup Instructions

### 1. Update .env File

```bash
# Copy new example
cp env.example .env.new

# Merge your existing credentials
# Edit .env.new with your values

# Replace old .env
mv .env.new .env
```

### 2. Add Notion Credentials

Get your Notion API key:

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it (e.g., "ServiceNow Migration")
4. Copy the API key (starts with `secret_`)

Add to `.env`:
```bash
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Test Configuration

```bash
python3 -c "
from config import Config

# Check .env exists
Config.check_env_file()

# Test validation
try:
    Config.validate_all(['servicenow', 'notion'])
    print('✅ All configuration valid!')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

## Files Modified

1. **config.py** - Enhanced with Notion support and validation methods
2. **env.example** - Updated with all configuration options including Notion

## Files Created

1. **docs/configuration.md** - Comprehensive configuration guide
2. **CONFIG_UPDATE.md** - This file (summary of changes)

## Benefits

### 1. Better Error Messages

**Before:**
```python
ValueError: SERVICENOW_INSTANCE is required
```

**After:**
```python
ConfigurationError: ServiceNow configuration is incomplete:
  - SERVICENOW_INSTANCE is required
  - SERVICENOW_USERNAME is required
  - SERVICENOW_PASSWORD is required

Please set the required environment variables in your .env file.
See env.example for reference.
```

### 2. Flexible Validation

```python
# Validate only what you need
Config.validate_all(['servicenow'])            # Pre-processing
Config.validate_all(['notion'])                # Post-processing
Config.validate_all(['servicenow', 'notion'])  # Both

# Don't raise errors, just check
if not Config.validate_notion(raise_error=False):
    print("Notion not configured, skipping organization")
```

### 3. Better Security

- Secrets are stripped of whitespace
- Config summary masks sensitive values
- Clear warnings about credential storage
- Instructions on secure practices

### 4. Better Developer Experience

- Auto-check for .env on import
- Helpful error messages with setup instructions
- Debug with `print_config_summary()`
- Complete documentation

## Next Steps

### For Users

1. **Update .env** - Add Notion API key
2. **Test config** - Run validation to ensure setup is correct
3. **Read docs** - Check [docs/configuration.md](test_agentic/docs/configuration.md)

### For Developers

1. **Use new validation** - Call `Config.validate_all()` in scripts
2. **Handle errors** - Catch `ConfigurationError` for better UX
3. **Debug config** - Use `Config.print_config_summary()` for troubleshooting

## Testing

All configuration tested and verified:

```bash
✅ Config module compiles successfully
✅ .env file detection works
✅ ServiceNow validation works
✅ Notion validation works
✅ Browser validation works
✅ Config summary prints correctly
✅ Error messages are helpful
✅ Backward compatibility maintained
```

## Summary

The configuration system now:
- ✅ Supports Notion API configuration
- ✅ Enforces required environment variables
- ✅ Provides clear, helpful error messages
- ✅ Validates module-specific requirements
- ✅ Includes comprehensive documentation
- ✅ Maintains backward compatibility
- ✅ Auto-checks for .env file
- ✅ Provides debug utilities

The update makes the tool production-ready with proper configuration management and validation! 🎉
