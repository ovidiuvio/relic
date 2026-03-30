#!/usr/bin/env python3
"""
Run all benchmarks and generate combined results.

Usage:
    python3 scripts/run_all_benchmarks.py --client-key YOUR_KEY --url http://localhost
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmarks.base import Benchmark
from scripts.benchmarks.test_read import ReadBenchmark
from scripts.benchmarks.test_search import SearchBenchmark
from scripts.benchmarks.test_spaces import SpaceBenchmark
from scripts.benchmarks.test_social import SocialBenchmark
from scripts.benchmarks.test_mixed import MixedBenchmark


async def fetch_relic_ids(base_url: str, client_key: str, limit: int = 100) -> list[str]:
    """Fetch relic IDs for benchmarks."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/api/v1/relics",
                headers={"X-Client-Key": client_key},
                params={"limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                return [r["id"] for r in data.get("relics", [])]
    except Exception as e:
        print(f"⚠️  Could not fetch relic IDs: {e}")
    return []


async def fetch_space_ids(base_url: str, client_key: str, limit: int = 50) -> list[str]:
    """Fetch space IDs for benchmarks."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/api/v1/spaces",
                headers={"X-Client-Key": client_key},
                params={"limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                return [s["id"] for s in data.get("spaces", [])]
    except Exception as e:
        print(f"⚠️  Could not fetch space IDs: {e}")
    return []


async def run_benchmarks(
    base_url: str,
    client_key: str,
    iterations: int = 5,
    workers: int = 5,
    operations: int = 100,
    relic_count: int = 100,
    space_count: int = 50,
) -> dict[str, dict]:
    """Run all benchmarks and return results."""
    print("=" * 60)
    print("🔬 RELIC BENCHMARK SUITE")
    print("=" * 60)
    print(f"   URL: {base_url}")
    print(f"   Iterations: {iterations}")
    print(f"   Workers: {workers}")
    print(f"   Operations per benchmark: {operations}")
    print("=" * 60)

    # Fetch IDs for benchmarks
    print("\n📋 Fetching relic and space IDs...")
    relic_ids = await fetch_relic_ids(base_url, client_key, relic_count)
    space_ids = await fetch_space_ids(base_url, client_key, space_count)
    print(f"   Found {len(relic_ids)} relics, {len(space_ids)} spaces")

    # Initialize benchmarks (skip those requiring data we don't have)
    common = dict(iterations=iterations, workers=workers, operations=operations, base_url=base_url, client_key=client_key)
    benchmarks: list[tuple[str, Benchmark | None]] = [
        ("create", None),  # Create is handled separately
        ("search", SearchBenchmark(**common)),
        ("spaces", SpaceBenchmark(space_ids=space_ids, **common)),
    ]
    if relic_ids:
        benchmarks += [
            ("read", ReadBenchmark(relic_ids=relic_ids, **common)),
            ("social", SocialBenchmark(relic_ids=relic_ids, **common)),
            ("mixed", MixedBenchmark(relic_ids=relic_ids, space_ids=space_ids, **common)),
        ]
    else:
        print("⚠️  Skipping read, social, mixed benchmarks: no relics available")

    results = {}
    start_time = time.perf_counter()

    for name, benchmark in benchmarks:
        if benchmark is None:
            continue

        try:
            await benchmark.run_all()
            results[name] = benchmark.get_median_result()
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            results[name] = {"error": str(e)}

    total_duration = time.perf_counter() - start_time

    # Add summary
    results["_summary"] = {
        "total_duration_seconds": round(total_duration, 2),
        "relic_ids_used": len(relic_ids),
        "space_ids_used": len(space_ids),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return results


def print_summary(results: dict[str, dict]):
    """Print benchmark summary."""
    print("\n" + "=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)

    for name, data in results.items():
        if name.startswith("_") or "error" in data:
            continue

        median = data.get("median", {})
        range_data = data.get("range", {})

        print(f"\n{name.upper()}")
        print(f"   Throughput: {median.get('operations_per_second', 'N/A')} ops/sec")
        print(f"   Success Rate: {median.get('success_rate', 'N/A')}%")
        print(f"   P95 Latency: {median.get('latency_ms', {}).get('p95', 'N/A')}ms")

        if range_data:
            tp_range = range_data.get('throughput', {})
            print(f"   Throughput Range: {tp_range.get('min', 'N/A')} - {tp_range.get('max', 'N/A')} ops/sec")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run all Relic benchmarks")
    parser.add_argument("--url", default="http://localhost", help="Base URL")
    parser.add_argument("--client-key", required=True, help="Client key")
    parser.add_argument("--iterations", type=int, default=5, help="Iterations per benchmark")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers")
    parser.add_argument("--operations", type=int, default=100, help="Operations per iteration")
    parser.add_argument("--relic-count", type=int, default=100, help="Relic IDs to fetch")
    parser.add_argument("--space-count", type=int, default=50, help="Space IDs to fetch")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--git-hash", type=str, help="Git hash")

    args = parser.parse_args()

    # Run benchmarks
    results = asyncio.run(run_benchmarks(
        base_url=args.url,
        client_key=args.client_key,
        iterations=args.iterations,
        workers=args.workers,
        operations=args.operations,
        relic_count=args.relic_count,
        space_count=args.space_count,
    ))

    # Add metadata
    results["_metadata"] = {
        "git_hash": args.git_hash or "unknown",
        "configuration": {
            "url": args.url,
            "iterations": args.iterations,
            "workers": args.workers,
            "operations": args.operations,
        }
    }

    # Print summary
    print_summary(results)

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")

    # Also output JSON for CI
    print("\n📄 JSON Output:")
    print(json.dumps(results, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
