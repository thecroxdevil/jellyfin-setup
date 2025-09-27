#!/bin/bash

# Migration script from Plex to Jellyfin
# Helps migrate existing Plex configuration and media

set -e

# Configuration
PLEX_CONFIG_DIR="${1:-$HOME/plex-setup/config}"
JELLYFIN_CONFIG_DIR="${2:-./jellyfin_config}"
PLEX_MEDIA_DIR="${3:-$HOME/plex-setup/media}"
JELLYFIN_MEDIA_DIR="${4:-./media}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Plex to Jellyfin Migration Tool${NC}"
echo "=================================="
echo
echo "Plex Config: $PLEX_CONFIG_DIR"
echo "Jellyfin Config: $JELLYFIN_CONFIG_DIR"
echo "Plex Media: $PLEX_MEDIA_DIR"
echo "Jellyfin Media: $JELLYFIN_MEDIA_DIR"
echo

# Check if Plex directories exist
if [ ! -d "$PLEX_CONFIG_DIR" ]; then
    echo -e "${RED}❌ Plex config directory not found: $PLEX_CONFIG_DIR${NC}"
    exit 1
fi

# Create Jellyfin directories
echo -e "${YELLOW}📁 Creating Jellyfin directories...${NC}"
mkdir -p "$JELLYFIN_CONFIG_DIR"
mkdir -p "$JELLYFIN_MEDIA_DIR"/{movies,tv,music,photos}

# Function to migrate media library structure
migrate_media() {
    echo -e "${BLUE}📺 Migrating media files...${NC}"
    
    if [ -d "$PLEX_MEDIA_DIR" ]; then
        # Copy or create symbolic links to media files
        read -p "Do you want to copy files or create symbolic links? (copy/link): " choice
        
        case $choice in
            copy)
                echo "Copying media files (this may take a while)..."
                cp -r "$PLEX_MEDIA_DIR"/* "$JELLYFIN_MEDIA_DIR"/ 2>/dev/null || echo "Some files could not be copied"
                ;;
            link)
                echo "Creating symbolic links to media files..."
                for dir in movies tv music; do
                    if [ -d "$PLEX_MEDIA_DIR/$dir" ]; then
                        ln -sf "$PLEX_MEDIA_DIR/$dir"/* "$JELLYFIN_MEDIA_DIR/$dir"/ 2>/dev/null || true
                    fi
                done
                ;;
            *)
                echo "Invalid choice, skipping media migration"
                ;;
        esac
    else
        echo -e "${YELLOW}⚠️ Plex media directory not found, skipping...${NC}"
    fi
}

# Function to extract Plex preferences
extract_plex_preferences() {
    echo -e "${BLUE}⚙️ Extracting Plex preferences...${NC}"
    
    local plex_prefs="$PLEX_CONFIG_DIR/Library/Application Support/Plex Media Server/Preferences.xml"
    
    if [ -f "$plex_prefs" ]; then
        echo "Found Plex preferences, extracting useful settings..."
        
        # Extract server name
        SERVER_NAME=$(grep -o 'FriendlyName="[^"]*"' "$plex_prefs" 2>/dev/null | sed 's/FriendlyName="//;s/"//' || echo "Jellyfin Server")
        
        # Extract timezone
        TIMEZONE=$(grep -o 'ScheduledLibraryUpdatesEnabled="[^"]*"' "$plex_prefs" 2>/dev/null || echo "")
        
        # Create Jellyfin configuration suggestions
        cat > jellyfin-migration-notes.txt << EOF
# Jellyfin Migration Notes
# Generated from Plex configuration

Server Name: $SERVER_NAME
Extracted from: $plex_prefs

## Recommended Jellyfin Settings:
1. Set server name to: "$SERVER_NAME"
2. Configure timezone in docker-compose.yml
3. Review media library paths
4. Set up user accounts (Jellyfin doesn't migrate users)

## Media Library Mapping:
- Movies: $JELLYFIN_MEDIA_DIR/movies
- TV Shows: $JELLYFIN_MEDIA_DIR/tv  
- Music: $JELLYFIN_MEDIA_DIR/music
- Photos: $JELLYFIN_MEDIA_DIR/photos

## Next Steps:
1. Start Jellyfin container: docker-compose up -d
2. Open Jellyfin web UI: http://your-server:8096
3. Complete the setup wizard
4. Add media libraries pointing to the directories above
5. Create user accounts
