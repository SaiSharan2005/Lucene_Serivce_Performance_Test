"""
Main benchmarking script for Lucene Search Service
"""

import time
import random
import logging
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import numpy as np

from config import (
    SEARCH_ENDPOINT, STATS_ENDPOINT, LUCENE_INDEX_PATH,
    RUNS_PER_QUERY, WARMUP_RUNS, WARMUP_QUERIES, TOP_K_VALUES,
    RANDOM_SEED, RESULTS_DIR, ENABLE_CONCURRENCY_TEST,
    CONCURRENCY_LEVELS, CONCURRENCY_QUERIES_PER_LEVEL
)
from queries import QUERIES, WARMUP_QUERY_SET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def log_config():
    """Log all configuration parameters at start."""
    logger.info("=" * 60)
    logger.info("Benchmark Configuration")
    logger.info("=" * 60)
    logger.info(f"Search Endpoint: {SEARCH_ENDPOINT}")
    logger.info(f"Queries: {len(QUERIES)}")
    logger.info(f"Runs per query: {RUNS_PER_QUERY}")
    logger.info(f"Warmup runs (discarded): {WARMUP_RUNS}")
    logger.info(f"Warmup queries: {WARMUP_QUERIES}")
    logger.info(f"TopK values: {TOP_K_VALUES}")
    logger.info(f"Random seed: {RANDOM_SEED}")
    logger.info(f"Concurrency test enabled: {ENABLE_CONCURRENCY_TEST}")
    logger.info("=" * 60)


def get_index_stats() -> Dict:
    """Get chunk/token counts from API."""
    try:
        response = requests.get(STATS_ENDPOINT, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get index stats: {e}")
        return {}


def get_index_size_mb() -> float:
    """Measure lucene-index directory size in MB."""
    index_path = Path(LUCENE_INDEX_PATH)
    if not index_path.exists():
        logger.warning(f"Index path does not exist: {index_path}")
        return 0.0

    total_size = 0
    for file in index_path.rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size

    return total_size / (1024 * 1024)  # Convert to MB


def run_single_query(query: str, top_k: int) -> Dict:
    """
    Execute one search, return latencies and results.

    Returns:
        Dict with api_latency_ms, lucene_latency_ms, total_hits
    """
    params = {
        "q": query,
        "topK": top_k
    }

    start = time.perf_counter()
    try:
        response = requests.get(SEARCH_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        end = time.perf_counter()

        api_latency_ms = (end - start) * 1000
        data = response.json()

        lucene_latency_ms = data.get("searchTimeMs")
        if lucene_latency_ms is None:
            logger.warning(f"searchTimeMs missing in response for query: {query}")
            lucene_latency_ms = -1

        total_hits = data.get("totalHits", 0)

        return {
            "api_latency_ms": api_latency_ms,
            "lucene_latency_ms": lucene_latency_ms,
            "total_hits": total_hits,
            "success": True
        }
    except requests.RequestException as e:
        end = time.perf_counter()
        api_latency_ms = (end - start) * 1000
        logger.error(f"Query failed: {query} - {e}")
        return {
            "api_latency_ms": api_latency_ms,
            "lucene_latency_ms": -1,
            "total_hits": 0,
            "success": False
        }


def warmup_search(n: int = WARMUP_QUERIES) -> None:
    """Run warmup queries to stabilize JVM JIT + cache."""
    logger.info("Warmup started")

    warmup_queries = []
    while len(warmup_queries) < n:
        warmup_queries.extend(WARMUP_QUERY_SET)
    warmup_queries = warmup_queries[:n]

    for i, query in enumerate(warmup_queries):
        top_k = random.choice(TOP_K_VALUES)
        run_single_query(query, top_k)
        if (i + 1) % 10 == 0:
            logger.info(f"Warmup progress: {i + 1}/{n}")

    logger.info("Warmup finished")


def benchmark_query(query: str, runs: int, top_k: int) -> List[Dict]:
    """
    Run query N times, return all results.
    First 2 runs will be discarded during stats calculation, but logged.
    """
    results = []
    for run in range(1, runs + 1):
        result = run_single_query(query, top_k)
        result["run"] = run
        result["query"] = query
        result["top_k"] = top_k
        result["timestamp"] = datetime.now().isoformat()
        results.append(result)
    return results


def benchmark_all_queries(
    queries: List[str],
    runs_per_query: int = RUNS_PER_QUERY,
    top_k_values: List[int] = TOP_K_VALUES,
    shuffle: bool = True
) -> Tuple[List[Dict], float]:
    """
    Benchmark all queries with all topK values.

    Returns:
        Tuple of (results list, total_elapsed_time in seconds)
    """
    logger.info("Benchmark started")

    if shuffle:
        random.seed(RANDOM_SEED)
        queries = random.sample(queries, len(queries))
        logger.info(f"Queries shuffled with seed {RANDOM_SEED}")

    all_results = []
    total_queries = len(queries) * len(top_k_values)
    current = 0

    benchmark_start = time.perf_counter()

    for top_k in top_k_values:
        for query in queries:
            results = benchmark_query(query, runs_per_query, top_k)
            all_results.extend(results)
            current += 1
            if current % 10 == 0:
                logger.info(f"Progress: {current}/{total_queries} query-topK combinations")

    benchmark_end = time.perf_counter()
    total_elapsed_time = benchmark_end - benchmark_start

    logger.info("Benchmark finished")
    logger.info(f"Total API calls: {len(all_results)}")
    logger.info(f"Total elapsed time: {total_elapsed_time:.2f} seconds")

    return all_results, total_elapsed_time


def calculate_statistics(results: List[Dict], warmup_runs: int = WARMUP_RUNS) -> Dict:
    """
    Calculate min/max/avg/p50/p95/p99/std_dev from results.
    Discards first `warmup_runs` runs per query-topK combination.
    """
    df = pd.DataFrame(results)

    # Filter out warmup runs (first N runs per query-topK combination)
    df_valid = df[df['run'] > warmup_runs].copy()

    if df_valid.empty:
        logger.warning("No valid results after discarding warmup runs")
        return {}

    # Only consider successful queries
    df_valid = df_valid[df_valid['success'] == True]

    if df_valid.empty:
        logger.warning("No successful queries found")
        return {}

    latencies = df_valid['api_latency_ms'].values
    lucene_latencies = df_valid[df_valid['lucene_latency_ms'] >= 0]['lucene_latency_ms'].values

    stats = {
        "valid_runs": len(latencies),
        "min_latency_ms": float(np.min(latencies)),
        "max_latency_ms": float(np.max(latencies)),
        "avg_latency_ms": float(np.mean(latencies)),
        "p50_latency_ms": float(np.percentile(latencies, 50)),
        "p95_latency_ms": float(np.percentile(latencies, 95)),
        "p99_latency_ms": float(np.percentile(latencies, 99)),
        "std_dev_ms": float(np.std(latencies)),
    }

    if len(lucene_latencies) > 0:
        stats["lucene_avg_latency_ms"] = float(np.mean(lucene_latencies))
        stats["lucene_p50_latency_ms"] = float(np.percentile(lucene_latencies, 50))
        stats["lucene_p95_latency_ms"] = float(np.percentile(lucene_latencies, 95))

    return stats


def calculate_throughput(total_requests: int, total_elapsed_time: float) -> float:
    """
    Compute QPS correctly: total_requests / total_elapsed_time
    NOT: 1000 / avg_latency_ms
    """
    if total_elapsed_time <= 0:
        return 0.0
    return total_requests / total_elapsed_time


def save_results_csv(results: List[Dict], pdf_count: int, results_dir: str = RESULTS_DIR) -> str:
    """Save raw results to CSV."""
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(results)

    # Reorder columns
    columns = ['timestamp', 'query', 'run', 'top_k', 'api_latency_ms',
               'lucene_latency_ms', 'total_hits', 'success']
    df = df[[c for c in columns if c in df.columns]]

    filename = f"benchmark_{pdf_count}_pdfs.csv"
    filepath = Path(results_dir) / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Results saved to {filepath}")
    return str(filepath)


def run_concurrency_benchmark(
    queries: List[str],
    concurrency_level: int,
    num_queries: int = CONCURRENCY_QUERIES_PER_LEVEL,
    top_k: int = 10
) -> Dict:
    """
    Thread pool benchmark for concurrency testing.

    Returns:
        Dict with avg_latency_ms, p95_latency_ms, throughput_qps
    """
    # Prepare query list
    query_list = []
    while len(query_list) < num_queries:
        query_list.extend(queries)
    query_list = query_list[:num_queries]
    random.shuffle(query_list)

    latencies = []

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency_level) as executor:
        futures = [executor.submit(run_single_query, q, top_k) for q in query_list]

        for future in as_completed(futures):
            result = future.result()
            if result['success']:
                latencies.append(result['api_latency_ms'])

    end_time = time.perf_counter()
    total_time = end_time - start_time

    if not latencies:
        return {
            "concurrency": concurrency_level,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "throughput_qps": 0
        }

    return {
        "concurrency": concurrency_level,
        "avg_latency_ms": float(np.mean(latencies)),
        "p95_latency_ms": float(np.percentile(latencies, 95)),
        "throughput_qps": len(latencies) / total_time
    }


def run_benchmark(
    pdf_count: int,
    queries: List[str] = QUERIES,
    runs_per_query: int = RUNS_PER_QUERY,
    top_k_values: List[int] = TOP_K_VALUES,
    results_dir: str = RESULTS_DIR,
    run_warmup: bool = True,
    run_concurrency: bool = ENABLE_CONCURRENCY_TEST
) -> Dict:
    """
    Run complete benchmark for a given PDF count.

    Returns:
        Summary statistics dict
    """
    log_config()

    # Get index stats
    logger.info("Fetching index statistics...")
    index_stats = get_index_stats()
    chunk_count = index_stats.get("totalChunks", 0)
    token_count = index_stats.get("totalTokens", 0)
    avg_tokens_per_chunk = index_stats.get("avgTokensPerChunk", 0)

    # Get index size
    index_size_mb = get_index_size_mb()

    logger.info(f"Index stats: {chunk_count} chunks, {token_count} tokens, {index_size_mb:.2f} MB")

    # Warmup
    if run_warmup:
        warmup_search(WARMUP_QUERIES)

    # Run benchmark
    results, total_elapsed_time = benchmark_all_queries(
        queries, runs_per_query, top_k_values
    )

    # Calculate statistics (excluding warmup runs)
    stats = calculate_statistics(results, WARMUP_RUNS)

    # Calculate throughput
    total_requests = stats.get("valid_runs", 0)
    throughput_qps = calculate_throughput(total_requests, total_elapsed_time)

    # Save raw results
    save_results_csv(results, pdf_count, results_dir)

    # Prepare summary
    summary = {
        "pdf_count": pdf_count,
        "chunk_count": chunk_count,
        "token_count": token_count,
        "index_size_mb": round(index_size_mb, 2),
        "avg_tokens_per_chunk": round(avg_tokens_per_chunk, 2),
        "queries_tested": len(queries),
        "runs_per_query": runs_per_query,
        "valid_runs": stats.get("valid_runs", 0),
        "total_api_calls": len(results),
        "avg_latency_ms": round(stats.get("avg_latency_ms", 0), 2),
        "min_latency_ms": round(stats.get("min_latency_ms", 0), 2),
        "max_latency_ms": round(stats.get("max_latency_ms", 0), 2),
        "p50_latency_ms": round(stats.get("p50_latency_ms", 0), 2),
        "p95_latency_ms": round(stats.get("p95_latency_ms", 0), 2),
        "p99_latency_ms": round(stats.get("p99_latency_ms", 0), 2),
        "std_dev_ms": round(stats.get("std_dev_ms", 0), 2),
        "total_time_sec": round(total_elapsed_time, 2),
        "throughput_qps": round(throughput_qps, 2)
    }

    # Concurrency benchmark (optional)
    concurrency_results = []
    if run_concurrency:
        logger.info("Running concurrency benchmark...")
        for level in CONCURRENCY_LEVELS:
            logger.info(f"Testing concurrency level: {level}")
            conc_result = run_concurrency_benchmark(queries, level)
            conc_result["pdf_count"] = pdf_count
            concurrency_results.append(conc_result)
        summary["concurrency_results"] = concurrency_results

    logger.info("=" * 60)
    logger.info("Benchmark Summary")
    logger.info("=" * 60)
    for key, value in summary.items():
        if key != "concurrency_results":
            logger.info(f"{key}: {value}")
    logger.info("=" * 60)

    return summary


def main():
    """Main entry point for standalone benchmark."""
    parser = argparse.ArgumentParser(description="Lucene Search Benchmark")
    parser.add_argument("--pdf-count", type=int, default=0,
                        help="Number of PDFs indexed (for labeling)")
    parser.add_argument("--queries", type=int, default=len(QUERIES),
                        help="Number of queries to test")
    parser.add_argument("--runs", type=int, default=RUNS_PER_QUERY,
                        help="Runs per query")
    parser.add_argument("--no-warmup", action="store_true",
                        help="Skip warmup queries")
    parser.add_argument("--concurrency", action="store_true",
                        help="Enable concurrency testing")

    args = parser.parse_args()

    queries = QUERIES[:args.queries]

    summary = run_benchmark(
        pdf_count=args.pdf_count,
        queries=queries,
        runs_per_query=args.runs,
        run_warmup=not args.no_warmup,
        run_concurrency=args.concurrency
    )

    return summary


if __name__ == "__main__":
    main()
