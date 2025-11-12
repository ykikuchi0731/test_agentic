"""Test script to list 10 articles from ServiceNow knowledge base."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """List 10 articles from the knowledge base."""
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Please set environment variables in .env file")
        return
    
    # Initialize ServiceNow client
    logger.info(f"Connecting to ServiceNow instance: {Config.SERVICENOW_INSTANCE}")
    
    try:
        with ServiceNowClient(
            instance=Config.SERVICENOW_INSTANCE,
            username=Config.SERVICENOW_USERNAME,
            password=Config.SERVICENOW_PASSWORD,
            timeout=Config.API_TIMEOUT
        ) as client:
            
            # Initialize knowledge base handler
            kb = KnowledgeBase(client, download_dir=Config.DOWNLOAD_DIR)
            
            # List 10 articles
            logger.info("\n=== Listing 10 knowledge articles ===\n")
            articles = kb.list_articles(limit=10)
            
            if not articles:
                logger.warning("No articles found in the knowledge base")
                return
            
            logger.info(f"Found {len(articles)} articles:\n")
            
            # Display article information
            for i, article in enumerate(articles, 1):
                print(f"\n{i}. Article Number: {article.get('number', 'N/A')}")
                print(f"   Title: {article.get('short_description', 'N/A')}")
                print(f"   State: {article.get('workflow_state', 'N/A')}")
                print(f"   Created: {article.get('sys_created_on', 'N/A')}")
                print(f"   Updated: {article.get('sys_updated_on', 'N/A')}")
                print(f"   Sys ID: {article.get('sys_id', 'N/A')}")
                
                # Show content preview if available
                text = article.get('text', '')
                if text:
                    preview = text[:100].replace('\n', ' ')
                    print(f"   Content Preview: {preview}...")
            
            print("\n" + "="*80)
            print(f"Successfully retrieved {len(articles)} articles")
            print("="*80)
            
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()

