"""
Test script for the async PDF ingestion API.

Uploads PDFs from Research-Paper-Downloder/data/arxiv/cs_ai/pdfs/
to the Lucene service in a SINGLE API call. The server handles all files
in one background job, producing one export JSON file.

Usage:
    # Test with 5 PDFs (quick smoke test)
    python test_async_ingestion.py

    # Test with custom count
    python test_async_ingestion.py --count 50

    # Full test with all 1082 PDFs
    python test_async_ingestion.py --count 1082

    # Verify exported JSON file
    python test_async_ingestion.py --count 10 --verify-export
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8080"
INGEST_ENDPOINT = f"{BASE_URL}/api/v1/ingest/pdf"
STATUS_ENDPOINT = f"{BASE_URL}/api/v1/ingest/status"
HEALTH_ENDPOINT = f"{BASE_URL}/api/v1/ingest/health"
STATS_ENDPOINT = f"{BASE_URL}/api/v1/ingest/stats"
CHUNK_STATS_ENDPOINT = f"{BASE_URL}/api/v1/search/chunk-stats"

PDF_SOURCE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "Research-Paper-Downloder", "data", "arxiv", "cs_ai", "pdfs"
)

EXPORT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "lucene-service", "chunk-exports"
)

# Polling config
POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 1800  # 30 minutes max (for large uploads like 1082 PDFs)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def wait_for_server(timeout: int = 60) -> bool:
    """Wait for the Lucene service to be ready."""
    logger.info("Waiting for server at %s ...", BASE_URL)
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            r = requests.get(HEALTH_ENDPOINT, timeout=5)
            if r.status_code == 200:
                logger.info("Server is UP")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(2)

    logger.error("Server not ready after %ds", timeout)
    return False


def get_pdf_files(limit: Optional[int] = None) -> List[Path]:
    """Get sorted list of PDFs from the data directory."""
    source = Path(PDF_SOURCE_PATH).resolve()

    if not source.exists():
        logger.error("PDF source directory not found: %s", source)
        sys.exit(1)

    pdfs = sorted(source.glob("*.pdf"))
    logger.info("Found %d PDFs in %s", len(pdfs), source)

    if limit:
        pdfs = pdfs[:limit]

    return pdfs


def submit_job(pdf_paths: List[Path]) -> dict:
    """
    Upload ALL PDFs in a single API call.
    The server creates one background job for all files.
    Returns the immediate response (jobId, status=PROCESSING).
    """
    files = []
    for path in pdf_paths:
        files.append(("file", (path.name, open(path, "rb"), "application/pdf")))

    total_size_mb = sum(p.stat().st_size for p in pdf_paths) / (1024 * 1024)
    logger.info("Uploading %d PDFs (%.1f MB) in a single API call...",
                len(pdf_paths), total_size_mb)

    try:
        r = requests.post(INGEST_ENDPOINT, files=files, timeout=300)

        # Close file handles
        for _, (_, fh, _) in files:
            fh.close()

        if r.status_code in (200, 202):
            return r.json()
        else:
            logger.error("Upload failed [%d]: %s", r.status_code, r.text[:500])
            return {"status": "FAILED", "message": r.text[:200]}

    except requests.RequestException as e:
        # Close file handles on error
        for _, (_, fh, _) in files:
            fh.close()
        logger.error("Upload request failed: %s", e)
        return {"status": "FAILED", "message": str(e)}


def poll_job(job_id: str, poll_interval: float = POLL_INTERVAL_SEC,
             timeout: float = POLL_TIMEOUT_SEC) -> dict:
    """
    Poll job status until COMPLETED or FAILED.
    Returns the final job status.
    """
    url = f"{STATUS_ENDPOINT}/{job_id}"
    start = time.time()
    last_chunks = 0

    while (time.time() - start) < timeout:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 404:
                logger.error("Job not found: %s", job_id)
                return {"status": "FAILED", "errorMessage": "Job not found"}

            status = r.json()
            current_status = status.get("status", "UNKNOWN")
            docs = status.get("documentsProcessed", 0)
            chunks = status.get("chunksProcessed", 0)
            total = status.get("totalFiles", "?")

            # Log progress only when chunks change
            if chunks != last_chunks:
                logger.info("  [%s] docs: %d/%s, chunks: %d",
                            current_status, docs, total, chunks)
                last_chunks = chunks

            if current_status in ("COMPLETED", "FAILED"):
                elapsed = time.time() - start
                logger.info("  Job finished in %.1fs", elapsed)
                return status

        except requests.RequestException as e:
            logger.warning("Poll error: %s", e)

        time.sleep(poll_interval)

    logger.error("Job %s timed out after %ds", job_id, timeout)
    return {"status": "FAILED", "errorMessage": "Poll timeout"}


def get_index_stats() -> dict:
    """Get current index statistics."""
    try:
        r = requests.get(CHUNK_STATS_ENDPOINT, timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return {}


def verify_export_file(file_name: str) -> dict:
    """Verify the exported JSON file is valid and has correct structure."""
    export_dir = Path(EXPORT_PATH).resolve()
    file_path = export_dir / file_name

    if not file_path.exists():
        return {"valid": False, "error": f"File not found: {file_path}"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return {"valid": False, "error": "Root is not a JSON array"}

        if len(data) == 0:
            return {"valid": False, "error": "Empty array"}

        # Validate first chunk structure
        sample = data[0]
        required_fields = ["id", "document_id", "content", "metadata"]
        missing = [f for f in required_fields if f not in sample]
        if missing:
            return {"valid": False, "error": f"Missing fields: {missing}"}

        meta = sample.get("metadata", {})
        meta_fields = ["source", "page_number", "chunk_index", "token_count", "created_at"]
        missing_meta = [f for f in meta_fields if f not in meta]
        if missing_meta:
            return {"valid": False, "error": f"Missing metadata fields: {missing_meta}"}

        # Collect stats
        doc_ids = set(chunk["document_id"] for chunk in data)
        sources = set(chunk["metadata"]["source"] for chunk in data)
        total_tokens = sum(chunk["metadata"]["token_count"] for chunk in data)

        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        return {
            "valid": True,
            "totalChunks": len(data),
            "uniqueDocuments": len(doc_ids),
            "sourceFiles": sorted(sources),
            "totalTokens": total_tokens,
            "fileSizeMB": round(file_size_mb, 2),
            "sampleChunk": {
                "id": sample["id"],
                "document_id": sample["document_id"],
                "content_preview": sample["content"][:100] + "...",
                "metadata": sample["metadata"]
            }
        }

    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Test Runners
# ---------------------------------------------------------------------------


def test_status_404() -> bool:
    """Test: requesting status of nonexistent job returns 404."""
    logger.info("=" * 60)
    logger.info("TEST: Status endpoint - 404 for unknown jobId")
    logger.info("=" * 60)

    r = requests.get(f"{STATUS_ENDPOINT}/job_does_not_exist", timeout=10)

    if r.status_code == 404:
        logger.info("PASS - Got 404 for unknown jobId")
        return True
    else:
        logger.error("FAIL - Expected 404, got %d", r.status_code)
        return False


def test_invalid_file() -> bool:
    """Test: uploading a non-PDF file returns 400."""
    logger.info("=" * 60)
    logger.info("TEST: Validation - reject non-PDF file")
    logger.info("=" * 60)

    files = [("file", ("test.txt", b"this is not a pdf", "text/plain"))]
    r = requests.post(INGEST_ENDPOINT, files=files, timeout=30)

    if r.status_code == 400:
        logger.info("PASS - Got 400 for non-PDF file")
        return True
    else:
        logger.error("FAIL - Expected 400, got %d: %s", r.status_code, r.text[:200])
        return False


def test_single_file(pdfs: List[Path]) -> bool:
    """Test: upload 1 PDF, poll until done."""
    logger.info("=" * 60)
    logger.info("TEST: Single file upload")
    logger.info("=" * 60)

    pdf = pdfs[0]
    logger.info("Uploading: %s (%.1f KB)", pdf.name, pdf.stat().st_size / 1024)

    response = submit_job([pdf])
    job_id = response.get("jobId")

    if not job_id:
        logger.error("FAIL - No jobId returned: %s", response)
        return False

    logger.info("Job submitted: %s", job_id)
    logger.info("Status: %s", response.get("status"))

    if response.get("status") != "PROCESSING":
        logger.error("FAIL - Expected PROCESSING, got: %s", response.get("status"))
        return False

    # Poll until done
    final = poll_job(job_id)

    if final.get("status") == "COMPLETED":
        logger.info("PASS - Single file ingestion completed")
        logger.info("  Documents: %s", final.get("documentsProcessed"))
        logger.info("  Chunks: %s", final.get("chunksProcessed"))
        logger.info("  Export: %s", final.get("exportFileName"))
        return True
    else:
        logger.error("FAIL - Job status: %s, error: %s",
                      final.get("status"), final.get("errorMessage"))
        return False


def test_ingestion(pdfs: List[Path], verify_export: bool) -> bool:
    """
    Test: upload ALL PDFs in a single API call.
    Server processes them in one background job → one export file.
    """
    logger.info("=" * 60)
    logger.info("TEST: Ingest %d PDFs (single API call → single job)", len(pdfs))
    logger.info("=" * 60)

    total_start = time.time()

    # One API call with all PDFs
    response = submit_job(pdfs)
    job_id = response.get("jobId")

    if not job_id:
        logger.error("FAIL - No jobId returned: %s", response)
        return False

    logger.info("Job submitted: %s", job_id)
    logger.info("Server is processing %d files in the background...", len(pdfs))

    # Poll until done
    final = poll_job(job_id)
    total_time = time.time() - total_start

    if final.get("status") != "COMPLETED":
        logger.error("FAIL - Job status: %s, error: %s",
                      final.get("status"), final.get("errorMessage"))
        return False

    total_docs = final.get("documentsProcessed", 0)
    total_chunks = final.get("chunksProcessed", 0)
    export_file = final.get("exportFileName")

    # Get index stats
    index_stats = get_index_stats()

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info("PDFs uploaded:     %d", len(pdfs))
    logger.info("Documents indexed: %d", total_docs)
    logger.info("Total chunks:      %d", total_chunks)
    logger.info("Total tokens:      %s", index_stats.get("totalTokens", "N/A"))
    logger.info("Export file:       %s", export_file)
    logger.info("Total time:        %.1fs", total_time)
    logger.info("Rate:              %.1f PDFs/sec", len(pdfs) / total_time if total_time > 0 else 0)
    logger.info("=" * 60)

    # Verify export if requested
    if verify_export and export_file:
        logger.info("")
        logger.info("VERIFYING EXPORT FILE")
        logger.info("-" * 40)
        logger.info("Checking: %s", export_file)
        result = verify_export_file(export_file)
        if result["valid"]:
            logger.info("  VALID - %d chunks, %d documents, %d tokens, %.2f MB",
                        result["totalChunks"], result["uniqueDocuments"],
                        result["totalTokens"], result["fileSizeMB"])
        else:
            logger.error("  INVALID - %s", result["error"])

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Test async PDF ingestion API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_async_ingestion.py                       # Quick smoke test (5 PDFs)
  python test_async_ingestion.py --count 50            # 50 PDFs, single API call
  python test_async_ingestion.py --count 1082          # Full dataset, single API call
  python test_async_ingestion.py --count 10 --verify-export  # Verify JSON export
        """
    )
    parser.add_argument("--count", type=int, default=5,
                        help="Number of PDFs to ingest (default: 5)")
    parser.add_argument("--verify-export", action="store_true",
                        help="Verify exported JSON file after ingestion")
    parser.add_argument("--skip-validation-tests", action="store_true",
                        help="Skip 404 and invalid file tests")

    args = parser.parse_args()

    # Check server
    if not wait_for_server():
        sys.exit(1)

    # Load PDFs
    pdfs = get_pdf_files(args.count)
    if not pdfs:
        logger.error("No PDFs found!")
        sys.exit(1)

    results = {}

    # Run validation tests
    if not args.skip_validation_tests:
        results["status_404"] = test_status_404()
        results["invalid_file"] = test_invalid_file()
        print()

    # Run ingestion test — single API call, server does the rest
    if args.count == 1:
        results["single_file"] = test_single_file(pdfs)
    else:
        results["ingestion"] = test_ingestion(pdfs, verify_export=args.verify_export)

    # Final report
    print()
    logger.info("=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info("  %-25s %s", test_name, status)
        if not passed:
            all_passed = False

    print()
    if all_passed:
        logger.info("ALL TESTS PASSED")
    else:
        logger.error("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
