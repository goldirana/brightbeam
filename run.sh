#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# run.sh — Single script to execute the full pipeline
# ──────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

# Setup virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "▶ Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "▶ Installing dependencies..."
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "═══════════════════════════════════════════════════════════"
echo "  BrightBeam Call Summarisation Pipeline"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Step 1: Build cluster centroids from training examples
echo "▶ Step 1: Discovering clusters from training examples..."
python -m src.cli discover-clusters
echo ""

# Step 2: Run summarisation on test transcripts
echo "▶ Step 2: Summarising test transcripts..."
python -m src.cli summarise
echo ""

# Step 3: Generate HTML dashboard
echo "▶ Step 3: Generating dashboard..."
python -m src.cli dashboard
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  Done! Results in ./output/"
echo "  - Summaries:  output/*-summary.txt"
echo "  - Dashboard:  output/dashboard.html"
echo "  - Raw data:   output/results.json"
echo "═══════════════════════════════════════════════════════════"
