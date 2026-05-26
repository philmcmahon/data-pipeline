#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./setup.sh

REPO_URL="https://github.com/philmcmahon/data-pipeline.git"
TARGET_DIR="${data-pipeline}"

if [[ -z "${REPO_URL}" ]]; then
	echo "Usage: $0 <repo-url> [target-dir]"
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "Installing uv..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="$HOME/.local/bin:$PATH"
fi

if [[ -d "${TARGET_DIR}/.git" ]]; then
	echo "Repository already exists at ${TARGET_DIR}, skipping clone."
else
	echo "Cloning repository..."
	git clone "${REPO_URL}" "${TARGET_DIR}"
fi

cd "${TARGET_DIR}"

echo "Installing worker dependencies with uv..."
uv sync --extra worker

echo "Setup complete."
