#!/usr/bin/env bash

set -euo pipefail

VERSION="$(cat VERSION)"
DATE="$(date +%+4Y%m%d%H%M%S)"

OUTPUT="living_world-${VERSION}-${DATE}.zip"

echo "Creating ${OUTPUT}..."

zip -r "${OUTPUT}" . \
    -x ".git/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x ".venv/*" \
    -x ".pytest_cache/*" \
    -x ".ruff_cache/*" \
    -x ".mypy_cache/*"

echo
echo "Snapshot created:"
echo "  ${OUTPUT}"