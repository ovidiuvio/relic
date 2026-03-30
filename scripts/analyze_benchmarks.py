#!/usr/bin/env python3
"""
Analyze benchmark results and generate trend plots.

Usage:
    python3 scripts/analyze_benchmarks.py --input benchmark-results/ --output trends/
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  matplotlib not installed. Install with: pip install matplotlib")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("⚠️  plotly not installed. Install with: pip install plotly")


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
        labels, throughputs, p95_latencies = [], [], []

        for r in bench_results:
            if "results" not in r or "metadata" not in r:
                continue
            try:
                git_hash = r["metadata"].get("git_hash", "")
                if not git_hash or git_hash == "unknown":
                    continue
                labels.append(git_hash[:8])
                throughputs.append(r["results"]["throughput_relics_per_sec"])
                p95_latencies.append(r["results"]["latency_ms"]["p95"])
            except (KeyError, ValueError):
                continue

        if not labels:
            continue

        x = range(len(labels))

        # Create plot
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f"{bench_name.upper()} Benchmark Trends", fontsize=14, fontweight='bold')

        # Throughput
        ax1 = axes[0]
        ax1.plot(x, throughputs, marker='o', linestyle='-', color='#2563eb', linewidth=2)
        ax1.set_ylabel("Throughput (ops/sec)")
        ax1.set_title(f"Throughput (avg: {sum(throughputs)/len(throughputs):.1f} ops/s)")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(labels, rotation=45, ha='right', fontfamily='monospace', fontsize=9)
        ax1.grid(True, alpha=0.3)

        # P95 latency
        ax2 = axes[1]
        ax2.plot(x, p95_latencies, marker='^', linestyle='-', color='#dc2626', linewidth=2)
        ax2.set_ylabel("P95 Latency (ms)")
        ax2.set_xlabel("Commit")
        ax2.set_title(f"P95 Latency (avg: {sum(p95_latencies)/len(p95_latencies):.1f}ms)")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(labels, rotation=45, ha='right', fontfamily='monospace', fontsize=9)
        ax2.grid(True, alpha=0.3)

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


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse ISO format timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Handle various ISO formats
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def prepare_benchmark_data(bench_results: list[dict]) -> tuple[list, list, list, list, list]:
    """Prepare data for plotting: timestamps, git hashes, throughputs, latencies, success rates."""
    timestamps, git_hashes, throughputs, p95_latencies, success_rates = [], [], [], [], []
    
    for r in bench_results:
        if "results" not in r or "metadata" not in r:
            continue
        try:
            ts_str = r["metadata"].get("timestamp", "")
            ts = parse_timestamp(ts_str)
            if not ts:
                continue
                
            git_hash = r["metadata"].get("git_hash", "")
            if not git_hash or git_hash == "unknown":
                continue
                
            timestamps.append(ts)
            git_hashes.append(git_hash[:8])
            throughputs.append(r["results"]["throughput_relics_per_sec"])
            p95_latencies.append(r["results"]["latency_ms"]["p95"])
            success_rates.append(r["results"].get("success_rate", 100))
        except (KeyError, ValueError):
            continue
    
    # Sort by timestamp
    if timestamps:
        sorted_indices = sorted(range(len(timestamps)), key=lambda i: timestamps[i])
        timestamps = [timestamps[i] for i in sorted_indices]
        git_hashes = [git_hashes[i] for i in sorted_indices]
        throughputs = [throughputs[i] for i in sorted_indices]
        p95_latencies = [p95_latencies[i] for i in sorted_indices]
        success_rates = [success_rates[i] for i in sorted_indices]
    
    return timestamps, git_hashes, throughputs, p95_latencies, success_rates


def generate_html_report(results: list[dict], output_dir: Path) -> None:
    """Generate interactive HTML report with Plotly charts."""
    if not HAS_PLOTLY or not results:
        return

    # Group results by benchmark type
    benchmarks = {}
    for r in results:
        bench_name = r.get("benchmark", "unknown")
        if bench_name not in benchmarks:
            benchmarks[bench_name] = []
        benchmarks[bench_name].append(r)

    # Prepare HTML content
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '    <title>Benchmark Report</title>',
        '    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>',
        '    <style>',
        '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #f5f5f5; }',
        '        .container { max-width: 1400px; margin: 0 auto; }',
        '        h1 { color: #1f2937; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }',
        '        h2 { color: #374151; margin-top: 40px; }',
        '        .chart-container { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
        '        table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
        '        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }',
        '        th { background: #3b82f6; color: white; font-weight: 600; }',
        '        tr:hover { background: #f9fafb; }',
        '        .summary { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
        '    </style>',
        '</head>',
        '<body>',
        '    <div class="container">',
        '        <h1>📊 Benchmark Report</h1>',
        f'        <p class="summary">Generated: {datetime.now().isoformat()}</p>',
    ]

    # Add summary table
    html_parts.append('        <h2>Latest Results Summary</h2>')
    html_parts.append('        <table>')
    html_parts.append('            <thead><tr><th>Benchmark</th><th>Throughput</th><th>Success Rate</th><th>P95 Latency</th></tr></thead>')
    html_parts.append('            <tbody>')
    
    for name in ["create", "read", "search", "spaces", "social", "mixed"]:
        if name not in benchmarks:
            continue
        latest = benchmarks[name][-1]
        tp = latest["results"]["throughput_relics_per_sec"]
        sr = latest["results"].get("success_rate", 100)
        p95 = latest["results"]["latency_ms"]["p95"]
        html_parts.append(f'            <tr><td><strong>{name.upper()}</strong></td><td>{tp:.1f} ops/sec</td><td>{sr:.1f}%</td><td>{p95:.2f}ms</td></tr>')
    
    html_parts.append('            </tbody>')
    html_parts.append('        </table>')

    # Generate charts for each benchmark
    for bench_name, bench_results in benchmarks.items():
        timestamps, git_hashes, throughputs, p95_latencies, success_rates = prepare_benchmark_data(bench_results)
        
        if not timestamps:
            continue

        # Create time-series plot
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                f"Throughput (avg: {sum(throughputs)/len(throughputs):.1f} ops/s)",
                f"P95 Latency (avg: {sum(p95_latencies)/len(p95_latencies):.1f}ms)"
            ),
            row_heights=[0.55, 0.45]
        )

        # Throughput trace
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=throughputs,
            mode='lines+markers',
            name='Throughput',
            line=dict(color='#2563eb', width=2),
            marker=dict(size=8),
            customdata=list(zip(git_hashes, success_rates)),
            hovertemplate=(
                '<b>%{x|%Y-%m-%d %H:%M}</b><br>'
                'Throughput: %{y:.1f} ops/sec<br>'
                'Commit: %{customdata[0]}<br>'
                'Success Rate: %{customdata[1]:.1f}%<extra></extra>'
            )
        ), row=1, col=1)

        # P95 Latency trace
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=p95_latencies,
            mode='lines+markers',
            name='P95 Latency',
            line=dict(color='#dc2626', width=2),
            marker=dict(size=8),
            customdata=list(zip(git_hashes, success_rates)),
            hovertemplate=(
                '<b>%{x|%Y-%m-%d %H:%M}</b><br>'
                'P95: %{y:.2f}ms<br>'
                'Commit: %{customdata[0]}<br>'
                'Success Rate: %{customdata[1]:.1f}%<extra></extra>'
            )
        ), row=2, col=1)

        # Update layout
        fig.update_layout(
            height=600,
            showlegend=False,
            hovermode='x unified',
            xaxis2=dict(title='Time', showgrid=True),
            yaxis1=dict(title='Throughput (ops/sec)', showgrid=True),
            yaxis2=dict(title='P95 Latency (ms)', showgrid=True),
            template='plotly_white'
        )

        # Add commit annotations as vertical lines (only for small datasets to avoid clutter)
        if len(timestamps) <= 10:
            for i, (ts, git_hash) in enumerate(zip(timestamps, git_hashes)):
                fig.add_vline(
                    x=ts,
                    line=dict(color='#9ca3af', width=1, dash='dot'),
                    opacity=0.3,
                    row=1, col=1,
                    annotation_text=git_hash,
                    annotation_position='top'
                )
                fig.add_vline(
                    x=ts,
                    line=dict(color='#9ca3af', width=1, dash='dot'),
                    opacity=0.3,
                    row=2, col=1,
                )

        chart_html = fig.to_html(include_plotlyjs=False, full_html=False)
        html_parts.append(f'        <div class="chart-container">')
        html_parts.append(f'            <h2>{bench_name.upper()} Benchmark Trends</h2>')
        html_parts.append(f'            {chart_html}')
        html_parts.append(f'        </div>')

    # Add combined comparison chart
    if len(benchmarks) > 1:
        latest = {name: results[-1] for name, results in benchmarks.items() if results}
        
        if latest:
            names = list(latest.keys())
            throughputs = [latest[n]["results"]["throughput_relics_per_sec"] for n in names]
            colors = ['#2563eb', '#16a34a', '#8b5cf6', '#f59e0b', '#dc2626', '#0891b2']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=[n.upper() for n in names],
                    y=throughputs,
                    marker_color=colors[:len(names)],
                    text=[f'{v:.1f}' for v in throughputs],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Throughput: %{y:.1f} ops/sec<extra></extra>'
                )
            ])
            
            fig.update_layout(
                height=400,
                showlegend=False,
                xaxis=dict(title='Benchmark'),
                yaxis=dict(title='Throughput (ops/sec)'),
                template='plotly_white'
            )
            
            chart_html = fig.to_html(include_plotlyjs=False, full_html=False)
            html_parts.append(f'        <div class="chart-container">')
            html_parts.append(f'            <h2>Benchmark Comparison (Latest)</h2>')
            html_parts.append(f'            {chart_html}')
            html_parts.append(f'        </div>')

    # Close HTML
    html_parts.extend([
        '    </div>',
        '</body>',
        '</html>'
    ])

    # Write HTML file
    html_content = '\n'.join(html_parts)
    output_path = output_dir / "benchmark_report.html"
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"✅ HTML report saved to: {output_path}")


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
    summary += "\n**NEW:** See `benchmark_report.html` for interactive charts with time-scale visualization.\n"

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
    generate_html_report(results, output_dir)
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
