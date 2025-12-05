# Isolated Claude Code Development Container

## What This Is

Run Claude Code in a container that limits filesystem access to your project directory. The container maintains an isolated `~/.claude` on a persistent volume and syncs select config files from localhost (CLAUDE.md, skills, agents). It uses host networking for VPN and localhost access but isolates the filesystem.

**Provides:**
- Filesystem isolation (Claude touches only mounted volumes)
- Full network access (host network mode)
- Fresh environment each launch
- Isolated `~/.claude` on persistent volume with selective localhost config sync

**Does not provide:**
- Security hardening
- Network isolation
- Protection from malicious code

This contains accidents, not attacks.

## Installation

### Prerequisites

- Podman installed
- `~/.local/bin` in your PATH
- (Optional) claude-code-toolbox plugin installed
- (Optional) Google Cloud CLI configured for Vertex AI authentication

### Google Vertex AI Setup

If your Claude Code billing model uses Vertex AI, configure Google Cloud CLI on the host system. The container mounts `~/.config/gcloud` to share credentials.

Install and authenticate:

```bash
# Install (Fedora)
sudo dnf install google-cloud-cli

# Or install (macOS)
brew install google-cloud-sdk

# Authenticate
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-quota-project>

# Set environment variables
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5
export ANTHROPIC_VERTEX_PROJECT_ID=<your-project-id>

# Make persistent (bash)
echo 'export CLAUDE_CODE_USE_VERTEX=1' >> ~/.bashrc
echo 'export CLOUD_ML_REGION=us-east5' >> ~/.bashrc
echo 'export ANTHROPIC_VERTEX_PROJECT_ID=<your-project-id>' >> ~/.bashrc

# Make persistent (zsh/macOS)
echo 'export CLAUDE_CODE_USE_VERTEX=1' >> ~/.zshrc
echo 'export CLOUD_ML_REGION=us-east5' >> ~/.zshrc
echo 'export ANTHROPIC_VERTEX_PROJECT_ID=<your-project-id>' >> ~/.zshrc
```

### Setup

```bash
# Clone and install the plugin
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
claude plugin install .

# Create CLI wrapper symlink
ln -s $(pwd)/devcontainer/scripts/claude-isolated ~/.local/bin/claude-isolated

# Verify
which claude-isolated
```

### Configure VS Code for Podman

The Dev Containers extension defaults to Docker. Configure it to use Podman:

```json
{
  "dev.containers.dockerPath": "podman"
}
```

## Usage

### CLI

```bash
claude-isolated /path/to/project
```

**First run:** Builds image (takes a few minutes), creates history volume, launches container.

**Subsequent runs:** Uses cached image, launches immediately.

**Multiple sessions:** Run multiple sessions simultaneously. They share bash history safely via `histappend`.

**Inside the container:**
- Project at `/workspace`
- Claude Code available via `claude` command
- Localhost agents, skills, commands available via symlinks
- Exit with `exit` or Ctrl+D

### VS Code

1. Open project in VS Code
2. Command Palette → "Dev Containers: Reopen in Container"
3. Browse to `~/.claude/plugins/claude-code-toolbox/devcontainer/devcontainer.json`
4. VS Code builds and launches container
5. Use Claude Code in integrated terminal

**Note:** VS Code requires `~/.claude` and `~/.claude.json` to exist. The `devcontainer.json` specification doesn't support conditional mounts. Create empty placeholders if needed:

```bash
mkdir -p ~/.claude
touch ~/.claude.json
```

**Rebuild:** Command Palette → "Dev Containers: Rebuild Container"

## How It Works

### Mounts

**Read/write:**
- `claude-home` → `/home/claude-user` (isolated container state: `~/.claude`, bash history, all user data)
- `<project-dir>` → `/workspace` (your repository)

**Read-only:**
- `~/.claude` → `/mnt/localhost-claude:ro` (source for selective config sync via symlinks)
- `~/.config/gcloud` → `/home/claude-user/.config/gcloud:ro` (GCloud credentials for Vertex AI)

**Ephemeral:**
- Everything else (container state persists on `claude-home` volume)

### User Mapping

Container user `claude-user` matches your host UID/GID via `--userns=keep-id`. Files created by Claude are owned by you on the host.

### SELinux

SELinux enforcement is disabled (`--security-opt label=disable`). Podman's `:z` relabel flag conflicts with `--userns=keep-id`. Disabling SELinux enforcement resolves permission errors while preserving UID/GID-based access control.

### Network

Uses `--network=host` for unrestricted network access. Reaches VPN resources and localhost services.

## Rebuilding

Rebuild the image and recreate the history volume:

```bash
claude-isolated --rebuild /path/to/project
```

The script stops any running containers using the volume before removal, allowing `--rebuild` to work without manual cleanup.

Use this when:
- Your UID/GID changed
- Adding tools to `Containerfile`
- Fixing permission errors
- History not persisting
- Claude Code not working

## Adding Tools to the Image

Edit `devcontainer/Containerfile` and add packages to the `microdnf install` line:

```dockerfile
RUN microdnf install -y \
    git \
    make \
    # ... existing packages ...
    nodejs \
    && microdnf clean all
```

Rebuild with `--rebuild` flag.
