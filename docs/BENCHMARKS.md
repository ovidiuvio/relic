# 🔬 Benchmark Suite

Comprehensive benchmark suite for Relic performance testing.

## Benchmarks

| Benchmark | Description | Operations |
|-----------|-------------|------------|
| **create** | Create relics | POST /api/v1/relics |
| **read** | Fetch relic content/metadata | GET /{id}/raw, GET /api/v1/relics/{id} |
| **search** | Search and filter | GET /api/v1/relics?search=, ?tag=, ?sort_by= |
| **spaces** | Space operations | GET /api/v1/spaces, /spaces/{id}/relics |
| **social** | Social features | GET /bookmarks/check, /comments, /lineage |
| **mixed** | Realistic workload | 50% read, 20% search, 15% social, 10% spaces, 5% write |

## Quick Start

### Run All Benchmarks
```bash
python3 scripts/run_all_benchmarks.py \
  --client-key YOUR_KEY \
  --url http://localhost \
  --iterations 5 \
  --workers 5 \
  --operations 100
```

### Run Create Benchmark Only
```bash
python3 scripts/benchmark_relics.py \
  --count 1000 \
  --workers 5 \
  --client-key YOUR_KEY
```

## GitHub Actions

The `benchmark-suite.yml` workflow runs automatically on pushes to `main`.

**Configuration:**
- Seeds 500 relics before running
- Runs 5 iterations per benchmark
- 100 operations per iteration
- 5 concurrent workers
- Create benchmark: 5 iterations × 1000 relics

**Outputs:**
- Workflow summary with all benchmark results
- Artifact: `benchmark-{sha}` (90 days)
- Artifact: `benchmark-history` (90 days)
- Trend plots and comparison charts

## Output Format

```json
{
  "create": {
    "name": "create",
    "iterations": 5,
    "median": {
      "operations_per_second": 130.5,
      "latency_ms": {"p95": 51.2}
    }
  },
  "read": {
    "name": "read",
    "iterations": 5,
    "median": {
      "operations_per_second": 450.2,
      "success_rate": 100,
      "latency_ms": {
        "p50": 12.5,
        "p95": 28.3,
        "p99": 45.1
      }
    }
  },
  "_metadata": {
    "git_hash": "abc1234",
    "configuration": {...}
  }
}
```

## Analyze Trends

```bash
# Download artifacts
gh run download <run-id> --dir benchmarks/

# Generate trends
python3 scripts/analyze_benchmarks.py \
  --input benchmarks/ \
  --output trends/

# View plots
open trends/comparison.png
```

## Benchmark Details

### Create
- Creates 1000 relics per iteration
- Measures throughput (relics/sec)
- Tracks latency percentiles
- Uses async httpx with configurable workers

### Read
- Randomly fetches relic content or metadata
- Uses pre-seeded relic IDs
- Handles 404/410 gracefully (expired relics)

### Search
- Tests search by text
- Tests filter by tag
- Tests pagination
- Tests sorting (created_at, name, access_count)

### Spaces
- Lists spaces
- Gets space details
- Lists space relics

### Social
- Checks bookmark status
- Fetches comments
- Fetches fork lineage
- Fetches bookmarker list

### Mixed
- Weighted distribution of all operations
- Simulates real-world usage patterns
- Best indicator of overall system performance

## Configuration Options

| Flag | Default | Description |
|------|---------|-------------|
| `--iterations` | 5 | Runs per benchmark |
| `--workers` | 5 | Concurrent connections |
| `--operations` | 100 | Ops per iteration |
| `--relic-count` | 100 | Relic IDs to fetch |
| `--space-count` | 50 | Space IDs to fetch |
| `--output` | - | JSON output file |

## Interpreting Results

**Throughput (ops/sec)**: Higher is better
- Create: ~100-200 relics/sec expected
- Read: ~400-800 ops/sec expected
- Mixed: ~200-400 ops/sec expected

**P95 Latency (ms)**: Lower is better
- < 50ms: Excellent
- 50-100ms: Good
- 100-200ms: Acceptable
- > 200ms: Needs investigation

**Success Rate (%)**: Should be > 99%
- < 95%: Investigate errors
- 95-99%: Monitor
- > 99%: Healthy

## Troubleshooting

**Low throughput**: 
- Check database connection pool
- Increase worker count
- Check for locks/contention

**High latency**:
- Check storage performance (MinIO)
- Monitor database query times
- Check network latency

**High failure rate**:
- Check backend logs
- Verify database connections
- Check storage availability
