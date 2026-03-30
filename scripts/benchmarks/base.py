"""Base benchmark runner class."""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import httpx


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    iterations: int
    total_operations: int
    successful: int
    failed: int
    duration_seconds: float
    operations_per_second: float
    latency_ms: dict[str, float]
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_operations": self.total_operations,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": round(self.successful / self.total_operations * 100, 2) if self.total_operations > 0 else 0,
            "duration_seconds": round(self.duration_seconds, 3),
            "operations_per_second": round(self.operations_per_second, 2),
            "latency_ms": self.latency_ms,
            "errors": self.errors[:10],
            "metadata": self.metadata
        }


class Benchmark(ABC):
    """Base class for all benchmarks."""

    name: str = "base"
    description: str = "Base benchmark"

    def __init__(
        self,
        base_url: str,
        client_key: str,
        iterations: int = 5,
        workers: int = 5,
        operations: int = 100,
    ):
        self.base_url = base_url
        self.client_key = client_key
        self.iterations = iterations
        self.workers = workers
        self.operations = operations
        self.results: list[BenchmarkResult] = []

    @abstractmethod
    async def run_operation(
        self,
        client: httpx.AsyncClient,
        operation_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Run a single operation.

        Returns: (success, error_message)
        """
        pass

    async def _run_single(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        operation_id: int
    ) -> tuple[bool, float, Optional[str]]:
        """Run operation with concurrency control."""
        async with semaphore:
            start = time.perf_counter()
            try:
                success, error = await self.run_operation(client, operation_id)
                elapsed = time.perf_counter() - start
                if not success:
                    return False, elapsed, error
                return True, elapsed, None
            except Exception as e:
                return False, time.perf_counter() - start, str(e)[:200]

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        """Calculate percentile using nearest-rank method."""
        n = len(sorted_values)
        idx = min(int(n * p), n - 1)
        return sorted_values[idx]

    async def run_iteration(
        self,
        iteration: int
    ) -> BenchmarkResult:
        """Run a single iteration of the benchmark."""
        limits = httpx.Limits(
            max_connections=self.workers,
            max_keepalive_connections=self.workers
        )

        latencies: list[float] = []
        successes = 0
        failures = 0
        errors: list[dict[str, Any]] = []

        wall_start = time.perf_counter()

        async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
            semaphore = asyncio.Semaphore(self.workers)
            tasks = [
                self._run_single(client, semaphore, i)
                for i in range(self.operations)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    failures += 1
                    errors.append({"error": str(result)[:200]})
                else:
                    success, latency, error = result
                    latencies.append(latency)
                    if success:
                        successes += 1
                    else:
                        failures += 1
                        if error:
                            errors.append({"error": error})

        wall_duration = time.perf_counter() - wall_start
        sorted_latencies = sorted(latencies) if latencies else [0]

        return BenchmarkResult(
            name=self.name,
            iterations=iteration,
            total_operations=self.operations,
            successful=successes,
            failed=failures,
            duration_seconds=round(wall_duration, 3),
            operations_per_second=round(successes / wall_duration, 2) if wall_duration > 0 else 0,
            latency_ms={
                "min": round(min(sorted_latencies) * 1000, 2),
                "max": round(max(sorted_latencies) * 1000, 2),
                "avg": round(sum(sorted_latencies) / len(sorted_latencies) * 1000, 2),
                "p50": round(self._percentile(sorted_latencies, 0.50) * 1000, 2),
                "p90": round(self._percentile(sorted_latencies, 0.90) * 1000, 2),
                "p95": round(self._percentile(sorted_latencies, 0.95) * 1000, 2),
                "p99": round(self._percentile(sorted_latencies, 0.99) * 1000, 2),
            },
            errors=errors[:10],
            metadata={
                "workers": self.workers,
                "base_url": self.base_url,
            }
        )

    async def run_all(self) -> list[BenchmarkResult]:
        """Run all iterations and return results."""
        print(f"\n🔬 Starting {self.name}: {self.operations} ops, {self.workers} workers, {self.iterations} iterations")
        self.results = []
        for i in range(1, self.iterations + 1):
            result = await self.run_iteration(i)
            self.results.append(result)
            print(f"   Iteration {i}/{self.iterations}: {result.operations_per_second} ops/sec, {result.successful}/{result.total_operations} success")
            if result.errors and i == 1:
                print(f"   Sample error: {result.errors[0]['error']}")
        return self.results

    def get_median_result(self) -> dict[str, Any]:
        """Calculate median values across all iterations."""
        if not self.results:
            return {}

        def median(values: list[float]) -> float:
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mid = n // 2
            if n % 2 == 0:
                return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            return sorted_vals[mid]

        # Collect all metrics
        throughputs = [r.operations_per_second for r in self.results]
        success_rates = [r.successful / r.total_operations * 100 for r in self.results]
        durations = [r.duration_seconds for r in self.results]

        # Collect latency metrics
        latency_keys = ["min", "max", "avg", "p50", "p90", "p95", "p99"]
        latency_medians = {}
        for key in latency_keys:
            values = [r.latency_ms[key] for r in self.results]
            latency_medians[key] = round(median(values), 2)

        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_operations": self.operations,
            "median": {
                "operations_per_second": round(median(throughputs), 2),
                "success_rate": round(median(success_rates), 2),
                "duration_seconds": round(median(durations), 3),
                "latency_ms": latency_medians,
            },
            "range": {
                "throughput": {"min": min(throughputs), "max": max(throughputs)},
                "success_rate": {"min": min(success_rates), "max": max(success_rates)},
                "p95_latency": {"min": min(r.latency_ms["p95"] for r in self.results),
                               "max": max(r.latency_ms["p95"] for r in self.results)},
            },
            "metadata": self.results[0].metadata if self.results else {}
        }
