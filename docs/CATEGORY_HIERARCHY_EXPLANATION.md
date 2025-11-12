# How Category Hierarchy Retrieval Works

## Overview

The category hierarchy system uses a **bottom-up traversal** approach to build the complete path from a child category to its root parent. This is a classic tree traversal algorithm.

## The Algorithm

### 1. Starting Point: Article with Category Reference

When you fetch an article, it contains a `kb_category` field with a reference to a category:

```json
{
  "sys_id": "001f43ddc3803650374e3441150131e8",
  "number": "KB0013936",
  "short_description": "ITツール利用申請マニュアル",
  "kb_category": {
    "link": "https://...",
    "value": "56810cacdbb3a910f4e15722f3961903"  // Category sys_id
  }
}
```

### 2. Category Structure in ServiceNow

Each category in the `kb_category` table has this structure:

```json
{
  "sys_id": "56810cacdbb3a910f4e15722f3961903",
  "label": "規定（ルール、ガイドライン）",
  "parent_id": {
    "link": "https://...",
    "value": "30fe4f671bd3f410de1233b5cc4bcb9c"  // Parent category sys_id
  }
}
```

### 3. The `get_category_hierarchy()` Method

This method walks **up the tree** from child to root:

```python
def get_category_hierarchy(self, category_sys_id: str) -> List[Dict[str, Any]]:
    hierarchy = []
    current_sys_id = category_sys_id
    max_depth = 10  # Safety limit
    depth = 0
    
    while current_sys_id and depth < max_depth:
        try:
            # Step 1: Fetch current category
            category = self.get_category(current_sys_id)
            
            # Step 2: Insert at beginning (to maintain root → child order)
            hierarchy.insert(0, category)
            
            # Step 3: Check if there's a parent
            parent_id = category.get('parent_id', {})
            if isinstance(parent_id, dict) and parent_id.get('value'):
                current_sys_id = parent_id['value']  # Move up to parent
            else:
                break  # No parent, we reached the root
                
        except Exception as e:
            # Parent not found (reached knowledge base level)
            break
        
        depth += 1
    
    return hierarchy
```

## Step-by-Step Example

Let's trace through a real example from your data:

**Article KB0011256**: "Organising an Event Visitor Entry Procedure"

### Iteration 1 (Starting category)
```
Input: category_sys_id = "4538b6861b9ff010de1233b5cc4bcb65"

1. Fetch category from API:
   {
     "sys_id": "4538b6861b9ff010de1233b5cc4bcb65",
     "label": "イベント",
     "parent_id": {"value": "a9614ac61b1ff010de1233b5cc4bcba3"}
   }

2. Insert at position 0:
   hierarchy = [
     {"label": "イベント", ...}
   ]

3. Move to parent:
   current_sys_id = "a9614ac61b1ff010de1233b5cc4bcba3"
```

### Iteration 2 (First parent)
```
Input: current_sys_id = "a9614ac61b1ff010de1233b5cc4bcba3"

1. Fetch category from API:
   {
     "sys_id": "a9614ac61b1ff010de1233b5cc4bcba3",
     "label": "東京オフィス",
     "parent_id": {"value": "7251c6c61b1ff010de1233b5cc4bcbce"}
   }

2. Insert at position 0 (pushes previous to position 1):
   hierarchy = [
     {"label": "東京オフィス", ...},
     {"label": "イベント", ...}
   ]

3. Move to parent:
   current_sys_id = "7251c6c61b1ff010de1233b5cc4bcbce"
```

### Iteration 3 (Second parent / Root)
```
Input: current_sys_id = "7251c6c61b1ff010de1233b5cc4bcbce"

1. Fetch category from API:
   {
     "sys_id": "7251c6c61b1ff010de1233b5cc4bcbce",
     "label": "オフィス",
     "parent_id": {"value": "dfc19531bf2021003f07e2c1ac0739ab"}
   }

2. Insert at position 0:
   hierarchy = [
     {"label": "オフィス", ...},
     {"label": "東京オフィス", ...},
     {"label": "イベント", ...}
   ]

3. Move to parent:
   current_sys_id = "dfc19531bf2021003f07e2c1ac0739ab"
```

### Iteration 4 (Knowledge Base - Not a Category)
```
Input: current_sys_id = "dfc19531bf2021003f07e2c1ac0739ab"

1. Try to fetch category from API:
   → 404 Error! This is a kb_knowledge_base ID, not a category

2. Exception caught → break loop

3. Final hierarchy:
   hierarchy = [
     {"label": "オフィス", ...},
     {"label": "東京オフィス", ...},
     {"label": "イベント", ...}
   ]
```

### Final Result
```
Path: オフィス > 東京オフィス > イベント
```

## Key Design Decisions

### 1. **Why `insert(0, category)` instead of `append()`?**

We want the final list ordered from **root → child**, but we traverse from **child → root**.

```python
# If we used append():
hierarchy = ["イベント", "東京オフィス", "オフィス"]  # Wrong order!

# Using insert(0, ...):
hierarchy = ["オフィス", "東京オフィス", "イベント"]  # Correct order!
```

### 2. **Why the `max_depth` limit?**

Prevents infinite loops in case of:
- Circular references (Category A → B → A)
- Data corruption
- Implementation bugs

### 3. **Why catch exceptions in the loop?**

ServiceNow categories can reference:
- Other categories (normal case)
- Knowledge bases (top of hierarchy - not in kb_category table)
- Invalid/deleted categories

Instead of crashing, we gracefully stop when we can't go higher.

## Data Flow Diagram

```
Article
  ↓ (has kb_category reference)
  ↓
Category: "イベント" (sys_id: 4538b686...)
  ↓ (has parent_id reference)
  ↓
Category: "東京オフィス" (sys_id: a9614ac6...)
  ↓ (has parent_id reference)
  ↓
Category: "オフィス" (sys_id: 7251c6c6...)
  ↓ (has parent_id reference)
  ↓
Knowledge Base (sys_id: dfc19531...)
  ↓ (404 - not a category)
  ↓
[STOP - reached top]
```

## API Calls Made

For the example above, the system makes these API calls:

1. `GET /api/now/table/kb_knowledge/001f43dd...` 
   → Get article (includes category reference)

2. `GET /api/now/table/kb_category/4538b686...`
   → Get "イベント" category

3. `GET /api/now/table/kb_category/a9614ac6...`
   → Get "東京オフィス" category

4. `GET /api/now/table/kb_category/7251c6c6...`
   → Get "オフィス" category

5. `GET /api/now/table/kb_category/dfc19531...`
   → Try to get parent (404 error - it's a knowledge base)

**Total: 5 API calls** for an article with 3-level category hierarchy

## Performance Considerations

### Optimization: Caching
For better performance when processing many articles, you could cache category lookups:

```python
self._category_cache = {}

def get_category(self, category_sys_id: str):
    if category_sys_id in self._category_cache:
        return self._category_cache[category_sys_id]
    
    category = self.client.get_record(...)
    self._category_cache[category_sys_id] = category
    return category
```

This reduces API calls when multiple articles share the same parent categories.

## Summary

The category hierarchy retrieval:
1. **Starts** with a category sys_id from an article
2. **Fetches** the category details from ServiceNow API
3. **Traverses up** the tree using the `parent_id` reference
4. **Builds** the hierarchy list in reverse order (using `insert(0, ...)`)
5. **Stops** when reaching the root (no parent) or knowledge base level
6. **Returns** a list ordered from root to leaf

This is a classic **linked list traversal** pattern, where each node (category) points to its parent, and we follow the chain until we reach the end.

