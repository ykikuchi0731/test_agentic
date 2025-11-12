"""Test script to demonstrate category hierarchy functionality."""
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
    """Test category hierarchy retrieval."""
    
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
            
            # Get a few articles with categories
            logger.info("\n=== Listing articles with category information ===\n")
            articles = kb.list_articles(limit=3)
            
            if not articles:
                logger.warning("No articles found")
                return
            
            print("="*100)
            
            # Display articles with their full category paths
            for i, article in enumerate(articles, 1):
                print(f"\n{i}. Article: {article.get('number', 'N/A')}")
                print(f"   Title: {article.get('short_description', 'N/A')}")
                print(f"   Sys ID: {article.get('sys_id', 'N/A')}")
                
                # Check if article has a category
                kb_category = article.get('kb_category', {})
                
                if isinstance(kb_category, dict) and kb_category.get('value'):
                    category_sys_id = kb_category['value']
                    print(f"\n   Category Sys ID: {category_sys_id}")
                    
                    # Get full category hierarchy
                    print(f"   Fetching category hierarchy...")
                    hierarchy = kb.get_category_hierarchy(category_sys_id)
                    
                    if hierarchy:
                        print(f"\n   Category Hierarchy (Root → Current):")
                        path_labels = []
                        for j, cat in enumerate(hierarchy):
                            indent = "     " + "  " * j
                            print(f"{indent}└─ {cat['label']} (ID: {cat['sys_id']})")
                            path_labels.append(cat['label'])
                        
                        print(f"\n   Full Path: {' > '.join(path_labels)}")
                else:
                    print("\n   No category assigned")
                
                print("\n" + "-"*100)
            
            # Demonstrate the convenience method
            if articles:
                print("\n\n=== Using get_article_with_category_path() convenience method ===\n")
                first_article_sys_id = articles[0]['sys_id']
                
                article_with_path = kb.get_article_with_category_path(first_article_sys_id)
                
                print(f"Article: {article_with_path['number']}")
                print(f"Title: {article_with_path['short_description']}")
                
                if article_with_path.get('category_path'):
                    path = ' > '.join([c['label'] for c in article_with_path['category_path']])
                    print(f"Category Path: {path}")
                else:
                    print("Category Path: None")
            
            print("\n" + "="*100)
            
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()

