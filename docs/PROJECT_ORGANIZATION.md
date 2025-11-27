# Project Organization

This document explains how the ServiceNow to Notion migration tool is organized.

## Directory Structure

```
test_agentic/
├── 📄 Configuration & Setup
│   ├── README.md              # Main project documentation
│   ├── requirements.txt       # Python dependencies
│   ├── config.py              # Configuration settings
│   ├── env.example            # Environment variables template
│   └── .gitignore             # Git ignore rules
│
├── 📦 Core Modules (servicenow/)
│   ├── __init__.py            # Package initialization
│   ├── client.py              # ServiceNow REST API client
│   ├── knowledge_base.py      # Knowledge base operations
│   └── parser.py              # HTML parsing utilities
│
├── 💡 Examples (examples/)
│   ├── main.py                # Basic usage demonstration
│   └── visualize_hierarchy.py # Category hierarchy visualization
│
├── 🧪 Tests (tests/)
│   ├── test_list_articles.py      # Test article listing
│   ├── test_categories.py         # Test category retrieval
│   ├── test_category_hierarchy.py # Test hierarchy traversal
│   └── test_optimization.py       # Performance optimization demo
│
├── 📚 Documentation (docs/)
│   ├── OPTIMIZATION_OPTIONS.md            # Compare optimization strategies
│   ├── API_OPTIMIZATION_SUMMARY.md        # Quick optimization guide
│   ├── OPTIMIZATION_VISUAL.txt            # Visual diagrams
│   ├── CATEGORY_HIERARCHY_EXPLANATION.md  # Algorithm details
│   └── ALGORITHM_SUMMARY.txt              # Quick algorithm reference
│
├── 📥 Data (downloads/)
│   └── {article_sys_id}/      # Downloaded attachments organized by article
│
└── 🛠️ Utilities
    └── show_structure.sh      # Display project structure
```

## File Descriptions

### Root Level Files

#### README.md
The main project documentation with:
- Quick start guide
- Usage examples
- API reference
- Performance metrics

#### requirements.txt
Python package dependencies:
- `requests` - HTTP client for ServiceNow API
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML parser
- `python-dotenv` - Environment variable management

#### config.py
Centralized configuration:
- ServiceNow connection settings
- API timeouts and retry limits
- Download directories
- Environment variable loading

#### env.example
Template for environment variables:
- `SERVICENOW_INSTANCE` - ServiceNow instance URL
- `SERVICENOW_USERNAME` - Authentication username
- `SERVICENOW_PASSWORD` - Authentication password
- Optional: API timeouts, download settings

### Core Modules (`servicenow/`)

#### client.py
Low-level ServiceNow REST API client:
- `ServiceNowClient` class
- HTTP authentication
- Generic table queries
- Record retrieval
- Attachment downloads
- Error handling

**Key Methods:**
```python
ServiceNowClient(instance, username, password, timeout)
.query_table(table, query, fields, limit, offset)
.get_record(table, sys_id, fields)
.get_attachment(sys_id)
```

#### knowledge_base.py
High-level knowledge base operations:
- `KnowledgeBase` class
- Article listing and retrieval
- Category hierarchy traversal
- Attachment management
- Performance optimization (caching, pre-fetching)

**Key Methods:**
```python
KnowledgeBase(client, download_dir, enable_cache)
.list_articles(query, fields, limit, offset)
.get_article(sys_id, fields)
.get_category_hierarchy(category_sys_id)
.get_article_with_category_path(sys_id)
.get_article_attachments(article_sys_id, download)
.prefetch_all_categories()  # Performance boost!
```

#### parser.py
HTML content parsing:
- `HTMLParser` class
- Extract text, images, links, tables
- Parse lists and code blocks
- Convert HTML to Markdown

**Key Methods:**
```python
HTMLParser()
.parse_html(html_content)
.extract_text(soup)
.extract_images(soup)
.html_to_markdown(html_content)
```

### Examples (`examples/`)

#### main.py
Comprehensive usage example demonstrating:
- Client initialization
- Article listing
- Full article retrieval
- HTML parsing
- Attachment downloads

**Run it:**
```bash
python examples/main.py
```

#### visualize_hierarchy.py
Interactive demonstration of category hierarchy algorithm:
- Step-by-step traversal
- Visual tree representation
- Explains the `insert(0, ...)` pattern

**Run it:**
```bash
python examples/visualize_hierarchy.py
```

### Tests (`tests/`)

#### test_list_articles.py
Tests article listing functionality:
- Fetches 10 articles
- Displays article metadata
- Shows HTML content preview

#### test_categories.py
Tests category retrieval:
- Fetches articles with categories
- Shows category references
- Displays category labels

#### test_category_hierarchy.py
Tests hierarchy traversal:
- Builds complete category paths
- Shows parent-child relationships
- Demonstrates the `get_article_with_category_path()` method

#### test_optimization.py
Performance comparison demo:
- Tests pre-fetching
- Measures API call reduction
- Shows cache statistics

**Run it to see 99% API call reduction:**
```bash
python tests/test_optimization.py
```

### Documentation (`docs/`)

#### OPTIMIZATION_OPTIONS.md
Comprehensive guide to 6 optimization strategies:
1. Current iterative approach (baseline)
2. Batch API calls
3. Custom ServiceNow API
4. Local caching (implemented)
5. Parallel API calls
6. Pre-fetch category tree (implemented)

**Read this to understand all options.**

#### API_OPTIMIZATION_SUMMARY.md
Quick reference guide with:
- Code examples
- Performance comparison table
- Real-world metrics
- Recommended approach

**Read this for quick implementation guide.**

#### OPTIMIZATION_VISUAL.txt
Visual diagrams showing:
- API call flow for each approach
- Cache hit/miss patterns
- Performance comparison charts

**Read this for visual understanding.**

#### CATEGORY_HIERARCHY_EXPLANATION.md
Deep dive into the algorithm:
- Step-by-step trace
- Data structure details
- Design decisions explained
- Performance analysis

**Read this to understand how it works.**

#### ALGORITHM_SUMMARY.txt
Quick reference card:
- Algorithm type and complexity
- Step-by-step process
- Data structure diagrams
- Key insights

**Read this for quick lookup.**

## Usage Patterns

### Pattern 1: Quick Test
```bash
# List some articles
python tests/test_list_articles.py
```

### Pattern 2: Development
```bash
# Work in root directory
cd /app/test_agentic

# Import modules
python
>>> from servicenow.client import ServiceNowClient
>>> from servicenow.knowledge_base import KnowledgeBase
```

### Pattern 3: Production Migration
```python
# In your migration script
import sys
from pathlib import Path
sys.path.insert(0, '/app/test_agentic')

from servicenow.client import ServiceNowClient
from servicenow.knowledge_base import KnowledgeBase
from config import Config

# Use optimized approach
with ServiceNowClient(...) as client:
    kb = KnowledgeBase(client)
    kb.prefetch_all_categories()  # One-time optimization
    
    # Process thousands of articles efficiently
    for article in kb.get_all_articles_paginated():
        migrate_to_notion(article)
```

## Import Paths

All test and example scripts include this boilerplate:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

This allows them to import modules from the root:
```python
from servicenow.client import ServiceNowClient
from servicenow.knowledge_base import KnowledgeBase
from config import Config
```

## Adding New Features

### Adding a New Core Feature
1. Add code to `servicenow/` module files
2. Update `servicenow/__init__.py` exports if needed
3. Add example to `examples/`
4. Add test to `tests/`
5. Document in `docs/` if complex
6. Update `README.md`

### Adding a New Test
1. Create `tests/test_feature.py`
2. Add path boilerplate at top
3. Import modules: `from servicenow import ...`
4. Write test logic
5. Run: `python tests/test_feature.py`

### Adding Documentation
1. Create `docs/FEATURE_NAME.md`
2. Use clear headings and examples
3. Add diagrams if helpful
4. Link from `README.md`

## Best Practices

### Code Organization
- ✅ Keep core logic in `servicenow/` modules
- ✅ Keep examples simple and focused
- ✅ Keep tests independent
- ✅ Document complex algorithms

### Imports
- ✅ Use absolute imports: `from servicenow.client import ...`
- ✅ Add path fix in scripts: `sys.path.insert(0, ...)`
- ✅ Import from `config` for settings

### Testing
- ✅ Run tests from project root: `python tests/test_*.py`
- ✅ Or from test directory with path fix
- ✅ Each test should be runnable independently

### Documentation
- ✅ README.md - Overall project guide
- ✅ docs/*.md - Detailed explanations
- ✅ Code comments - Implementation details
- ✅ Docstrings - API documentation

## Common Commands

```bash
# Show project structure
./show_structure.sh

# Run examples
python examples/main.py
python examples/visualize_hierarchy.py

# Run all tests
for test in tests/test_*.py; do python "$test"; done

# Check specific functionality
python tests/test_optimization.py

# Start development
cd /app/test_agentic
python
>>> from servicenow import ServiceNowClient, KnowledgeBase
```

## Migration from Old Structure

The project was reorganized from:
```
test_agentic/
├── *.py (all mixed together)
├── *.md (all mixed together)
└── servicenow/
```

To the current organized structure. All functionality remains the same, just better organized.

## Summary

| Directory | Purpose | File Count |
|-----------|---------|------------|
| Root | Config & setup | 5 files |
| `servicenow/` | Core modules | 3 modules |
| `examples/` | Usage examples | 2 scripts |
| `tests/` | Test scripts | 4 tests |
| `docs/` | Documentation | 5 documents |
| `downloads/` | Attachments | (dynamic) |

**Total:** Well-organized project with clear separation of concerns!

