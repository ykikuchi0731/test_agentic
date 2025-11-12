"""Test ZIP export functionality."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from pre_processing.client import ServiceNowClient
from pre_processing.knowledge_base import KnowledgeBase
from pre_processing.zip_exporter import ZipExporter
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test ZIP export for a few articles."""
    
    print("="*80)
    print("ZIP Export Test")
    print("="*80)
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    logger.info(f"Connecting to ServiceNow: {Config.SERVICENOW_INSTANCE}")
    
    with ServiceNowClient(
        instance=Config.SERVICENOW_INSTANCE,
        username=Config.SERVICENOW_USERNAME,
        password=Config.SERVICENOW_PASSWORD
    ) as client:
        
        # Initialize handlers
        kb = KnowledgeBase(client)
        exporter = ZipExporter(output_dir='./test_exports')
        
        # Pre-fetch categories for better performance
        print("\nPre-fetching categories...")
        kb.prefetch_all_categories()
        
        # Get latest versions only
        print("\nFetching articles (latest versions only)...")
        articles = kb.get_latest_articles_only(limit=3)
        
        if not articles:
            print("No articles found")
            return
        
        print(f"\nFound {len(articles)} articles")
        print("\n" + "="*80)
        
        # Process each article
        articles_data = []
        
        for i, article in enumerate(articles, 1):
            article_number = article.get('number', 'unknown')
            title = article.get('short_description', 'Untitled')
            
            print(f"\n{i}. Processing article {article_number}: {title}")
            
            # Get article with merged translations
            full_article = kb.get_article_with_translations(article['sys_id'])
            
            # Get category path
            article_with_cat = kb.get_article_with_category_path(article['sys_id'])
            category_path = article_with_cat.get('category_path', [])
            full_article['category_path'] = category_path
            
            if category_path:
                path_str = ' > '.join([c['label'] for c in category_path])
                print(f"   Category: {path_str}")
            
            # Get attachments
            attachments = kb.get_article_attachments(
                article['sys_id'],
                download=True
            )
            
            print(f"   Attachments: {len(attachments)}")
            
            # Show translation info
            translations = full_article.get('translations', [])
            if translations:
                print(f"   Translations: {len(translations)} (merged into HTML)")
            
            # Prepare data with merged HTML
            article_data = {
                'article': full_article,
                'html_content': full_article.get('merged_html', full_article.get('text', '')),
                'attachments': attachments,
                'category_path': category_path,
                'translations': translations
            }
            
            articles_data.append(article_data)
        
        # Create bulk ZIP
        print("\n" + "="*80)
        print("Creating ZIP export...")
        print("="*80)
        
        zip_path = exporter.create_bulk_zip(articles_data)
        
        print(f"\n✅ ZIP created successfully!")
        print(f"   Location: {zip_path}")
        print(f"   Articles: {len(articles_data)}")
        
        # Display ZIP contents info
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            print(f"   Files in ZIP: {len(zf.namelist())}")
            print(f"\n   Contents:")
            for name in sorted(zf.namelist())[:20]:  # Show first 20
                print(f"      - {name}")
            if len(zf.namelist()) > 20:
                print(f"      ... and {len(zf.namelist()) - 20} more files")
        
        print("\n" + "="*80)
        print("Test complete!")
        print("="*80)


if __name__ == '__main__':
    main()

