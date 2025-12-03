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

2. After manually importing zip, get `page_id`s of imported pages.
  - This process is done in `get_imported_page_ids.py` module.
  - It takes `parent_page_ids` as an argument. The value should be string and may contain one parent_page_id such as `1q2w3e4r` or multiple parent_pagers_ids with comma separated such as `1q2w3e4r,5t6y7u8i`
  - Get chilren page of given `parent_page_id` and get pages whose name starts with 'KB'.
    - Ignore pages whose name doesn't start with 'KB'
    - There may be many pages, so make sure to use pagination to get all pages.
  - If multiple `parent_page_ids` are given, iterate this process per `parent_page_id`
  - Output file is in CSV format, having `page_id`, `page_title` columns
  - Output file name is `imported_page_ids_YYYYMMDD_hhmm.csv`, `YYYYMMDD_hhmm` is the date and time of execution

3. Move imported pages to target datanbase
  - This process is done in `move_pages_to_database.py` module.
  - It takes two arguments: `target_database_id` and `pages_csv`
    - `target_database_id` is string
    - `page_csv` is string and filepath pointing to list of `page_id`s to be moved under the database
      - make sure the CSV containing a column `page_id`
  - Documentation of Notion's page move API is not publicly avaiable in this time. Please refer `docs/SPEC_PAGE_MOVE_API.md` for implementation details.
    - Runtime argument `target_database_id` is `database_id` in the document above. Therefore we have to get `database_source_id` to make page moves 
  - All page move operations should be logged in a log file to check whether operations are executed
    - If there are error open move operation, write down error messages as well for later trouble shoot

4. After creating categories, move Notion pages under corresponding categories in target database
  - This process is done in `categorize_pages.py` module.
  - It takes 3 argements: `database_id`, `page_list_csv` and `category_list_csv`.
    - Shorthand name for these arguments are `db`, `pl` and `cl` respectively
  - Argument `database_id` is string, id of target Notion database
  - Argument `page_list_csv` is string, path to CSV file
    - The CSV file must have `page_id` and `category_path` columns.
  - Argument `category_list_csv` is string, path to another CSV file
    - This CSV file must have `full_path` and `page_id` columns.
  - The `categorize_pages.py` module will work as following:
    - Iterate lines in `page_list_csv` and get `page_id` and `category_path` values
    - Search `category_path` in column `full_path` of `category_list_csv` and get corresponding `page_id` in `category_list_csv`
      - To avoid confusing 2 `page_id`s, `page_id` from `category_list_csv` should be called `category_page_id`
    - Make `page_id` from `page_list_csv` sub-item of `category_page_id`
      - Use `make-subitem` method to populate under its category
  - Execution log will be outputed under `logs` directory

## Performance concern
- Use threading to concurrently execute Notion API
- There are rate limit threshold in Notion side. When using threading, always make max_workers argument so that we can set the number of max_workers at runtime

### memos
- 11/20: fixed, need test
  - process time of category_organizer.py is much slower than expected. Need to improve logic
     - Searching parent item property everytime? Since target database is explicitly specified and we can assume its structure will not change during the execution, we don't have to search everytime.
     - Searching pages under databse takes time as number pages increase. Page id can be cached right after page creation, use it later as reference