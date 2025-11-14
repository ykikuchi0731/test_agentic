"""Export Google Documents to DOCX format using browser automation (Selenium)."""
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

logger = logging.getLogger(__name__)


class GoogleDocsBrowserExporter:
    """Export Google Documents to DOCX format using browser automation."""

    def __init__(
        self,
        download_dir: str = "./google_docs_exports",
        browser_type: str = "chrome",
        headless: bool = False,
        timeout: int = 30,
    ):
        """
        Initialize Google Docs browser exporter.

        Args:
            download_dir: Directory to save exported DOCX files
            browser_type: Browser to use ('chrome', 'firefox', 'edge')
            headless: Run browser in headless mode (no GUI)
            timeout: Timeout in seconds for browser operations

        Example:
            exporter = GoogleDocsBrowserExporter(
                download_dir='./exports',
                browser_type='chrome',
                headless=True,
                timeout=30
            )
        """
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.browser_type = browser_type.lower()
        self.headless = headless
        self.timeout = timeout

        self.driver: Optional[webdriver.Remote] = None
        self.is_logged_in = False

        logger.info(
            f"Google Docs browser exporter initialized with output dir: {download_dir}"
        )
        logger.info(f"Browser: {browser_type}, Headless: {headless}")

    def _setup_browser(self) -> webdriver.Remote:
        """
        Setup and configure browser with download preferences.

        Returns:
            Configured WebDriver instance

        Raises:
            ValueError: If browser_type is not supported
        """
        logger.info(f"Setting up {self.browser_type} browser...")

        # Chrome setup
        if self.browser_type == "chrome":
            options = webdriver.ChromeOptions()

            # Download preferences
            prefs = {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
            }
            options.add_experimental_option("prefs", prefs)

            if self.headless:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")

            # Additional options for stability
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        # Firefox setup
        elif self.browser_type == "firefox":
            options = webdriver.FirefoxOptions()

            # Download preferences
            options.set_preference("browser.download.folderList", 2)
            options.set_preference(
                "browser.download.dir", str(self.download_dir)
            )
            options.set_preference("browser.download.useDownloadDir", True)
            options.set_preference(
                "browser.helperApps.neverAsk.saveToDisk",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            options.set_preference("browser.download.manager.showWhenStarting", False)
            options.set_preference("pdfjs.disabled", True)

            if self.headless:
                options.add_argument("--headless")

            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)

        # Edge setup
        elif self.browser_type == "edge":
            options = webdriver.EdgeOptions()

            # Download preferences
            prefs = {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            options.add_experimental_option("prefs", prefs)

            if self.headless:
                options.add_argument("--headless")

            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)

        else:
            raise ValueError(
                f"Unsupported browser type: {self.browser_type}. "
                f"Supported: chrome, firefox, edge"
            )

        # Set window size
        if not self.headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)

        logger.info("✅ Browser setup complete")
        return driver

    def start_browser(self) -> bool:
        """
        Start browser session.

        Returns:
            True if browser started successfully, False otherwise
        """
        try:
            if self.driver is None:
                self.driver = self._setup_browser()
            return True
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    def stop_browser(self):
        """Stop browser session and cleanup."""
        if self.driver:
            try:
                logger.info("Stopping browser...")
                self.driver.quit()
                self.driver = None
                self.is_logged_in = False
                logger.info("✅ Browser stopped")
            except Exception as e:
                logger.error(f"Error stopping browser: {e}")

    def manual_login_wait(self, wait_message: str = None) -> bool:
        """
        Wait for user to manually log in to Google account.

        Args:
            wait_message: Custom message to display

        Returns:
            True if login appears successful, False otherwise

        This method:
            1. Opens Google Docs homepage
            2. Displays message asking user to log in
            3. Waits for user to complete login
            4. Checks if login was successful
        """
        if not self.driver:
            logger.error("Browser not started")
            return False

        try:
            logger.info("Opening Google Docs for manual login...")

            # Navigate to Google Docs
            self.driver.get("https://docs.google.com/")

            message = wait_message or (
                "Please log in to your Google account in the browser window.\n"
                "Press Enter in the terminal when you're logged in..."
            )

            print("\n" + "=" * 80)
            print("MANUAL LOGIN REQUIRED")
            print("=" * 80)
            print(message)
            print("=" * 80)

            # Wait for user confirmation
            input()

            # Check if logged in by looking for Google account indicators
            time.sleep(2)  # Give page time to load

            # Try to find indicators of being logged in
            try:
                # Look for common Google account elements
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Google Account']")
                self.is_logged_in = True
                logger.info("✅ Login verification successful")
                print("✅ Login verified!")
                return True
            except NoSuchElementException:
                # Fallback: assume login if not on login page
                current_url = self.driver.current_url
                if "accounts.google.com" not in current_url:
                    self.is_logged_in = True
                    logger.info("✅ Appears to be logged in (not on login page)")
                    print("✅ Proceeding (login page not detected)")
                    return True
                else:
                    logger.warning("⚠️  Still on login page")
                    print("⚠️  Warning: Still appears to be on login page")
                    return False

        except Exception as e:
            logger.error(f"Error during manual login: {e}")
            return False

    def extract_file_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract Google Docs file ID from URL.

        Args:
            url: Google Docs URL

        Returns:
            File ID if found, None otherwise

        Supported URL formats:
            - https://docs.google.com/document/d/{FILE_ID}/edit
            - https://docs.google.com/document/d/{FILE_ID}/preview
            - https://docs.google.com/document/d/{FILE_ID}
            - {FILE_ID} (raw file ID)
        """
        pattern = r"https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)"

        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            logger.debug(f"Extracted file ID from URL: {file_id}")
            return file_id

        # If no URL pattern matched, assume it's already a file ID
        if re.match(r"^[a-zA-Z0-9-_]+$", url):
            logger.debug(f"Input appears to be a file ID: {url}")
            return url

        logger.warning(f"Could not extract file ID from: {url}")
        return None

    def _wait_for_download_complete(
        self, expected_extension: str = ".docx", timeout: int = None
    ) -> Optional[Path]:
        """
        Wait for file download to complete.

        Args:
            expected_extension: Expected file extension
            timeout: Timeout in seconds (uses self.timeout if not provided)

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        timeout = timeout or self.timeout
        logger.info(f"Waiting for download to complete (timeout: {timeout}s)...")

        start_time = time.time()
        initial_files = set(self.download_dir.glob("*"))

        while time.time() - start_time < timeout:
            current_files = set(self.download_dir.glob("*"))
            new_files = current_files - initial_files

            # Filter for completed files (not .crdownload, .tmp, .part)
            completed_files = [
                f
                for f in new_files
                if f.suffix == expected_extension
                and not any(
                    f.name.endswith(ext) for ext in [".crdownload", ".tmp", ".part"]
                )
            ]

            if completed_files:
                downloaded_file = completed_files[0]
                logger.info(f"✅ Download complete: {downloaded_file.name}")
                return downloaded_file

            # Check for partial downloads
            partial_files = [
                f
                for f in current_files
                if any(f.name.endswith(ext) for ext in [".crdownload", ".tmp", ".part"])
            ]
            if partial_files:
                logger.debug("Download in progress...")

            time.sleep(0.5)

        logger.warning(f"Download timeout after {timeout}s")
        return None

    def export_single_document(
        self, file_id_or_url: str, output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a single Google Document to DOCX format.

        Args:
            file_id_or_url: Google Docs file ID or URL
            output_filename: Custom output filename (optional)

        Returns:
            Dictionary with export results:
                {
                    'success': bool,
                    'file_path': str (path to exported file if successful),
                    'title': str (document title),
                    'error': str (error message if failed)
                }

        Note:
            Browser must be started and user must be logged in before calling this method.

        Example:
            exporter.start_browser()
            exporter.manual_login_wait()
            result = exporter.export_single_document(
                'https://docs.google.com/document/d/abc123/edit'
            )
            if result['success']:
                print(f"Exported to: {result['file_path']}")
        """
        result = {"success": False, "file_path": None, "title": None, "error": None}

        if not self.driver:
            result["error"] = "Browser not started. Call start_browser() first."
            logger.error(result["error"])
            return result

        if not self.is_logged_in:
            result["error"] = (
                "Not logged in. Call manual_login_wait() first."
            )
            logger.error(result["error"])
            return result

        try:
            # Extract file ID
            file_id = self.extract_file_id_from_url(file_id_or_url)
            if not file_id:
                result["error"] = f"Invalid file ID or URL: {file_id_or_url}"
                logger.error(result["error"])
                return result

            logger.info(f"Exporting Google Doc: {file_id}")

            # Navigate to document
            doc_url = f"https://docs.google.com/document/d/{file_id}/edit"
            logger.info(f"Opening document: {doc_url}")
            self.driver.get(doc_url)

            # Wait for document to load
            wait = WebDriverWait(self.driver, self.timeout)

            try:
                # Wait for document canvas or title to indicate page loaded
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".kix-page-canvas, .docs-title-input"))
                )
                logger.debug("Document loaded")
            except TimeoutException:
                result["error"] = "Timeout waiting for document to load"
                logger.error(result["error"])
                return result

            # Get document title
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, ".docs-title-input")
                doc_title = title_element.get_attribute("value") or "Untitled"
                result["title"] = doc_title
                logger.info(f"Document title: {doc_title}")
            except NoSuchElementException:
                doc_title = "Untitled"
                result["title"] = doc_title
                logger.warning("Could not find document title, using 'Untitled'")

            # Download as DOCX
            # Method: Use File > Download > Microsoft Word (.docx)
            # URL parameter method (more reliable than menu navigation)
            download_url = f"https://docs.google.com/document/d/{file_id}/export?format=docx"
            logger.info("Initiating download...")
            self.driver.get(download_url)

            # Wait for download to complete
            downloaded_file = self._wait_for_download_complete(
                expected_extension=".docx", timeout=self.timeout
            )

            if not downloaded_file:
                result["error"] = "Download timeout or failed"
                logger.error(result["error"])
                return result

            # Rename file if custom filename provided
            if output_filename:
                if not output_filename.endswith(".docx"):
                    output_filename += ".docx"

                final_path = self.download_dir / output_filename

                # Handle duplicate filenames
                counter = 1
                while final_path.exists():
                    name_without_ext = output_filename.rsplit(".docx", 1)[0]
                    final_path = self.download_dir / f"{name_without_ext}_{counter}.docx"
                    counter += 1

                downloaded_file.rename(final_path)
                logger.info(f"Renamed to: {final_path.name}")
            else:
                final_path = downloaded_file

            result["success"] = True
            result["file_path"] = str(final_path)
            logger.info(f"✅ Export successful: {final_path}")

        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logger.error(f"Export failed: {e}", exc_info=True)

        return result

    def export_multiple_documents(
        self, file_ids_or_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Export multiple Google Documents to DOCX format.

        Args:
            file_ids_or_urls: List of Google Docs file IDs or URLs

        Returns:
            List of export result dictionaries (same format as export_single_document)

        Example:
            exporter.start_browser()
            exporter.manual_login_wait()
            results = exporter.export_multiple_documents([
                'https://docs.google.com/document/d/abc123/edit',
                'https://docs.google.com/document/d/def456/edit',
            ])
            for result in results:
                if result['success']:
                    print(f"✅ {result['title']}: {result['file_path']}")
                else:
                    print(f"❌ {result['error']}")
        """
        logger.info(f"Starting batch export of {len(file_ids_or_urls)} documents...")

        results = []
        for i, file_id_or_url in enumerate(file_ids_or_urls, 1):
            logger.info(f"Exporting document {i}/{len(file_ids_or_urls)}")
            result = self.export_single_document(file_id_or_url)
            results.append(result)

            # Small delay between downloads to avoid rate limiting
            if i < len(file_ids_or_urls):
                time.sleep(2)

        successful = sum(1 for r in results if r["success"])
        logger.info(
            f"✅ Batch export complete: {successful}/{len(file_ids_or_urls)} successful"
        )

        return results

    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_browser()
