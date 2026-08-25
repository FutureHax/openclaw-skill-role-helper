#!/usr/bin/env bash
# Backward-compatible wrapper: catalog-only lookup (never guild-wide roles).
# Usage: lookup.sh <game_name_or_search>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
QUERY="${1:?Usage: lookup.sh <game_name_or_search>}"
exec bash "${ROOT}/roles.sh" lookup "$QUERY"
