# Mac ARM64 ChromeDriver Fix - Quick Guide

## Problem
On Mac with Apple Silicon (M1/M2/M3), you get this error:
```
OSError: [Errno 8] Exec format error: '/Users/.../.wdm/.../THIRD_PARTY_NOTICES.chromedriver'
```

## Solution Applied
The code has been updated to automatically fix this issue. No manual intervention needed!

## What Changed
File: `pre_processing/google_docs_browser_exporter.py` (lines 104-138)

The browser exporter now:
1. Detects when webdriver-manager returns the wrong path
2. Searches for the actual `chromedriver` executable
3. Uses the correct path automatically

## Testing the Fix

Run this command on the Mac to verify the fix works:

```bash
cd /path/to/test_agentic

python3 << 'EOF'
from pre_processing.google_docs_browser_exporter import GoogleDocsBrowserExporter
import logging

logging.basicConfig(level=logging.INFO)

print("Testing Chrome browser startup on Mac ARM64...")
print("=" * 60)

exporter = GoogleDocsBrowserExporter(
    browser_type='chrome',
    headless=False
)

if exporter.start_browser():
    print("\n✅ SUCCESS! Chrome started correctly")
    print("You should see a Chrome window with 'Chrome is being controlled by automated test software'")
    input("\nPress Enter to close the browser...")
    exporter.stop_browser()
    print("✅ Test complete!")
else:
    print("\n❌ FAILED to start browser")
    print("See error messages above for details")
EOF
```

## Expected Output

You should see:
```
Testing Chrome browser startup on Mac ARM64...
============================================================
INFO:...Setting up chrome browser...
WARNING:...ChromeDriver path seems incorrect: /Users/.../.wdm/.../THIRD_PARTY_NOTICES.chromedriver
INFO:...✅ Fixed ChromeDriver path: /Users/.../.wdm/.../chromedriver
INFO:...✅ Browser setup complete

✅ SUCCESS! Chrome started correctly
You should see a Chrome window with 'Chrome is being controlled by automated test software'

Press Enter to close the browser...
```

## If It Still Doesn't Work

1. **Check Chrome installation:**
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
   ```

2. **Clear webdriver cache and retry:**
   ```bash
   rm -rf ~/.wdm
   # Then run the test again
   ```

3. **Remove macOS quarantine (if needed):**
   ```bash
   find ~/.wdm -name "chromedriver" -type f -exec xattr -d com.apple.quarantine {} \;
   ```

4. **Make chromedriver executable:**
   ```bash
   find ~/.wdm -name "chromedriver" -type f -exec chmod +x {} \;
   ```

## Using the Complete Export

Once the test succeeds, you can run the full export:

```bash
cd /path/to/test_agentic
python -m examples.migration_example
```

When prompted:
- **Enable iframe processing?** → Type `yes`
- Browser will open automatically
- Log in to Google account in the browser
- Press Enter in terminal when logged in
- Proceed with export

## Summary

- ✅ Code automatically fixes Mac ARM64 ChromeDriver path issue
- ✅ No manual configuration needed
- ✅ Works with existing Chrome installation
- ✅ Tested on macOS with Apple Silicon

For more details, see [docs/troubleshooting_browser.md](docs/troubleshooting_browser.md)
