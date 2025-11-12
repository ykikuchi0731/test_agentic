# Optimizing Category Hierarchy API Calls

## Current Approach: Iterative (Multiple API Calls)

**Problem:** For a 3-level hierarchy, we make 3-4 API calls:
```
Call 1: GET /kb_category/child_id
Call 2: GET /kb_category/parent_id  
Call 3: GET /kb_category/grandparent_id
Call 4: GET /kb_category/root_id (404 - knowledge base)
```

## Optimization Options

### Option 1: Query with `sysparm_display_value=all` (Best for Single Record)

ServiceNow can return display values and full referenced object details in one call.

**Example:**
```python
# Instead of just getting the sys_id reference
GET /api/now/table/kb_knowledge/article_id?sysparm_fields=kb_category

# Response:
{
  "kb_category": {
    "value": "abc123",
    "link": "..."
  }
}

# Use sysparm_display_value=all to get full category details
GET /api/now/table/kb_knowledge/article_id?sysparm_fields=kb_category&sysparm_display_value=all

# Response includes category label:
{
  "kb_category": {
    "value": "abc123",
    "display_value": "IT",
    "link": "..."
  }
}
```

**Limitation:** This only gives you the immediate category, not the full hierarchy.

---

### Option 2: Batch API Calls (Reduce Total Time)

ServiceNow REST API doesn't have built-in batching, but you can:
1. Collect all category sys_ids from multiple articles
2. Query all at once with OR conditions

**Example:**
```python
# Instead of:
# GET /kb_category/id1
# GET /kb_category/id2  
# GET /kb_category/id3

# Do:
GET /kb_category?sysparm_query=sys_idINid1,id2,id3&sysparm_fields=sys_id,label,parent_id
```

**Benefits:**
- Fewer HTTP connections
- Reduced latency
- Better for bulk operations

---

### Option 3: Custom ServiceNow Scripted REST API (Best Solution!)

Create a custom REST endpoint in ServiceNow that returns the full hierarchy in ONE call.

**ServiceNow Script:**
```javascript
// Custom Scripted REST API in ServiceNow
(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {
    var categoryId = request.pathParams.category_id;
    var hierarchy = [];
    var current = categoryId;
    var depth = 0;
    var maxDepth = 10;
    
    // Build hierarchy in ServiceNow (server-side)
    while (current && depth < maxDepth) {
        var gr = new GlideRecord('kb_category');
        if (gr.get(current)) {
            hierarchy.unshift({
                sys_id: gr.sys_id.toString(),
                label: gr.label.toString(),
                parent_id: gr.parent_id.toString()
            });
            current = gr.parent_id.toString();
        } else {
            break;
        }
        depth++;
    }
    
    return hierarchy;
})(request, response);
```

**Client Call:**
```python
# Single API call returns complete hierarchy
GET /api/x_custom/category_hierarchy/{category_id}

# Response:
[
  {"sys_id": "root_id", "label": "IT", "parent_id": ""},
  {"sys_id": "child_id", "label": "Applications", "parent_id": "root_id"},
  {"sys_id": "leaf_id", "label": "Figma", "parent_id": "child_id"}
]
```

**Benefits:**
- ✅ 1 API call instead of N calls
- ✅ Faster (server-side traversal)
- ✅ Less bandwidth
- ✅ Reduced client complexity

**Drawbacks:**
- Requires ServiceNow admin access to create custom API
- Not available in all ServiceNow instances

---

### Option 4: Local Caching (Best for Multiple Articles)

Cache categories in memory when processing multiple articles.

**Impact:**
```
Without cache:
- Article 1 (IT > Apps > Figma): 3 calls
- Article 2 (IT > Apps > Slack): 3 calls  
- Article 3 (IT > Hardware > Laptops): 3 calls
Total: 9 calls

With cache:
- Article 1: 3 calls (cache IT, Apps, Figma)
- Article 2: 1 call (IT and Apps cached, fetch Slack)
- Article 3: 2 calls (IT cached, fetch Hardware, Laptops)
Total: 6 calls (33% reduction)
```

---

### Option 5: Parallel API Calls

If you know all category IDs in advance, fetch them in parallel.

**Example:**
```python
import concurrent.futures

def fetch_category(cat_id):
    return client.get_record('kb_category', cat_id)

category_ids = ['id1', 'id2', 'id3']

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    categories = list(executor.map(fetch_category, category_ids))
```

**Benefits:**
- Same number of calls, but executed simultaneously
- Total time = slowest call (not sum of all calls)

---

### Option 6: Pre-fetch and Store Category Tree

Download the entire category tree once and store locally.

**One-time Setup:**
```python
# Fetch ALL categories (one time)
all_categories = client.query_table(
    'kb_category',
    fields=['sys_id', 'label', 'parent_id']
)

# Build local lookup dictionary
category_map = {cat['sys_id']: cat for cat in all_categories}

# Store to file
import json
with open('categories_cache.json', 'w') as f:
    json.dump(category_map, f)
```

**Runtime Usage:**
```python
# Load cached categories
with open('categories_cache.json', 'r') as f:
    category_map = json.load(f)

# Traverse locally (NO API CALLS!)
def get_hierarchy_local(category_id):
    hierarchy = []
    current = category_id
    
    while current and current in category_map:
        cat = category_map[current]
        hierarchy.insert(0, cat)
        current = cat.get('parent_id')
    
    return hierarchy
```

**Benefits:**
- ✅ ZERO API calls during migration
- ✅ Extremely fast
- ✅ Works offline

**Drawbacks:**
- Stale data if categories change
- Need to refresh cache periodically

---

## Comparison Table

| Method | API Calls per Article | Latency | Setup Complexity | Best For |
|--------|----------------------|---------|------------------|----------|
| Current (Iterative) | N (hierarchy depth) | High | None | Quick start |
| Batch Queries | N/M (M articles) | Medium | Low | Multiple articles |
| Custom API | 1 | Low | High | Production |
| Local Cache | 0-N (cache hits) | Low-Medium | Low | Bulk migration |
| Parallel Calls | N (concurrent) | Medium | Medium | Real-time |
| Pre-fetch Tree | 0 (after setup) | Very Low | Medium | Large migrations |

---

## Recommended Approach

For your ServiceNow → Notion migration, I recommend:

### **Immediate: Local Caching (Option 4)**
- Easy to implement now
- Significant improvement for multiple articles
- No ServiceNow admin required

### **Best: Pre-fetch Category Tree (Option 6)**
- Perfect for one-time migration
- Zero API calls during processing
- Very fast

### **Long-term: Custom API (Option 3)**
- If you have ServiceNow admin access
- Best for ongoing integrations
- Reusable for other projects

---

## Implementation Recommendations

1. **For small migrations (<100 articles):** Current approach is fine
2. **For medium migrations (100-1000 articles):** Add caching
3. **For large migrations (>1000 articles):** Pre-fetch entire category tree
4. **For ongoing sync:** Request custom ServiceNow API endpoint

