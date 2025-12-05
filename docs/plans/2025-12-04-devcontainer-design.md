# Isolated Claude Code Development Container

**Date:** 2025-12-04
**Status:** Final Design - Isolated with Selective Config Sync

## Overview

This devcontainer configuration runs Claude Code in a fully isolated filesystem with selective config sync from localhost. It contains blast radius—Claude Code affects only the workspace directory. The container maintains its own `~/.claude` state on a persistent volume, with select localhost configs (CLAUDE.md, skills, agents, etc.) symlinked in for consistency.

## Problem Statement

Running Claude Code directly on the host with `--dangerously-skip-permissions` lets Claude modify any file on the system, risking files not under version control. Additionally, sharing localhost's `~/.claude` directory with containers creates path portability issues due to hardcoded absolute paths in plugin metadata and project configurations.

We need isolation that:

- Confines Claude's destructive behavior to the workspace directory only
- Maintains isolated `~/.claude` state (disposable, no localhost coupling)
- Selectively syncs desired localhost configs (CLAUDE.md, skills, agents, etc.)
- Reaches VPN and localhost services through host network
- Delivers a repeatable, clean environment with declarative plugin setup

## Design Decisions

### Container Runtime
- **Podman only** to align with Fedora/RHEL ecosystem
- Docker support deferred

### Base Image
- **registry.access.redhat.com/ubi9/ubi-minimal:latest**
- RHEL-based with familiar tooling (microdnf)
- Lighter than full Fedora, heavier than Alpine
- Freely redistributable, no subscription required
- Good balance for development containers

### Claude Code Installation
- **Native binary** via `curl -fsSL https://claude.ai/install.sh | bash`
- Self-contained executable without Node.js
- Better auto-updater support
- Add Node.js later for Node projects

### User Mapping
- **Match host UID/GID** for transparent file ownership
- Build-time args: `HOST_UID` and `HOST_GID`
- Container user: `claude-user` with matching IDs
- Host user owns files created in mounted volumes

### Network Configuration
- **Host network mode** (`--network=host`)
- Unrestricted access to VPN and localhost services
- Opposite of Anthropic's firewall approach
- Isolates filesystem, not network

### Volume Strategy

**Persistent volume:**
- `claude-home → /home/claude-user` - Isolated container state including `~/.claude`, bash history, all user data

**Read-only mounts from localhost:**
- `~/.claude → /mnt/localhost-claude:ro` - Source for selective config sync (not used directly by Claude)
- `~/.config/gcloud → /home/claude-user/.config/gcloud:ro` - GCloud credentials for Vertex AI

**Workspace mount (only writable localhost coupling):**
- `<project-dir> → /workspace` - Repository being worked on

**Config sync mechanism:**
- Entrypoint script creates symlinks from container's `~/.claude` → `/mnt/localhost-claude` for select files
- Synced items: CLAUDE.md, settings.json, skills/, agents/, commands/, hooks/
- Always fresh (symlinks to read-only mount)
- Modifiable by editing LINKS array in entrypoint script (requires rebuild)

**Ephemeral:**
- Everything else in the container is disposable
- Clean slate on each rebuild

### Pre-installed Tools
- git (required for Claude operations)
- Common dev tools: make, curl, wget, jq
- Text editors: vim, nano
- Python 3 (many projects need it)
- gh CLI (for GitHub operations)
- Basic utilities: less, procps, sudo

## Architecture

### Directory Structure

```
claude-code-toolbox/
├── devcontainer/
│   ├── Containerfile        # Container image definition
│   ├── devcontainer.json    # VS Code devcontainer config
│   └── scripts/
│       ├── claude-isolated  # CLI wrapper script
│       └── entrypoint.sh    # Container entrypoint (config linking + plugin setup)
└── docs/
    ├── plans/
    │   └── 2025-12-04-devcontainer-design.md  # This document
    └── devcontainer.md      # Detailed usage guide
```

Main README updated with quick start section.

### CLI Usage Flow

1. User runs: `claude-isolated /path/to/repo`
2. Script validates path exists
3. Script builds image if absent (passes HOST_UID/GID, bakes in entrypoint.sh)
4. Script creates `claude-home` volume if absent
5. Podman launches container with:
   - Host network
   - `claude-home` volume mounted at `/home/claude-user`
   - Localhost `~/.claude` mounted read-only at `/mnt/localhost-claude`
   - Localhost `~/.config/gcloud` mounted read-only
   - Project directory mounted to /workspace
   - Interactive terminal
   - Auto-remove on exit
6. Entrypoint script runs:
   - Creates symlinks for select localhost configs → container's `~/.claude`
   - Installs/updates marketplaces (idempotent)
   - Installs plugins (idempotent)
7. Shell opens at /workspace
8. User runs `claude` commands (localhost skills/agents/commands available via symlinks)

### VS Code Usage Flow

1. Open project in VS Code
2. Command Palette → "Dev Containers: Reopen in Container"
3. Browse to `~/.claude/plugins/claude-code-toolbox/devcontainer/devcontainer.json`
4. VS Code builds and launches container (same entrypoint as CLI)
5. Entrypoint runs automatically (config linking + plugin setup)
6. Work normally, Claude Code available with localhost skills/agents/commands

## Component Specifications

### Containerfile

**Base:** `registry.access.redhat.com/ubi9/ubi-minimal:latest`

**Build arguments:**
- `HOST_UID` - User ID from host
- `HOST_GID` - Group ID from host
- `CLAUDE_CODE_VERSION` - Version pin (default: 2.0.58)
- `GCLOUD_VERSION` - GCloud SDK version pin (default: 509.0.0)

**User setup:**
- Create `claude-user` with matching UID/GID
- Grant sudo access for package installation if needed
- Set as default user

**Installation steps:**
1. Install system packages via microdnf
2. Install Google Cloud SDK
3. Download Claude Code installer
4. Create `claude-user` with matching UID/GID
5. Create `/workspace` directory
6. Copy `entrypoint.sh` script into image
7. Switch to `claude-user`
8. Install Claude Code
9. Configure bash history and PATH
10. Set entrypoint to `entrypoint.sh`, default command to bash

### CLI Wrapper Script (claude-isolated)

**Location:** `devcontainer/scripts/claude-isolated`
**Symlink:** `~/.local/bin/claude-isolated` (user creates during setup)

**Arguments:**
- `$1` - Required: Path to project directory (defaults to current directory)

**Behavior:**
1. Validate project path exists and is directory
2. Check if image exists, build if not:
   - Image name: `localhost/claude-isolated:latest`
   - Pass `--build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g)`
   - Build context includes `entrypoint.sh`
3. Check if volume exists, create if not:
   - Volume name: `claude-home`
4. Run podman:
   ```bash
   podman run -it --rm \
     --network=host \
     --userns=keep-id \
     --security-opt=label=disable \
     -v claude-home:/home/claude-user \
     -v ~/.claude:/mnt/localhost-claude:ro \
     -v ~/.config/gcloud:/home/claude-user/.config/gcloud:ro \
     -v <project-path>:/workspace \
     -w /workspace \
     -e CLAUDE_CODE_USE_VERTEX \
     -e CLOUD_ML_REGION \
     -e ANTHROPIC_VERTEX_PROJECT_ID \
     -e DISABLE_AUTOUPDATER=1 \
     localhost/claude-isolated:latest
   ```
5. Entrypoint runs config linking and plugin setup
6. Drop to interactive bash shell

### VS Code devcontainer.json

**Location:** `devcontainer/devcontainer.json`

**Key configuration:**
- `build.dockerfile`: Points to Containerfile
- `build.args`: Pass HOST_UID, HOST_GID from environment
- `runArgs`: `["--network=host", "--userns=keep-id", "--security-opt=label=disable"]`
- `remoteUser`: `"claude-user"`
- `workspaceFolder`: `"/workspace"`
- `mounts`:
  - `claude-home` volume → `/home/claude-user`
  - Localhost `~/.claude` → `/mnt/localhost-claude` (read-only)
  - Localhost `~/.config/gcloud` → `/home/claude-user/.config/gcloud` (read-only)
- `containerEnv`: Pass Vertex AI environment variables
- `postCreateCommand`: Simple echo (entrypoint handles setup)

### Entrypoint Script

**Location:** `devcontainer/scripts/entrypoint.sh`
**Copied into image:** `/usr/local/bin/entrypoint.sh`

**Configuration arrays (modify these to change sync behavior - requires rebuild):**
- `LINKS`: Files/directories to symlink from localhost (supports globs)
  - Default: CLAUDE.md, settings.json, skills, agents, commands, hooks
- `MARKETPLACES`: Git URLs or owner/repo to install
  - Default: https://github.com/anthropics/claude-code-plugins
- `PLUGINS`: Plugins to install (name or name@marketplace)
  - Default: @anthropic/episodic-memory

**Behavior:**
1. Create symlinks for items in LINKS array from `/mnt/localhost-claude` to `~/.claude`
   - Supports globs (e.g., "agents/*.md")
   - Creates parent directories as needed
   - Skips items that don't exist on localhost
2. Install/update marketplaces (try add, fallback to update if already exists)
3. Install plugins (idempotent)
4. Execute command passed to container (default: bash)

## What Persists vs. What's Ephemeral

### Persists (survives container removal)
- Container's `~/.claude` (volume) - isolated plugin state, settings, history
- Bash history (volume, stored in `/home/claude-user`)
- Project files (host mount at `/workspace`)
- Localhost config files (host, read-only mounted)

### Ephemeral (lost on container removal)
- Nothing - `claude-home` volume persists everything in home directory

### Disposable by Choice
- Delete `claude-home` volume to reset container state completely
- Localhost configs remain safe (read-only mounts)
- Rebuild image to update entrypoint logic or base packages

## Documentation Plan

### docs/devcontainer.md

**Sections:**
1. **Introduction** - Why use isolated container
2. **Quick Start** - CLI and VS Code usage examples
3. **How It Works** - Architecture overview, toolbox plugin integration
4. **Advanced Usage** - Rebuilding image, version pinning
5. **Troubleshooting** - Common issues and solutions

### README.md Addition

Add section:
```markdown
## Isolated Development Container

Run Claude Code in an isolated container to limit blast radius when working on projects:

```bash
claude-isolated /path/to/repo
```

The container includes Claude Code with this toolbox plugin pre-loaded. See [devcontainer documentation](./docs/devcontainer.md) for setup and usage details.
```

## Installation & Setup

After implementation:

1. Clone this repo and install the plugin:
   ```bash
   git clone https://github.com/macgregor/claude-code-toolbox.git
   cd claude-code-toolbox
   claude plugin install .
   ```

2. Create symlink for CLI wrapper:
   ```bash
   ln -s $(pwd)/devcontainer/scripts/claude-isolated ~/.local/bin/claude-isolated
   ```

3. Ensure `~/.local/bin` is in PATH

4. First invocation builds the image (may take a few minutes)

5. Subsequent launches are fast

### Customizing Synced Config

To change which localhost files are synced:

1. Edit `devcontainer/scripts/entrypoint.sh`
2. Modify `LINKS`, `MARKETPLACES`, or `PLUGINS` arrays
3. Rebuild image: `podman image rm localhost/claude-isolated:latest`
4. Next launch will rebuild with new configuration

## Testing Plan

### Unit Tests
- Script validates invalid paths correctly
- Script handles missing image/volume appropriately
- Script constructs correct podman command
- Entrypoint creates symlinks correctly for various LINKS patterns
- Entrypoint handles missing localhost files gracefully

### Integration Tests
- Build image successfully with entrypoint baked in
- Launch container and verify volume mounts
- Verify file ownership matches host in `/workspace`
- Verify Claude Code is accessible and functional
- Verify localhost configs are symlinked (CLAUDE.md, skills, etc.)
- Verify localhost configs are read-only (can't modify source)
- Verify container's `~/.claude` is writable and isolated
- Verify plugins install successfully on first launch
- Verify plugins persist on subsequent launches
- Verify marketplace update works when re-adding existing marketplace
- Verify host network access (can reach VPN resources)
- Verify bash history persists across sessions

### End-to-End Tests
- Complete workflow: launch container, run claude commands, use localhost skills/agents, modify files, verify changes on host
- VS Code: Open in container, verify entrypoint runs, use Claude Code, verify functionality
- Multi-project: Use same volume with different projects
- Reset test: Delete `claude-home` volume, verify clean slate on next launch
- Config change test: Modify LINKS array, rebuild, verify new symlinks

## Future Enhancements

**Potential additions (not in initial version):**
- Docker support alongside Podman
- Node.js variant for Node project work
- Additional language runtimes (Go, Ruby, etc.) via variants
- Shell customization (zsh, oh-my-zsh, etc.)
- Resource limits (CPU, memory)
- Multiple simultaneous isolated environments
- Image auto-update mechanism

## Trade-offs

**Chosen approach advantages:**
- True isolation - container can't affect localhost `~/.claude`
- Disposable state - delete volume to reset completely
- Selective config sync - only sync what you need
- Always fresh configs - symlinks to read-only mounts
- Familiar RHEL tooling
- Transparent file ownership in `/workspace`
- Full network access
- Repeatable environment
- Declarative plugin setup

**Trade-offs accepted:**
- Security isolation omitted by design (host network, full VPN access)
- Podman-only initially
- Changing synced configs requires image rebuild
- Config changes on localhost visible immediately, but plugin changes need rebuild
- Startup slightly slower than native (entrypoint runs on every launch)
- UBI minimal may need additional packages for some projects
- Localhost symlinks in plugins/ won't work (but plugins/ isn't synced anyway)

## Success Criteria

Implementation succeeds when:
1. CLI wrapper launches container with correct volume and mounts
2. Container's `~/.claude` is isolated on persistent volume
3. Localhost configs (CLAUDE.md, skills, etc.) are symlinked and readable
4. Localhost configs cannot be modified from container (read-only enforcement)
5. Plugins install declaratively on first launch
6. Plugins persist across container restarts
7. Host user owns files created by Claude in `/workspace`
8. Claude Code reaches VPN resources through host network
9. Bash history persists across sessions
10. VS Code integration works with devcontainer.json
11. Container affects only `/workspace` on localhost
12. Deleting `claude-home` volume resets container state
13. Documentation enables understanding and troubleshooting

## Design Evolution

**Original approach (discarded):**
- Mounted localhost `~/.claude` directly into container
- Shared plugin state between localhost and container
- Problem: Hardcoded absolute paths in plugin metadata broke across environments

**Final approach (this design):**
- Container maintains isolated `~/.claude` on persistent volume
- Selective config sync via read-only mounts and symlinks
- Declarative plugin installation in container
- Only `/workspace` couples to localhost filesystem

**Key insight:** Path portability issues with Claude Code's plugin system made sharing `~/.claude` impractical. True isolation is simpler, safer, and more maintainable.

## References

- [Red Hat Universal Base Images](https://developers.redhat.com/products/rhel/ubi)
- [UBI Minimal Catalog](https://catalog.redhat.com/en/software/containers/ubi9/ubi-minimal)
- [Claude Code Native Installation](https://code.claude.com/docs/en/setup)
- [Claude Code Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [DevContainers Images](https://github.com/devcontainers/images)
- [DevContainers Specification](https://containers.dev/)
