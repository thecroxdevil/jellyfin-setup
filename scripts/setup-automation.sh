#!/bin/bash

# Setup script for GitHub sync automation
# This sets up a cron job to automatically sync from GitHub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SYNC_SCRIPT="$SCRIPT_DIR/sync-from-github.sh"
CRON_SCHEDULE="*/15 * * * *"  # Every 15 minutes

echo "Setting up GitHub sync automation..."
echo "Project directory: $PROJECT_DIR"
echo "Sync script: $SYNC_SCRIPT"

# Make scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Setup log file
sudo mkdir -p /var/log
sudo touch /var/log/jellyfin-sync.log
sudo chown $USER:$USER /var/log/jellyfin-sync.log

# Create cron job
echo "Setting up cron job to run every 15 minutes..."

# Remove any existing cron job for this script
(crontab -l 2>/dev/null | grep -v "sync-from-github.sh" | crontab -) || true

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE cd $PROJECT_DIR && $SYNC_SCRIPT >> /var/log/jellyfin-sync.log 2>&1") | crontab -

echo "✅ Automation setup complete!"
echo
echo "The system will now:"
echo "  - Check for GitHub updates every 15 minutes"
echo "  - Automatically pull changes and restart containers if needed"
echo "  - Log all activities to /var/log/jellyfin-sync.log"
echo
echo "To monitor the sync log:"
echo "  tail -f /var/log/jellyfin-sync.log"
echo
echo "To manually trigger a sync:"
echo "  $SYNC_SCRIPT"
echo
echo "To disable automation:"
echo "  crontab -e  # and remove the sync-from-github.sh line"
