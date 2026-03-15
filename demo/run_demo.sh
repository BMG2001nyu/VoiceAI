#!/usr/bin/env bash
# Run the Sequoia demo mission
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "=== Mission Control Demo ==="
echo "Backend:  $BASE_URL"
echo "Frontend: $FRONTEND_URL"
echo ""

# Check backend is running
if ! curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Backend not reachable at $BASE_URL/health"
    echo "Start it with: cd backend && uvicorn main:app --reload --port 8000"
    exit 1
fi

echo "Backend is healthy."
echo ""

# Seed the demo mission
python3 demo/seed_sequoia.py --base-url "$BASE_URL"

echo ""
echo "Open the War Room in your browser (URL printed above)."
