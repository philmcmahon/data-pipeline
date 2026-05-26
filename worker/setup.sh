#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./setup.sh

REPO_URL="https://github.com/philmcmahon/data-pipeline.git"
TARGET_DIR="${data-pipeline}"

curl -LsSf https://astral.sh/uv/install.sh | sh

if [[ -d "${TARGET_DIR}/.git" ]]; then
	echo "Repository already exists at ${TARGET_DIR}, skipping clone."
else
	echo "Cloning repository..."
	git clone "${REPO_URL}" "${TARGET_DIR}"
fi

apt update
apt install ffmpeg

cd "${TARGET_DIR}"

echo "Installing worker dependencies with uv..."
uv sync --extra worker

echo "Setup complete."
