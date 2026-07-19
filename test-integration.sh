#!/usr/bin/env bash
set -euo pipefail
PKGMAN_TEST_INTEGRATION=1 uv run pytest tests/ "$@"