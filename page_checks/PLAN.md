# Scan invisible elements
- This process is done in `scan_div_accshow.py`
- Scan a folder recursively to get htmls
- Search for elements that are not visible after rendering because of style settings in each html
  - `div` elements with `accshow` class
- Report these htmls and elements in CSV format

# Scan unneccessary lines
- This process is done in `scan_empty_list_wrappers.py`
- See. /data/mer/test_1205/(Migration用) Merportal/articles_exported_20251203_111041/KB0011626_KB0011613-備品の経費精算について_Reimbursement_for_equipment.html
- line 64 to 142
- When importing this html to Notion, import pager has lots of blank lines which do harm usability
- Analyze this html and search for htmls with elemenets that are converted poorly formated pages upon impoting to Notion