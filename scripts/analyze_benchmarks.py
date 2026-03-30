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
                
                # Handle benchmark suite format (multiple benchmarks in one file)
                if any(k in data for k in ["read", "search", "spaces", "social", "mixed", "create"]):
                    # Extract each benchmark as a separate result entry
                    for bench_name in ["create", "read", "search", "spaces", "social", "mixed"]:
                        if bench_name in data:
                            bench = data[bench_name]
                            if "median" in bench:
                                results.append({
                                    "metadata": data.get("_metadata", {}),
                                    "benchmark": bench_name,
                                    "results": {
                                        "throughput_relics_per_sec": bench["median"].get("operations_per_second", 0),
                                        "success_rate": bench["median"].get("success_rate", 100),
                                        "latency_ms": bench["median"].get("latency_ms", {"p95": 0})
                                    }
                                })
                
                # Handle new format with runs array and median (create benchmark)
                elif "median" in data and "runs" in data:
                    latency_ms = data["median"].get("latency_ms")
                    if latency_ms is None:
                        latency_ms = {"p95": data["median"].get("p95_latency_ms", 0)}
                    results.append({
                        "metadata": data.get("metadata", {}),
                        "benchmark": "create",
                        "results": {
                            "throughput_relics_per_sec": data["median"]["throughput_relics_per_sec"],
                            "success_rate": data["median"]["success_rate"],
                            "duration_seconds": data["median"]["duration_seconds"],
                            "latency_ms": latency_ms
                        }
                    })
                elif "results" in data:
                    # Legacy format with results object
                    results.append(data)
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"⚠️  Could not load {f}: {e}")
    return results


def generate_plots(results: list[dict], output_dir: Path) -> None:
    """Generate trend plots for each benchmark type."""
    if not HAS_MATPLOTLIB or not results:
        return
    
    # Group results by benchmark type
    benchmarks = {}
    for r in results:
        bench_name = r.get("benchmark", "unknown")
        if bench_name not in benchmarks:
            benchmarks[bench_name] = []
        benchmarks[bench_name].append(r)
    
    # Generate plots for each benchmark type
    for bench_name, bench_results in benchmarks.items():
        dates, throughputs, p95_latencies = [], [], []
        
        for r in bench_results:
            if "results" not in r or "metadata" not in r:
                continue
            try:
                ts = r["metadata"].get("timestamp", "")
                if not ts:
                    continue
                dates.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                throughputs.append(r["results"]["throughput_relics_per_sec"])
                p95_latencies.append(r["results"]["latency_ms"]["p95"])
            except (KeyError, ValueError):
                continue
        
        if not dates or len(dates) < 1:
            continue
        
        # Create plot
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f"{bench_name.upper()} Benchmark Trends", fontsize=14, fontweight='bold')
        
        # Throughput
        ax1 = axes[0]
        ax1.plot(dates, throughputs, marker='o', linestyle='-', color='#2563eb', linewidth=2)
        ax1.set_ylabel("Throughput (ops/sec)")
        ax1.set_title(f"Throughput (avg: {sum(throughputs)/len(throughputs):.1f} ops/s)")
        ax1.grid(True, alpha=0.3)
        
        # P95 latency
        ax2 = axes[1]
        ax2.plot(dates, p95_latencies, marker='^', linestyle='-', color='#dc2626', linewidth=2)
        ax2.set_ylabel("P95 Latency (ms)")
        ax2.set_xlabel("Date")
        ax2.set_title(f"P95 Latency (avg: {sum(p95_latencies)/len(p95_latencies):.1f}ms)")
        ax2.grid(True, alpha=0.3)
        
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(output_dir / f"{bench_name}_trends.png", dpi=150, bbox_inches='tight')
        print(f"✅ Plot saved to: {output_dir / f'{bench_name}_trends.png'}")
    
    # Also create combined summary plot (throughput comparison)
    if len(benchmarks) > 1:
        generate_combined_plot(benchmarks, output_dir)


def generate_combined_plot(benchmarks: dict, output_dir: Path) -> None:
    """Generate combined throughput comparison plot."""
    if not HAS_MATPLOTLIB:
        return
    
    # Get latest result for each benchmark
    latest = {}
    for name, results in benchmarks.items():
        if results:
            latest[name] = results[-1]
    
    if not latest:
        return
    
    names = list(latest.keys())
    throughputs = [latest[n]["results"]["throughput_relics_per_sec"] for n in names]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, throughputs, color=['#2563eb', '#16a34a', '#8b5cf6', '#f59e0b', '#dc2626', '#0891b2'])
    ax.set_ylabel("Throughput (ops/sec)")
    ax.set_title("Benchmark Comparison (Latest Results)")
    ax.set_xticklabels([n.upper() for n in names], rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, val in zip(bars, throughputs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / "comparison.png", dpi=150, bbox_inches='tight')
    print(f"✅ Comparison plot saved to: {output_dir / 'comparison.png'}")


def generate_summary(results: list[dict], output_dir: Path) -> None:
    """Generate markdown summary."""
    if not results:
        return
    
    # Group by benchmark type
    benchmarks = {}
    for r in results:
        bench_name = r.get("benchmark", "unknown")
        if bench_name not in benchmarks:
            benchmarks[bench_name] = []
        benchmarks[bench_name].append(r)
    
    # Get latest timestamp
    latest_ts = "N/A"
    for r in results:
        ts = r.get("metadata", {}).get("timestamp", "")
        if ts:
            latest_ts = ts
    
    summary = f"""# 📊 Benchmark Suite Summary

Generated: {datetime.now().isoformat()}
Last Run: {latest_ts}

## Latest Results

| Benchmark | Throughput | Success Rate | P95 Latency |
|-----------|------------|--------------|-------------|
"""
    
    for name in ["create", "read", "search", "spaces", "social", "mixed"]:
        if name not in benchmarks:
            continue
        latest = benchmarks[name][-1]
        tp = latest["results"]["throughput_relics_per_sec"]
        sr = latest["results"].get("success_rate", 100)
        p95 = latest["results"]["latency_ms"]["p95"]
        summary += f"| {name.upper()} | {tp:.1f} ops/sec | {sr:.1f}% | {p95:.2f}ms |\n"
    
    # Add trends info
    summary += f"""
## Trends

Total runs analyzed: {len(results)}

See individual plots for each benchmark:
"""
    
    for name in benchmarks.keys():
        summary += f"- `{name}_trends.png` - {name.upper()} throughput and latency over time\n"
    
    summary += "\nSee `comparison.png` for side-by-side benchmark comparison.\n"
    
    with open(output_dir / "SUMMARY.md", 'w') as f:
        f.write(summary)
    print(f"✅ Summary saved to: {output_dir / 'SUMMARY.md'}")
    
    # Print summary to stdout
    print("\n" + "=" * 50)
    print("📈 BENCHMARK SUITE SUMMARY")
    print("=" * 50)
    for name in ["create", "read", "search", "spaces", "social", "mixed"]:
        if name not in benchmarks:
            continue
        latest = benchmarks[name][-1]
        tp = latest["results"]["throughput_relics_per_sec"]
        p95 = latest["results"]["latency_ms"]["p95"]
        print(f"   {name.upper()}: {tp:.1f} ops/sec, P95: {p95:.2f}ms")
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
