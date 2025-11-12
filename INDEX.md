# Project Index

Quick reference to find what you need in the ServiceNow to Notion migration tool.

## 🚀 Getting Started

| File | Purpose | When to Read |
|------|---------|--------------|
| [QUICK_START.md](QUICK_START.md) | 5-minute setup guide | **Start here!** |
| [README.md](README.md) | Complete documentation | After quick start |
| [PROJECT_ORGANIZATION.md](PROJECT_ORGANIZATION.md) | Structure explanation | Understanding layout |

## 📦 Core Code

| File | What It Does | Key Classes/Functions |
|------|--------------|----------------------|
| [servicenow/client.py](servicenow/client.py) | ServiceNow API client | `ServiceNowClient` |
| [servicenow/knowledge_base.py](servicenow/knowledge_base.py) | Article operations | `KnowledgeBase` |
| [servicenow/parser.py](servicenow/parser.py) | HTML parsing | `HTMLParser` |
| [config.py](config.py) | Configuration | `Config` class |

## 💡 Examples

| File | Demonstrates | Run Command |
|------|--------------|-------------|
| [examples/main.py](examples/main.py) | Basic usage | `python examples/main.py` |
| [examples/visualize_hierarchy.py](examples/visualize_hierarchy.py) | Category algorithm | `python examples/visualize_hierarchy.py` |

## 🧪 Tests

| File | Tests What | Run Command |
|------|-----------|-------------|
| [tests/test_list_articles.py](tests/test_list_articles.py) | Article listing | `python tests/test_list_articles.py` |
| [tests/test_categories.py](tests/test_categories.py) | Category retrieval | `python tests/test_categories.py` |
| [tests/test_category_hierarchy.py](tests/test_category_hierarchy.py) | Hierarchy traversal | `python tests/test_category_hierarchy.py` |
| [tests/test_optimization.py](tests/test_optimization.py) | Performance demo | `python tests/test_optimization.py` |

## 📚 Documentation

### Performance & Optimization
| File | Topic | Read When |
|------|-------|-----------|
| [docs/API_OPTIMIZATION_SUMMARY.md](docs/API_OPTIMIZATION_SUMMARY.md) | Quick optimization guide | **Recommended** |
| [docs/OPTIMIZATION_OPTIONS.md](docs/OPTIMIZATION_OPTIONS.md) | All 6 strategies compared | Deep dive |
| [docs/OPTIMIZATION_VISUAL.txt](docs/OPTIMIZATION_VISUAL.txt) | Visual diagrams | Visual learner |

### Algorithm Details
| File | Topic | Read When |
|------|-------|-----------|
| [docs/CATEGORY_HIERARCHY_EXPLANATION.md](docs/CATEGORY_HIERARCHY_EXPLANATION.md) | How it works | Understanding algorithm |
| [docs/ALGORITHM_SUMMARY.txt](docs/ALGORITHM_SUMMARY.txt) | Quick reference | Quick lookup |

### Project Info
| File | Topic | Read When |
|------|-------|-----------|
| [REORGANIZATION_SUMMARY.txt](REORGANIZATION_SUMMARY.txt) | Before/after organization | Curious about changes |
| [show_structure.sh](show_structure.sh) | Display structure | Exploring project |

## 🔍 Find By Task

### I want to...

#### List articles
```python
# See: examples/main.py or tests/test_list_articles.py
articles = kb.list_articles(limit=10)
```

#### Get article with category
```python
# See: tests/test_category_hierarchy.py
article = kb.get_article_with_category_path('sys_id')
```

#### Download attachments
```python
# See: examples/main.py
attachments = kb.get_article_attachments('sys_id', download=True)
```

#### Parse HTML
```python
# See: examples/main.py
parsed = kb.parse_article_html(html_content)
```

#### Optimize performance
```python
# See: tests/test_optimization.py
kb.prefetch_all_categories()  # 99% API call reduction!
```

#### Understand category hierarchy
- Read: [docs/CATEGORY_HIERARCHY_EXPLANATION.md](docs/CATEGORY_HIERARCHY_EXPLANATION.md)
- Run: `python examples/visualize_hierarchy.py`

#### Migrate to Notion
- Start: [QUICK_START.md](QUICK_START.md) section 5
- Reference: [examples/main.py](examples/main.py)

## 📖 Documentation Map

```
Root Level (Start Here)
├── QUICK_START.md          ← Begin here (5 min)
├── README.md               ← Complete guide
├── INDEX.md                ← You are here
└── PROJECT_ORGANIZATION.md ← Structure details

Deep Dives
└── docs/
    ├── API_OPTIMIZATION_SUMMARY.md     ← Performance (recommended)
    ├── CATEGORY_HIERARCHY_EXPLANATION.md ← How algorithm works
    ├── OPTIMIZATION_OPTIONS.md          ← All strategies
    ├── OPTIMIZATION_VISUAL.txt          ← Visual diagrams
    └── ALGORITHM_SUMMARY.txt            ← Quick reference
```

## 🎯 Common Workflows

### 1. First Time Setup
```
1. Read: QUICK_START.md
2. Run: pip install -r requirements.txt
3. Edit: .env (from env.example)
4. Test: python tests/test_list_articles.py
```

### 2. Learning the System
```
1. Read: README.md
2. Run: python examples/main.py
3. Run: python tests/test_optimization.py
4. Read: docs/API_OPTIMIZATION_SUMMARY.md
```

### 3. Building Your Migration
```
1. Copy: examples/main.py
2. Add: kb.prefetch_all_categories()
3. Process: kb.get_all_articles_paginated()
4. Transform: Your Notion logic
```

### 4. Debugging Issues
```
1. Check: config.py settings
2. Verify: .env credentials
3. Test: python tests/test_list_articles.py
4. Review: servicenow/knowledge_base.py code
```

## 🛠️ Utility Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| show_structure.sh | Display project tree | `./show_structure.sh` |
| env.example | Credentials template | `cp env.example .env` |

## 📊 Key Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Categories in system | 593 | Your ServiceNow |
| Pre-fetch time | 2.34s | One-time cost |
| API calls saved | 99% | With pre-fetching |
| Processing speed | 0.16s/article | After pre-fetch |

## 🎓 Learning Path

### Beginner
1. ✅ [QUICK_START.md](QUICK_START.md)
2. ✅ `python examples/main.py`
3. ✅ [README.md](README.md) - Usage Examples section

### Intermediate
1. ✅ [docs/API_OPTIMIZATION_SUMMARY.md](docs/API_OPTIMIZATION_SUMMARY.md)
2. ✅ `python tests/test_optimization.py`
3. ✅ Build your migration script

### Advanced
1. ✅ [docs/CATEGORY_HIERARCHY_EXPLANATION.md](docs/CATEGORY_HIERARCHY_EXPLANATION.md)
2. ✅ Study `servicenow/knowledge_base.py` code
3. ✅ [docs/OPTIMIZATION_OPTIONS.md](docs/OPTIMIZATION_OPTIONS.md)

## 🔗 Quick Links

| Need | Go To |
|------|-------|
| Setup in 5 min | [QUICK_START.md](QUICK_START.md) |
| API reference | [README.md](README.md) - API Reference section |
| Performance boost | [docs/API_OPTIMIZATION_SUMMARY.md](docs/API_OPTIMIZATION_SUMMARY.md) |
| Code examples | [examples/](examples/) directory |
| Test scripts | [tests/](tests/) directory |
| Algorithm details | [docs/CATEGORY_HIERARCHY_EXPLANATION.md](docs/CATEGORY_HIERARCHY_EXPLANATION.md) |

## 📝 File Counts

- **Root files**: 10
- **Core modules**: 3 (in `servicenow/`)
- **Examples**: 2 (in `examples/`)
- **Tests**: 4 (in `tests/`)
- **Documentation**: 5 (in `docs/`)

**Total**: 24 files, all organized!

---

**Need help?** Start with [QUICK_START.md](QUICK_START.md) and [README.md](README.md)!

