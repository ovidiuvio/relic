"""Search and filter benchmark."""
import random
from scripts.benchmarks.base import Benchmark


class SearchBenchmark(Benchmark):
    """Benchmark search and filter operations."""

    name = "search"
    description = "Search and filter relics"

    def __init__(
        self,
        search_terms: list[str] = None,
        tags: list[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.search_terms = search_terms or ["draft", "config", "data", "auth", "test"]
        self.tags = tags or ["python", "code", "docs", "config", "data"]

    async def run_operation(self, client, operation_id):
        """Randomly choose search, tag filter, or list operation."""
        op_type = random.choice(["search", "tag", "list", "sort"])
        headers = {"X-Client-Key": self.client_key}

        if op_type == "search":
            term = random.choice(self.search_terms)
            url = f"{self.base_url}/api/v1/relics?search={term}&limit=25"

        elif op_type == "tag":
            tag = random.choice(self.tags)
            url = f"{self.base_url}/api/v1/relics?tag={tag}&limit=25"

        elif op_type == "list":
            offset = random.randint(0, 5) * 25
            url = f"{self.base_url}/api/v1/relics?limit=25&offset={offset}"

        else:  # sort
            sort_by = random.choice(["created_at", "name", "access_count"])
            sort_order = random.choice(["asc", "desc"])
            url = f"{self.base_url}/api/v1/relics?sort_by={sort_by}&sort_order={sort_order}&limit=25"

        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return True, None
        else:
            return False, f"Status {response.status_code}: {response.text[:100]}"
