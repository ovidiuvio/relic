## 2024-05-14 - Fix Comment Creation Test
**Bug/Edge Case:** The `test_create_and_get_comment` in `tests/test_comments.py` was failing with a 400 Bad Request error.
**Learning:** The comment creation endpoint requires the client to have a display name set. The test was not registering a client or setting a display name before attempting to create a comment. The test environment also required passing `X-Client-Key` header with requests.
**Prevention:** Ensure that tests for endpoints requiring client identity properly register a client, set required profile information (like the display name), and include the `X-Client-Key` in the request headers.

## 2025-03-25 - Fix Comment Responses Test
**Bug/Edge Case:** The `test_create_and_get_comment` in `tests/test_comments.py` was failing with an AssertionError when comparing the length of the JSON response to 1.
**Learning:** The get comments endpoint `GET /api/v1/relics/{relic_id}/comments` was refactored to return a paginated response dictionary (`{"comments": [...], "total": X, "limit": Y, "offset": Z}`) rather than a direct JSON list. The test was asserting against the length of the dictionary keys rather than the list of comments inside the payload.
**Prevention:** Ensure that tests for list endpoints that have pagination verify the correct response shape and extract the list of items from the appropriate key (e.g., `response.json()["comments"]`) instead of assuming the root JSON object is the list.
