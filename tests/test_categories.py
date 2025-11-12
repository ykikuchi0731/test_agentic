"""Test script to check category information in ServiceNow knowledge base articles."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import json
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
    """Check category information in articles."""
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    logger.info(f"Connecting to ServiceNow instance: {Config.SERVICENOW_INSTANCE}")
    
    try:
        with ServiceNowClient(
            instance=Config.SERVICENOW_INSTANCE,
            username=Config.SERVICENOW_USERNAME,
            password=Config.SERVICENOW_PASSWORD,
            timeout=Config.API_TIMEOUT
        ) as client:
            
            kb = KnowledgeBase(client, download_dir=Config.DOWNLOAD_DIR)
            
            # Get articles with category fields
            logger.info("\n=== Fetching articles with category information ===\n")
            
            # Include all possible category-related fields
            category_fields = [
                'sys_id',
                'number',
                'short_description',
                'kb_category',  # Category reference
                'category',      # Alternative category field
                'kb_knowledge_base',  # Knowledge base reference
                'workflow_state'
            ]
            
            articles = kb.list_articles(fields=category_fields, limit=5)
            
            if not articles:
                logger.warning("No articles found")
                return
            
            print(f"Found {len(articles)} articles\n")
            print("="*100)
            
            # Display article information with categories
            for i, article in enumerate(articles, 1):
                print(f"\n{i}. Article: {article.get('number', 'N/A')}")
                print(f"   Title: {article.get('short_description', 'N/A')}")
                print(f"   State: {article.get('workflow_state', 'N/A')}")
                print(f"   Sys ID: {article.get('sys_id', 'N/A')}")
                
                # Check category fields
                kb_category = article.get('kb_category', {})
                category = article.get('category', {})
                kb_knowledge_base = article.get('kb_knowledge_base', {})
                
                print(f"\n   Category Information:")
                print(f"   - kb_category: {kb_category}")
                print(f"   - category: {category}")
                print(f"   - kb_knowledge_base: {kb_knowledge_base}")
                
                # If kb_category has a value (sys_id), fetch the category details
                if kb_category and isinstance(kb_category, dict) and kb_category.get('value'):
                    category_sys_id = kb_category['value']
                    print(f"\n   Fetching category details for: {category_sys_id}")
                    
                    try:
                        category_details = client.get_record(
                            table='kb_category',
                            sys_id=category_sys_id,
                            fields=['sys_id', 'label', 'parent_id', 'full_path']
                        )
                        print(f"   Category Details:")
                        print(f"     - Label: {category_details.get('label', 'N/A')}")
                        print(f"     - Parent ID: {category_details.get('parent_id', 'N/A')}")
                        print(f"     - Full Path: {category_details.get('full_path', 'N/A')}")
                        
                        # If there's a parent, show hierarchy
                        if category_details.get('parent_id') and isinstance(category_details['parent_id'], dict):
                            parent_value = category_details['parent_id'].get('value')
                            if parent_value:
                                print(f"     - Has parent category: {parent_value}")
                    
                    except Exception as e:
                        print(f"   Error fetching category details: {e}")
                
                print("\n" + "-"*100)
            
            print("\n" + "="*100)
            print("\nCategory Metadata Summary:")
            print("- Articles have 'kb_category' field that references the kb_category table")
            print("- Categories can have parent categories (hierarchy)")
            print("- Category details include: label, parent_id, and full_path")
            print("="*100)
            
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()

