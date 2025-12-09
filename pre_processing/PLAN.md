# Pre_processing plan 
## Background
- In Service Now Knowledge portal, there are both Japanese version articles and English ones
- Articles may have a property "translated from" which points to original article
  - This relation is one-way, that is we can know the original articles from the "translated from" property of translated articles but there is no way to tell which is the translated version based on properites of original articles.

## Export
- Upon exporting each articles, we will merge Japanese version and English version
  - The name of HTML will be "JP_KB_NUMBER/EN_KB_NUMBER-JP_ARTICLE_NAME/EN_ARTICLE_NAME", where
    - JP_KB_NUMBER and EN_KB_NUMBER: knowledge base number of articles
    - JP_ARTICLE_NAME and EN_ARTICLE_NAME: names of articles
  - In the exported HTML, Japanese version comes first, then English ver. follows
  - At the beginning of each version, we will add header either "(Japanese ver.)" or "(English ver.)"
- Some articles may contain `<iframe>` elements. Since Notion importer doesn't support `<iframe>`, we will edit htmls containing `<iframe>` as follows:
  - If source of `<iframe>` points to Google Documents, download that Google Documents in form of `.docx` instead of downloading HTML
    - In this case, we will download original and translated version separatly and don't merge them
    - Names of downloaded docx is in similar format of htmls, that is KB_NUMBER_ARTICLE_NAME.
  - If source of `<iframe>` points to URLs other than Google Documents, edit `<iframe>` to `<a>` element and set `href` property to that URL
- Download of Google Documents will be done through browser and automation tool, Selenium
  - Google Documents can be accessible only from OAuth2. Ask users to enter credentials for authentication
- Articles may contain attached files, such as images and videos
  - We will also download these attached files
  - Attached files are stored in the directory `attachments_KBXXXXX` with suffix that has the same knowledge base article number of linked html
  - Make sure to download all attachments of both Japanese ver. and English ver.
  - HTML should have correct relative path to downloaded attached files. Edit the html to satisfy this as well
- We will get category metadata as well upon downloading html
  - Knowledge base has category hierarchy structure.
  - We have to get the category where each articles belongs to and its category hierarchy
    - These information will be used later in Notion database preparation
- All exported html and Google Documents will be downloaded under a folder `migration_output/articles_exported_YYYYMMDD_hhmm`.
  - `YYYYMMDD_hhmm` is the execution data and time in JST
- List of download htmls and docxs will be outputed in CSV format.
  - This CSV contains at least name of exported KB numbers, original sys_ids, category hierarchy
  - The number of rows should be equals to the number of downloaded htmls and Google Documets