# Quick Start Guide

Get up and running with the ServiceNow to Notion migration tool in 5 minutes!

## 1. Install Dependencies (30 seconds)

```bash
cd /app/test_agentic
pip install -r requirements.txt
```

## 2. Configure Credentials (1 minute)

Create `.env` file from template:
```bash
cp env.example .env
```

Edit `.env` with your ServiceNow credentials:
```bash
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

## 3. Test Connection (30 seconds)

List 10 articles:
```bash
python tests/test_list_articles.py
```

You should see output like:
```
1. Article Number: KB0013936
   Title: ITツール利用申請マニュアル
   ...
```

## 4. Explore Features (2 minutes)

### See Category Hierarchy
```bash
python tests/test_category_hierarchy.py
```

Output:
```
Category Path: オフィス > 東京オフィス > イベント
```

### See Performance Optimization
```bash
python tests/test_optimization.py
```

Output:
```
Loaded 593 categories in 2.34 seconds
Processing 5 articles with 0 category API calls!
```

### Run Full Example
```bash
python examples/main.py
```

## 5. Start Your Migration (1 minute)

Create your migration script:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from servicenow.client import ServiceNowClient
from servicenow.knowledge_base import KnowledgeBase
from config import Config

# Initialize
with ServiceNowClient(
    instance=Config.SERVICENOW_INSTANCE,
    username=Config.SERVICENOW_USERNAME,
    password=Config.SERVICENOW_PASSWORD
) as client:
    
    kb = KnowledgeBase(client)
    
    # IMPORTANT: Pre-fetch for 99% API call reduction!
    print("Loading categories...")
    kb.prefetch_all_categories()
    
    # Get all published articles
    articles = kb.get_all_articles_paginated(
        query='workflow_state=published'
    )
    
    print(f"Found {len(articles)} articles")
    
    # Process each article
    for i, article in enumerate(articles, 1):
        print(f"\nProcessing {i}/{len(articles)}: {article['number']}")
        
        # Get full details with category hierarchy
        full_article = kb.get_article_with_category_path(article['sys_id'])
        
        # Get category path
        if full_article['category_path']:
            category = ' > '.join([c['label'] for c in full_article['category_path']])
            print(f"  Category: {category}")
        
        # Parse HTML content
        parsed = kb.parse_article_html(full_article['text'])
        print(f"  Content: {len(parsed['text'])} chars, {len(parsed['images'])} images")
        
        # Get attachments
        attachments = kb.get_article_attachments(
            article['sys_id'],
            download=True
        )
        print(f"  Attachments: {len(attachments)}")
        
        # TODO: Your Notion migration logic here
        # migrate_to_notion(full_article, parsed, attachments)

print("\nMigration complete!")
```

Save as `migrate.py` and run:
```bash
python migrate.py
```

## Common Tasks

### List All Articles
```python
from servicenow.client import ServiceNowClient
from servicenow.knowledge_base import KnowledgeBase
from config import Config

with ServiceNowClient(...) as client:
    kb = KnowledgeBase(client)
    articles = kb.list_articles()
```

### Get Article with Category
```python
article = kb.get_article_with_category_path('article_sys_id')
category_path = ' > '.join([c['label'] for c in article['category_path']])
```

### Download Attachments
```python
attachments = kb.get_article_attachments(
    article_sys_id='abc123',
    download=True
)
```

### Parse HTML
```python
parsed = kb.parse_article_html(html_content)
print(parsed['text'])        # Plain text
print(parsed['images'])      # Image list
print(parsed['links'])       # Link list
```

## Performance Tips

### ⚡ Always Use Pre-fetching
```python
kb = KnowledgeBase(client)
kb.prefetch_all_categories()  # Add this ONE line

# Now process thousands of articles
# with ZERO category API calls!
```

**Impact:**
- Without: ~3,500 API calls for 1000 articles
- With: 1 API call total
- **99% reduction!**

### ⚡ Use Pagination for Large Datasets
```python
articles = kb.get_all_articles_paginated(page_size=100)
```

### ⚡ Filter to Reduce Volume
```python
# Only published articles
articles = kb.list_articles(query='workflow_state=published')

# Articles from specific knowledge base
articles = kb.list_articles(query='kb_knowledge_base=xyz123')
```

## Troubleshooting

### "Module not found" Error
Make sure you're running from the right directory or have the path fix:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### "Configuration error" Message
Check your `.env` file has correct credentials:
```bash
cat .env
```

### API Rate Limiting
If you hit rate limits, use pre-fetching to reduce API calls:
```python
kb.prefetch_all_categories()  # This helps!
```

## Next Steps

1. ✅ Set up and test connection
2. ✅ Explore features with test scripts
3. ⬜ Create your migration script
4. ⬜ Test with small batch (10-20 articles)
5. ⬜ Run full migration
6. ⬜ Verify data in Notion

## Resources

- **README.md** - Complete documentation
- **PROJECT_ORGANIZATION.md** - File structure explained
- **docs/API_OPTIMIZATION_SUMMARY.md** - Performance guide
- **examples/main.py** - Full working example

## Getting Help

1. Check the examples: `examples/main.py`
2. Read the docs: `docs/*.md`
3. Review test scripts: `tests/*.py`
4. Check the code: `servicenow/*.py` (well-documented)

## Summary

```
✅ Install: pip install -r requirements.txt
✅ Configure: Copy env.example to .env
✅ Test: python tests/test_list_articles.py
✅ Optimize: kb.prefetch_all_categories()
✅ Migrate: Process all articles with 99% fewer API calls!
```

Happy migrating! 🚀

