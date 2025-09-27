# Jellyfin Media Server Setup

A comprehensive Jellyfin media server setup with IPTV support, automated playlist cleaning, and reverse proxy configuration. This project migrates from Plex to Jellyfin with enhanced features for IPTV streaming and EPG management.

## Features

- **Jellyfin Media Server**: Free and open-source media server
- **IPTV Support**: Stream live TV channels through m3u playlists
- **Automated Playlist Cleaning**: Remove dead/broken IPTV links automatically
- **EPG Integration**: Electronic Program Guide support
- **Reverse Proxy**: Nginx Proxy Manager for SSL and domain management
- **Docker Compose**: Easy deployment and management
- **GitHub Sync**: Automated deployment from GitHub commits

## Components

- **Jellyfin**: Media server for movies, TV shows, and live TV
- **Nginx Proxy Manager**: Reverse proxy with SSL certificate management
- **xTeve**: M3U proxy and EPG aggregator for IPTV
- **Python Scripts**: Automated playlist cleaning and EPG processing

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/thecroxdevil/jellyfin-setup.git
   cd jellyfin-setup
   ```

2. Create required directories:
   ```bash
   mkdir -p media/{movies,tv} config jellyfin_config xteve_config npm_data letsencrypt
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

5. Access your services:
   - Jellyfin: http://your-server:8096
   - Nginx Proxy Manager: http://your-server:81
   - xTeve: http://your-server:34400

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

- `PUID`: Your user ID (run `id -u` to get)
- `PGID`: Your group ID (run `id -g` to get)
- `TZ`: Your timezone (e.g., America/Vancouver)
- `JELLYFIN_PUBLISHED_SERVER_URL`: Your external server URL

### IPTV Setup

1. Add your M3U playlist to `xteve_config/`
2. Run playlist cleaner:
   ```bash
   python3 clean_m3u.py your_playlist.m3u
   ```
3. Configure xTeve to use the cleaned playlist
4. Set up Jellyfin to use xTeve as Live TV source

## Scripts

### Playlist Cleaner (`clean_m3u.py`)

Removes dead/broken links from M3U playlists:

```bash
python3 clean_m3u.py playlist.m3u -o cleaned_playlist.m3u -t 10 -w 20
```

Options:
- `-o, --output`: Output file (default: cleaned_input.m3u)
- `-r, --report`: Dead links report file
- `-t, --timeout`: URL test timeout in seconds (default: 10)
- `-w, --workers`: Number of concurrent workers (default: 20)
- `-v, --verbose`: Verbose output

### EPG Scraper (`epg_scraper.py`)

Process and clean EPG data for better compatibility.

### XMLTV Generator (`xmltv_generator.py`)

Generate XMLTV-compatible EPG files from various sources.

## Docker Services

### Jellyfin
- **Port**: 8096 (web interface)
- **Config**: `./jellyfin_config`
- **Media**: `./media`

### Nginx Proxy Manager
- **Ports**: 80 (HTTP), 443 (HTTPS), 81 (Admin)
- **Data**: `./npm_data`
- **SSL**: `./letsencrypt`

### xTeve
- **Port**: 34400
- **Config**: `./xteve_config`

## Automated Deployment

This project includes GitHub Actions for automated deployment:

1. **On Push**: Syncs code to server and restarts containers
2. **Health Check**: Monitors service status
3. **Error Reporting**: Notifies on deployment failures

### Setup Deployment

1. Add server details to GitHub Secrets:
   - `SERVER_HOST`: Your server IP/hostname
   - `SERVER_USER`: SSH username
   - `SERVER_SSH_KEY`: Private SSH key
   - `DEPLOY_PATH`: Path to deployment directory

2. The workflow will automatically:
   - Pull latest code
   - Restart Docker containers
   - Run health checks
   - Report status

## Migration from Plex

This project provides tools to migrate from Plex:

1. **Media Files**: Copy/move your existing media to `./media/`
2. **Playlists**: Use the playlist cleaner for IPTV channels
3. **Configuration**: Jellyfin setup wizard will guide you through

### Migration Script

```bash
python3 migrate_from_plex.py /path/to/plex/config ./jellyfin_config
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 8096, 80, 443, 81, 34400 are available
2. **Permissions**: Check PUID/PGID settings match your user
3. **SSL Issues**: Configure Nginx Proxy Manager for HTTPS
4. **IPTV Not Working**: Verify M3U playlist and xTeve configuration

### Logs

Check container logs:
```bash
docker-compose logs jellyfin
docker-compose logs nginx-proxy-manager
docker-compose logs xteve
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: GitHub Issues
- **Documentation**: Wiki
- **Community**: Discussions

## Acknowledgments

- Jellyfin Team for the amazing media server
- LinuxServer.io for Docker images
- Contributors and community members
