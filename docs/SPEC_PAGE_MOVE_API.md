Moves a page to a new parent location (either another page or a database).

## Endpoint

**POST** `/v1/pages/{page_id}/move`

## Authentication

Requires Bearer token authentication with appropriate page edit permissions.

## Path parameters

**page_id** (required)

- Type: `string` (UUID)
- Description: The ID of the page to move
- Format: UUIDs can be provided with or without dashes
- Example: `195de9221179449fab8075a27c979105` or `195de922-1179-449f-ab80-75a27c979105`

## Request body

**parent** (required)

- Type: `object`
- Description: The new parent location for the page

The parent object must be one of two types:

### Page parent

Move the page under another page:

```json
{
  "parent": {
    "type": "page_id",
    "page_id": "<parent-page-id>"
  }
}
```

- **type**: Always `"page_id"`
- **page_id**: UUID of the parent page (with or without dashes)

### Database parent

Move the page into a database:

```json
{
  "parent": {
    "type": "data_source_id",
    "data_source_id": "<database-data-source-id>"
  }
}
```

- **type**: Always `"data_source_id"`
- **data_source_id**: UUID of the database's data source (with or without dashes)

Note: You must use `data_source_id` rather than `database_id`. Use the Retrieve database endpoint to get the data source URL from the database.

## Response

Returns a page object on success. The response can be either:

- **Partial page object**: Contains only `object` and `id` fields
- **Full page object**: Contains all page properties and metadata

### Partial response example

```json
{
  "object": "page",
  "id": "195de922-1179-449f-ab80-75a27c979105"
}
```

### Full response example

```json
{
  "object": "page",
  "id": "195de922-1179-449f-ab80-75a27c979105",
  "created_time": "2025-01-15T10:30:00.000Z",
  "last_edited_time": "2025-01-15T14:45:00.000Z",
  "created_by": {
    "object": "user",
    "id": "abc123..."
  },
  "last_edited_by": {
    "object": "user",
    "id": "abc123..."
  },
  "parent": {
    "type": "page_id",
    "page_id": "new-parent-id"
  },
  "archived": false,
  "in_trash": false,
  "properties": { ... },
  "url": "https://notion.so/..."
}
```

## Example request

### Move page under another page

```bash
curl -X POST https://api.notion.com/v1/pages/195de9221179449fab8075a27c979105/move \
  -H "Authorization: Bearer secret_xxx" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {
      "type": "page_id",
      "page_id": "f336d0bc-b841-465b-8045-024475c079dd"
    }
  }'
```

### Move page into a database

```bash
curl -X POST https://api.notion.com/v1/pages/195de9221179449fab8075a27c979105/move \
  -H "Authorization: Bearer secret_xxx" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {
      "type": "data_source_id",
      "data_source_id": "1c7b35e6-e67f-8096-bf3f-000ba938459e"
    }
  }'
```

## Error responses

### 400 Bad Request - Validation errors

Returned for various validation failures:

**New parent is the same as current parent:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "New parent must be different from the current parent"
}
```

**Trying to move a page to itself:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "Parent ID must be different from the child ID: {page_id}"
}
```

**Circular reference (moving page under its own descendant):**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "New parent {parent_id} cannot be under the hierarchy of child {page_id}"
}
```

**Page is in trash:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "Object {page_id} is in trash and cannot be moved"
}
```

**Parent is in trash:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "Cannot move to a parent that is in trash: {parent_id}"
}
```

**System block cannot be moved:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "System blocks cannot be moved"
}
```

**Cannot load or access new parent:**

```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "Could not load new parent {parent_id} or missing edit permission"
}
```

### 404 Not Found - Object not found

Returned when the page to move or the specified parent doesn't exist or isn't accessible:

```json
{
  "object": "error",
  "status": 404,
  "code": "object_not_found",
  "message": "Could not find page with ID: {page_id}. Check that you have access and that you're authenticated to the correct workspace."
}
```

## Validation rules

The endpoint performs comprehensive validation before moving a page:

**Page validation:**

- Page must exist and be accessible by the integration
- Page must be a navigable block type (page or database)
- Page cannot be a system block (including personal home pages)
- Page cannot be a People primitive (person profile or people directory page)
- Page cannot be in trash
- Integration must have edit permission for the page

**Parent validation:**

- New parent must exist and be accessible by the integration
- Integration must have edit permission for the new parent
- New parent cannot be in trash
- New parent must be different from the page being moved
- New parent must be different from the page's current parent

**Hierarchy validation:**

- The move must not create circular references (i.e., cannot move a parent page under one of its own descendants)
- The page ID and parent ID must be different

**Database-specific rules:**

- When moving to a database, use `data_source_id` (not `database_id`)
- If a database has multiple data sources, specify which data source to use
- When moving into a database, the page will adopt the database's property schema

## Implementation notes

- **PR:** https://github.com/makenotion/notion-next/pull/145064
- The endpoint uses the `AbstractApiEndpoint` class-based DSL pattern
- Internally identified as `public_movePage`
- Operation ID: `move-page`
- Owner: Public API team
- Validation includes checking for circular references and permission requirements
- The operation is performed using admin actor with the requesting bot as the author
- All parent records and their ancestors are loaded for validation
- Moving a page to a database requires using `data_source_id`, not `database_id`

## Related endpoints

- **Retrieve a page**: `GET /v1/pages/{page_id}`
- **Update page properties**: `PATCH /v1/pages/{page_id}`
- **Create a page**: `POST /v1/pages`
- **Retrieve a database**: `GET /v1/databases/{database_id}` (to get data source URLs)