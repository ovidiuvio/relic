"""Space operations benchmark."""
import random
from scripts.benchmarks.base import Benchmark


class SpaceBenchmark(Benchmark):
    """Benchmark space operations: list, get relics, add/remove."""

    name = "spaces"
    description = "Space operations"

    def __init__(
        self,
        space_ids: list[str] = None,
        relic_ids: list[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.space_ids = space_ids or []
        self.relic_ids = relic_ids or []

    async def run_operation(self, client, operation_id):
        """Randomly choose space operation."""
        headers = {"X-Client-Key": self.client_key}

        op_type = random.choice(["list", "get", "get_relics"])

        if op_type == "list":
            url = f"{self.base_url}/api/v1/spaces?limit=25"
            response = await client.get(url, headers=headers)

        elif op_type == "get" and self.space_ids:
            space_id = random.choice(self.space_ids)
            url = f"{self.base_url}/api/v1/spaces/{space_id}"
            response = await client.get(url, headers=headers)

        elif op_type == "get_relics" and self.space_ids:
            space_id = random.choice(self.space_ids)
            url = f"{self.base_url}/api/v1/spaces/{space_id}/relics?limit=25"
            response = await client.get(url, headers=headers)

        else:
            # Fallback to list
            url = f"{self.base_url}/api/v1/spaces?limit=25"
            response = await client.get(url, headers=headers)

        if response.status_code in (200, 404):
            return True, None
        else:
            return False, f"Status {response.status_code}: {response.text[:100]}"
