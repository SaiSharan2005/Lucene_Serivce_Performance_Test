"""
Configuration for Lucene Search Service Benchmarking
"""

# API Endpoints
BASE_URL = "http://localhost:8080"
SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/search"
STATS_ENDPOINT = f"{BASE_URL}/api/v1/search/chunk-stats"
INGEST_ENDPOINT = f"{BASE_URL}/api/v1/ingest/pdf"

# Benchmark parameters
RUNS_PER_QUERY = 20
WARMUP_RUNS = 2  # Discard first 2 runs per query during stats calculation
WARMUP_QUERIES = 40  # Warmup queries before benchmark (JVM JIT + cache)
TOP_K_VALUES = [1, 5, 10, 20, 50]
PDF_COUNTS = [100, 200, 400, 800, 1082]

# Concurrency testing (optional, disabled by default)
ENABLE_CONCURRENCY_TEST = False
CONCURRENCY_LEVELS = [1, 5, 10]
CONCURRENCY_QUERIES_PER_LEVEL = 100

# Paths
LUCENE_INDEX_PATH = "../lucene-service/lucene-index"
PDF_SOURCE_PATH = "../Research-Paper-Downloder/data/arxiv/cs_ai/pdfs"

# Random seed for reproducibility
RANDOM_SEED = 42

# Results directory
RESULTS_DIR = "results"
