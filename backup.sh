#!/usr/bin/env bash
set -euo pipefail

# Navigate to OpenClaw workspace root
cd /home/ec2-user/.openclaw

# Add all changes
git add .

# Check if there are changes to commit
if git diff-index --quiet HEAD --; then
    echo "No changes to commit."
    exit 0
fi

# Commit with timestamp
git commit -m "Auto backup $(date +'%Y-%m-%d %H:%M:%S')" || true

# Push to GitHub (uses stored credentials)
git push origin main