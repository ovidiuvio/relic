## 2024-05-24 - Relic Sharing Needs
**Observation:** Relic currently supports standard time-based expiration (e.g., 1h, 24h), but lacks a mechanism for securely sharing highly sensitive, one-time-use secrets (like passwords or tokens) where the sender needs assurance that the data cannot be accessed multiple times or intercepted by a third party later.
**Insight:** A "Burn after reading" feature perfectly aligns with the core product mission of sharing snippets, offering a distinct value proposition for security-conscious users.
**Strategy:** Propose "Burn after reading" as a lightweight extension to the existing expiration system, keeping the MVP simple by integrating it with the existing access/retrieval endpoints.
