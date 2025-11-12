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

