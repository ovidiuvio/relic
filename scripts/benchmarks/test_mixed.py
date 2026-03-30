"""Mixed workload benchmark: realistic usage pattern."""
import random
from scripts.benchmarks.base import Benchmark


class MixedBenchmark(Benchmark):
    """
    Mixed workload benchmark simulating real usage patterns.

    Distribution:
    - 50% Read operations (GET content/metadata)
    - 20% List/Search operations
    - 15% Social operations (check bookmarks, comments)
    - 10% Space operations
    - 5% Write operations (create relic)
    """

    name = "mixed"
    description = "Mixed workload (50% read, 20% search, 15% social, 10% spaces, 5% write)"

    def __init__(
        self,
        relic_ids: list[str] = None,
        space_ids: list[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.relic_ids = relic_ids or []
        self.space_ids = space_ids or []
        self.search_terms = ["draft", "config", "data", "auth", "test"]
        self.tags = ["python", "code", "docs", "config", "data"]

    async def run_operation(self, client, operation_id):
        """Run operation based on weighted distribution."""
        headers = {"X-Client-Key": self.client_key}
        roll = random.random()

        # 50% Read operations
        if roll < 0.50 and self.relic_ids:
            relic_id = random.choice(self.relic_ids)
            endpoint = random.choice(["raw", "metadata"])
            url = f"{self.base_url}/{relic_id}" if endpoint == "raw" else f"{self.base_url}/api/v1/relics/{relic_id}"
            response = await client.get(url, headers=headers)

        # 20% List/Search operations
        elif roll < 0.70:
            op_type = random.choice(["search", "tag", "list"])
            if op_type == "search":
                term = random.choice(self.search_terms)
                url = f"{self.base_url}/api/v1/relics?search={term}&limit=25"
            elif op_type == "tag":
                tag = random.choice(self.tags)
                url = f"{self.base_url}/api/v1/relics?tag={tag}&limit=25"
            else:
                url = f"{self.base_url}/api/v1/relics?limit=25"
            response = await client.get(url, headers=headers)

        # 15% Social operations
        elif roll < 0.85 and self.relic_ids:
            relic_id = random.choice(self.relic_ids)
            op_type = random.choice(["check_bookmark", "get_comments", "lineage"])
            if op_type == "check_bookmark":
                url = f"{self.base_url}/api/v1/bookmarks/check/{relic_id}"
            elif op_type == "get_comments":
                url = f"{self.base_url}/api/v1/relics/{relic_id}/comments?limit=50"
            else:
                url = f"{self.base_url}/api/v1/relics/{relic_id}/lineage"
            response = await client.get(url, headers=headers)

        # 10% Space operations
        elif roll < 0.95 and self.space_ids:
            space_id = random.choice(self.space_ids)
            op_type = random.choice(["get", "get_relics"])
            if op_type == "get":
                url = f"{self.base_url}/api/v1/spaces/{space_id}"
            else:
                url = f"{self.base_url}/api/v1/spaces/{space_id}/relics?limit=25"
            response = await client.get(url, headers=headers)

        # 5% Write operations (create relic)
        else:
            content = f"Mixed benchmark content {operation_id}"
            files = {"file": ("benchmark.txt", content.encode(), "text/plain")}
            data = {"name": f"benchmark-{operation_id}", "access_level": "public"}
            url = f"{self.base_url}/api/v1/relics"
            response = await client.post(url, headers=headers, files=files, data=data)

        if response.status_code in (200, 201):
            return True, 0, None
        elif response.status_code == 404:
            return True, 0, None
        else:
            return False, 0, f"Status {response.status_code}: {response.text[:100]}"
