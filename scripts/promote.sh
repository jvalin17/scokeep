#!/usr/bin/env bash
# Promote stable (main) to production (prod branch).
# Usage: ./scripts/promote.sh
#
# What it does:
#   1. Checks you're on main with no uncommitted changes
#   2. Shows what commits will be promoted
#   3. Asks for confirmation
#   4. Fast-forward merges main into prod and pushes

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Must be on main
current=$(git branch --show-current)
if [ "$current" != "main" ]; then
    echo -e "${RED}Error: must be on main branch (currently on $current)${NC}"
    exit 1
fi

# No uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${RED}Error: uncommitted changes. Commit or stash first.${NC}"
    exit 1
fi

# Fetch latest
git fetch origin prod --quiet 2>/dev/null || true

# Show what's being promoted
echo -e "${YELLOW}Commits to promote (main → prod):${NC}"
echo ""
git log --oneline origin/prod..main
echo ""

count=$(git rev-list --count origin/prod..main)
if [ "$count" -eq 0 ]; then
    echo -e "${GREEN}Nothing to promote — prod is up to date.${NC}"
    exit 0
fi

echo -e "${YELLOW}Promote $count commit(s) to production?${NC} [y/N] "
read -r confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

# Merge and push
git checkout prod
git merge main --ff-only
git push origin prod
git checkout main

echo ""
echo -e "${GREEN}✓ Promoted to prod. Render will deploy shortly.${NC}"
echo -e "  Prod: https://scokeep.onrender.com"
echo -e "  Stable: https://scokeep-stable.onrender.com"
