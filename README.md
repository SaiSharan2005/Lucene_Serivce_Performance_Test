# 🔬 Lucene Service Performance Testing Suite

Complete testing and benchmarking tools for the Lucene Search Service.

**Two main test systems**:
1. **Async Ingestion Test** - Validate PDF upload & processing
2. **Performance Benchmark** - Measure latency, throughput, scalability

---

## 📁 Directory Structure

```
Lucene_Serivce_Performance_Test/
├── test_async_ingestion.py              ⭐ Ingestion API tests
├── README.md                            (this file)
│
└── lucene-pdf-performance/              Benchmark suite
    ├── benchmark.py                     Core benchmark script
    ├── run_full_benchmark.py            Full suite orchestrator
    ├── ingest_pdfs.py                   PDF ingestion helper
    ├── visualize.py                     Dashboard generator
    ├── config.py                        Configuration
    ├── queries.py                       20 AI/ML test queries
    ├── requirements.txt                 Dependencies
    ├── README.md                        Detailed docs
    └── results/                         Output (CSV + HTML)
```

---

## 🚀 Quick Start

### **Start Lucene Service**
```bash
cd lucene-service
mvn spring-boot:run
# Wait until server is ready (10-20 seconds)
```

### **Test 1: Ingestion (5 min)**
```bash
cd Lucene_Serivce_Performance_Test

# Install basic dependencies
pip install requests

# Quick smoke test (5 PDFs)
python test_async_ingestion.py

# Test with custom count (auto-batches if > 100)
python test_async_ingestion.py --count 50

# Full dataset (1,353 PDFs, auto-batched)
python test_async_ingestion.py --count 1353
```

### **Test 2: Benchmark (varies)**
```bash
# Install benchmark dependencies
pip install -r lucene-pdf-performance/requirements.txt

# Quick test (5 queries × 5 runs = 30 sec)
python lucene-pdf-performance/benchmark.py --queries 5 --runs 5 --pdf-count 100

# Single index size (2000 queries = 1 min)
python lucene-pdf-performance/run_full_benchmark.py --pdf-count 100 --skip-ingest

# Full suite (all sizes = 1 hour)
python lucene-pdf-performance/run_full_benchmark.py

# View interactive dashboard
python lucene-pdf-performance/visualize.py
```

---

## 📊 System 1: Async Ingestion Test

**File**: `test_async_ingestion.py`
**Purpose**: Validate PDF upload, processing, and JSON export

### What It Tests
✅ 404 error handling (unknown job IDs)
✅ 400 validation (non-PDF files)
✅ Single PDF ingestion
✅ Bulk PDF ingestion
✅ Auto-batching (max 100 PDFs per API call)
✅ Job status polling
✅ JSON export structure

### Usage

```bash
# Smoke test (5 PDFs, single API call)
python test_async_ingestion.py

# 50 PDFs (single API call)
python test_async_ingestion.py --count 50

# 1,353 PDFs (auto-batched into 14 API calls)
python test_async_ingestion.py --count 1353

# Verify exported JSON files
python test_async_ingestion.py --count 10 --verify-export

# Skip validation tests (404, invalid file)
python test_async_ingestion.py --count 50 --skip-validation-tests
```

### Auto-Batching Logic

| Count | Behavior |
|-------|----------|
| ≤100 | Single API call, 1 job, 1 export file |
| 200 | 2 API calls (100+100), 2 jobs, 2 export files |
| 1,353 | 14 API calls (13×100 + 1×53), 14 jobs, 14 export files |

Each batch is ~400 MB to avoid HTTP upload timeouts.

### Sample Output

```
[INFO] Server is UP
[INFO] PASS - Got 404 for unknown jobId
[INFO] PASS - Got 400 for non-PDF file
[INFO] TEST: Ingest 50 PDFs (single API call)
[INFO] Uploading 50 PDFs (175.5 MB) in a single API call...
[INFO] Job submitted: job_abc123
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
[INFO] ALL TESTS PASSED ✓
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--count` | 5 | Number of PDFs to ingest |
| `--verify-export` | off | Validate exported JSON structure |
| `--skip-validation-tests` | off | Skip 404 and invalid file tests |

---

## 📈 System 2: Performance Benchmark Suite

**Location**: `lucene-pdf-performance/`
**Purpose**: Comprehensive latency & throughput testing

### What It Measures

**Per Query**:
- API latency (client-side)
- Lucene latency (server-reported)
- Total hits
- Success/failure

**Statistical Analysis**:
- Min, max, avg latency
- P50 (median), P95, P99
- Standard deviation
- Throughput (QPS)

**Across Variables**:
- 5 TopK values: [1, 5, 10, 20, 50]
- 5 index sizes: [100, 200, 400, 800, 1,082] PDFs
- 20 AI/ML test queries
- 20 runs per query
- 2 warmup runs per query (discarded)
- 40 warmup queries before benchmark

### Sample Performance Results

| PDFs | Chunks | Avg (ms) | P50 (ms) | P95 (ms) | QPS |
|------|--------|----------|----------|----------|-----|
| 100 | 2,906 | 19.20 | 15.84 | 41.91 | 45.74 |
| 200 | 8,810 | 22.25 | 18.78 | 44.55 | 39.53 |
| 400 | 20,532 | 22.35 | 19.70 | 43.41 | 39.10 |
| 800 | 44,086 | 16.03 | 12.94 | 36.63 | 54.56 |
| 1,082 | 76,154 | 16.98 | 13.97 | 32.94 | 50.85 |

### Usage

```bash
# Quick test (5 queries × 5 runs = ~30 sec)
python lucene-pdf-performance/benchmark.py --queries 5 --runs 5 --pdf-count 100

# Single index size (100 PDFs, 2000 API calls = ~1 min)
python lucene-pdf-performance/run_full_benchmark.py --pdf-count 100 --skip-ingest

# Full suite (all 5 sizes, 10,000 API calls = ~1 hour)
python lucene-pdf-performance/run_full_benchmark.py

# Custom PDF counts
python lucene-pdf-performance/run_full_benchmark.py --pdf-counts "100,200,400"

# Generate dashboard
python lucene-pdf-performance/visualize.py
```

### benchmark.py Options

| Flag | Description |
|------|-------------|
| `--pdf-count N` | Label for PDF count (for CSV naming) |
| `--queries N` | Number of queries to test (max 20) |
| `--runs N` | Runs per query (default 20) |
| `--no-warmup` | Skip 40 warmup queries |
| `--concurrency` | Enable concurrency testing |

### run_full_benchmark.py Options

| Flag | Description |
|------|-------------|
| `--pdf-count N` | Benchmark single index size |
| `--pdf-counts "100,200"` | Benchmark specific sizes (comma-separated) |
| `--skip-ingest` | Use existing index (don't ingest) |
| `--skip-clear` | Don't clear index between runs |

### Test Queries (20 AI/ML Topics)

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

### Output Files

```
lucene-pdf-performance/results/
├── benchmark_100_pdfs.csv      Raw data (2,000 rows per file)
├── benchmark_200_pdfs.csv
├── benchmark_400_pdfs.csv
├── benchmark_800_pdfs.csv
├── benchmark_1082_pdfs.csv
├── summary.csv                 Aggregated stats per index size
└── dashboard.html              Interactive visualization
```

### CSV Columns

**Per-Query CSV**:
- `timestamp` - ISO timestamp
- `query` - Search text
- `run` - Run number
- `top_k` - TopK parameter
- `api_latency_ms` - Client latency
- `lucene_latency_ms` - Server latency
- `total_hits` - Matching chunks
- `success` - Query succeeded

**Summary CSV**:
- `pdf_count` - PDFs indexed
- `chunk_count` - Total chunks
- `token_count` - Total tokens
- `index_size_mb` - Lucene index size
- `avg_latency_ms` - Average API latency
- `p50_latency_ms` - Median latency
- `p95_latency_ms` - 95th percentile
- `p99_latency_ms` - 99th percentile
- `throughput_qps` - Queries per second

### Interactive Dashboard

```bash
python lucene-pdf-performance/visualize.py
# Opens: results/dashboard.html
```

**Charts**:
- Latency percentiles (Avg/P50/P95/P99)
- Throughput (QPS by index size)
- Latency distribution (box plot)
- TopK impact on latency
- All data points (9,000+ scatter plot)
- Index growth (chunks/size scaling)
- Latency histogram (by PDF count)
- Query heatmap (latency by query & TopK)

**Filters**:
- PDF Count (100, 200, 400, 800, 1,082)
- TopK Value (1, 5, 10, 20, 50)
- Query (all 20 test queries)

**Stats Display**:
- Dynamic stats (update with filters)
- Overall stats (entire dataset)

---

## ⚙️ Configuration

### Default Settings

**Endpoints**:
```
Server: http://localhost:8080
Ingest: /api/v1/ingest/pdf
Status: /api/v1/ingest/status/{jobId}
Search: /api/v1/search
```

**Paths**:
```
PDFs: ../Arxiv_Pdf_Feathcer/data/arxiv/cs_ai/pdfs
Index: ../lucene-service/lucene-index
Exports: ../lucene-service/chunk-exports
```

**Benchmark Parameters** (edit `config.py`):
```python
RUNS_PER_QUERY = 20
WARMUP_RUNS = 2 per query
WARMUP_QUERIES = 40
TOP_K_VALUES = [1, 5, 10, 20, 50]
PDF_COUNTS = [100, 200, 400, 800, 1082]
```

**Ingestion Parameters** (edit `test_async_ingestion.py`):
```python
BASE_URL = "http://localhost:8080"
PDF_SOURCE_PATH = "../Arxiv_Pdf_Feathcer/data/arxiv/cs_ai/pdfs"
BATCH_SIZE = 100  # Max PDFs per API call
POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 1800  # 30 minutes
```

---

## 🐛 Troubleshooting

### Server not responding
```bash
curl http://localhost:8080/api/v1/search/chunk-stats
```
If no response, restart the server:
```bash
cd lucene-service
mvn spring-boot:run
```

### No PDFs found
```bash
ls ../Arxiv_Pdf_Feathcer/data/arxiv/cs_ai/pdfs/*.pdf | wc -l
```
Ensure PDFs are downloaded in `Arxiv_Pdf_Feathcer/data/arxiv/cs_ai/pdfs/`

### 413 Payload Too Large
Server's `max-request-size` is 5GB. Ingestion tests auto-batch at 100 PDFs (~400 MB) to avoid this.

### Import errors
```bash
pip install --upgrade -r lucene-pdf-performance/requirements.txt
```

### Timeout on large uploads
For 1,000+ PDFs, poll timeout is 30 minutes. Increase `POLL_TIMEOUT_SEC` in `test_async_ingestion.py` if needed.

### Index errors after clearing
If server returns 500 errors, restart:
```bash
# Kill Java process
taskkill /F /IM java.exe   # Windows
pkill -f java              # Linux/Mac

# Restart server
cd lucene-service
mvn spring-boot:run
```

---

## 📋 Complete Workflow Example

```bash
# Terminal 1: Start service
cd lucene-service
mvn spring-boot:run

# Terminal 2: Run tests
cd Lucene_Serivce_Performance_Test
pip install requests

# Test 1: Ingestion (5 min)
python test_async_ingestion.py --count 100

# Test 2: Quick benchmark (30 sec)
pip install -r lucene-pdf-performance/requirements.txt
python lucene-pdf-performance/benchmark.py --queries 5 --runs 5 --pdf-count 100

# Test 3: View results
python lucene-pdf-performance/visualize.py
# Opens: lucene-pdf-performance/results/dashboard.html
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Smoke test (ingestion) | `python test_async_ingestion.py` |
| Full ingestion test | `python test_async_ingestion.py --count 1353` |
| Quick benchmark | `python lucene-pdf-performance/benchmark.py --queries 5 --runs 5 --pdf-count 100` |
| Full benchmark | `python lucene-pdf-performance/run_full_benchmark.py` |
| Generate dashboard | `python lucene-pdf-performance/visualize.py` |
| Check server health | `curl http://localhost:8080/api/v1/search/chunk-stats` |
| View results | Open `lucene-pdf-performance/results/dashboard.html` |

---

## ✅ Status

- ✓ Async ingestion testing (validated)
- ✓ Performance benchmarking (20 queries, all index sizes)
- ✓ Auto-batching (tested up to 1,353 PDFs)
- ✓ Interactive dashboard (charts, filters, stats)
- ✓ CSV export (for graphing)
- ✓ Statistical analysis (P50, P95, P99)
- ✓ Production-grade testing suite

**Ready to use!** 🚀
