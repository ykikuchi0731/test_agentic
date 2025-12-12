"""Export Google Documents to DOCX format using browser automation (Selenium)."""
import logging
import os
import re
import time
import uuid
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

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

load_dotenv()
logger = logging.getLogger(__name__)


class DownloadManager:
    """Manages Google Docs downloads with deterministic file tracking using global lock."""

    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.download_lock = threading.Lock()
        logger.info("DownloadManager initialized with sequential download enforcement")

    def download_with_tracking(self, driver, file_id: str, doc_title: Optional[str],
                               download_url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Download Google Doc with deterministic tracking using global lock."""
        with self.download_lock:
            logger.debug(f"Acquired download lock for {file_id}")
            initial_files = set(self.download_dir.glob("*.docx"))

            try:
                driver.get(download_url)
            except Exception as e:
                logger.error(f"Failed to navigate to download URL: {e}")
                return None

            start_time = time.time()
            while time.time() - start_time < timeout:
                current_files = set(self.download_dir.glob("*.docx"))
                new_files = current_files - initial_files
                completed_files = [f for f in new_files if not any(f.name.endswith(ext)
                                   for ext in [".crdownload", ".tmp", ".part"])
                                   and not f.name.endswith(".tracking.json")]

                if completed_files:
                    downloaded_file = (sorted(completed_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
                                      if len(completed_files) > 1 else completed_files[0])
                    if len(completed_files) > 1:
                        logger.warning(f"Multiple files during single download: {[f.name for f in completed_files]}, using: {downloaded_file.name}")

                    logger.info(f"✅ Download complete: {downloaded_file.name} (deterministic - had lock)")

                    doc_title = doc_title or downloaded_file.stem
                    logger.debug(f"Extracted doc_title from filename: {doc_title}" if doc_title == downloaded_file.stem else "")

                    tracking_file = self.download_dir / f"{downloaded_file.name}.tracking.json"
                    tracking_data = {
                        "download_id": str(uuid.uuid4()),
                        "file_id": file_id,
                        "doc_title": doc_title,
                        "downloaded_filename": downloaded_file.name,
                        "download_timestamp": time.time()
                    }

                    try:
                        tracking_file.write_text(json.dumps(tracking_data, indent=2))
                        logger.debug(f"Created tracking file: {tracking_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to create tracking file: {e}")

                    return {'filename': downloaded_file.name, 'filepath': str(downloaded_file),
                           'file_id': file_id, 'doc_title': doc_title}

                if partial := [f for f in current_files if any(f.name.endswith(ext)
                               for ext in [".crdownload", ".tmp", ".part"])]:
                    logger.debug("Download in progress...")

                time.sleep(0.5)

            logger.warning(f"Download timeout after {timeout}s for {file_id}")
            return None


class GoogleDocsBrowserExporter:
    """Export Google Documents to DOCX format using browser automation."""

    def __init__(self, download_dir: str = "./google_docs_exports", browser_type: str = "chrome",
                 headless: bool = False, timeout: int = None, download_timeout: int = None):
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.timeout = timeout if timeout is not None else int(os.getenv('GOOGLE_DOCS_BROWSER_TIMEOUT', '60'))
        self.download_timeout = download_timeout if download_timeout is not None else int(os.getenv('GOOGLE_DOCS_DOWNLOAD_TIMEOUT', '120'))
        self.driver: Optional[webdriver.Remote] = None
        self.is_logged_in = False
        self.download_manager = DownloadManager(self.download_dir)
        logger.info(f"Google Docs browser exporter initialized with output dir: {download_dir}")
        logger.info(f"Browser: {browser_type}, Headless: {headless}, Timeouts - Browser: {self.timeout}s, Download: {self.download_timeout}s")

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
                for possible_path in [os.path.join(driver_dir, 'chromedriver'),
                                     os.path.join(os.path.dirname(driver_dir), 'chromedriver')]:
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
        """Extract Google Docs file ID from URL or return raw file ID."""
        if match := re.search(r"https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)", url):
            file_id = match.group(1)
            logger.debug(f"Extracted file ID from URL: {file_id}")
            return file_id
        if re.match(r"^[a-zA-Z0-9-_]+$", url):
            logger.debug(f"Input appears to be a file ID: {url}")
            return url
        logger.warning(f"Could not extract file ID from: {url}")
        return None

    def export_single_document(self, file_id_or_url: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """Export a single Google Document to DOCX format."""
        result = {"success": False, "file_path": None, "title": None, "error": None}

        if not self.driver:
            result["error"] = "Browser not started. Call start_browser() first."
            logger.error(result["error"])
            return result

        if not self.is_logged_in:
            result["error"] = "Not logged in. Call manual_login_wait() first."
            logger.error(result["error"])
            return result

        if not (file_id := self.extract_file_id_from_url(file_id_or_url)):
            result["error"] = f"Invalid file ID or URL: {file_id_or_url}"
            logger.error(result["error"])
            return result

        logger.info(f"Exporting Google Doc: {file_id}")

        for attempt in range(2):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/1 for {file_id}")
                    time.sleep(2 * attempt)

                download_url = f"https://docs.google.com/document/d/{file_id}/export?format=docx"
                logger.info(f"Downloading directly from export URL (no page load required)")

                download_result = self.download_manager.download_with_tracking(
                    driver=self.driver, file_id=file_id, doc_title=None,
                    download_url=download_url, timeout=self.download_timeout
                )

                if not download_result:
                    if attempt < 1:
                        logger.warning(f"Download failed, will retry ({attempt + 1}/1)")
                        continue
                    else:
                        result["error"] = "Download timeout or failed after retries"
                        logger.error(result["error"])
                        return result

                downloaded_file = Path(download_result['filepath'])
                result["title"] = downloaded_file.stem
                logger.info(f"Document downloaded: {result['title']}")
                break

            except Exception as e:
                if attempt < 1:
                    logger.warning(f"Download error: {e}, will retry ({attempt + 1}/1)")
                    continue
                else:
                    result["error"] = f"Download failed after retries: {e}"
                    logger.error(result["error"], exc_info=True)
                    return result

        try:
            if output_filename:
                output_filename = output_filename if output_filename.endswith(".docx") else f"{output_filename}.docx"
                final_path = self.download_dir / output_filename
                counter = 1
                while final_path.exists():
                    final_path = self.download_dir / f"{output_filename.rsplit('.docx', 1)[0]}_{counter}.docx"
                    counter += 1

                old_tracking = self.download_dir / f"{downloaded_file.name}.tracking.json"
                new_tracking = self.download_dir / f"{final_path.name}.tracking.json"
                if old_tracking.exists():
                    try:
                        old_tracking.rename(new_tracking)
                        logger.debug(f"Moved tracking file: {new_tracking.name}")
                    except Exception as e:
                        logger.warning(f"Failed to move tracking file: {e}")

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

    def export_multiple_documents(self, file_ids_or_urls: List[str]) -> List[Dict[str, Any]]:
        """Export multiple Google Documents to DOCX format."""
        logger.info(f"Starting batch export of {len(file_ids_or_urls)} documents...")
        results = []
        for i, file_id_or_url in enumerate(file_ids_or_urls, 1):
            logger.info(f"Exporting document {i}/{len(file_ids_or_urls)}")
            results.append(self.export_single_document(file_id_or_url))
            if i < len(file_ids_or_urls):
                time.sleep(2)

        successful = sum(1 for r in results if r["success"])
        logger.info(f"✅ Batch export complete: {successful}/{len(file_ids_or_urls)} successful")
        return results

    def __enter__(self):
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_browser()
