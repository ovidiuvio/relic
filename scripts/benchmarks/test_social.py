"""Social features benchmark: bookmarks, comments, forks."""
import random
from scripts.benchmarks.base import Benchmark


class SocialBenchmark(Benchmark):
    """Benchmark social features: bookmarks, comments, forks."""

    name = "social"
    description = "Social features (bookmarks, comments, forks)"

    def __init__(
        self,
        relic_ids: list[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.relic_ids = relic_ids or []

    async def run_operation(self, client, operation_id):
        """Randomly choose social operation."""
        if not self.relic_ids:
            return True, 0, None

        relic_id = random.choice(self.relic_ids)
        headers = {"X-Client-Key": self.client_key}

        op_type = random.choice(["check_bookmark", "get_comments", "get_forks", "get_bookmarkers"])

        if op_type == "check_bookmark":
            url = f"{self.base_url}/api/v1/bookmarks/check/{relic_id}"
            response = await client.get(url, headers=headers)

        elif op_type == "get_comments":
            url = f"{self.base_url}/api/v1/relics/{relic_id}/comments?limit=50"
            response = await client.get(url, headers=headers)

        elif op_type == "get_forks":
            url = f"{self.base_url}/api/v1/relics/{relic_id}/lineage"
            response = await client.get(url, headers=headers)

        elif op_type == "get_bookmarkers":
            url = f"{self.base_url}/api/v1/relics/{relic_id}/bookmarkers?limit=25"
            response = await client.get(url, headers=headers)

        else:
            url = f"{self.base_url}/api/v1/bookmarks/check/{relic_id}"
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return True, 0, None
        elif response.status_code == 404:
            return True, 0, None
        else:
            return False, 0, f"Status {response.status_code}: {response.text[:100]}"
