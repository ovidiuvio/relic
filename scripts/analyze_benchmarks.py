#!/usr/bin/env python3
"""
Analyze benchmark results and generate trend plots.

Usage:
    python3 scripts/analyze_benchmarks.py --input benchmark-results/ --output trends/
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  matplotlib not installed. Install with: pip install matplotlib")


def load_results(input_dir: Path) -> list[dict]:
    """Load all benchmark JSON files from directory."""
    results = []
    for f in sorted(input_dir.glob("*.json")):
        try:
            with open(f) as fp:
                data = json.load(fp)
                # Handle new format with runs array and median
                if "median" in data and "runs" in data:
                    # Use median values as the result
                    results.append({
                        "metadata": data.get("metadata", {}),
                        "results": {
                            "throughput_relics_per_sec": data["median"]["throughput_relics_per_sec"],
                            "success_rate": data["median"]["success_rate"],
                            "duration_seconds": data["median"]["duration_seconds"],
                            "latency_ms": {
                                "p95": data["median"]["p95_latency_ms"]
                            }
                        }
                    })
                else:
                    # Legacy format
                    results.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Could not load {f}: {e}")
    return results


def generate_plots(results: list[dict], output_dir: Path) -> None:
    """Generate trend plots."""
    if not HAS_MATPLOTLIB or not results:
        return
    
    dates, throughputs, success_rates, p95_latencies = [], [], [], []
    
    for r in results:
        if "results" not in r or "metadata" not in r:
            continue
        try:
            dates.append(datetime.fromisoformat(r["metadata"]["timestamp"].replace("Z", "+00:00")))
            throughputs.append(r["results"]["throughput_relics_per_sec"])
            success_rates.append(r["results"]["success_rate"])
            p95_latencies.append(r["results"]["latency_ms"]["p95"])
        except (KeyError, ValueError):
            continue
    
    if not dates:
        print("⚠️  No valid data to plot")
        return
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle("Relic Creation Benchmark Trends", fontsize=14, fontweight='bold')
    
    # Throughput
    ax1 = axes[0]
    ax1.plot(dates, throughputs, marker='o', linestyle='-', color='#2563eb', linewidth=2)
    ax1.set_ylabel("Throughput (relics/sec)")
    ax1.set_title(f"Throughput (avg: {sum(throughputs)/len(throughputs):.1f} req/s)")
    ax1.grid(True, alpha=0.3)
    
    # Success rate
    ax2 = axes[1]
    ax2.plot(dates, success_rates, marker='s', linestyle='-', color='#16a34a', linewidth=2)
    ax2.set_ylabel("Success Rate (%)")
    ax2.set_title(f"Success Rate (avg: {sum(success_rates)/len(success_rates):.1f}%)")
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(max(0, min(success_rates) - 2), 100.5)
    
    # P95 latency
    ax3 = axes[2]
    ax3.plot(dates, p95_latencies, marker='^', linestyle='-', color='#dc2626', linewidth=2)
    ax3.set_ylabel("P95 Latency (ms)")
    ax3.set_xlabel("Date")
    ax3.set_title(f"P95 Latency (avg: {sum(p95_latencies)/len(p95_latencies):.1f}ms)")
    ax3.grid(True, alpha=0.3)
    
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / "benchmark_trends.png", dpi=150, bbox_inches='tight')
    print(f"✅ Plot saved to: {output_dir / 'benchmark_trends.png'}")


def generate_summary(results: list[dict], output_dir: Path) -> None:
    """Generate markdown summary."""
    if not results:
        return
    
    latest = results[-1]
    throughputs = [r["results"]["throughput_relics_per_sec"] for r in results if "results" in r]
    success_rates = [r["results"]["success_rate"] for r in results if "results" in r]
    p95s = [r["results"]["latency_ms"]["p95"] for r in results if "results" in r and "latency_ms" in r["results"]]
    
    summary = f"""# 📊 Benchmark Summary

Generated: {datetime.now().isoformat()}

## Latest Run

| Metric | Value |
|--------|-------|
| Date | {latest.get("metadata", {}).get("timestamp", "N/A")} |
| Git Hash | {latest.get("metadata", {}).get("git_hash", "N/A")[:7]} |
| Throughput | {latest["results"]["throughput_relics_per_sec"]} relics/sec |
| Success Rate | {latest["results"]["success_rate"]}% |
| P95 Latency | {latest["results"]["latency_ms"]["p95"]} ms |

## Trends ({len(results)} runs)

| Metric | Min | Max | Average |
|--------|-----|-----|---------|
| Throughput | {min(throughputs):.2f} | {max(throughputs):.2f} | {sum(throughputs)/len(throughputs):.2f} |
| Success Rate | {min(success_rates):.2f}% | {max(success_rates):.2f}% | {sum(success_rates)/len(success_rates):.2f}% |
| P95 Latency | {min(p95s):.2f}ms | {max(p95s):.2f}ms | {sum(p95s)/len(p95s):.2f}ms |

## History

See `benchmark_trends.png` for visual trends.
"""
    
    with open(output_dir / "SUMMARY.md", 'w') as f:
        f.write(summary)
    print(f"✅ Summary saved to: {output_dir / 'SUMMARY.md'}")
    
    # Print summary to stdout for workflow logs
    print("\n" + "=" * 50)
    print("📈 TREND SUMMARY")
    print("=" * 50)
    print(f"   Total runs: {len(results)}")
    print(f"   Throughput avg: {sum(throughputs)/len(throughputs):.2f} relics/sec")
    print(f"   Success rate avg: {sum(success_rates)/len(success_rates):.2f}%")
    print(f"   P95 latency avg: {sum(p95s)/len(p95s):.2f}ms")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("--input", type=str, required=True, help="Input directory with JSON results")
    parser.add_argument("--output", type=str, required=True, help="Output directory for analysis")
    args = parser.parse_args()
    
    input_dir, output_dir = Path(args.input), Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    print(f"📊 Loading results from: {input_dir}")
    results = load_results(input_dir)
    print(f"   Found {len(results)} benchmark runs")
    
    if not results:
        print("⚠️  No results to analyze")
        sys.exit(0)
    
    generate_summary(results, output_dir)
    generate_plots(results, output_dir)
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
