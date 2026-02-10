"""
Script to ingest N PDFs into the Lucene search service.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import List, Optional

import requests

from config import INGEST_ENDPOINT, PDF_SOURCE_PATH, STATS_ENDPOINT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_pdf_files(source_path: str, limit: Optional[int] = None) -> List[Path]:
    """
    Get list of PDF files from source directory.

    Args:
        source_path: Path to directory containing PDFs
        limit: Maximum number of PDFs to return (None for all)

    Returns:
        List of Path objects for PDF files
    """
    source_dir = Path(source_path)

    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return []

    pdf_files = sorted(source_dir.glob("*.pdf"))

    if limit is not None:
        pdf_files = pdf_files[:limit]

    logger.info(f"Found {len(pdf_files)} PDF files to ingest")
    return pdf_files


def ingest_pdf(pdf_path: Path, timeout: int = 300) -> dict:
    """
    Ingest a single PDF file.

    Args:
        pdf_path: Path to the PDF file
        timeout: Request timeout in seconds

    Returns:
        Response data dict
    """
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(
                INGEST_ENDPOINT,
                files=files,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to ingest {pdf_path.name}: {e}")
        return {"status": "FAILED", "error": str(e)}
    except Exception as e:
        logger.error(f"Error reading {pdf_path.name}: {e}")
        return {"status": "FAILED", "error": str(e)}


def wait_for_server(max_retries: int = 30, retry_delay: float = 2.0) -> bool:
    """
    Wait for the server to be ready.

    Args:
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds

    Returns:
        True if server is ready, False otherwise
    """
    logger.info("Waiting for server to be ready...")

    for i in range(max_retries):
        try:
            response = requests.get(STATS_ENDPOINT, timeout=5)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except requests.RequestException:
            pass

        if i < max_retries - 1:
            time.sleep(retry_delay)

    logger.error("Server not ready after maximum retries")
    return False


def ingest_pdfs(
    num_pdfs: int,
    source_path: str = PDF_SOURCE_PATH,
    fail_fast: bool = True
) -> dict:
    """
    Ingest specified number of PDFs.

    Args:
        num_pdfs: Number of PDFs to ingest
        source_path: Path to source directory
        fail_fast: If True, stop on first failure

    Returns:
        Dict with ingestion statistics
    """
    logger.info(f"Starting ingestion of {num_pdfs} PDFs from {source_path}")

    # Wait for server
    if not wait_for_server():
        return {"success": False, "error": "Server not ready"}

    # Get PDF files
    pdf_files = get_pdf_files(source_path, num_pdfs)

    if not pdf_files:
        return {"success": False, "error": "No PDF files found"}

    # Ingest each PDF
    success_count = 0
    failed_count = 0
    failed_files = []

    start_time = time.time()

    for i, pdf_path in enumerate(pdf_files):
        logger.info(f"Ingesting [{i + 1}/{len(pdf_files)}]: {pdf_path.name}")

        result = ingest_pdf(pdf_path)

        if result.get("status") == "SUCCESS":
            success_count += 1
            chunk_count = result.get("totalChunks", 0)
            token_count = result.get("totalTokens", 0)
            logger.info(f"  SUCCESS: {chunk_count} chunks, {token_count} tokens")
        else:
            failed_count += 1
            failed_files.append(pdf_path.name)
            logger.error(f"  FAILED: {result.get('error', 'Unknown error')}")

            if fail_fast:
                raise Exception(f"Ingestion failed: {pdf_path.name}")

        # Progress update every 10 files
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (len(pdf_files) - i - 1) / rate if rate > 0 else 0
            logger.info(f"Progress: {i + 1}/{len(pdf_files)} ({rate:.1f} PDFs/sec, ~{remaining:.0f}s remaining)")

    end_time = time.time()
    total_time = end_time - start_time

    # Get final stats
    try:
        response = requests.get(STATS_ENDPOINT, timeout=30)
        final_stats = response.json() if response.status_code == 200 else {}
    except requests.RequestException:
        final_stats = {}

    logger.info("=" * 60)
    logger.info("Ingestion complete")
    logger.info("=" * 60)
    logger.info(f"Total PDFs: {len(pdf_files)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info(f"Average rate: {len(pdf_files) / total_time:.2f} PDFs/second")
    logger.info(f"Total chunks: {final_stats.get('totalChunks', 'N/A')}")
    logger.info(f"Total tokens: {final_stats.get('totalTokens', 'N/A')}")
    logger.info("=" * 60)

    return {
        "success": failed_count == 0,
        "total_pdfs": len(pdf_files),
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files,
        "total_time_sec": total_time,
        "chunk_count": final_stats.get("totalChunks", 0),
        "token_count": final_stats.get("totalTokens", 0)
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest PDFs into Lucene Search Service")
    parser.add_argument("num_pdfs", type=int, help="Number of PDFs to ingest")
    parser.add_argument("--source", type=str, default=PDF_SOURCE_PATH,
                        help="Source directory containing PDFs")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Continue ingestion even if some PDFs fail")

    args = parser.parse_args()

    result = ingest_pdfs(
        num_pdfs=args.num_pdfs,
        source_path=args.source,
        fail_fast=not args.continue_on_error
    )

    if not result["success"]:
        sys.exit(1)

    return result


if __name__ == "__main__":
    main()
