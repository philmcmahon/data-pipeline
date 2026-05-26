#!/usr/bin/env bash
set -euo pipefail
set -x

# Usage:
#   ./setup.sh <queue_url> <output_bucket>

QUEUE_URL="$1"
OUTPUT_BUCKET="$2"
REPO_URL="https://github.com/philmcmahon/data-pipeline.git"
UBUNTU_USER="ubuntu"
UBUNTU_HOME="/home/${UBUNTU_USER}"
TARGET_DIR="${UBUNTU_HOME}/data-pipeline"
UV_BIN="${UBUNTU_HOME}/.local/bin/uv"
WORKER_LOG="${UBUNTU_HOME}/worker.log"

if ! id -u "${UBUNTU_USER}" >/dev/null 2>&1; then
	echo "User ${UBUNTU_USER} does not exist."
	exit 1
fi

sudo -u "${UBUNTU_USER}" -H bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'

if [[ -d "${TARGET_DIR}/.git" ]]; then
	echo "Repository already exists at ${TARGET_DIR}, skipping clone."
else
	echo "Cloning repository..."
	sudo -u "${UBUNTU_USER}" -H git clone "${REPO_URL}" "${TARGET_DIR}"
fi

apt update
apt install -y ffmpeg

cd "${TARGET_DIR}"

echo "Installing worker dependencies with uv..."
sudo -u "${UBUNTU_USER}" -H bash -lc "cd '${TARGET_DIR}' && '${UV_BIN}' sync --extra worker"

echo "Installing vllm..."
sudo -u "${UBUNTU_USER}" -H bash -lc "cd '${TARGET_DIR}' && '${UV_BIN}' pip install vllm --torch-backend auto"

echo "Setup complete."

echo "Starting worker..."
sudo -u "${UBUNTU_USER}" -H env QUEUE_URL="${QUEUE_URL}" OUTPUT_BUCKET="${OUTPUT_BUCKET}" TARGET_DIR="${TARGET_DIR}" UV_BIN="${UV_BIN}" WORKER_LOG="${WORKER_LOG}" bash -lc '
cd "$TARGET_DIR"
nohup "$UV_BIN" run worker "$QUEUE_URL" "$OUTPUT_BUCKET" > "$WORKER_LOG" 2>&1 &
'

echo "Worker started in background. Logs: ${WORKER_LOG}"
