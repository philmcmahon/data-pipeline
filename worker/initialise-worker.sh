#!/usr/bin/env bash
set -euo pipefail
set -x

# This script runs as the ubuntu user.
# Usage:
#   initialise-worker.sh <queue_url> <output_bucket> <working_directory>

QUEUE_URL="$1"
OUTPUT_BUCKET="$2"
WORKING_DIRECTORY="$3"

TARGET_DIR="${WORKING_DIRECTORY}/data-pipeline"
WORKER_LOG="${WORKING_DIRECTORY}/worker.log"

export UV_CACHE_DIR="${WORKING_DIRECTORY}/.cache/uv"
export HF_HOME="${WORKING_DIRECTORY}/.cache/huggingface"
export WORK_DIR="${WORKING_DIRECTORY}/tmp"

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

cd "${TARGET_DIR}"

# Install dependencies
echo "Installing worker dependencies with uv..."
uv sync --extra worker

echo "Installing vllm..."
uv pip install vllm --torch-backend auto

# Start worker in background
echo "Starting worker..."
nohup uv run worker "${QUEUE_URL}" "${OUTPUT_BUCKET}" > "${WORKER_LOG}" 2>&1 &

echo "Worker started in background. Logs: ${WORKER_LOG}"
