## 2024-05-14 - Fix Comment Creation Test
**Bug/Edge Case:** The `test_create_and_get_comment` in `tests/test_comments.py` was failing with a 400 Bad Request error.
**Learning:** The comment creation endpoint requires the client to have a display name set. The test was not registering a client or setting a display name before attempting to create a comment. The test environment also required passing `X-Client-Key` header with requests.
**Prevention:** Ensure that tests for endpoints requiring client identity properly register a client, set required profile information (like the display name), and include the `X-Client-Key` in the request headers.
