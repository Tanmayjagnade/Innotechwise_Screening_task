#!/usr/bin/env bash
# Demo script: exercises all three endpoints in sequence.
BASE="http://localhost:8000"

echo "=========================================="
echo "  GreenPack EPR Service — Demo"
echo "=========================================="

echo ""
echo "--- 1. POST /submit ---"
curl -s -X POST "$BASE/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "producer_id": "GREENPACK-001",
    "month": "2026-04",
    "declared_quantities_kg": {
      "rigid_plastic": 12000,
      "flexible_plastic": 8500,
      "multilayer_plastic": 3200
    }
  }' | python3 -m json.tool

echo ""
echo "--- 2. GET /summary/GREENPACK-001/2026-04 ---"
curl -s "$BASE/summary/GREENPACK-001/2026-04" | python3 -m json.tool

echo ""
echo "--- 3a. POST /ask (answerable question) ---"
curl -s -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the EPR registration requirements for plastic producers?"}' \
  | python3 -m json.tool

echo ""
echo "--- 3b. POST /ask (out-of-scope question — expect I do not know) ---"
curl -s -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France?"}' \
  | python3 -m json.tool

echo ""
echo "--- 4. POST /submit (validation error — negative quantity) ---"
curl -s -X POST "$BASE/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "producer_id": "GREENPACK-001",
    "month": "2026-05",
    "declared_quantities_kg": {
      "rigid_plastic": -500
    }
  }' | python3 -m json.tool

echo ""
echo "Demo complete."
