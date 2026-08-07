# REST API

The API is rooted at `/api/v1`. Fetch the machine-readable OpenAPI 3.1 document from `/api/v1/openapi.json`.

Exchange account credentials at `POST /api/v1/token`, then send `Authorization: Bearer TOKEN`. Tokens expire after one hour. Collection and item reads are available for organizations, jobs, applications, activities, and tasks. Private resources are always scoped to the token owner; collection pages accept `page` and `per_page` (maximum 100).

API clients should use HTTPS and treat tokens like passwords.
