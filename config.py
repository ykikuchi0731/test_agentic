"""Configuration settings for ServiceNow to Notion migration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# Use override=True to ensure .env values take precedence over shell environment
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """Configuration class for ServiceNow to Notion migration."""

    # =========================================================================
    # SERVICENOW CONFIGURATION (REQUIRED for pre-processing)
    # =========================================================================

    SERVICENOW_INSTANCE = os.getenv('SERVICENOW_INSTANCE', '').strip()
    SERVICENOW_USERNAME = os.getenv('SERVICENOW_USERNAME', '').strip()
    SERVICENOW_PASSWORD = os.getenv('SERVICENOW_PASSWORD', '').strip()

    # =========================================================================
    # NOTION API CONFIGURATION (REQUIRED for post-processing)
    # =========================================================================

    NOTION_API_KEY = os.getenv('NOTION_API_KEY', '').strip()
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '').strip()

    # =========================================================================
    # API SETTINGS
    # =========================================================================

    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

    # =========================================================================
    # FILE DOWNLOAD SETTINGS
    # =========================================================================

    DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '104857600'))  # 100MB default

    # =========================================================================
    # KNOWLEDGE BASE SETTINGS
    # =========================================================================

    KB_TABLE = 'kb_knowledge'
    ATTACHMENT_TABLE = 'sys_attachment'

    # =========================================================================
    # EXPORT SETTINGS
    # =========================================================================

    MIGRATION_OUTPUT_DIR = os.getenv('MIGRATION_OUTPUT_DIR', './migration_output')
    CREATE_ZIP_EXPORTS = os.getenv('CREATE_ZIP_EXPORTS', 'true').lower() == 'true'

    # =========================================================================
    # GOOGLE WORKSPACE API SETTINGS (for Google Docs export - API method)
    # Currently disabled due to GCP restrictions - use browser automation instead
    # =========================================================================

    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', './credentials.json')
    GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', './token.json')
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents.readonly'
    ]
    GOOGLE_DOCS_OUTPUT_DIR = os.getenv('GOOGLE_DOCS_OUTPUT_DIR', './google_docs_exports')

    # =========================================================================
    # BROWSER AUTOMATION SETTINGS (for Google Docs export - Selenium method)
    # RECOMMENDED method for Google Docs download
    # =========================================================================

    BROWSER_DOWNLOAD_DIR = os.getenv('BROWSER_DOWNLOAD_DIR', './google_docs_exports')
    BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')  # chrome, firefox, edge
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '30'))  # seconds

    # Optional: Google account credentials for automation (use with caution)
    # Manual login is recommended for security
    GOOGLE_EMAIL = os.getenv('GOOGLE_EMAIL', '').strip()
    GOOGLE_PASSWORD = os.getenv('GOOGLE_PASSWORD', '').strip()

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================

    @classmethod
    def validate_servicenow(cls, raise_error: bool = True) -> bool:
        """
        Validate ServiceNow configuration.

        Args:
            raise_error: If True, raises ConfigurationError when invalid.
                        If False, returns False when invalid.

        Returns:
            True if valid, False otherwise (only if raise_error=False)

        Raises:
            ConfigurationError: If required settings are missing and raise_error=True
        """
        errors = []

        if not cls.SERVICENOW_INSTANCE:
            errors.append("SERVICENOW_INSTANCE is required")
        if not cls.SERVICENOW_USERNAME:
            errors.append("SERVICENOW_USERNAME is required")
        if not cls.SERVICENOW_PASSWORD:
            errors.append("SERVICENOW_PASSWORD is required")

        if errors:
            if raise_error:
                error_msg = (
                    "ServiceNow configuration is incomplete:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                    + "\n\nPlease set the required environment variables in your .env file."
                    + "\nSee env.example for reference."
                )
                raise ConfigurationError(error_msg)
            return False

        return True

    @classmethod
    def validate_notion(cls, raise_error: bool = True) -> bool:
        """
        Validate Notion API configuration.

        Args:
            raise_error: If True, raises ConfigurationError when invalid.
                        If False, returns False when invalid.

        Returns:
            True if valid, False otherwise (only if raise_error=False)

        Raises:
            ConfigurationError: If required settings are missing and raise_error=True
        """
        errors = []

        if not cls.NOTION_API_KEY:
            errors.append("NOTION_API_KEY is required")

        if not cls.NOTION_DATABASE_ID:
            errors.append("NOTION_DATABASE_ID is required (optional for some operations)")

        if errors:
            if raise_error:
                error_msg = (
                    "Notion API configuration is incomplete:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                    + "\n\nPlease set the required environment variables in your .env file."
                    + "\nSee env.example for reference."
                    + "\n\nTo get your Notion API key:"
                    + "\n  1. Go to https://www.notion.so/my-integrations"
                    + "\n  2. Create a new integration"
                    + "\n  3. Copy the Internal Integration Token"
                )
                raise ConfigurationError(error_msg)
            return False

        return True

    @classmethod
    def validate_google_browser(cls, raise_error: bool = True) -> bool:
        """
        Validate browser automation configuration for Google Docs export.

        Args:
            raise_error: If True, raises ConfigurationError when invalid.
                        If False, returns False when invalid.

        Returns:
            True if valid, False otherwise (only if raise_error=False)

        Raises:
            ConfigurationError: If configuration is invalid and raise_error=True
        """
        errors = []

        valid_browsers = ['chrome', 'firefox', 'edge']
        if cls.BROWSER_TYPE not in valid_browsers:
            errors.append(
                f"BROWSER_TYPE must be one of {valid_browsers}, got '{cls.BROWSER_TYPE}'"
            )

        if cls.BROWSER_TIMEOUT < 10:
            errors.append("BROWSER_TIMEOUT should be at least 10 seconds")

        if errors:
            if raise_error:
                error_msg = (
                    "Browser automation configuration is invalid:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                    + "\n\nPlease check your .env file settings."
                )
                raise ConfigurationError(error_msg)
            return False

        return True

    @classmethod
    def validate_all(cls, modules: list = None) -> bool:
        """
        Validate all required configuration based on modules being used.

        Args:
            modules: List of modules to validate. Valid values:
                    - 'servicenow': Validate ServiceNow config
                    - 'notion': Validate Notion config
                    - 'google_browser': Validate browser automation config
                    If None, validates only ServiceNow (for backward compatibility)

        Returns:
            True if all specified modules are valid

        Raises:
            ConfigurationError: If any required settings are missing

        Example:
            # Validate ServiceNow only
            Config.validate_all()

            # Validate ServiceNow and Notion
            Config.validate_all(['servicenow', 'notion'])

            # Validate everything
            Config.validate_all(['servicenow', 'notion', 'google_browser'])
        """
        if modules is None:
            modules = ['servicenow']  # Default for backward compatibility

        all_valid = True

        if 'servicenow' in modules:
            all_valid &= cls.validate_servicenow(raise_error=True)

        if 'notion' in modules:
            all_valid &= cls.validate_notion(raise_error=True)

        if 'google_browser' in modules:
            all_valid &= cls.validate_google_browser(raise_error=True)

        return all_valid

    @classmethod
    def validate(cls):
        """
        Legacy validation method for backward compatibility.
        Validates ServiceNow configuration only.

        Returns:
            True if ServiceNow configuration is valid

        Raises:
            ValueError: If ServiceNow configuration is missing
        """
        try:
            return cls.validate_servicenow(raise_error=True)
        except ConfigurationError as e:
            # Convert to ValueError for backward compatibility
            raise ValueError(str(e))

    @classmethod
    def check_env_file(cls) -> bool:
        """
        Check if .env file exists and display helpful message if not.

        Returns:
            True if .env file exists, False otherwise
        """
        env_path = Path(__file__).parent / '.env'

        if not env_path.exists():
            print("=" * 80)
            print("⚠️  WARNING: .env file not found")
            print("=" * 80)
            print()
            print("Please create a .env file in the project root with your configuration.")
            print()
            print("Steps:")
            print("  1. Copy env.example to .env:")
            print("     cp env.example .env")
            print()
            print("  2. Edit .env and add your credentials:")
            print("     - ServiceNow instance, username, password")
            print("     - Notion API key (if using post-processing)")
            print("     - Other optional settings")
            print()
            print("  3. Run your script again")
            print()
            print("=" * 80)
            return False

        return True

    @classmethod
    def print_config_summary(cls, hide_secrets: bool = True):
        """
        Print configuration summary for debugging.

        Args:
            hide_secrets: If True, masks sensitive information
        """
        def mask(value: str) -> str:
            """Mask sensitive values."""
            if not value or not hide_secrets:
                return value or '(not set)'
            if len(value) <= 4:
                return '***'
            return value[:4] + '***'

        print("=" * 80)
        print("Configuration Summary")
        print("=" * 80)
        print()
        print("ServiceNow:")
        print(f"  Instance:  {cls.SERVICENOW_INSTANCE or '(not set)'}")
        print(f"  Username:  {cls.SERVICENOW_USERNAME or '(not set)'}")
        print(f"  Password:  {mask(cls.SERVICENOW_PASSWORD)}")
        print()
        print("Notion:")
        print(f"  API Key:   {mask(cls.NOTION_API_KEY)}")
        print(f"  Database:  {cls.NOTION_DATABASE_ID or '(not set)'}")
        print()
        print("Directories:")
        print(f"  Downloads: {cls.DOWNLOAD_DIR}")
        print(f"  Exports:   {cls.MIGRATION_OUTPUT_DIR}")
        print(f"  Google:    {cls.BROWSER_DOWNLOAD_DIR}")
        print()
        print("Browser Automation:")
        print(f"  Type:      {cls.BROWSER_TYPE}")
        print(f"  Headless:  {cls.BROWSER_HEADLESS}")
        print(f"  Timeout:   {cls.BROWSER_TIMEOUT}s")
        print()
        print("=" * 80)


# Auto-check for .env file on module import
if __name__ != "__main__":
    Config.check_env_file()
