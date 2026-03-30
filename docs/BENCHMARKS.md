# 🔬 Benchmarking Guide

Simple benchmarking for relic creation performance. Results stored as GitHub artifacts for 90 days.

## Quick Start

### Run Locally
```bash
python3 scripts/benchmark_relics.py \
  --count 1000 \
  --workers 5 \
  --url http://localhost \
  --client-key YOUR_KEY
```

### Run via GitHub Actions
Go to **Actions** → **Benchmark - Relic Creation** → **Run workflow**

Optional parameters:
- `relic_count`: default 1000
- `workers`: default 5

## Scripts

### `scripts/benchmark_relics.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--count` | 1000 | Number of relics |
| `--workers` | 5 | Concurrent workers |
| `--url` | http://localhost | Base URL |
| `--client-key` | (required) | Auth key |
| `--output` | none | Output JSON file |

### `scripts/analyze_benchmarks.py`

Analyze historical results and generate plots.

```bash
# Download artifact from GitHub
gh run download <run-id> --dir benchmark-results/

# Analyze
python3 scripts/analyze_benchmarks.py \
  --input benchmark-results/ \
  --output trends/
```

Requires: `pip install matplotlib`

## Metrics

- **Throughput**: relics/sec
- **Latency**: min, max, avg, P50, P90, P95, P99
- **Success Rate**: %

## Viewing Results

### GitHub Actions Summary
Each workflow run displays a markdown table with key metrics.

### Download Artifacts
1. Go to the workflow run
2. Click **benchmark-{sha}** artifact
3. Extract and view `results.json`

### Local Analysis
```bash
# Download all artifacts for a repo
gh run list --limit 20 --json databaseId --jq '.[].databaseId' | while read id; do
  gh run download "$id" --dir "benchmarks/$id"
done

# Generate trends
python3 scripts/analyze_benchmarks.py --input benchmarks/ --output trends/
```

## Results Structure

```
benchmark-results/
├── results.json    # Full metrics
└── (uploaded as artifact, retained 90 days)
```

## Example Output

```
📊 BENCHMARK RESULTS
------------------------------------------------------------
   Total requested:     1000
   Successful:          998
   Failed:              2
   Success rate:        99.8%
   Duration:            45.23s
   Throughput:          22.06 relics/sec

   Latency (ms):
      MIN: 12.34
      MAX: 892.45
      AVG: 45.67
      P50: 38.21
      P90: 78.43
      P95: 125.67
      P99: 345.21
```
