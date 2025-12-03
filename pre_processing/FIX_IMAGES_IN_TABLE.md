# Fixing import issue relating to table containing images
## Background
- Notion's table block is "simple", which doesn't support embedding images within tables
- Images in tables are allowed in other platform or formats, such as HTML
- When importing html containing images in table to Notion, layout of resulted page is corrupted
- To overcome this issue, we will edit table elements in html to other element so that Notion can convert them to column blocks

## Specification of Notion import relating to column blocks
- If `div` elements have `data-notion-column-list` property, the elements within are converted to column blocks upon importing to Notion
- Sample html is `resources/sample-columns.html`

## Fix plan
- Scan htmls under given folder and find tables containging images within
- Convert these tables to `div` elements with `data-notion-column-list`
  - A table row will be convert to a `div` element.
    - This is to respect original layout
  - If table have N rows, there will be N `div` elements with `data-notion-column-list`
- We must not convert table elements that don't have embedded images. This conversion should be done only to table elements containing images
- It's OK to change original layout rendered on browers. The purpose here is to maintain layout as much as possible after importing html to Notion
- Create `convert_table_column.py` to execute these conversion
- Make cli subcommand for this module. Argument should be a folder path that contains htmls