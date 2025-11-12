"""Example usage of ServiceNow knowledge portal migration tool."""
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
    """Main function demonstrating the usage of the migration tool."""
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Please set environment variables or update config.py")
        return
    
    # Initialize ServiceNow client
    logger.info(f"Connecting to ServiceNow instance: {Config.SERVICENOW_INSTANCE}")
    
    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD,
        timeout=Config.API_TIMEOUT
    ) as client:
        
        # Initialize knowledge base handler
        kb = KnowledgeBase(client, download_dir=Config.DOWNLOAD_DIR)
        
        # Example 1: List all articles
        logger.info("\n=== Listing all knowledge articles ===")
        articles = kb.list_articles(
            query='workflow_state=published',
            limit=10  # Limit for demonstration
        )
        
        logger.info(f"Found {len(articles)} articles")
        for article in articles:
            logger.info(f"  - {article['number']}: {article['short_description']}")
        
        # Example 2: Get specific article with HTML content
        if articles:
            first_article = articles[0]
            article_sys_id = first_article['sys_id']
            
            logger.info(f"\n=== Getting article details: {first_article['number']} ===")
            article_data = kb.get_article(article_sys_id)
            
            logger.info(f"Title: {article_data['short_description']}")
            logger.info(f"Created: {article_data['sys_created_on']}")
            logger.info(f"HTML content length: {len(article_data.get('text', ''))} characters")
            
            # Parse HTML content
            if article_data.get('text'):
                parsed = kb.parse_article_html(article_data['text'])
                logger.info(f"Parsed content:")
                logger.info(f"  - Plain text length: {len(parsed['text'])} characters")
                logger.info(f"  - Images found: {len(parsed['images'])}")
                logger.info(f"  - Links found: {len(parsed['links'])}")
                logger.info(f"  - Tables found: {len(parsed['tables'])}")
                logger.info(f"  - Headings found: {len(parsed['headings'])}")
            
            # Example 3: Get and download attachments
            logger.info(f"\n=== Getting attachments for article: {first_article['number']} ===")
            attachments = kb.get_article_attachments(
                article_sys_id,
                download=True  # Set to False to only get metadata
            )
            
            if attachments:
                logger.info(f"Found {len(attachments)} attachments:")
                for att in attachments:
                    logger.info(f"  - {att['file_name']} ({att['size_bytes']} bytes)")
                    if 'file_path' in att:
                        logger.info(f"    Downloaded to: {att['file_path']}")
            else:
                logger.info("No attachments found")
        
        logger.info("\n=== Migration tool demonstration complete ===")


if __name__ == '__main__':
    main()

