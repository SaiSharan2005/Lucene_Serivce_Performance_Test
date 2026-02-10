# Lucene Search Service - Benchmark Suite

A comprehensive benchmarking system to measure Lucene search performance across different index sizes with latency measurements, statistical analysis, and CSV output for graphing.

## Prerequisites

1. **Lucene Service Running** - The Java service must be running on port 8080
2. **PDF Source** - PDFs should be in `Research-Paper-Downloder/data/arxiv/cs_ai/pdfs/`
3. **Python 3.8+** - With pip installed

## Installation

```bash
cd api-test
pip install -r requirements.txt
```

Dependencies: `requests`, `pandas`, `numpy`, `plotly`

## Starting the Lucene Server

In a separate terminal:

```bash
cd lucene-service
mvn spring-boot:run
```

Wait until you see the server is ready (usually takes 10-20 seconds).

## Verify Server is Running

```bash
curl http://localhost:8080/api/v1/search/chunk-stats
```

You should see JSON with chunk/token counts.

---

## Test Options

### Option A: Quick Test (5 queries, 5 runs)

```bash
cd api-test
python benchmark.py --queries 5 --runs 5 --pdf-count 100
```

This takes ~30 seconds and produces a quick sample.

### Option B: Single Index Size Benchmark

```bash
cd api-test
python run_full_benchmark.py --pdf-count 100 --skip-ingest
```

This benchmarks the existing index (2000 API calls, ~1 minute).

### Option C: Full Benchmark Suite (All Sizes)

```bash
cd api-test
python run_full_benchmark.py
```

This runs the complete suite:
- Clears index, ingests 100 PDFs, benchmarks
- Clears index, ingests 200 PDFs, benchmarks
- Repeats for 400, 800, 1082 PDFs
- **Takes ~1 hour total**

### Option D: Custom PDF Counts

```bash
python run_full_benchmark.py --pdf-counts "100,200,400"
```

---

## Command Line Options

### benchmark.py

| Flag | Description |
|------|-------------|
| `--pdf-count N` | Label for the PDF count (for CSV naming) |
| `--queries N` | Number of queries to test (max 20) |
| `--runs N` | Runs per query (default 20) |
| `--no-warmup` | Skip 40 warmup queries |
| `--concurrency` | Enable concurrency testing |

### run_full_benchmark.py

| Flag | Description |
|------|-------------|
| `--pdf-count N` | Benchmark single index size |
| `--pdf-counts "100,200"` | Benchmark specific sizes (comma-separated) |
| `--skip-ingest` | Use existing index (don't ingest PDFs) |
| `--skip-clear` | Don't clear index between runs |

### ingest_pdfs.py

```bash
python ingest_pdfs.py 100                    # Ingest 100 PDFs
python ingest_pdfs.py 500 --source /path/to/pdfs  # Custom source
python ingest_pdfs.py 100 --continue-on-error     # Don't stop on failures
```

### visualize.py

```bash
python visualize.py                          # Generate interactive dashboard
```

Opens `results/dashboard.html` in your default browser with charts, filters, and stats.

---

## Output Files

After running, check `api-test/results/`:

```
results/
├── benchmark_100_pdfs.csv    # Raw data: 2000 rows per file
├── benchmark_200_pdfs.csv
├── benchmark_400_pdfs.csv
├── benchmark_800_pdfs.csv
├── benchmark_1082_pdfs.csv
├── summary.csv               # Aggregated stats for graphing
└── dashboard.html            # Interactive visualization dashboard
```

### Per-Query CSV Columns

| Column | Description |
|--------|-------------|
| `timestamp` | ISO timestamp of the query |
| `query` | The search query text |
| `run` | Run number (1-20) |
| `top_k` | TopK parameter used |
| `api_latency_ms` | Client-measured latency |
| `lucene_latency_ms` | Server-reported search time |
| `total_hits` | Number of matching chunks |
| `success` | Whether the query succeeded |

### Summary CSV Columns

| Column | Description |
|--------|-------------|
| `pdf_count` | Number of PDFs indexed |
| `chunk_count` | Total chunks in index |
| `token_count` | Total tokens in index |
| `index_size_mb` | Size of lucene-index directory |
| `avg_tokens_per_chunk` | Average chunk size |
| `queries_tested` | Number of unique queries |
| `runs_per_query` | Runs per query |
| `valid_runs` | Runs used for stats (excludes warmup) |
| `total_api_calls` | Total API calls made |
| `avg_latency_ms` | Average latency |
| `min_latency_ms` | Minimum latency |
| `max_latency_ms` | Maximum latency |
| `p50_latency_ms` | Median (50th percentile) |
| `p95_latency_ms` | 95th percentile |
| `p99_latency_ms` | 99th percentile |
| `std_dev_ms` | Standard deviation |
| `total_time_sec` | Total benchmark time |
| `throughput_qps` | Queries per second |

---

## Quick Start Example

```bash
# Terminal 1: Start server
cd lucene-service
mvn spring-boot:run

# Terminal 2: Run quick benchmark
cd api-test
python benchmark.py --queries 3 --runs 5 --no-warmup --pdf-count 100

# Check results
head -20 results/benchmark_100_pdfs.csv
```

This runs 75 API calls (3 queries × 5 runs × 5 topK values) in about 10 seconds.

---

## Benchmark Parameters

| Parameter | Default Value |
|-----------|---------------|
| Queries | 20 |
| Runs per query | 20 |
| Warmup runs (discarded) | 2 per query |
| Warmup queries | 40 (before benchmark) |
| TopK values | [1, 5, 10, 20, 50] |
| Total API calls per size | 2000 |
| Valid runs for stats | 1800 |

---

## Test Queries

The benchmark uses 20 realistic AI/ML research queries:

1. attention mechanism in transformers
2. neural network architecture
3. deep learning optimization
4. natural language processing
5. reinforcement learning algorithms
6. computer vision techniques
7. gradient descent convergence
8. convolutional neural network
9. recurrent neural network LSTM
10. generative adversarial network
11. transfer learning pretrained models
12. bert language model
13. graph neural network
14. self-supervised learning
15. multi-task learning
16. federated learning privacy
17. neural machine translation
18. object detection YOLO
19. semantic segmentation
20. knowledge distillation

---

## Sample Results

| PDFs | Chunks | Tokens | Size (MB) | Avg (ms) | P50 (ms) | P95 (ms) | QPS |
|------|--------|--------|-----------|----------|----------|----------|-----|
| 100 | 2,906 | 1.1M | 6.81 | 19.20 | 15.84 | 41.91 | 45.74 |
| 200 | 8,810 | 3.4M | 19.87 | 22.25 | 18.78 | 44.55 | 39.53 |
| 400 | 20,532 | 7.9M | 45.39 | 22.35 | 19.70 | 43.41 | 39.10 |
| 800 | 44,086 | 16.9M | 96.30 | 16.03 | 12.94 | 36.63 | 54.56 |
| 1082 | 76,154 | 29.2M | 168.70 | 16.98 | 13.97 | 32.94 | 50.85 |

---

## Configuration

Edit `config.py` to customize:

```python
# API Endpoints
BASE_URL = "http://localhost:8080"

# Benchmark parameters
RUNS_PER_QUERY = 20
WARMUP_RUNS = 2
WARMUP_QUERIES = 40
TOP_K_VALUES = [1, 5, 10, 20, 50]
PDF_COUNTS = [100, 200, 400, 800, 1082]

# Paths
LUCENE_INDEX_PATH = "../lucene-service/lucene-index"
PDF_SOURCE_PATH = "../Research-Paper-Downloder/data/arxiv/cs_ai/pdfs"

# Optional: Enable concurrency testing
ENABLE_CONCURRENCY_TEST = False
CONCURRENCY_LEVELS = [1, 5, 10]
```

---

## Troubleshooting

### Server not responding

```bash
# Check if server is running
curl http://localhost:8080/api/v1/search/chunk-stats

# If not, restart it
cd lucene-service
mvn spring-boot:run
```

### No PDFs found

```bash
# Check PDF source directory
ls ../Research-Paper-Downloder/data/arxiv/cs_ai/pdfs/*.pdf | wc -l
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Index errors after clearing

If the server returns 500 errors after clearing the index, restart the server:

```bash
# Kill existing Java processes and restart
taskkill //F //IM java.exe   # Windows
pkill -f java                 # Linux/Mac

cd lucene-service
mvn spring-boot:run
```

---

## Interactive Dashboard

Generate an interactive visualization dashboard from your benchmark results:

```bash
cd api-test
python visualize.py
```

This opens `results/dashboard.html` in your browser with:

### Charts Included

| Chart | Description |
|-------|-------------|
| Latency Percentiles | Line chart showing Avg/P50/P95/P99 across index sizes |
| Throughput | Bar chart of QPS by index size |
| Latency Distribution | Box plot showing spread and outliers |
| TopK Impact | How result count affects latency |
| All Data Points | Scatter plot of all 9,000+ API calls |
| Index Growth | Chunks and size scaling |
| Latency Histogram | Stacked frequency distribution by PDF count |
| Query Heatmap | Average latency by query and TopK value |

### Filters

The dashboard includes interactive filters:

- **PDF Count** - Filter by index size (100, 200, 400, 800, 1082)
- **TopK Value** - Filter by result count (1, 5, 10, 20, 50)
- **Query** - Filter by specific search query

### Stats Display

**Dynamic Stats** (update with filters):
- API Calls count
- Avg/P50/P95/Min/Max Latency

**Overall Stats** (fixed - entire dataset):
- Total Records
- Max Chunks / Tokens / Index Size
- Average QPS

### Dashboard Screenshot

When "All" is selected, shows overall stats with green badge.
When filtered, shows filtered stats with orange badge indicating active filters.
