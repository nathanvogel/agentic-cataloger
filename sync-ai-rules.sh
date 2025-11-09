#!/bin/bash

set -e

KIRO_DIR=".kiro/steering"
CURSOR_DIR=".cursor/rules"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

usage() {
  echo "Usage: $0 [kiro-to-cursor|cursor-to-kiro]"
  echo ""
  echo "Syncs AI rules between Kiro and Cursor, converting formats and filtering for always-applied rules."
  echo ""
  echo "Options:"
  echo "  kiro-to-cursor    Copy from .kiro/steering to .cursor/rules"
  echo "  cursor-to-kiro    Copy from .cursor/rules to .kiro/steering"
  exit 1
}

kiro_to_cursor() {
  echo -e "${GREEN}Syncing from Kiro to Cursor...${NC}"
  
  mkdir -p "$CURSOR_DIR"
  
  for file in "$KIRO_DIR"/*.md; do
    [ -e "$file" ] || continue
    
    local basename=$(basename "$file" .md)
    local target="$CURSOR_DIR/${basename}.mdc"
    

    # Check if file has "inclusion: always"
    if grep -q "inclusion: always" "$file"; then
      echo -e "${YELLOW}Processing: $basename.md -> $basename.mdc${NC}"
      
      # Transform: replace Kiro frontmatter with Cursor frontmatter
      sed 's/inclusion: always/alwaysApply: true/' "$file" > "$target"
    else
      echo -e "Skipping: $basename.md (not always-applied)"
    fi
  done
  
  echo -e "${GREEN}✓ Synced file(s) to Cursor${NC}"
}

cursor_to_kiro() {
  echo -e "${GREEN}Syncing from Cursor to Kiro...${NC}"
  
  mkdir -p "$KIRO_DIR"
  
  
  for file in "$CURSOR_DIR"/*.mdc; do
    [ -e "$file" ] || continue
    
    local basename=$(basename "$file" .mdc)
    local target="$KIRO_DIR/${basename}.md"
    
    # Check if file has "alwaysApply: true"
    if grep -q "alwaysApply: true" "$file"; then
      echo -e "${YELLOW}Processing: $basename.mdc -> $basename.md${NC}"
      
      # Transform: replace Cursor frontmatter with Kiro frontmatter
      sed 's/alwaysApply: true/inclusion: always/' "$file" > "$target"
      
    else
      echo -e "Skipping: $basename.mdc (not always-applied)"
    fi
  done
  
  echo -e "${GREEN}✓ Synced file(s) to Kiro${NC}"
}

# Main
if [ $# -ne 1 ]; then
  usage
fi

case "$1" in
  kiro-to-cursor)
    kiro_to_cursor
    ;;
  cursor-to-kiro)
    cursor_to_kiro
    ;;
  *)
    usage
    ;;
esac
