# Isolated Claude Code Development Container

**Date:** 2025-12-04
**Status:** Design Adapted for claude-code-toolbox, Ready for Implementation

## Overview

This devcontainer configuration runs Claude Code in an isolated filesystem while maintaining host network access. It contains blast radius rather than hardening security—Claude Code affects only explicitly mounted volumes. The container automatically includes the claude-code-toolbox plugin through the `~/.claude` mount.

## Problem Statement

Running Claude Code directly on the host with `--dangerously-skip-permissions` lets Claude modify any file on the system, risking files not under version control. We need isolation that:

- Confines Claude's destructive behavior to specific mounted volumes
- Reaches VPN and localhost services through host network
- Delivers a repeatable, clean environment for each session
- Integrates with existing ~/.claude configuration (including installed toolbox plugin)

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

**Mounted volumes (read/write):**
1. `~/.claude → /home/claude-user/.claude` - Configuration, skills, agents, **installed toolbox plugin**
2. `<project-dir> → /workspace` - Repository being worked on
3. Named volume for command history - Persists bash history across sessions

**Ephemeral:**
- Everything else in the container is disposable
- Clean slate on each launch

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
│   ├── Dockerfile           # Container image definition
│   ├── devcontainer.json    # VS Code devcontainer config
│   └── claude-isolated      # CLI wrapper script
└── docs/
    ├── plans/
    │   └── 2025-12-04-devcontainer-design-adapted.md  # This document
    └── devcontainer.md      # Detailed usage guide
```

Main README updated with quick start section.

### CLI Usage Flow

1. User runs: `claude-isolated /path/to/repo`
2. Script validates path exists
3. Script builds image if absent (passes HOST_UID/GID)
4. Script creates history volume if absent
5. Podman launches container with:
   - Host network
   - ~/.claude mounted (includes toolbox plugin)
   - Project directory mounted to /workspace
   - History volume mounted
   - Interactive terminal
   - Auto-remove on exit
6. Shell opens at /workspace
7. User runs `claude` commands (toolbox agents/skills/commands available)

### VS Code Usage Flow

1. Open project in VS Code
2. Command Palette → "Dev Containers: Reopen in Container"
3. Browse to `~/.claude/plugins/claude-code-toolbox/devcontainer/devcontainer.json`
4. VS Code builds and launches container
5. Work normally, Claude Code + toolbox available in integrated terminal

## Component Specifications

### Dockerfile

**Base:** `registry.access.redhat.com/ubi9/ubi-minimal:latest`

**Build arguments:**
- `HOST_UID` - User ID from host
- `HOST_GID` - Group ID from host
- `CLAUDE_CODE_VERSION` - Optional version pin (defaults to latest)

**User setup:**
- Create `claude-user` with matching UID/GID
- Grant sudo access for package installation if needed
- Set as default user

**Installation steps:**
1. Install system packages via microdnf
2. Create directory structure (/workspace, /commandhistory, ~/.claude)
3. Install Claude Code via universal installer script
4. Configure bash history persistence
5. Set working directory to /workspace

### CLI Wrapper Script (claude-isolated)

**Location:** `devcontainer/claude-isolated`
**Symlink:** `~/.local/bin/claude-isolated` (user creates during setup)

**Arguments:**
- `$1` - Required: Path to project directory

**Behavior:**
1. Validate project path exists and is directory
2. Check if image exists, build if not:
   - Image name: `localhost/claude-isolated:latest`
   - Pass `--build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g)`
3. Check if history volume exists, create if not:
   - Volume name: `claude-isolated-history`
4. Run podman:
   ```bash
   podman run -it --rm \
     --network=host \
     -v ~/.claude:/home/claude-user/.claude \
     -v <project-path>:/workspace \
     -v claude-isolated-history:/commandhistory \
     -w /workspace \
     localhost/claude-isolated:latest
   ```
5. Drop to interactive bash shell

### VS Code devcontainer.json

**Location:** `devcontainer/devcontainer.json`

**Key configuration:**
- `build.dockerfile`: Points to Dockerfile
- `build.args`: Pass HOST_UID, HOST_GID
- `runArgs`: `["--network=host"]`
- `remoteUser`: `"claude-user"`
- `workspaceFolder`: `"/workspace"`
- `mounts`: Array defining ~/.claude, workspace, history volume
- `customizations.vscode.extensions`: Can add Claude Code extension if desired

## What Persists vs. What's Ephemeral

### Persists (survives container removal)
- ~/.claude configuration (host mount) - includes toolbox plugin
- Project files (host mount)
- Bash history (named volume)

### Ephemeral (lost on container removal)
- Installed packages (beyond what's in image)
- Temporary files
- Container home directory contents (except mounted dirs)
- Any files created outside mounted volumes

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
   ln -s $(pwd)/devcontainer/claude-isolated ~/.local/bin/claude-isolated
   ```

3. Ensure `~/.local/bin` is in PATH

4. First invocation builds the image (may take a few minutes)

5. Subsequent launches are fast

## Testing Plan

### Unit Tests
- Script validates invalid paths correctly
- Script handles missing image/volume appropriately
- Script constructs correct podman command

### Integration Tests
- Build image successfully
- Launch container and verify mounts
- Verify file ownership matches host
- Verify Claude Code is accessible and functional
- Verify toolbox plugin is available (agents, skills, commands work)
- Verify host network access (can reach VPN resources)
- Verify bash history persists across sessions

### End-to-End Tests
- Complete workflow: launch container, run claude commands with toolbox skills/agents, modify files, verify changes on host
- VS Code: Open in container, use Claude Code with toolbox, verify functionality
- Multi-project: Use same container image with different projects

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
- Simple, focused implementation
- Familiar RHEL tooling
- Transparent file ownership
- Full network access
- Repeatable environment
- Toolbox plugin automatically available

**Trade-offs accepted:**
- Security isolation omitted by design
- Podman-only initially
- Tool updates require image rebuild
- Startup slightly slower than native (negligible)
- UBI minimal may need additional packages for some projects

## Success Criteria

Implementation succeeds when:
1. CLI wrapper launches container with correct mounts
2. Host user owns files created by Claude
3. Claude Code reaches VPN resources through host network
4. Bash history persists across sessions
5. Toolbox plugin agents/skills/commands are available in container
6. VS Code integration works with devcontainer.json
7. Container affects only mounted volumes
8. Documentation enables understanding and troubleshooting

## References

- [Red Hat Universal Base Images](https://developers.redhat.com/products/rhel/ubi)
- [UBI Minimal Catalog](https://catalog.redhat.com/en/software/containers/ubi9/ubi-minimal)
- [Claude Code Native Installation](https://code.claude.com/docs/en/setup)
- [DevContainers Images](https://github.com/devcontainers/images)
- [DevContainers Specification](https://containers.dev/)
