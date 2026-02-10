"""
Orchestrator for running full benchmark across all index sizes.

This script:
1. Clears the Lucene index
2. Ingests N PDFs
3. Runs benchmark
4. Repeats for each PDF count [100, 200, 400, 800, 1082]
5. Generates summary.csv
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd

from config import (
    PDF_COUNTS, LUCENE_INDEX_PATH, PDF_SOURCE_PATH, RESULTS_DIR,
    ENABLE_CONCURRENCY_TEST, CONCURRENCY_LEVELS, BASE_URL
)
from benchmark import run_benchmark, get_index_stats
from ingest_pdfs import ingest_pdfs, wait_for_server
from queries import QUERIES

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def clear_index(index_path: str = LUCENE_INDEX_PATH) -> bool:
    """
    Delete the Lucene index folder.

    Args:
        index_path: Path to the Lucene index directory

    Returns:
        True if successful, False otherwise
    """
    index_dir = Path(index_path)

    if not index_dir.exists():
        logger.info(f"Index directory does not exist: {index_dir}")
        return True

    try:
        logger.info(f"Clearing index at {index_dir}")
        shutil.rmtree(index_dir)
        logger.info("Index cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to clear index: {e}")
        return False


def check_server_running() -> bool:
    """Check if the Lucene server is running."""
    try:
        stats = get_index_stats()
        return True
    except Exception:
        return False


def restart_server(lucene_service_path: str = "../lucene-service") -> bool:
    """
    Restart the Lucene server.

    Args:
        lucene_service_path: Path to the lucene-service directory

    Returns:
        True if server restarted successfully, False otherwise
    """
    logger.info("Restarting Lucene server...")

    # Kill existing Java processes
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "//F", "//IM", "java.exe"],
                         capture_output=True, timeout=30)
        else:
            subprocess.run(["pkill", "-f", "lucene"],
                         capture_output=True, timeout=30)
        logger.info("Stopped existing server processes")
    except Exception as e:
        logger.warning(f"Could not stop existing processes: {e}")

    time.sleep(2)

    # Start server in background
    try:
        service_path = Path(lucene_service_path).resolve()
        logger.info(f"Starting server from {service_path}")

        if sys.platform == "win32":
            subprocess.Popen(
                ["mvn", "spring-boot:run", "-q"],
                cwd=str(service_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            subprocess.Popen(
                ["mvn", "spring-boot:run", "-q"],
                cwd=str(service_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        logger.info("Server process started, waiting for it to be ready...")

        # Wait for server to be ready
        for i in range(60):  # Wait up to 2 minutes
            time.sleep(2)
            try:
                response = requests.get(f"{BASE_URL}/api/v1/search/chunk-stats", timeout=5)
                if response.status_code == 200:
                    logger.info("Server is ready!")
                    return True
            except requests.RequestException:
                pass
            if (i + 1) % 10 == 0:
                logger.info(f"Still waiting for server... ({(i+1)*2}s)")

        logger.error("Server did not become ready in time")
        return False

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return False


def save_summary_csv(summaries: List[Dict], results_dir: str = RESULTS_DIR) -> str:
    """
    Save combined summary CSV for all benchmark runs.

    Args:
        summaries: List of summary dicts from each benchmark run
        results_dir: Output directory

    Returns:
        Path to the saved summary file
    """
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(summaries)

    # Reorder columns for summary.csv
    columns = [
        "pdf_count", "chunk_count", "token_count", "index_size_mb",
        "avg_tokens_per_chunk", "queries_tested", "runs_per_query",
        "valid_runs", "total_api_calls", "avg_latency_ms", "min_latency_ms",
        "max_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms",
        "std_dev_ms", "total_time_sec", "throughput_qps"
    ]
    df = df[[c for c in columns if c in df.columns]]

    filepath = Path(results_dir) / "summary.csv"
    df.to_csv(filepath, index=False)

    logger.info(f"Summary saved to {filepath}")
    return str(filepath)


def save_concurrency_csv(
    concurrency_results: List[Dict],
    results_dir: str = RESULTS_DIR
) -> str:
    """
    Save concurrency benchmark results to CSV.

    Args:
        concurrency_results: List of concurrency benchmark results
        results_dir: Output directory

    Returns:
        Path to the saved file
    """
    if not concurrency_results:
        return ""

    Path(results_dir).mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(concurrency_results)
    filepath = Path(results_dir) / "concurrency_benchmark.csv"
    df.to_csv(filepath, index=False)

    logger.info(f"Concurrency results saved to {filepath}")
    return str(filepath)


def run_full_benchmark(
    pdf_counts: List[int] = PDF_COUNTS,
    skip_ingest: bool = False,
    skip_clear: bool = False,
    server_auto_restart: bool = False
) -> List[Dict]:
    """
    Run the full benchmark suite across all index sizes.

    Args:
        pdf_counts: List of PDF counts to benchmark
        skip_ingest: Skip ingestion (use existing index)
        skip_clear: Skip clearing index between runs
        server_auto_restart: Attempt to restart server automatically

    Returns:
        List of summary dicts for each run
    """
    logger.info("=" * 60)
    logger.info("Starting Full Benchmark Suite")
    logger.info("=" * 60)
    logger.info(f"PDF counts to test: {pdf_counts}")
    logger.info(f"Results directory: {RESULTS_DIR}")
    logger.info("=" * 60)

    summaries = []
    all_concurrency_results = []

    for pdf_count in pdf_counts:
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"BENCHMARK RUN: {pdf_count} PDFs")
        logger.info("=" * 60)

        # Step 1: Clear index and restart server (unless skipped)
        if not skip_clear:
            logger.info("Step 1: Clearing index...")
            if not clear_index():
                logger.error("Failed to clear index. Aborting.")
                sys.exit(1)

            # Restart server after clearing index
            logger.info("Step 1b: Restarting server after index clear...")
            if not restart_server():
                logger.error("Failed to restart server. Aborting.")
                sys.exit(1)
        else:
            # Just check server is running
            if not check_server_running():
                logger.error("Server is not running. Please start the Lucene service first.")
                logger.error("Command: cd lucene-service && mvn spring-boot:run")
                sys.exit(1)

        # Step 3: Ingest PDFs
        if not skip_ingest:
            logger.info(f"Step 2: Ingesting {pdf_count} PDFs...")
            ingest_result = ingest_pdfs(pdf_count, PDF_SOURCE_PATH)

            if not ingest_result["success"]:
                logger.error(f"Ingestion failed for {pdf_count} PDFs")
                continue

            # Wait for index to stabilize
            time.sleep(2)

        # Step 4: Run benchmark
        logger.info(f"Step 3: Running benchmark for {pdf_count} PDFs...")
        summary = run_benchmark(
            pdf_count=pdf_count,
            run_warmup=True,
            run_concurrency=ENABLE_CONCURRENCY_TEST
        )

        summaries.append(summary)

        # Collect concurrency results if available
        if "concurrency_results" in summary:
            all_concurrency_results.extend(summary["concurrency_results"])

        logger.info(f"Completed benchmark for {pdf_count} PDFs")
        logger.info("")

    # Save combined summary
    logger.info("=" * 60)
    logger.info("Saving combined results...")
    logger.info("=" * 60)

    save_summary_csv(summaries)

    if all_concurrency_results:
        save_concurrency_csv(all_concurrency_results)

    # Print final summary table
    print_summary_table(summaries)

    return summaries


def print_summary_table(summaries: List[Dict]) -> None:
    """Print a formatted summary table to console."""
    logger.info("")
    logger.info("=" * 100)
    logger.info("BENCHMARK RESULTS SUMMARY")
    logger.info("=" * 100)

    # Header
    header = (
        f"{'PDFs':>6} | {'Chunks':>8} | {'Tokens':>10} | "
        f"{'Size(MB)':>9} | {'Avg(ms)':>8} | {'P50(ms)':>8} | "
        f"{'P95(ms)':>8} | {'P99(ms)':>8} | {'QPS':>8}"
    )
    logger.info(header)
    logger.info("-" * 100)

    # Data rows
    for s in summaries:
        row = (
            f"{s.get('pdf_count', 0):>6} | "
            f"{s.get('chunk_count', 0):>8} | "
            f"{s.get('token_count', 0):>10} | "
            f"{s.get('index_size_mb', 0):>9.2f} | "
            f"{s.get('avg_latency_ms', 0):>8.2f} | "
            f"{s.get('p50_latency_ms', 0):>8.2f} | "
            f"{s.get('p95_latency_ms', 0):>8.2f} | "
            f"{s.get('p99_latency_ms', 0):>8.2f} | "
            f"{s.get('throughput_qps', 0):>8.2f}"
        )
        logger.info(row)

    logger.info("=" * 100)


def run_single_benchmark(pdf_count: int, skip_ingest: bool = False) -> Dict:
    """
    Run benchmark for a single PDF count.

    Args:
        pdf_count: Number of PDFs to benchmark
        skip_ingest: Skip ingestion (use existing index)

    Returns:
        Summary dict
    """
    logger.info(f"Running single benchmark for {pdf_count} PDFs")

    # Check server
    if not check_server_running():
        logger.error("Server is not running.")
        sys.exit(1)

    # Ingest if needed
    if not skip_ingest:
        logger.info("Clearing index...")
        clear_index()
        time.sleep(2)

        logger.info(f"Ingesting {pdf_count} PDFs...")
        ingest_result = ingest_pdfs(pdf_count, PDF_SOURCE_PATH)

        if not ingest_result["success"]:
            logger.error("Ingestion failed")
            sys.exit(1)

        time.sleep(2)

    # Run benchmark
    summary = run_benchmark(pdf_count=pdf_count)

    # Save summary
    save_summary_csv([summary])

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run full Lucene search benchmark suite"
    )
    parser.add_argument(
        "--pdf-count", type=int, default=None,
        help="Run benchmark for specific PDF count only"
    )
    parser.add_argument(
        "--skip-ingest", action="store_true",
        help="Skip ingestion, use existing index"
    )
    parser.add_argument(
        "--skip-clear", action="store_true",
        help="Skip clearing index between runs"
    )
    parser.add_argument(
        "--pdf-counts", type=str, default=None,
        help="Comma-separated list of PDF counts (e.g., '100,200,400')"
    )

    args = parser.parse_args()

    # Determine PDF counts to run
    if args.pdf_count:
        summaries = [run_single_benchmark(args.pdf_count, args.skip_ingest)]
    elif args.pdf_counts:
        counts = [int(x.strip()) for x in args.pdf_counts.split(",")]
        summaries = run_full_benchmark(
            pdf_counts=counts,
            skip_ingest=args.skip_ingest,
            skip_clear=args.skip_clear
        )
    else:
        summaries = run_full_benchmark(
            skip_ingest=args.skip_ingest,
            skip_clear=args.skip_clear
        )

    logger.info("")
    logger.info("Full benchmark suite completed!")
    logger.info(f"Results saved in: {RESULTS_DIR}/")

    return summaries


if __name__ == "__main__":
    main()
