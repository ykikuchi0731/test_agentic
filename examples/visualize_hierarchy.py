"""Visual demonstration of how category hierarchy traversal works."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def demonstrate_hierarchy_algorithm():
    """
    Step-by-step demonstration of the category hierarchy algorithm.
    """
    print("="*80)
    print("CATEGORY HIERARCHY ALGORITHM - STEP BY STEP DEMONSTRATION")
    print("="*80)
    print()
    
    # Simulated category data from ServiceNow
    categories_db = {
        "4538b686": {
            "sys_id": "4538b686",
            "label": "イベント",
            "parent_id": "a9614ac6"
        },
        "a9614ac6": {
            "sys_id": "a9614ac6",
            "label": "東京オフィス",
            "parent_id": "7251c6c6"
        },
        "7251c6c6": {
            "sys_id": "7251c6c6",
            "label": "オフィス",
            "parent_id": "dfc19531"  # This is a knowledge base, not a category
        }
    }
    
    print("Starting with article KB0011256: 'Organising an Event Visitor Entry Procedure'")
    print("Article's kb_category reference: 4538b686")
    print()
    
    # Algorithm implementation
    hierarchy = []
    current_sys_id = "4538b686"
    depth = 0
    max_depth = 10
    
    print("Beginning traversal UP the category tree...")
    print()
    
    while current_sys_id and depth < max_depth:
        print(f"--- ITERATION {depth + 1} ---")
        print(f"Current sys_id: {current_sys_id}")
        print()
        
        # Try to fetch category
        if current_sys_id in categories_db:
            category = categories_db[current_sys_id]
            print(f"✓ Found category: '{category['label']}'")
            print(f"  - sys_id: {category['sys_id']}")
            print(f"  - parent_id: {category.get('parent_id', 'None')}")
            print()
            
            # Insert at beginning
            hierarchy.insert(0, category)
            print(f"Action: Insert '{category['label']}' at position 0")
            print(f"Current hierarchy (root → current):")
            for i, cat in enumerate(hierarchy):
                print(f"  [{i}] {cat['label']}")
            print()
            
            # Check for parent
            if category.get('parent_id'):
                current_sys_id = category['parent_id']
                print(f"Next: Move to parent with sys_id: {current_sys_id}")
            else:
                print("No parent found. Reached root!")
                break
        else:
            print(f"✗ Category not found (sys_id: {current_sys_id})")
            print("  This is likely a knowledge base reference, not a category.")
            print("  Stopping traversal here.")
            break
        
        print()
        depth += 1
    
    print("="*80)
    print("TRAVERSAL COMPLETE")
    print("="*80)
    print()
    print(f"Total iterations: {depth + 1}")
    print(f"Hierarchy depth: {len(hierarchy)} levels")
    print()
    print("Final Category Path:")
    path = " > ".join([cat['label'] for cat in hierarchy])
    print(f"  {path}")
    print()
    
    print("Visual representation:")
    print()
    for i, cat in enumerate(hierarchy):
        indent = "  " * i
        if i == 0:
            print(f"{indent}🏠 {cat['label']} (root)")
        elif i == len(hierarchy) - 1:
            print(f"{indent}└─ 📄 {cat['label']} (current)")
        else:
            print(f"{indent}└─ 📁 {cat['label']}")
    
    print()
    print("="*80)
    
    # Show why we use insert(0) instead of append
    print()
    print("WHY USE insert(0, category) INSTEAD OF append(category)?")
    print("="*80)
    print()
    
    print("If we used append():")
    append_order = ["イベント", "東京オフィス", "オフィス"]
    print(f"  Result: {' > '.join(append_order)}")
    print("  ❌ Wrong! This is BACKWARDS (child to root)")
    print()
    
    print("Using insert(0, category):")
    correct_order = ["オフィス", "東京オフィス", "イベント"]
    print(f"  Result: {' > '.join(correct_order)}")
    print("  ✓ Correct! This is root to child")
    print()
    
    print("="*80)
    
    # Show the actual code structure
    print()
    print("SIMPLIFIED CODE STRUCTURE")
    print("="*80)
    print()
    print("""
def get_category_hierarchy(category_sys_id):
    hierarchy = []              # Empty list to store path
    current = category_sys_id   # Start with child category
    
    while current:
        # 1. Fetch category from ServiceNow API
        category = api.get_category(current)
        
        # 2. Add to FRONT of list (maintains root→child order)
        hierarchy.insert(0, category)
        
        # 3. Move UP to parent
        current = category.parent_id
        
        # 4. Stop if no parent (reached root)
        if not current:
            break
    
    return hierarchy  # Returns [root, ..., child]
    """)
    
    print("="*80)


if __name__ == '__main__':
    demonstrate_hierarchy_algorithm()

