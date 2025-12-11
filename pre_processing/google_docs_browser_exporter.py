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
        """Setup and configure browser with download preferences."""
        logger.info(f"Setting up {self.browser_type} browser...")

        if self.browser_type == "chrome":
            options = webdriver.ChromeOptions()
            options.add_experimental_option("prefs", {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
            })
            if self.headless:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
            for arg in ["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]:
                options.add_argument(arg)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            driver_path = ChromeDriverManager().install()
            if 'THIRD_PARTY_NOTICES' in driver_path or not os.path.isfile(driver_path):
                logger.warning(f"ChromeDriver path seems incorrect: {driver_path}")
                driver_dir = os.path.dirname(driver_path)
                for possible_path in [os.path.join(driver_dir, 'chromedriver'), os.path.join(os.path.dirname(driver_dir), 'chromedriver')]:
                    if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                        driver_path = possible_path
                        logger.info(f"✅ Fixed ChromeDriver path: {driver_path}")
                        break
                else:
                    wdm_base = os.path.dirname(os.path.dirname(driver_dir))
                    for root, dirs, files in os.walk(wdm_base):
                        if 'chromedriver' in files and os.access(potential_driver := os.path.join(root, 'chromedriver'), os.X_OK):
                            driver_path = potential_driver
                            logger.info(f"✅ Found ChromeDriver: {driver_path}")
                            break
            driver = webdriver.Chrome(service=ChromeService(driver_path), options=options)

        elif self.browser_type == "firefox":
            options = webdriver.FirefoxOptions()
            for key, value in [("browser.download.folderList", 2), ("browser.download.dir", str(self.download_dir)),
                              ("browser.download.useDownloadDir", True), ("browser.download.manager.showWhenStarting", False),
                              ("browser.helperApps.neverAsk.saveToDisk", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                              ("pdfjs.disabled", True)]:
                options.set_preference(key, value)
            if self.headless:
                options.add_argument("--headless")
            driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

        elif self.browser_type == "edge":
            options = webdriver.EdgeOptions()
            options.add_experimental_option("prefs", {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            })
            if self.headless:
                options.add_argument("--headless")
            driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

        else:
            raise ValueError(f"Unsupported browser type: {self.browser_type}. Supported: chrome, firefox, edge")

        driver.maximize_window() if not self.headless else driver.set_window_size(1920, 1080)
        logger.info("✅ Browser setup complete")
        return driver

    def start_browser(self) -> bool:
        """Start browser session."""
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
                self.driver = self.is_logged_in = None
                logger.info("✅ Browser stopped")
            except Exception as e:
                logger.error(f"Error stopping browser: {e}")

    def manual_login_wait(self, wait_message: str = None) -> bool:
        """Wait for user to manually log in to Google account."""
        if not self.driver:
            logger.error("Browser not started")
            return False

        try:
            logger.info("Opening Google Docs for manual login...")
            self.driver.get("https://docs.google.com/")
            message = wait_message or "Please log in to your Google account in the browser window.\nPress Enter in the terminal when you're logged in..."
            print("\n" + "=" * 80 + "\nMANUAL LOGIN REQUIRED\n" + "=" * 80 + f"\n{message}\n" + "=" * 80)
            input()
            time.sleep(2)

            try:
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Google Account']")
                self.is_logged_in = True
                logger.info("✅ Login verification successful")
                print("✅ Login verified!")
                return True
            except NoSuchElementException:
                if "accounts.google.com" not in self.driver.current_url:
                    self.is_logged_in = True
                    logger.info("✅ Appears to be logged in (not on login page)")
                    print("✅ Proceeding (login page not detected)")
                    return True
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
        self, expected_extension: str = ".docx", timeout: int = None, min_creation_time: float = None, expected_filename_pattern: str = None, marker_file: Path = None
    ) -> Optional[Path]:
        """
        Wait for file download to complete.

        Args:
            expected_extension: Expected file extension
            timeout: Timeout in seconds (uses self.timeout if not provided)
            min_creation_time: Only consider files created after this timestamp (epoch time) - DEPRECATED, use marker_file instead
            expected_filename_pattern: Optional pattern to match in filename (helps avoid wrong file matches)
            marker_file: Unique marker file created before download - files created after this marker are candidates

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        timeout = timeout or self.timeout
        logger.info(f"Waiting for download to complete (timeout: {timeout}s)...")

        start_time = time.time()
        initial_files = set(self.download_dir.glob("*"))

        # Get marker file creation time if provided (more reliable than timestamp)
        marker_creation_time = None
        if marker_file and marker_file.exists():
            marker_creation_time = marker_file.stat().st_mtime
            logger.debug(f"Using marker file created at {marker_creation_time}")
        elif min_creation_time is not None:
            # Fallback to min_creation_time for backward compatibility
            marker_creation_time = min_creation_time
            logger.debug(f"Using timestamp-based matching (legacy mode)")

        while time.time() - start_time < timeout:
            current_files = set(self.download_dir.glob("*"))
            new_files = current_files - initial_files

            # Filter for completed files (not .crdownload, .tmp, .part, and not marker files)
            completed_files = [
                f
                for f in new_files
                if f.suffix == expected_extension
                and not any(
                    f.name.endswith(ext) for ext in [".crdownload", ".tmp", ".part"]
                )
                and not f.name.startswith(".download_marker_")
            ]

            # Further filter by marker creation time if specified
            if marker_creation_time is not None:
                completed_files = [
                    f for f in completed_files
                    if f.stat().st_mtime >= marker_creation_time
                ]

            # Further filter by expected filename pattern if specified
            if expected_filename_pattern and completed_files:
                import re
                sanitized_pattern = re.sub(r'[<>:"/\\|?*]', '', expected_filename_pattern)
                matched_files = [
                    f for f in completed_files
                    if sanitized_pattern in f.stem
                ]
                if matched_files:
                    completed_files = matched_files
                    logger.debug(f"Filtered {len(completed_files)} files matching pattern '{sanitized_pattern}'")
                else:
                    logger.warning(f"No files matched expected pattern '{sanitized_pattern}', using all {len(completed_files)} candidates")

            if completed_files:
                # Sort by modification time (newest first) to get the most recently downloaded file
                # This is critical when multiple downloads happen simultaneously
                downloaded_file = sorted(completed_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
                logger.info(f"✅ Download complete: {downloaded_file.name} (selected most recent from {len(completed_files)} new files)")
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
                # Wait for URL to contain the correct file_id (ensures navigation completed)
                wait.until(lambda driver: file_id in driver.current_url)
                logger.debug(f"URL loaded with file_id: {file_id}")

                # Wait for document canvas or title to indicate page loaded
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".kix-page-canvas, .docs-title-input"))
                )
                logger.debug("Document loaded")

                # Additional wait to ensure title has updated (avoid stale element)
                import time
                time.sleep(1)

            except TimeoutException:
                result["error"] = "Timeout waiting for document to load"
                logger.error(result["error"])
                return result

            # Get document title with retry logic
            doc_title = "Untitled"
            try:
                for attempt in range(3):
                    try:
                        if (title := self.driver.find_element(By.CSS_SELECTOR, ".docs-title-input").get_attribute("value") or "Untitled") and title != "Untitled":
                            doc_title = title
                            break
                        if attempt < 2:
                            logger.debug(f"Title empty/Untitled, retrying (attempt {attempt + 1})")
                            time.sleep(0.5)
                    except Exception as e:
                        if attempt < 2:
                            logger.debug(f"Error getting title, retrying (attempt {attempt + 1}): {e}")
                            time.sleep(0.5)
                        else:
                            raise
                result["title"] = doc_title
                logger.info(f"Document title: {doc_title}")
            except NoSuchElementException:
                result["title"] = doc_title
                logger.warning("Could not find document title, using 'Untitled'")

            # Download as DOCX
            # Method: Use File > Download > Microsoft Word (.docx)
            # URL parameter method (more reliable than menu navigation)
            download_url = f"https://docs.google.com/document/d/{file_id}/export?format=docx"
            logger.info("Initiating download...")

            # Create a unique marker file to identify downloads from THIS request
            # This is much more reliable than timestamp-only matching
            import uuid
            marker_id = str(uuid.uuid4())
            marker_file = self.download_dir / f".download_marker_{marker_id}"
            marker_file.touch()
            logger.debug(f"Created download marker: {marker_file.name}")

            try:
                self.driver.get(download_url)

                # Wait for download to complete
                # Pass marker file and doc_title for accurate matching
                downloaded_file = self._wait_for_download_complete(
                    expected_extension=".docx",
                    timeout=self.timeout,
                    marker_file=marker_file,
                    expected_filename_pattern=doc_title if doc_title and doc_title != "Untitled" else None
                )

                if not downloaded_file:
                    result["error"] = "Download timeout or failed"
                    logger.error(result["error"])
                    return result

            finally:
                try:
                    if marker_file.exists():
                        marker_file.unlink()
                        logger.debug(f"Removed download marker: {marker_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove marker file: {e}")

            # Verify filename matches doc title
            if doc_title and doc_title != "Untitled" and (sanitized_title := re.sub(r'[<>:"/\\|?*]', '', doc_title)) not in downloaded_file.stem:
                logger.warning(f"⚠️  Downloaded file name mismatch! Expected: '{sanitized_title}', Got: '{downloaded_file.stem}'. This may indicate wrong file match.")

            # Rename if custom filename provided
            if output_filename:
                output_filename = output_filename if output_filename.endswith(".docx") else f"{output_filename}.docx"
                final_path = self.download_dir / output_filename
                counter = 1
                while final_path.exists():
                    final_path = self.download_dir / f"{output_filename.rsplit('.docx', 1)[0]}_{counter}.docx"
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
