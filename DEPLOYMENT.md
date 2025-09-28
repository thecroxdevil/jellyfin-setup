# Deployment Guide

This guide explains how to set up automatic deployment for the Jellyfin Media Server setup using GitHub Actions.

## Prerequisites

- A Linux server with Docker and Docker Compose installed
- SSH access to your deployment server
- A GitHub repository with this codebase

## GitHub Secrets Configuration

The deployment workflow requires several secrets to be configured in your GitHub repository. These secrets contain sensitive information and should never be committed to your repository.

### Setting up Secrets

1. Go to your GitHub repository
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each required secret

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SERVER_HOST` | IP address or hostname of your deployment server | `192.168.1.100` or `myserver.example.com` |
| `SERVER_USER` | SSH username for your server | `ubuntu`, `root`, or your username |
| `SERVER_SSH_KEY` | Private SSH key for authentication | Contents of `~/.ssh/id_rsa` |

### Optional Secrets

| Secret Name | Description | Default Value |
|-------------|-------------|---------------|
| `SERVER_PORT` | SSH port for your server | `22` |
| `DEPLOY_PATH` | Deployment directory on your server | `/home/thecroxdevil/jellyfin-setup` |
| `SLACK_WEBHOOK_URL` | Webhook URL for Slack notifications | Not set |

## SSH Key Setup

### 1. Generate SSH Key Pair (if you don't have one)

On your local machine or any machine with SSH access:

```bash
ssh-keygen -t rsa -b 4096 -C "github-actions@yourdomain.com"
```

This creates:
- `~/.ssh/id_rsa` (private key)
- `~/.ssh/id_rsa.pub` (public key)

### 2. Add Public Key to Server

Copy the public key to your deployment server:

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub user@your-server-ip
```

Or manually add it to `~/.ssh/authorized_keys` on your server:

```bash
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Add Private Key to GitHub Secrets

1. Copy the **entire** private key:
   ```bash
   cat ~/.ssh/id_rsa
   ```
2. Copy the output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)
3. Add it as the `SERVER_SSH_KEY` secret in GitHub

## Server Setup

Your deployment server should have:

1. **Docker and Docker Compose installed**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```

2. **Git installed**:
   ```bash
   sudo apt update
   sudo apt install git -y
   ```

3. **Python 3 and pip**:
   ```bash
   sudo apt install python3 python3-pip -y
   ```

4. **Repository cloned** in the deployment directory:
   ```bash
   git clone https://github.com/yourusername/jellyfin-setup.git /home/thecroxdevil/jellyfin-setup
   cd /home/thecroxdevil/jellyfin-setup
   ```

## Deployment Process

The GitHub Action will automatically deploy when you push to the `main` branch. The deployment process:

1. **Validates secrets** - Ensures all required configuration is present
2. **Runs tests** - Executes any available tests
3. **Connects to server** - Uses SSH to connect to your deployment server
4. **Updates code** - Pulls the latest changes from the repository
5. **Installs dependencies** - Updates Python packages
6. **Creates directories** - Sets up required media and config directories
7. **Updates containers** - Stops, pulls, and restarts Docker containers
8. **Runs health checks** - Verifies services are running correctly
9. **Sends notifications** - Notifies about deployment status (if configured)

## Directory Structure on Server

The deployment creates the following directory structure:

```
/home/thecroxdevil/jellyfin-setup/
├── docker-compose.yml
├── requirements.txt
├── scripts/
│   ├── health-check.sh
│   ├── pre-deploy.sh (optional)
│   └── post-deploy.sh (optional)
├── media/
│   ├── movies/
│   ├── tv/
│   ├── music/
│   └── photos/
├── jellyfin_config/
├── xteve_config/
├── npm_data/
└── letsencrypt/
```

## Troubleshooting

### Common Issues

1. **"missing server host" error**
   - Ensure `SERVER_HOST` secret is configured in GitHub
   - Check that the secret value is not empty

2. **SSH connection failed**
   - Verify SSH key is correctly formatted (includes begin/end markers)
   - Test SSH connection manually: `ssh -i ~/.ssh/id_rsa user@server`
   - Check that the public key is in `~/.ssh/authorized_keys` on the server

3. **Permission denied**
   - Ensure the deployment user has sudo access (if needed)
   - Check file permissions on the server
   - Verify Docker group membership: `groups $USER`

4. **Port conflicts**
   - Check if ports 8096 (Jellyfin), 34400 (xTeVe) are available
   - Stop conflicting services: `sudo netstat -tlnp | grep :8096`

### Manual Deployment

If automatic deployment fails, you can deploy manually:

```bash
# On your server
cd /home/thecroxdevil/jellyfin-setup
git pull origin main
pip3 install -r requirements.txt --user
docker-compose down
docker-compose pull
docker-compose up -d
```

### Logs and Debugging

Check deployment logs:
- GitHub Actions logs: Go to your repository → Actions → Select the workflow run
- Server logs: `docker-compose logs -f`
- Individual service logs: `docker-compose logs jellyfin`, `docker-compose logs xteve`

## Security Notes

- Never commit secrets to your repository
- Use strong SSH keys (RSA 4096-bit or ED25519)
- Regularly rotate SSH keys and secrets
- Consider using a dedicated deployment user with limited privileges
- Keep your server and Docker images updated

## Custom Deployment Scripts

You can add custom pre and post-deployment scripts:

- `scripts/pre-deploy.sh` - Runs before containers are updated
- `scripts/post-deploy.sh` - Runs after containers are started

These scripts should be executable (`chmod +x scripts/*.sh`) and will be executed automatically if they exist.

Test