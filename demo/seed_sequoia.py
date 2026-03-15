#!/usr/bin/env python3
"""Seed a Sequoia demo mission with a fixed task graph.

Usage:
    python demo/seed_sequoia.py [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import httpx

OBJECTIVE = (
    "I'm pitching to Sequoia next week. Find their recent investments, "
    "partner priorities, founder complaints, and AI portfolio weaknesses."
)

SEED_TASKS = [
    {
        "description": "Scrape sequoiacap.com for recent portfolio and partners",
        "agent_type": "OFFICIAL_SITE",
        "priority": 10,
    },
    {
        "description": "Search news and blogs for Sequoia 2024-2025 investments",
        "agent_type": "NEWS_BLOG",
        "priority": 8,
    },
    {
        "description": "Search Reddit/HN for founder complaints about Sequoia",
        "agent_type": "REDDIT_HN",
        "priority": 7,
    },
    {
        "description": "Search GitHub for AI projects in Sequoia portfolio",
        "agent_type": "GITHUB",
        "priority": 5,
    },
    {
        "description": "Retrieve financial data on recent Sequoia fund sizes",
        "agent_type": "FINANCIAL",
        "priority": 6,
    },
    {
        "description": "Find recent news about Sequoia AI strategy and bets",
        "agent_type": "RECENT_NEWS",
        "priority": 9,
    },
]


async def main(base_url: str) -> None:
    print(f"Seeding Sequoia demo mission at {base_url}")
    print(f"Objective: {OBJECTIVE[:80]}...")
    print()

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # 1. Create mission
        resp = await client.post(
            "/missions",
            json={"objective": OBJECTIVE},
            headers={"X-API-Key": "changeme"},
        )
        if resp.status_code not in (200, 201):
            print(f"Failed to create mission: {resp.status_code} {resp.text}")
            sys.exit(1)

        mission = resp.json()
        mission_id = mission["id"]
        print(f"Mission created: {mission_id}")
        print(f"Status: {mission['status']}")
        print(f"Task graph: {len(mission.get('task_graph', []))} tasks")
        print()

        # 2. Poll status
        print("Polling mission status...")
        start = time.time()
        timeout = 120
        status = "UNKNOWN"

        while time.time() - start < timeout:
            resp = await client.get(
                f"/missions/{mission_id}",
                headers={"X-API-Key": "changeme"},
            )
            if resp.status_code != 200:
                print(f"Poll error: {resp.status_code}")
                await asyncio.sleep(3)
                continue

            data = resp.json()
            status = data["status"]
            elapsed = time.time() - start
            print(f"  [{elapsed:5.1f}s] Status: {status}")

            if status in ("COMPLETE", "FAILED"):
                break

            await asyncio.sleep(5)

        print()
        print(f"Final status: {status}")
        print(f"Elapsed: {time.time() - start:.1f}s")
        print(f"War Room URL: http://localhost:5173?mission={mission_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Sequoia demo mission")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    asyncio.run(main(args.base_url))
