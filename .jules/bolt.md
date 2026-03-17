## 2024-03-16 - [Eager Loading Access Lists in list_spaces]
**Learning:** Eager loading relationships in SQLAlchemy (like `Space.access_list`) using `selectinload` prevents N+1 query problems when accessing properties like `space.access_list` in Python loops over query results. Always verify that `selectinload` is properly imported from `sqlalchemy.orm`.
**Action:** When querying for objects that will have their relationship collections accessed later (especially in a loop), always append `.options(selectinload(Model.relationship))` to the query.
