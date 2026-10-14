#!/usr/bin/env bash
# See scripts/RESIZE-CATEGORY-IMAGES.md. Normal site builds never run this tool.
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'resize.sh: Python 3 is required; no dependencies were installed.' >&2
  exit 1
fi
exec python3 "$script_dir/resize_category_images.py" "$@"
