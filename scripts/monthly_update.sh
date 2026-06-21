#!/usr/bin/env bash
# Groth Adventures Scrapbook - Monthly Update Script (Bash)
# Run this script monthly to sync the latest blog posts
# Usage: bash scripts/monthly_update.sh [--source NAME] [--full] [--no-media]

set -e

SOURCE="grothadventures"
DATA_DIR=""
FULL=false
NO_MEDIA=false
PORT=8420

while [[ $# -gt 0 ]]; do
    case $1 in
        --source) SOURCE="$2"; shift 2 ;;
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        --full) FULL=true; shift ;;
        --no-media) NO_MEDIA=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " Groth Adventures Scrapbook Update"
echo " $(date '+%Y-%m-%d %H:%M')"
echo "========================================"
echo ""

# Check if scrapbook is installed
if ! command -v scrapbook &>/dev/null; then
    echo "ERROR: 'scrapbook' command not found."
    echo "Install with: pip install -e '$PROJECT_DIR'"
    exit 1
fi

# Build sync args
SYNC_ARGS=("sync" "--source" "$SOURCE")
[[ -n "$DATA_DIR" ]] && SYNC_ARGS+=("--data-dir" "$DATA_DIR")
[[ "$FULL" == true ]] && SYNC_ARGS+=("--full")
[[ "$NO_MEDIA" == true ]] && SYNC_ARGS+=("--no-media")

echo "Step 1: Syncing latest posts from $SOURCE..."
scrapbook "${SYNC_ARGS[@]}"
echo ""

echo "Step 2: Rebuilding search index..."
INDEX_ARGS=("reindex" "--fts" "--tags")
[[ -n "$DATA_DIR" ]] && INDEX_ARGS+=("--data-dir" "$DATA_DIR")
scrapbook "${INDEX_ARGS[@]}"
echo ""

echo "Step 3: Status check..."
STATUS_ARGS=("status")
[[ -n "$DATA_DIR" ]] && STATUS_ARGS+=("--data-dir" "$DATA_DIR")
scrapbook "${STATUS_ARGS[@]}"
echo ""

echo "========================================"
echo " Update complete!"
echo " View your scrapbook:"
echo "   scrapbook serve --port $PORT"
echo "========================================"
