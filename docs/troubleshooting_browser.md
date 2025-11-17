# Browser Automation Troubleshooting Guide

This guide covers common issues when using browser automation for Google Docs export.

---

## Mac ARM64 ChromeDriver Issue

### Error Message
```
OSError: [Errno 8] Exec format error: '/Users/username/.wdm/drivers/chromedriver/mac64/142.0.7444.162/chromedriver-mac-arm64/THIRD_PARTY_NOTICES.chromedriver'
```

### Root Cause
On Mac ARM64 (Apple Silicon M1/M2/M3), `webdriver-manager` downloads the correct ChromeDriver but returns the wrong file path. It points to `THIRD_PARTY_NOTICES.chromedriver` instead of the actual `chromedriver` executable.

### Solution
The code now includes an automatic fix for this issue. The browser exporter will:
1. Detect if the path points to the wrong file
2. Search for the actual `chromedriver` executable
3. Use the correct path automatically

### Verification
After updating the code, test the fix:

```bash
cd /path/to/test_agentic
python -c "
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter
exporter = GoogleDocsBrowserExporter(browser_type='chrome', headless=False)
if exporter.start_browser():
    print('✅ Chrome started successfully!')
    exporter.stop_browser()
else:
    print('❌ Still failing')
"
```

### Manual Fix (if needed)
If the automatic fix doesn't work, manually specify the ChromeDriver path:

1. Find the actual chromedriver:
   ```bash
   find ~/.wdm -name "chromedriver" -type f
   ```

2. Look for output like:
   ```
   /Users/username/.wdm/drivers/chromedriver/mac64/142.0.7444.162/chromedriver-mac-arm64/chromedriver
   ```

3. Update the code to use this path directly (as a temporary workaround):
   ```python
   # In google_docs_browser_exporter.py, line 137:
   driver_path = "/Users/username/.wdm/drivers/chromedriver/mac64/142.0.7444.162/chromedriver-mac-arm64/chromedriver"
   service = ChromeService(driver_path)
   ```

---

## Common Browser Startup Errors

### Error: Browser not found

**Symptoms:**
```
selenium.common.exceptions.WebDriverException: Message: unknown error: cannot find Chrome binary
```

**Solution:**
1. Verify Chrome is installed:
   ```bash
   # Mac
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

   # Linux
   google-chrome --version

   # Windows
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --version
   ```

2. If Chrome is not installed, download from: https://www.google.com/chrome/

3. If installed in non-standard location, specify the path in the code:
   ```python
   options.binary_location = "/path/to/chrome"
   ```

---

### Error: ChromeDriver version mismatch

**Symptoms:**
```
selenium.common.exceptions.SessionNotCreatedException: Message: session not created: This version of ChromeDriver only supports Chrome version XX
```

**Solution:**
The `webdriver-manager` should automatically download the correct version. If this fails:

1. Update webdriver-manager:
   ```bash
   pip install --upgrade webdriver-manager
   ```

2. Clear the webdriver cache:
   ```bash
   rm -rf ~/.wdm
   ```

3. Run the script again - it will download the correct version

---

### Error: Permission denied

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/Users/username/.wdm/drivers/chromedriver/...'
```

**Solution:**
1. Make the chromedriver executable:
   ```bash
   find ~/.wdm -name "chromedriver" -type f -exec chmod +x {} \;
   ```

2. On Mac, you may need to remove the quarantine attribute:
   ```bash
   find ~/.wdm -name "chromedriver" -type f -exec xattr -d com.apple.quarantine {} \;
   ```

---

### Error: Operation not permitted (Mac)

**Symptoms:**
```
selenium.common.exceptions.WebDriverException: Message: unknown error: cannot find Chrome binary
OSError: [Errno 1] Operation not permitted
```

**Solution:**
On macOS, grant terminal/Python access to control Chrome:

1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Click **Automation** in the left sidebar
3. Grant access to Terminal (or your IDE)
4. Click **Accessibility** in the left sidebar
5. Add Terminal (or your IDE) to the list

---

### Error: Headless mode not working

**Symptoms:**
- Browser starts but doesn't download files
- Login pages don't work in headless mode

**Solution:**
1. Start with headless mode **disabled** for testing:
   ```bash
   # In .env file:
   BROWSER_HEADLESS=false
   ```

2. Once verified working, enable headless mode:
   ```bash
   BROWSER_HEADLESS=true
   ```

3. Some sites block headless browsers - may need to keep headless disabled

---

## Platform-Specific Issues

### macOS Specific

**Issue: "chromedriver" cannot be opened because the developer cannot be verified**

Solution:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine $(find ~/.wdm -name "chromedriver" -type f)
```

Or manually:
1. Right-click the ChromeDriver file
2. Select "Open"
3. Click "Open" in the warning dialog
4. Run the script again

---

### Windows Specific

**Issue: Windows Defender blocks ChromeDriver**

Solution:
1. Open Windows Security
2. Go to Virus & threat protection
3. Click "Manage settings"
4. Add exclusion for the `.wdm` folder:
   ```
   C:\Users\YourUsername\.wdm
   ```

---

### Linux Specific

**Issue: Missing dependencies**

Solution:
```bash
# Ubuntu/Debian
sudo apt-get install -y \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1

# RHEL/CentOS
sudo yum install -y \
    nss \
    libXScrnSaver \
    alsa-lib \
    at-spi2-atk \
    gtk3 \
    mesa-libgbm
```

---

## Testing and Verification

### Quick Test
```bash
python -c "
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter
import logging
logging.basicConfig(level=logging.INFO)

exporter = GoogleDocsBrowserExporter(
    browser_type='chrome',
    headless=False
)

print('Testing browser startup...')
if exporter.start_browser():
    print('✅ SUCCESS: Browser started')
    print('You should see a Chrome window with automation banner')
    input('Press Enter to close browser...')
    exporter.stop_browser()
    print('✅ Browser closed')
else:
    print('❌ FAILED: Could not start browser')
    print('Check the error messages above')
"
```

### Full Integration Test
```bash
cd /path/to/test_agentic
python -m examples.export_google_doc_browser
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs**: Look for error messages in the console output
2. **Test Chrome manually**: Verify Chrome works outside of automation
3. **Update dependencies**:
   ```bash
   pip install --upgrade selenium webdriver-manager
   ```
4. **Clear cache**:
   ```bash
   rm -rf ~/.wdm
   ```
5. **Try Firefox instead**:
   ```bash
   # In .env:
   BROWSER_TYPE=firefox
   ```

For project-specific issues, check the main documentation or contact the maintainer.
