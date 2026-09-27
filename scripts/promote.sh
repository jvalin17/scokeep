#!/usr/bin/env bash
# Promote stable (main) to production (prod branch).
# Usage: ./scripts/promote.sh
#
# What it does:
#   1. Checks you're on main with no uncommitted changes
#   2. Shows what commits will be promoted / dropped
#   3. Asks for confirmation
#   4. Points prod at main (reset --hard) and force-with-lease pushes
#
# No PR needed. prod is a pointer to what's live, not a divergent history.

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
git fetch origin main prod --quiet

MAIN_SHA=$(git rev-parse origin/main)
PROD_SHA=$(git rev-parse origin/prod)

echo -e "${YELLOW}main:${NC} $(git rev-parse --short origin/main)  $(git log -1 --format='%s' origin/main)"
echo -e "${YELLOW}prod:${NC} $(git rev-parse --short origin/prod)  $(git log -1 --format='%s' origin/prod)"
echo ""

if [ "$PROD_SHA" = "$MAIN_SHA" ]; then
    echo -e "${GREEN}Nothing to promote — prod already points at main.${NC}"
    exit 0
fi

new_count=$(git rev-list --count origin/prod..origin/main)
drop_count=$(git rev-list --count origin/main..origin/prod)

echo -e "${YELLOW}Commits on main not on prod ($new_count):${NC}"
git log --oneline origin/prod..origin/main || true
echo ""
echo -e "${YELLOW}Commits on prod that will be dropped ($drop_count):${NC}"
git log --oneline origin/main..origin/prod || true
echo ""

echo -e "${YELLOW}Point prod at main and force-with-lease push?${NC} [y/N] "
read -r confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

git checkout prod
git reset --hard origin/main
git push --force-with-lease=refs/heads/prod:origin/prod origin prod
git checkout main
git fetch origin prod --quiet

echo ""
echo -e "${GREEN}✓ Promoted to prod @ $(git rev-parse --short origin/main). Render will deploy shortly.${NC}"
echo -e "  Prod: https://scokeep.onrender.com"
echo -e "  Stable: https://scokeep-stable.onrender.com"
