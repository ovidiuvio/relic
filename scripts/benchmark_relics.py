#!/usr/bin/env python3
"""
Benchmark script: creates relics with controlled concurrency and collects performance metrics.
Outputs results as JSON for historical tracking and visualization.

Usage:
    python3 scripts/benchmark_relics.py --client-key YOUR_KEY --count 1000 --workers 5 --output results/benchmark-2026-03-30.json
"""
import argparse
import json
import os
import random
import sys
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
import uuid

# Import generators from seed script
sys.path.insert(0, str(Path(__file__).parent))
from seed_relics import (
    TAGS_POOL, VERBS, NOUNS, GENERATORS,
    create_relic_async, create_space_async, rname
)


class BenchmarkMetrics:
    """Collects and calculates benchmark metrics."""

    def __init__(self, total_count: int):
        self.total_count = total_count
        self.successes = 0
        self.failures = 0
        self.latencies: list[float] = []
        self.start_time: float = 0
        self.end_time: float = 0
        self.errors: list[dict[str, Any]] = []
    
    def record_success(self, latency: float):
        self.successes += 1
        self.latencies.append(latency)
    
    def record_failure(self, error: str):
        self.failures += 1
        self.errors.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(error)
        })
    
    def calculate_results(self) -> dict[str, Any]:
        duration = self.end_time - self.start_time
        sorted_latencies = sorted(self.latencies) if self.latencies else [0]
        
        return {
            "total_requested": self.total_count,
            "successful": self.successes,
            "failed": self.failures,
            "success_rate": round(self.successes / self.total_count * 100, 2) if self.total_count > 0 else 0,
            "duration_seconds": round(duration, 3),
            "throughput_relics_per_sec": round(self.successes / duration, 2) if duration > 0 else 0,
            "latency_ms": {
                "min": round(min(sorted_latencies) * 1000, 2),
                "max": round(max(sorted_latencies) * 1000, 2),
                "avg": round(sum(sorted_latencies) / len(sorted_latencies) * 1000, 2) if sorted_latencies else 0,
                "p50": round(sorted_latencies[min(int(len(sorted_latencies) * 0.50), len(sorted_latencies) - 1)] * 1000, 2),
                "p90": round(sorted_latencies[min(int(len(sorted_latencies) * 0.90), len(sorted_latencies) - 1)] * 1000, 2),
                "p95": round(sorted_latencies[min(int(len(sorted_latencies) * 0.95), len(sorted_latencies) - 1)] * 1000, 2),
                "p99": round(sorted_latencies[min(int(len(sorted_latencies) * 0.99), len(sorted_latencies) - 1)] * 1000, 2),
            },
            "errors_sample": self.errors[:10],  # First 10 errors
            "total_errors": len(self.errors),
        }


async def benchmark_relic_task(
    client: httpx.AsyncClient,
    base_url: str,
    client_key: str,
    space_id: str | None,
    access_level: str,
    semaphore: asyncio.Semaphore,
    metrics: BenchmarkMetrics,
    task_id: int,
) -> None:
    """Create a single relic and record metrics."""
    async with semaphore:
        start = time.perf_counter()
        try:
            _, content_type, language_hint, gen_fn = random.choice(GENERATORS)
            tags = list(random.choice(TAGS_POOL))
            if random.random() < 0.3:
                tags = list(set(tags + random.choice(TAGS_POOL)))
            name = rname()
            content = gen_fn()
            
            await create_relic_async(
                client, base_url, client_key,
                content, content_type, language_hint,
                name, tags, access_level,
                space_id=space_id
            )
            
            latency = time.perf_counter() - start
            metrics.record_success(latency)
            
        except Exception as e:
            latency = time.perf_counter() - start
            metrics.record_failure(f"{type(e).__name__}: {str(e)[:200]}")


def generate_metadata(args: argparse.Namespace, git_hash: str | None) -> dict[str, Any]:
    """Generate benchmark metadata."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_hash": git_hash or "unknown",
        "configuration": {
            "count": args.count,
            "workers": args.workers,
            "url": args.url,
            "access_level": args.access_level,
        }
    }


async def main_async():
    parser = argparse.ArgumentParser(
        description="Benchmark relic creation performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--count", type=int, default=1000,
                        help="Number of relics to create (default: 1000)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Number of concurrent requests (default: 5)")
    parser.add_argument("--url", default="http://localhost",
                        help="Base URL (default: http://localhost)")
    parser.add_argument("--client-key", required=True,
                        help="Your client key")
    parser.add_argument("--space-id", default=None,
                        help="Use an existing space instead of creating a new one")
    parser.add_argument("--space-name", default="Benchmark Test Space",
                        help="Name for the new space (default: 'Benchmark Test Space')")
    parser.add_argument("--access-level", default="public", choices=["public", "private"],
                        help="Access level for created relics (default: public)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file path for results")
    parser.add_argument("--git-hash", type=str, default=None,
                        help="Git hash for the benchmark run")
    args = parser.parse_args()

    # Initialize metrics collector
    metrics = BenchmarkMetrics(args.count)
    
    # Get git hash from environment if not provided
    git_hash = args.git_hash or os.environ.get("GITHUB_SHA")
    
    print(f"🔬 Starting benchmark: {args.count} relics, {args.workers} workers")
    print(f"   URL: {args.url}")
    print(f"   Space: {args.space_id or 'global'}")
    print("-" * 60)

    limits = httpx.Limits(max_connections=args.workers, max_keepalive_connections=args.workers)
    
    async with httpx.AsyncClient(limits=limits) as client:
        # Ensure client key is registered before benchmarking
        await client.post(f"{args.url}/api/v1/client/register", headers={"X-Client-Key": args.client_key})

        space_id = args.space_id
        if not space_id:
            print("No space ID provided. Relics will be created globally.")
        else:
            print(f"Using space: {space_id}")

        metrics.start_time = time.perf_counter()
        
        semaphore = asyncio.Semaphore(args.workers)
        tasks = []
        for i in range(args.count):
            tasks.append(benchmark_relic_task(
                client, args.url, args.client_key,
                space_id, args.access_level,
                semaphore, metrics, i
            ))

        # Process in chunks to show progress
        chunk_size = 100
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            await asyncio.gather(*chunk, return_exceptions=True)
            completed = min(i + chunk_size, args.count)
            elapsed = time.perf_counter() - metrics.start_time
            current_throughput = completed / elapsed if elapsed > 0 else 0
            print(f"   Progress: {completed}/{args.count} | "
                  f"Success: {metrics.successes} | Fail: {metrics.failures} | "
                  f"Throughput: {current_throughput:.1f} req/s")

        metrics.end_time = time.perf_counter()

    # Calculate final results
    results = metrics.calculate_results()
    
    # Build complete output
    output = {
        "metadata": generate_metadata(args, git_hash),
        "results": results,
    }
    
    # Print summary
    print("-" * 60)
    print("📊 BENCHMARK RESULTS")
    print("-" * 60)
    print(f"   Total requested:     {output['results']['total_requested']}")
    print(f"   Successful:          {output['results']['successful']}")
    print(f"   Failed:              {output['results']['failed']}")
    print(f"   Success rate:        {output['results']['success_rate']}%")
    print(f"   Duration:            {output['results']['duration_seconds']}s")
    print(f"   Throughput:          {output['results']['throughput_relics_per_sec']} relics/sec")
    print()
    print("   Latency (ms):")
    for key, value in output['results']['latency_ms'].items():
        if key != 'avg':
            print(f"      {key.upper()}: {value}")
        else:
            print(f"      {key}: {value}")
    print("-" * 60)
    
    # Write output file if specified
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"💾 Results saved to: {output_path}")
    
    # Also output to stdout as JSON for CI parsing
    print("\n📄 JSON Output:")
    print(json.dumps(output, indent=2))
    
    # Exit with error if failure rate is too high
    if output['results']['success_rate'] < 95:
        print("\n❌ Benchmark failed: success rate below 95%")
        sys.exit(1)
    
    print("\n✅ Benchmark completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
