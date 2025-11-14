"""Configuration settings for ServiceNow to Notion migration."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# Use override=True to ensure .env values take precedence over shell environment
load_dotenv(override=True)


class Config:
    """Configuration class for ServiceNow connection."""
    
    # ServiceNow instance settings
    SERVICENOW_INSTANCE = os.getenv('SERVICENOW_INSTANCE', '')
    SERVICENOW_USERNAME = os.getenv('SERVICENOW_USERNAME', '')
    SERVICENOW_PASSWORD = os.getenv('SERVICENOW_PASSWORD', '')
    
    # API configuration
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # File download settings
    DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '104857600'))  # 100MB default
    
    # Knowledge base settings
    KB_TABLE = 'kb_knowledge'
    ATTACHMENT_TABLE = 'sys_attachment'
    
    # Export settings
    MIGRATION_OUTPUT_DIR = os.getenv('MIGRATION_OUTPUT_DIR', './migration_output')
    CREATE_ZIP_EXPORTS = os.getenv('CREATE_ZIP_EXPORTS', 'true').lower() == 'true'

    # Google Workspace API settings (for Google Docs export - API method, currently disabled)
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', './credentials.json')
    GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', './token.json')
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents.readonly'
    ]
    GOOGLE_DOCS_OUTPUT_DIR = os.getenv('GOOGLE_DOCS_OUTPUT_DIR', './google_docs_exports')

    # Browser automation settings (for Google Docs export - Selenium method)
    BROWSER_DOWNLOAD_DIR = os.getenv('BROWSER_DOWNLOAD_DIR', './google_docs_exports')
    BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')  # chrome, firefox, edge
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '30'))  # seconds
    GOOGLE_EMAIL = os.getenv('GOOGLE_EMAIL', '')  # Optional: for auto-login
    GOOGLE_PASSWORD = os.getenv('GOOGLE_PASSWORD', '')  # Optional: for auto-login (use with caution)

    @classmethod
    def validate(cls):
        """Validate required configuration settings."""
        if not cls.SERVICENOW_INSTANCE:
            raise ValueError("SERVICENOW_INSTANCE is required")
        if not cls.SERVICENOW_USERNAME:
            raise ValueError("SERVICENOW_USERNAME is required")
        if not cls.SERVICENOW_PASSWORD:
            raise ValueError("SERVICENOW_PASSWORD is required")
        return True

