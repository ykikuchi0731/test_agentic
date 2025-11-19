# Configuration Guide

This guide explains how to configure the ServiceNow to Notion migration tool using environment variables.

## Overview

The tool uses a `.env` file for configuration. This file contains all necessary credentials and settings for:
- ServiceNow API access (pre-processing)
- Notion API access (post-processing)
- Browser automation for Google Docs export
- File download and export settings

## Quick Start

### 1. Create .env File

Copy the example file and edit it with your credentials:

```bash
cp env.example .env
```

### 2. Add Required Credentials

Edit `.env` and add at minimum:

**For Pre-Processing (ServiceNow export):**
```bash
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

**For Post-Processing (Notion organization):**
```bash
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Verify Configuration

```python
from config import Config

# Check if .env exists
Config.check_env_file()

# Validate ServiceNow config
Config.validate_servicenow()

# Validate Notion config (if using post-processing)
Config.validate_notion()

# Print summary (secrets masked)
Config.print_config_summary()
```

---

## Configuration Sections

### ServiceNow Configuration (REQUIRED for pre-processing)

```bash
# Your ServiceNow instance URL (without https://)
SERVICENOW_INSTANCE=your-instance.service-now.com

# ServiceNow authentication credentials
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

**How to get:**
1. ServiceNow instance URL from your company
2. Username and password from ServiceNow admin
3. Ensure user has read access to Knowledge Base

**Validation:**
```python
from config import Config
Config.validate_servicenow()  # Raises error if missing
```

---

### Notion API Configuration (REQUIRED for post-processing)

```bash
# Your Notion integration API key (starts with 'secret_')
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Database ID for organizing imported content
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**How to get your Notion API key:**

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Name it (e.g., "ServiceNow Migration")
4. Select the workspace
5. Click **"Submit"**
6. Copy the **Internal Integration Token** (starts with `secret_`)

**How to get Database ID:**

1. Open your database in Notion
2. Look at the URL: `https://notion.so/{workspace}/{DATABASE_ID}?v=...`
3. Copy the `DATABASE_ID` part (32 character hex string)

**Validation:**
```python
from config import Config
Config.validate_notion()  # Raises error if missing or invalid
```

**Note:** Database ID is optional for some operations (like making pages sub-items).

---

### API Settings

```bash
# Timeout for API requests in seconds
API_TIMEOUT=30

# Maximum number of retry attempts for failed requests
MAX_RETRIES=3
```

**Recommendations:**
- **API_TIMEOUT**: 30-60 seconds for stable connections, 60-120 for slow networks
- **MAX_RETRIES**: 3-5 retries handles temporary network issues

---

### File Download Settings

```bash
# Directory for downloaded files (attachments, etc.)
DOWNLOAD_DIR=./downloads

# Maximum file size to download in bytes (100MB default)
MAX_FILE_SIZE=104857600
```

**MAX_FILE_SIZE values:**
- `10485760` = 10MB
- `52428800` = 50MB
- `104857600` = 100MB (default)
- `209715200` = 200MB

---

### Export Settings

```bash
# Output directory for migration exports (ZIP files, CSV reports, etc.)
MIGRATION_OUTPUT_DIR=./migration_output

# Whether to create ZIP exports for Notion import
CREATE_ZIP_EXPORTS=true
```

**Output structure:**
```
migration_output/
├── zips/
│   └── bulk_export_50_articles.zip
├── bulk_export_50_articles_report.csv
└── iframe_report_processed_20250119_143000.csv
```

---

### Browser Automation Settings (for Google Docs export)

```bash
# Directory for exported Google Docs (DOCX files)
BROWSER_DOWNLOAD_DIR=./google_docs_exports

# Run browser in headless mode (no GUI)
BROWSER_HEADLESS=false

# Browser type to use: chrome, firefox, or edge
BROWSER_TYPE=chrome

# Timeout for browser operations in seconds
BROWSER_TIMEOUT=30
```

**BROWSER_TYPE options:**
- `chrome` - Google Chrome (recommended)
- `firefox` - Mozilla Firefox
- `edge` - Microsoft Edge

**BROWSER_HEADLESS:**
- `false` - Shows browser window (recommended for debugging)
- `true` - Runs in background (faster, but harder to debug)

**BROWSER_TIMEOUT:**
- Minimum: 10 seconds
- Recommended: 30-60 seconds
- Large documents: 60-120 seconds

**Validation:**
```python
from config import Config
Config.validate_google_browser()  # Checks browser settings
```

---

### Google Account Credentials (OPTIONAL)

```bash
# Google account email (optional)
GOOGLE_EMAIL=

# Google account password (optional, use with extreme caution)
GOOGLE_PASSWORD=
```

**⚠️ Security Warning:**
- Storing passwords in .env is **NOT recommended**
- Manual login is preferred for security
- Leave these empty to use manual authentication
- Only use if you fully understand the security implications

**Manual login is recommended:**
- Browser opens for login
- You authenticate securely
- Session persists for batch operations
- No stored credentials

---

## Validation Methods

### Module-Specific Validation

The `Config` class provides validation for different modules:

```python
from config import Config, ConfigurationError

# Validate ServiceNow only
try:
    Config.validate_servicenow()
    print("✅ ServiceNow config valid")
except ConfigurationError as e:
    print(f"❌ {e}")

# Validate Notion only
try:
    Config.validate_notion()
    print("✅ Notion config valid")
except ConfigurationError as e:
    print(f"❌ {e}")

# Validate browser automation
try:
    Config.validate_google_browser()
    print("✅ Browser config valid")
except ConfigurationError as e:
    print(f"❌ {e}")
```

### Validate Multiple Modules

```python
from config import Config

# Validate based on what you're using
Config.validate_all(['servicenow'])  # Pre-processing only
Config.validate_all(['servicenow', 'notion'])  # Pre + post processing
Config.validate_all(['servicenow', 'notion', 'google_browser'])  # Everything
```

### Check Without Raising Errors

```python
from config import Config

# Returns True/False instead of raising errors
is_valid = Config.validate_servicenow(raise_error=False)
if not is_valid:
    print("ServiceNow config is incomplete")
```

---

## Configuration Summary

Print a summary of current configuration:

```python
from config import Config

# With secrets masked (default)
Config.print_config_summary()

# Show full values (for debugging only)
Config.print_config_summary(hide_secrets=False)
```

**Example output:**
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

---

## Usage in Scripts

### Pre-Processing Scripts (ServiceNow export)

```python
from config import Config

# Validate configuration
Config.validate_all(['servicenow'])

# Use configuration
from pre_processing.knowledge_base import KnowledgeBase

kb = KnowledgeBase(
    instance=Config.SERVICENOW_INSTANCE,
    username=Config.SERVICENOW_USERNAME,
    password=Config.SERVICENOW_PASSWORD
)
```

### Post-Processing Scripts (Notion organization)

```python
from config import Config

# Validate configuration
Config.validate_all(['notion'])

# Use configuration
from post_processing.page_hierarchy import NotionPageHierarchy

hierarchy = NotionPageHierarchy(api_key=Config.NOTION_API_KEY)
```

### Full Migration (ServiceNow → Notion)

```python
from config import Config

# Validate everything
Config.validate_all(['servicenow', 'notion', 'google_browser'])

# All modules can now access configuration safely
```

---

## Troubleshooting

### Error: ".env file not found"

**Problem:**
```
⚠️  WARNING: .env file not found
```

**Solution:**
```bash
# Copy example file
cp env.example .env

# Edit with your credentials
nano .env
# or
vi .env
```

---

### Error: "SERVICENOW_INSTANCE is required"

**Problem:**
```
ConfigurationError: ServiceNow configuration is incomplete:
  - SERVICENOW_INSTANCE is required
```

**Solution:**
Edit `.env` and add:
```bash
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

---

### Error: "NOTION_API_KEY is required"

**Problem:**
```
ConfigurationError: Notion API configuration is incomplete:
  - NOTION_API_KEY is required
```

**Solution:**
1. Get API key from [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Add to `.env`:
```bash
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### Error: "NOTION_API_KEY must start with 'secret_'"

**Problem:**
```
ConfigurationError: NOTION_API_KEY must start with 'secret_'
```

**Solution:**
- Verify you copied the entire API key including the `secret_` prefix
- Get a new key if needed from Notion integrations page

---

### Error: "BROWSER_TYPE must be one of..."

**Problem:**
```
ConfigurationError: BROWSER_TYPE must be one of ['chrome', 'firefox', 'edge'], got 'chromium'
```

**Solution:**
Edit `.env` and use a valid browser type:
```bash
BROWSER_TYPE=chrome  # or firefox, or edge
```

---

## Security Best Practices

### 1. Never Commit .env to Git

Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

### 2. Use Strong Passwords

- ServiceNow: Use dedicated API user with minimal permissions
- Notion: Regularly rotate API keys
- Google: Use app-specific passwords if 2FA enabled

### 3. Limit Access

- ServiceNow: Read-only access to Knowledge Base
- Notion: Only share pages that need integration access
- File permissions: `chmod 600 .env` (owner read/write only)

### 4. Regular Audits

- Review active Notion integrations monthly
- Check ServiceNow audit logs
- Rotate credentials periodically

---

## Advanced Configuration

### Environment-Specific Settings

Use different .env files for different environments:

```bash
# Development
cp .env.development .env

# Production
cp .env.production .env
```

### Override in Code

```python
from config import Config

# Override specific settings
Config.BROWSER_HEADLESS = True
Config.API_TIMEOUT = 60
```

### Dynamic Validation

```python
from config import Config

def run_migration():
    # Determine what modules are needed
    modules = ['servicenow']

    if use_google_docs:
        modules.append('google_browser')

    if organize_in_notion:
        modules.append('notion')

    # Validate only what's needed
    Config.validate_all(modules)

    # Proceed with migration
    ...
```

---

## Reference

### All Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICENOW_INSTANCE` | Yes (pre) | - | ServiceNow instance URL |
| `SERVICENOW_USERNAME` | Yes (pre) | - | ServiceNow username |
| `SERVICENOW_PASSWORD` | Yes (pre) | - | ServiceNow password |
| `NOTION_API_KEY` | Yes (post) | - | Notion integration API key |
| `NOTION_DATABASE_ID` | No | - | Notion database ID |
| `API_TIMEOUT` | No | 30 | API request timeout (seconds) |
| `MAX_RETRIES` | No | 3 | Max retry attempts |
| `DOWNLOAD_DIR` | No | ./downloads | Download directory |
| `MAX_FILE_SIZE` | No | 104857600 | Max file size (bytes) |
| `MIGRATION_OUTPUT_DIR` | No | ./migration_output | Export directory |
| `CREATE_ZIP_EXPORTS` | No | true | Create ZIP files |
| `BROWSER_DOWNLOAD_DIR` | No | ./google_docs_exports | Google Docs export dir |
| `BROWSER_HEADLESS` | No | false | Headless browser mode |
| `BROWSER_TYPE` | No | chrome | Browser type |
| `BROWSER_TIMEOUT` | No | 30 | Browser timeout (seconds) |
| `GOOGLE_EMAIL` | No | - | Google email (optional) |
| `GOOGLE_PASSWORD` | No | - | Google password (optional) |

**Legend:**
- **(pre)** = Required for pre-processing (ServiceNow export)
- **(post)** = Required for post-processing (Notion organization)

---

## Next Steps

- **Set up ServiceNow**: See [docs/servicenow_setup.md](servicenow_setup.md)
- **Set up Notion**: See [docs/page_hierarchy.md](page_hierarchy.md)
- **Run migration**: See [examples/migration_example.py](../examples/migration_example.py)
- **Organize in Notion**: See [examples/make_page_subitem.py](../examples/make_page_subitem.py)
