# Organizing Notion pages after import.

## Prerequisite
- List of articles in Service Now Knowledge Portal is exported
- HTMLs and Google Documents of Knowledge Portal are exported and imported to Notion via Zip importer

## Organizing plan process
1. Based on list of articles, first create category hieararchy in a Notion database.
  - Exmaple list is `/app/test_agentic/migration_output/article_list_20251119_065308.csv`
  - In the CSV, category hierarchy data is stored in `category_path` column
  - Deduplicate category_path and get unique category hierarchy
  - In category_path column, 'A > B' means A is a parent category and B is a child category.
  - Analyze these category and create blank pages in Notion whose title name is the same as the category name
    - In the example above, we should create page A and page B
    - Created page names and page_ids will be outputed in CSV after creation
  - There may be pages that have the same category name, but under another parent category. These should be treated as different category 
  - Then, based on category hierarchy data, make item-subitem relation between pages that corresponding original category hierarchy
    - In the example above, page B should be sub-item of page A
  - Target databse id will be provided as an argument
2. After creating categories, move Notion pages under corresponding categories
  - List of page_ids of Notion pages and category hierarchy is given through CSV file
  - Use `make-subitem` method to populate under its category

## Performance concern
- Use threading to concurrently execute Notion API
- There are rate limit threshold in Notion side. When using threading, always make max_workers argument so that we can set the number of max_workers at runtime

### memos
- 11/20
  - process time of category_organizer.py is much slower than expected. Need to improve logic
     - Searching parent item property everytime? Since target database is explicitly specified and we can assume its structure will not change during the execution, we don't have to search everytime.
     - Searching pages under databse takes time as number pages increase. Page id can be cached right after page creation, use it later as reference