"""Read operations benchmark: GET relic content and metadata."""
import random
from scripts.benchmarks.base import Benchmark


class ReadBenchmark(Benchmark):
    """Benchmark read operations: GET /{id}/raw and GET /api/v1/relics/{id}."""

    name = "read"
    description = "Read relic content and metadata"

    def __init__(self, relic_ids: list[str], **kwargs):
        super().__init__(**kwargs)
        self.relic_ids = relic_ids
        if not self.relic_ids:
            raise ValueError("relic_ids cannot be empty")

    async def run_operation(self, client, operation_id):
        """Randomly choose between raw content and metadata fetch."""
        relic_id = random.choice(self.relic_ids)
        endpoint = random.choice(["raw", "metadata"])

        if endpoint == "raw":
            url = f"{self.base_url}/{relic_id}"
        else:
            url = f"{self.base_url}/api/v1/relics/{relic_id}"

        headers = {"X-Client-Key": self.client_key}
        response = await client.get(url, headers=headers)

        if response.status_code in (200, 404, 410):
            return True, None
        else:
            return False, f"Status {response.status_code}: {response.text[:100]}"
