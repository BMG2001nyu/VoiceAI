#!/usr/bin/env python3
"""Load test — fire multiple missions in parallel and measure performance.

Usage:
    python demo/load_test.py [--base-url http://localhost:8000] [--concurrency 10]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import statistics
import time

import httpx

OBJECTIVES = [
    "Research Sequoia Capital's recent AI investments and partner priorities",
    "Analyze Andreessen Horowitz's crypto and web3 portfolio strategy",
    "Investigate Y Combinator's latest batch companies and success metrics",
    "Research Benchmark Capital's investment thesis and notable exits",
    "Analyze Lightspeed Venture Partners' AI and enterprise software bets",
    "Investigate Accel's European expansion and fintech portfolio",
    "Research Founders Fund's contrarian investment philosophy",
    "Analyze Index Ventures' cloud infrastructure and developer tool investments",
    "Investigate Greylock Partners' AI-first portfolio companies",
    "Research General Catalyst's growth-stage investment strategy",
    "Analyze Tiger Global's public-to-private crossover approach",
    "Investigate Khosla Ventures' deep tech and climate portfolio",
]


async def run_mission(
    client: httpx.AsyncClient,
    objective: str,
    mission_num: int,
    timeout_s: int = 120,
) -> dict:
    """Run a single mission and return results."""
    result = {
        "mission_num": mission_num,
        "objective": objective[:60],
        "mission_id": "",
        "status": "ERROR",
        "elapsed_sec": 0.0,
        "evidence_count": 0,
        "error": "",
    }

    start = time.time()

    try:
        # Create mission
        resp = await client.post(
            "/missions",
            json={"objective": objective},
            headers={"X-API-Key": "changeme"},
        )
        if resp.status_code not in (200, 201):
            result["error"] = f"Create failed: {resp.status_code}"
            result["elapsed_sec"] = time.time() - start
            return result

        mission = resp.json()
        mission_id = mission["id"]
        result["mission_id"] = mission_id

        # Poll until complete or timeout
        while time.time() - start < timeout_s:
            resp = await client.get(
                f"/missions/{mission_id}",
                headers={"X-API-Key": "changeme"},
            )
            if resp.status_code != 200:
                await asyncio.sleep(3)
                continue

            data = resp.json()
            status = data["status"]

            if status in ("COMPLETE", "FAILED"):
                result["status"] = status
                break

            await asyncio.sleep(3)
        else:
            result["status"] = "TIMEOUT"

        # Get evidence count
        resp = await client.get(
            f"/missions/{mission_id}/evidence",
            headers={"X-API-Key": "changeme"},
        )
        if resp.status_code == 200:
            evidence = resp.json()
            result["evidence_count"] = (
                len(evidence) if isinstance(evidence, list) else 0
            )

    except Exception as exc:
        result["error"] = str(exc)

    result["elapsed_sec"] = round(time.time() - start, 2)
    return result


async def main(base_url: str, concurrency: int) -> None:
    print("=== Mission Control Load Test ===")
    print(f"Base URL:    {base_url}")
    print(f"Concurrency: {concurrency}")
    print()

    objectives = OBJECTIVES[:concurrency]

    async with httpx.AsyncClient(base_url=base_url, timeout=150.0) as client:
        # Check health
        try:
            resp = await client.get("/health")
            if resp.status_code != 200:
                print(f"Backend not healthy: {resp.status_code}")
                return
        except Exception as exc:
            print(f"Backend not reachable: {exc}")
            return

        print(f"Backend healthy. Launching {len(objectives)} missions...\n")

        # Run all missions in parallel
        start = time.time()
        tasks = [run_mission(client, obj, i + 1) for i, obj in enumerate(objectives)]
        results = await asyncio.gather(*tasks)
        total_elapsed = time.time() - start

    # Print results table
    print(
        f"{'#':>3}  {'Status':<10}  {'Time':>7}  {'Evidence':>8}  "
        f"{'Objective':<50}  {'Error'}"
    )
    print("-" * 120)
    for r in results:
        print(
            f"{r['mission_num']:>3}  "
            f"{r['status']:<10}  "
            f"{r['elapsed_sec']:>6.1f}s  "
            f"{r['evidence_count']:>8}  "
            f"{r['objective']:<50}  "
            f"{r['error']}"
        )

    # Statistics
    times = [r["elapsed_sec"] for r in results if r["status"] != "ERROR"]
    success = sum(1 for r in results if r["status"] == "COMPLETE")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    timeout = sum(1 for r in results if r["status"] == "TIMEOUT")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print()
    print("=== Summary ===")
    print(f"Total time:  {total_elapsed:.1f}s")
    print(f"Success:     {success}/{len(results)}")
    print(f"Failed:      {failed}")
    print(f"Timeout:     {timeout}")
    print(f"Errors:      {errors}")

    if times:
        print(f"p50 time:    {statistics.median(times):.1f}s")
        if len(times) >= 2:
            sorted_times = sorted(times)
            p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
            print(f"p95 time:    {sorted_times[p95_idx]:.1f}s")

    total_evidence = sum(r["evidence_count"] for r in results)
    print(f"Total evidence: {total_evidence}")

    # Write CSV
    csv_path = "demo/load_test_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mission_num",
                "mission_id",
                "objective",
                "status",
                "elapsed_sec",
                "evidence_count",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mission Control load test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.concurrency))
