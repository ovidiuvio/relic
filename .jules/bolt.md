## 2024-03-16 - [Eager Loading Access Lists in list_spaces]
**Learning:** Eager loading relationships in SQLAlchemy (like `Space.access_list`) using `selectinload` prevents N+1 query problems when accessing properties like `space.access_list` in Python loops over query results. Always verify that `selectinload` is properly imported from `sqlalchemy.orm`.
**Action:** When querying for objects that will have their relationship collections accessed later (especially in a loop), always append `.options(selectinload(Model.relationship))` to the query.

## 2024-03-20 - [Eager Loading Access Lists in get_relic_access]
**Learning:** Eager loading a related model nested inside a related collection (like `RelicAccess.client` within `Relic.access_list`) can be achieved seamlessly by chaining `selectinload` and `joinedload`, e.g., `options(selectinload(Relic.access_list).joinedload(RelicAccess.client))`. This ensures that iterating through a nested collection and accessing its relations does not trigger separate N+1 database queries.
**Action:** When working with nested relational data where deep properties (e.g., `entry.client.name`) are needed, use combined eager loading strategies (`selectinload(..).joinedload(..)`) to fetch everything efficiently upfront.
