# API Test Suite

Testing and benchmarking tools for the Lucene Search Service. Includes an async ingestion test script and a comprehensive search performance benchmark suite.

## Directory Structure

```
api-test/
├── test_async_ingestion.py          # Async ingestion API test
├── lucene-pdf-performance/          # Search benchmark suite
│   ├── benchmark.py                 # Core benchmarking script
│   ├── run_full_benchmark.py        # Full suite orchestrator
│   ├── ingest_pdfs.py               # PDF ingestion helper
│   ├── visualize.py                 # Interactive dashboard generator
│   ├── config.py                    # Benchmark configuration
│   ├── queries.py                   # 20 test queries
│   ├── requirements.txt             # Python dependencies
│   ├── results/                     # Benchmark output (CSV + HTML)
│   └── README.md                    # Benchmark-specific docs
└── README.md
```

## Prerequisites

- **Python 3.8+**
- **Lucene Service running** on `http://localhost:8080`
- **PDF source**: `Research-Paper-Downloder/data/arxiv/cs_ai/pdfs/` (1082 arXiv papers)

## Install Dependencies

```bash
pip install requests
```

For the benchmark suite:
```bash
pip install -r lucene-pdf-performance/requirements.txt
```

---

## 1. Async Ingestion Test (`test_async_ingestion.py`)

Tests the async PDF ingestion API by uploading PDFs in a single API call, polling job status until completion, and optionally verifying the exported JSON.

### How It Works

1. For **<= 100 PDFs**: sends all in **one API call** (one server job, one export file)
2. For **> 100 PDFs**: auto-batches into 100-PDF chunks (one job per batch, one export per batch)
3. Polls `GET /api/v1/ingest/status/{jobId}` until `COMPLETED` or `FAILED`
4. Reports ingestion summary (docs, chunks, time, rate)
5. Optionally verifies the exported JSON structure

### Usage

```bash
cd api-test

# Quick smoke test (5 PDFs)
python test_async_ingestion.py

# 50 PDFs (single API call)
python test_async_ingestion.py --count 50

# Full dataset (auto-batched: 11 batches of 100)
python test_async_ingestion.py --count 1082

# Verify JSON export after ingestion
python test_async_ingestion.py --count 10 --verify-export

# Skip validation tests (404, invalid file)
python test_async_ingestion.py --count 50 --skip-validation-tests
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--count` | 5 | Number of PDFs to ingest |
| `--verify-export` | off | Validate the exported JSON structure after ingestion |
| `--skip-validation-tests` | off | Skip the 404 and invalid file validation tests |

### Tests Included

| Test | What It Checks |
|------|---------------|
| `status_404` | `GET /status/fake_id` returns 404 |
| `invalid_file` | Uploading a `.txt` file returns 400 |
| `single_file` | Upload 1 PDF, poll until COMPLETED |
| `ingestion` | Upload N PDFs in single call, poll until COMPLETED |

### Auto-Batching

| Count | Behavior |
|---|---|
| `--count 50` | 1 API call, 1 job, 1 export file |
| `--count 200` | 2 API calls (100+100), 2 jobs, 2 export files |
| `--count 1082` | 11 API calls (10x100 + 1x82), 11 jobs, 11 export files |

Each batch is <= 100 PDFs (~400 MB) to avoid HTTP upload timeouts. Each batch is still one server job producing one export JSON file.

### Sample Output

```
[INFO] Server is UP
[INFO] PASS - Got 404 for unknown jobId
[INFO] PASS - Got 400 for non-PDF file
[INFO] TEST: Ingest 50 PDFs (single API call)
[INFO] Uploading 50 PDFs (175.5 MB) in a single API call...
[INFO] Job submitted: job_1c98a739-737
[INFO]   [COMPLETED] docs: 50/50, chunks: 1443
[INFO]   Job finished in 40.7s
[INFO] ============================================================
[INFO] INGESTION SUMMARY
[INFO] ============================================================
[INFO] PDFs uploaded:     50
[INFO] Documents indexed: 50
[INFO] Total chunks:      1443
[INFO] Jobs completed:    1/1
[INFO] Export files:      1
[INFO] Total time:        40.7s
[INFO] Rate:              1.2 PDFs/sec
[INFO] ============================================================
[INFO] ALL TESTS PASSED
```

### Export Verification (`--verify-export`)

When enabled, validates the exported JSON file:
- Root is a JSON array
- Each chunk has: `id`, `document_id`, `content`, `metadata`
- Metadata has: `source`, `title`, `author`, `page_number`, `total_pages`, `chunk_index`, `chunk_position`, `token_count`, `created_at`
- Reports: total chunks, unique documents, total tokens, file size

---

## 2. Search Benchmark Suite (`lucene-pdf-performance/`)

Comprehensive benchmarking system measuring Lucene search latency across different index sizes.

See [lucene-pdf-performance/README.md](lucene-pdf-performance/README.md) for full documentation.

### Quick Start

```bash
cd api-test/lucene-pdf-performance

# Quick test (5 queries, 5 runs)
python benchmark.py --queries 5 --runs 5 --pdf-count 100

# Full benchmark suite (all index sizes)
python run_full_benchmark.py

# Generate interactive dashboard
python visualize.py
```

### What It Measures

- API latency (client-side, `time.perf_counter()`)
- Lucene latency (server-reported `searchTimeMs`)
- Throughput (QPS)
- Statistical analysis: min, max, avg, P50, P95, P99, std dev
- Across 5 TopK values: [1, 5, 10, 20, 50]
- Across 5 index sizes: [100, 200, 400, 800, 1082] PDFs

### Output

```
lucene-pdf-performance/results/
├── benchmark_100_pdfs.csv     # Raw data per index size
├── benchmark_200_pdfs.csv
├── benchmark_400_pdfs.csv
├── benchmark_800_pdfs.csv
├── benchmark_1082_pdfs.csv
├── summary.csv                # Aggregated stats for graphing
└── dashboard.html             # Interactive visualization
```

---

## Configuration

Both scripts use these defaults:

| Setting | Value |
|---------|-------|
| Server URL | `http://localhost:8080` |
| Ingest endpoint | `/api/v1/ingest/pdf` |
| Status endpoint | `/api/v1/ingest/status/{jobId}` |
| Search endpoint | `/api/v1/search` |
| PDF source | `../Research-Paper-Downloder/data/arxiv/cs_ai/pdfs` |
| Export path | `../lucene-service/chunk-exports` |

---

## Troubleshooting

### Server not responding
```bash
curl http://localhost:8080/api/v1/ingest/health
```
If no response, start the server:
```bash
cd lucene-service && mvn spring-boot:run
```

### No PDFs found
Ensure the PDF source directory exists:
```bash
ls ../Research-Paper-Downloder/data/arxiv/cs_ai/pdfs/*.pdf | head -5
```

### 413 Payload Too Large
The server's `max-request-size` is set to 5GB in `application.yml`. If you still hit this, check the config.

### Poll timeout
For large uploads (1000+ PDFs), the poll timeout is 30 minutes. If it still times out, check server logs for errors.
