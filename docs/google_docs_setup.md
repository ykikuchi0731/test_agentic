# Google Docs Export Setup Guide

This guide walks you through exporting Google Documents to DOCX format using two methods:
1. **Browser Automation (Selenium)** - Recommended, no GCP setup required
2. **Google API (OAuth2)** - Currently disabled due to GCP restrictions

---

# Method 1: Browser Automation (Selenium) - RECOMMENDED

This method uses Selenium to automate browser-based downloads, requiring no Google Cloud Platform setup.

## Overview

The browser automation exporter:
- Uses your existing Google account login
- Automates the browser download process
- Supports bulk exports
- Works with Chrome, Firefox, or Edge
- No API keys or credentials needed

## Prerequisites

- Google account with access to documents
- Chrome, Firefox, or Edge browser installed
- Python 3.7 or higher

---

## Step 1: Install Dependencies

Install Selenium and WebDriver Manager:

```bash
pip install -r requirements.txt
```

This installs:
- `selenium==4.15.2` - Browser automation framework
- `webdriver-manager==4.0.1` - Automatic WebDriver management

**Note**: WebDriver Manager automatically downloads and manages browser drivers (ChromeDriver, GeckoDriver, etc.), so no manual driver installation is needed.

---

## Step 2: Configure Settings

Add to your `.env` file:

```bash
# Browser automation settings
BROWSER_DOWNLOAD_DIR=./google_docs_exports
BROWSER_HEADLESS=false
BROWSER_TYPE=chrome
BROWSER_TIMEOUT=30
```

### Configuration Options:

- **BROWSER_DOWNLOAD_DIR**: Directory for exported DOCX files
- **BROWSER_HEADLESS**: Run browser without GUI (`true` or `false`)
  - `false` (default): Shows browser window - useful for debugging and manual login
  - `true`: Runs in background - faster but harder to debug
- **BROWSER_TYPE**: Browser to use (`chrome`, `firefox`, or `edge`)
- **BROWSER_TIMEOUT**: Timeout in seconds for browser operations

---

## Step 3: Run Export Script

### Single Document Export:

```bash
python examples/export_google_doc_browser.py
```

**Interactive Flow:**

1. **Start Browser**: Chrome/Firefox/Edge opens automatically
2. **Manual Login**:
   - Browser navigates to Google Docs
   - You log in manually (one-time per session)
   - Press Enter in terminal when logged in
3. **Enter Document URL**: Paste Google Doc URL or file ID
4. **Export**: Document downloads automatically to output directory

### Multiple Documents Export:

Run the same script and select option 2:

```bash
python examples/export_google_doc_browser.py
# Select mode: 2 (Multiple documents)
# Enter URLs (one per line)
# Press Enter twice when done
```

---

## Usage Examples

### Basic Usage:

```python
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter
from config import Config

# Initialize exporter
exporter = GoogleDocsBrowserExporter(
    download_dir=Config.BROWSER_DOWNLOAD_DIR,
    browser_type='chrome',
    headless=False,
    timeout=30
)

# Start browser
exporter.start_browser()

# Manual login (interactive)
exporter.manual_login_wait()

# Export single document
result = exporter.export_single_document(
    'https://docs.google.com/document/d/YOUR_DOC_ID/edit'
)

if result['success']:
    print(f"Exported: {result['file_path']}")

# Stop browser
exporter.stop_browser()
```

### Batch Export with Context Manager:

```python
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter

urls = [
    'https://docs.google.com/document/d/DOC_ID_1/edit',
    'https://docs.google.com/document/d/DOC_ID_2/edit',
    'https://docs.google.com/document/d/DOC_ID_3/edit',
]

# Context manager automatically starts/stops browser
with GoogleDocsBrowserExporter(
    download_dir='./exports',
    browser_type='chrome',
    headless=False
) as exporter:
    # Login once
    exporter.manual_login_wait()

    # Export all documents
    results = exporter.export_multiple_documents(urls)

    # Check results
    for result in results:
        if result['success']:
            print(f"✅ {result['title']}: {result['file_path']}")
        else:
            print(f"❌ Error: {result['error']}")
```

---

## Troubleshooting

### Browser doesn't start

**Solutions**:
- Verify browser is installed (Chrome, Firefox, or Edge)
- Check browser version compatibility
- Try different `BROWSER_TYPE` in config
- WebDriver Manager will auto-download compatible driver

### Login issues

**Solutions**:
- Ensure you're using the correct Google account
- Check if 2FA is enabled (complete verification manually)
- Try non-headless mode first (`BROWSER_HEADLESS=false`)
- Look for login prompts in browser window

### Download timeout

**Solutions**:
- Increase `BROWSER_TIMEOUT` in config (default: 30s)
- Check internet connection
- Verify you have access to the document
- Try downloading manually first to test access

### "Document not found" errors

**Solutions**:
- Verify document URL or file ID is correct
- Check document sharing settings
- Ensure document still exists (not deleted)
- Try opening document manually in browser

### Headless mode issues

**Solutions**:
- Start with `BROWSER_HEADLESS=false` for debugging
- Some login flows don't work in headless mode
- Use headless only after confirming exports work

### Multiple documents failing

**Solutions**:
- Check rate limiting (2s delay between downloads)
- Verify all URLs are valid
- Ensure you stay logged in throughout batch export
- Check disk space for downloads

---

## Security Best Practices

### Browser Session:

- **Manual login**: You control when and how to log in
- **Session-based**: Login persists only during browser session
- **No stored credentials**: No passwords saved in code
- **Clean sessions**: Browser closes after export completes

### Headless Mode Caution:

- **Use with care**: Harder to detect login issues
- **Debug first**: Test with `headless=false` before enabling headless
- **Monitor logs**: Check console output for errors

---

## Advanced Configuration

### Custom Download Location per Export:

```python
exporter = GoogleDocsBrowserExporter(
    download_dir='./custom_location',
    browser_type='chrome'
)
```

### Timeout Adjustment:

```python
exporter = GoogleDocsBrowserExporter(
    download_dir='./exports',
    timeout=60  # Increase for large documents
)
```

### Browser-Specific Options:

The exporter automatically configures:
- Download preferences (no prompts)
- Security settings (allow downloads)
- Anti-detection measures (avoid bot detection)

---

## Performance Tips

### Single Session for Batch Exports:

Login once, export many documents:
```python
with GoogleDocsBrowserExporter() as exporter:
    exporter.manual_login_wait()  # Login once

    for url in large_list_of_urls:
        result = exporter.export_single_document(url)
        # Process result
```

### Headless Mode for Production:

After testing, use headless for faster automated exports:
```bash
BROWSER_HEADLESS=true
```

### Rate Limiting:

The exporter includes a 2-second delay between bulk exports to avoid rate limiting.

---

# Method 2: Google API (OAuth2) - CURRENTLY DISABLED

**Note**: This method is currently disabled due to GCP API restrictions. Use Method 1 (Browser Automation) instead.

The following steps are preserved for reference if API access becomes available in the future.

---

## Step 1: Create Google Cloud Project (API Method - DISABLED)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter project name (e.g., "ServiceNow Migration Tool")
5. Click **"Create"**
6. Wait for project creation (takes a few seconds)

---

## Step 2: Enable Required APIs

### Enable Google Drive API

1. In Google Cloud Console, ensure your project is selected
2. Go to **"APIs & Services"** > **"Library"**
3. Search for **"Google Drive API"**
4. Click on **"Google Drive API"**
5. Click **"Enable"**

### Enable Google Docs API

1. In the API Library, search for **"Google Docs API"**
2. Click on **"Google Docs API"**
3. Click **"Enable"**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Select **"External"** user type (unless you have a Google Workspace organization)
3. Click **"Create"**

### Fill in App Information:

- **App name**: ServiceNow Migration Tool (or your preferred name)
- **User support email**: Your email address
- **Developer contact information**: Your email address
- Click **"Save and Continue"**

### Add Scopes:

1. Click **"Add or Remove Scopes"**
2. Filter for: `https://www.googleapis.com/auth/drive.readonly`
3. Check the box next to:
   - `.../auth/drive.readonly` (View and download all your Google Drive files)
   - `.../auth/documents.readonly` (View your Google Docs documents)
4. Click **"Update"**
5. Click **"Save and Continue"**

### Add Test Users (for External apps):

1. Click **"Add Users"**
2. Enter email addresses of users who will use this tool
3. Click **"Add"**
4. Click **"Save and Continue"**

### Review and Complete:

1. Review your settings
2. Click **"Back to Dashboard"**

---

## Step 4: Create OAuth2 Credentials

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"Create Credentials"** > **"OAuth client ID"**
3. Select **Application type**: **"Desktop app"**
4. **Name**: ServiceNow Migration OAuth (or your preferred name)
5. Click **"Create"**

### Download Credentials:

1. A dialog will appear with your Client ID and Client Secret
2. Click **"Download JSON"**
3. Save the file as `credentials.json`
4. Move `credentials.json` to your project root directory: `/app/test_agentic/credentials.json`

**⚠️ Security Note**: Keep `credentials.json` private. Don't commit it to version control.

---

## Step 5: Configure Environment Variables

1. Open or create `.env` file in project root
2. Add the following configuration:

```bash
# Google Workspace API settings
GOOGLE_CREDENTIALS_FILE=./credentials.json
GOOGLE_TOKEN_FILE=./token.json
GOOGLE_DOCS_OUTPUT_DIR=./google_docs_exports
```

### Configuration Options:

- **GOOGLE_CREDENTIALS_FILE**: Path to OAuth2 credentials JSON file
- **GOOGLE_TOKEN_FILE**: Path where refresh token will be saved (auto-created on first run)
- **GOOGLE_DOCS_OUTPUT_DIR**: Directory for exported DOCX files

---

## Step 6: Install Dependencies

Install required Google API client libraries:

```bash
pip install -r requirements.txt
```

This will install:
- `google-auth==2.25.2`
- `google-auth-oauthlib==1.2.0`
- `google-auth-httplib2==0.2.0`
- `google-api-python-client==2.110.0`

---

## Step 7: First-Time Authentication

Run the export script for the first time:

```bash
python examples/export_google_doc.py
```

### What Happens:

1. **Browser Opens**: A browser window will open automatically
2. **Sign In**: Sign in with your Google account
3. **Grant Permissions**: Review and grant requested permissions
   - View and download all your Google Drive files
   - View your Google Docs documents
4. **Success**: You'll see "The authentication flow has completed"
5. **Token Saved**: A `token.json` file is created with your refresh token

### Subsequent Runs:

- No browser window will open
- The saved `token.json` is used automatically
- Token is refreshed automatically when expired

---

## Usage Example

### Export a Single Document:

```python
from pre_processing.google_docs_exporter import GoogleDocsExporter
from config import Config

# Initialize exporter
exporter = GoogleDocsExporter(
    credentials_file=Config.GOOGLE_CREDENTIALS_FILE,
    token_file=Config.GOOGLE_TOKEN_FILE,
    scopes=Config.GOOGLE_SCOPES,
    output_dir=Config.GOOGLE_DOCS_OUTPUT_DIR
)

# Export document
result = exporter.export_single_document(
    'https://docs.google.com/document/d/YOUR_DOC_ID/edit'
)

if result['success']:
    print(f"Exported to: {result['file_path']}")
else:
    print(f"Error: {result['error']}")
```

### Using the Example Script:

```bash
python examples/export_google_doc.py
```

Follow the interactive prompts:
1. Enter Google Doc URL or file ID
2. Optionally provide custom filename
3. Confirm export

---

## Troubleshooting

### Error: "Credentials file not found"

**Solution**:
- Verify `credentials.json` exists in project root
- Check `GOOGLE_CREDENTIALS_FILE` path in `.env`

### Error: "Permission denied (403)"

**Solutions**:
- Verify you have access to the document
- Check document sharing settings
- Ensure you're signed in with the correct Google account
- For External OAuth apps, verify your email is added as a test user

### Error: "Document not found (404)"

**Solutions**:
- Verify the document URL or file ID is correct
- Check if document still exists
- Ensure document hasn't been deleted

### Error: "File is not a Google Document"

**Solution**:
- Only Google Docs can be exported to DOCX
- Google Sheets, Slides, or other file types are not supported
- Verify the URL points to a Google Doc

### Browser Doesn't Open on First Run

**Solutions**:
- Check if port 8080 is available
- Try running in an environment with GUI access
- Look for authentication URL in terminal output and open manually

### Token Expired Errors

**Solution**:
- Delete `token.json` and re-authenticate
- The tool will automatically open browser for new authorization

---

## Security Best Practices

### Protect Credentials:

1. **Never commit credentials**: Add to `.gitignore`:
   ```
   credentials.json
   token.json
   ```

2. **Limit scope**: Only request necessary permissions (readonly is sufficient)

3. **Review access**: Periodically review authorized apps at:
   https://myaccount.google.com/permissions

### Revoke Access:

To revoke application access:
1. Go to https://myaccount.google.com/permissions
2. Find "ServiceNow Migration Tool" (or your app name)
3. Click **"Remove Access"**
4. Delete `token.json` from your machine

---

## Advanced Configuration

### Using Service Account (Alternative)

For server-side automation without user interaction, consider using a Service Account:

1. Create Service Account in Google Cloud Console
2. Download Service Account JSON key
3. Share Google Docs with service account email
4. Use service account authentication in code

**Note**: Service accounts can only access documents explicitly shared with them.

### Custom Scopes

Modify `config.py` to add additional scopes:

```python
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    # Add more scopes as needed
]
```

### Rate Limits

Google Drive API has usage quotas:
- **Queries per day**: 1,000,000,000
- **Queries per 100 seconds per user**: 1,000

For high-volume exports, implement rate limiting or request quota increase.

---

## Additional Resources

- [Google Drive API Documentation](https://developers.google.com/drive/api/v3/about-sdk)
- [Google Docs API Documentation](https://developers.google.com/docs/api)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [API Quotas and Limits](https://developers.google.com/drive/api/v3/handle-errors#rate-limit-errors)

---

## Support

If you encounter issues not covered in this guide:

1. Check Google Cloud Console > APIs & Services > Credentials
2. Verify APIs are enabled
3. Check OAuth consent screen configuration
4. Review application logs for detailed error messages
5. Ensure test users are added (for External apps)

For project-specific issues, check the project repository or contact the maintainer.
