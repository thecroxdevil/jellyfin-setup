#!/bin/bash

echo "🏥 Running Jellyfin Setup Health Checks"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health check results
HEALTH_STATUS=0

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2
    local path=${3:-""}
    
    echo -n "Checking $service_name... "
    
    if docker-compose ps | grep -q "$service_name.*Up"; then
        if curl -f -s "http://localhost:$port$path" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Running${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ Container up but service not responding${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    echo -n "Checking disk space... "
    
    # Get available space in GB
    AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$AVAILABLE_GB" -gt 5 ]; then
        echo -e "${GREEN}✓ ${AVAILABLE_GB}GB available${NC}"
        return 0
    elif [ "$AVAILABLE_GB" -gt 1 ]; then
        echo -e "${YELLOW}⚠ Only ${AVAILABLE_GB}GB available${NC}"
        return 1
    else
        echo -e "${RED}✗ Critical: Only ${AVAILABLE_GB}GB available${NC}"
        return 1
    fi
}

# Function to check Docker status
check_docker() {
    echo -n "Checking Docker... "
    
    if systemctl is-active --quiet docker; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to check file permissions
check_permissions() {
    echo -n "Checking file permissions... "
    
    local errors=0
    
    # Check if directories are writable
    for dir in "jellyfin_config" "xteve_config" "npm_data" "media"; do
        if [ ! -w "$dir" ] 2>/dev/null; then
            errors=$((errors + 1))
        fi
    done
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ All directories writable${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Some permission issues found${NC}"
        return 1
    fi
}

# Function to check container logs for errors
check_container_logs() {
    local service_name=$1
    echo -n "Checking $service_name logs... "
    
    local error_count=$(docker-compose logs --tail=50 "$service_name" 2>/dev/null | grep -i -c "error\|fail\|exception" || echo "0")
    
    if [ "$error_count" -eq 0 ]; then
        echo -e "${GREEN}✓ No errors in recent logs${NC}"
        return 0
    elif [ "$error_count" -lt 5 ]; then
        echo -e "${YELLOW}⚠ $error_count errors in recent logs${NC}"
        return 1
    else
        echo -e "${RED}✗ $error_count errors in recent logs${NC}"
        return 1
    fi
}

# Function to test IPTV playlist
check_iptv_playlist() {
    echo -n "Checking IPTV playlist... "
    
    if [ -f "xteve_config/playlist.m3u" ] || [ -f "xteve_config/cleaned_playlist.m3u" ]; then
        echo -e "${GREEN}✓ Playlist file found${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ No playlist file found${NC}"
        return 1
    fi
}

# Main health checks
echo "Starting health checks..."
echo

# Check Docker daemon
check_docker || HEALTH_STATUS=1

echo

# Check disk space
check_disk_space || HEALTH_STATUS=1

echo

# Check file permissions
check_permissions || HEALTH_STATUS=1

echo

# Check services
echo "Service Health Checks:"
echo "---------------------"

check_service "jellyfin" "8096" "/health" || HEALTH_STATUS=1
check_service "nginx-proxy-manager" "81" || HEALTH_STATUS=1
check_service "xteve" "34400" || HEALTH_STATUS=1

echo

# Check container logs
echo "Container Log Checks:"
echo "--------------------"

check_container_logs "jellyfin" || HEALTH_STATUS=1
check_container_logs "nginx-proxy-manager" || HEALTH_STATUS=1
check_container_logs "xteve" || HEALTH_STATUS=1

echo

# Check IPTV setup
echo "IPTV Setup Check:"
echo "-----------------"
check_iptv_playlist || HEALTH_STATUS=1

echo

# Summary
echo "Health Check Summary:"
echo "===================="

if [ $HEALTH_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    echo "Your Jellyfin setup is running smoothly."
else
    echo -e "${YELLOW}⚠️ Some health checks failed.${NC}"
    echo "Please review the issues above."
fi

echo
echo "Quick Access URLs:"
echo "- Jellyfin Web UI: http://$(hostname -I | awk '{print $1}'):8096"
echo "- Nginx Proxy Manager: http://$(hostname -I | awk '{print $1}'):81"
echo "- xTeve: http://$(hostname -I | awk '{print $1}'):34400"

exit $HEALTH_STATUS
