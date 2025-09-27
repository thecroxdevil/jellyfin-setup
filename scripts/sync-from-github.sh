#!/bin/bash

# GitHub sync script for Jellyfin setup
# This script pulls changes from GitHub and restarts services if needed

set -e

# Configuration
REPO_URL="https://github.com/thecroxdevil/jellyfin-setup.git"
BRANCH="main"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && dirname "$(pwd)")"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
RESTART_CONTAINERS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$TIMESTAMP] $1"
}

# Error handling
handle_error() {
    log "${RED}❌ Error occurred during sync: $1${NC}"
    exit 1
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    log "${YELLOW}⚠️ Not a git repository, initializing...${NC}"
    git init
    git remote add origin "$REPO_URL" || true
fi

# Change to project directory
cd "$PROJECT_DIR" || handle_error "Cannot change to project directory"

log "${BLUE}🔄 Starting GitHub sync...${NC}"

# Fetch latest changes
log "Fetching latest changes from GitHub..."
git fetch origin "$BRANCH" || handle_error "Failed to fetch from GitHub"

# Check if there are new commits
LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_HASH=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

if [ "$LOCAL_HASH" == "$REMOTE_HASH" ]; then
    log "${GREEN}✅ Already up to date${NC}"
    exit 0
fi

log "${YELLOW}📥 New changes detected, updating...${NC}"

# Backup current configuration
log "Creating backup of current configuration..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
cp .env "$BACKUP_DIR/" 2>/dev/null || true

# Check what files have changed
CHANGED_FILES=$(git diff --name-only HEAD "origin/$BRANCH" || echo "")

# Determine if containers need restart
if echo "$CHANGED_FILES" | grep -qE "(docker-compose\.yml|\.env|scripts/)"; then
    RESTART_CONTAINERS=true
    log "${YELLOW}🔄 Container restart required due to configuration changes${NC}"
fi

# Pull changes
log "Pulling changes from GitHub..."
git reset --hard "origin/$BRANCH" || handle_error "Failed to pull changes"

# Install/update Python dependencies if requirements.txt changed
if echo "$CHANGED_FILES" | grep -q "requirements.txt"; then
    log "📦 Updating Python dependencies..."
    python3 -m pip install --user -r requirements.txt || log "${YELLOW}⚠️ Some dependencies failed to install${NC}"
fi

# Create required directories
log "📁 Ensuring required directories exist..."
mkdir -p media/{movies,tv,music,photos} jellyfin_config xteve_config npm_data letsencrypt

# Set permissions
log "🔐 Setting permissions..."
sudo chown -R $USER:$USER . 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# Run pre-sync script if exists
if [ -f "scripts/pre-sync.sh" ]; then
    log "🔧 Running pre-sync tasks..."
    bash scripts/pre-sync.sh || log "${YELLOW}⚠️ Pre-sync script failed${NC}"
fi

# Restart containers if needed
if [ "$RESTART_CONTAINERS" = true ]; then
    log "🔄 Restarting containers..."
    
    # Stop containers
    log "⏹️ Stopping containers..."
    docker-compose down || log "${YELLOW}⚠️ Failed to stop some containers${NC}"
    
    # Pull latest images
    log "📦 Pulling latest Docker images..."
    docker-compose pull || log "${YELLOW}⚠️ Failed to pull some images${NC}"
    
    # Start containers
    log "▶️ Starting containers..."
    docker-compose up -d || handle_error "Failed to start containers"
    
    # Wait for services to be ready
    log "⏳ Waiting for services to start..."
    sleep 30
    
    # Run health check
    log "🏥 Running health check..."
    if [ -f "scripts/health-check.sh" ]; then
        bash scripts/health-check.sh || log "${YELLOW}⚠️ Health check issues detected${NC}"
    fi
else
    log "${GREEN}✅ No container restart needed${NC}"
fi

# Run post-sync script if exists
if [ -f "scripts/post-sync.sh" ]; then
    log "✅ Running post-sync tasks..."
    bash scripts/post-sync.sh || log "${YELLOW}⚠️ Post-sync script failed${NC}"
fi

# Send notification if webhook is configured
if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
    COMMIT_MSG=$(git log -1 --pretty=format:"%s" || echo "Sync completed")
    curl -H "Content-Type: application/json" -d "{\"content\":\"🚀 Jellyfin setup updated: $COMMIT_MSG\"}" "$DISCORD_WEBHOOK_URL" 2>/dev/null || true
fi

log "${GREEN}🎉 GitHub sync completed successfully!${NC}"

# Show container status
if [ "$RESTART_CONTAINERS" = true ]; then
    log "${BLUE}📊 Container status:${NC}"
    docker-compose ps
fi

exit 0
