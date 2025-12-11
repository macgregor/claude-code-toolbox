---
name: devcontainer
description: >
  Use when setting up filesystem isolation for plugin development or working with
  untrusted projects. Covers CLI and VS Code usage, customization, and architecture.
categories: [workflow, development]
tags: [isolation, containers, podman, testing]
related_docs:
  - CONTRIBUTING.md
complexity: intermediate
---

# Devcontainer

Filesystem-isolated Claude Code environment. Claude operates in a container with access only to your project directory—your host filesystem remains untouched. Config files (CLAUDE.md, skills, agents) sync from localhost via symlinks.

**Use this when:**
- Testing plugin changes without polluting host `~/.claude`
- Working on projects with unknown safety
- Needing a clean environment that persists across sessions

**Provides:**
- Filesystem isolation (only project directory is writable)
- Full network access (host network mode for VPN/localhost)
- Persistent `~/.claude` on named volume
- Localhost config sync (CLAUDE.md, skills, agents, commands, hooks)

**Doesn't provide:**
- Security hardening
- Network isolation
- Protection from malicious code

This contains accidents, not attacks.

## Architecture

**Isolation**: Container runs on named volume `claude-home` containing isolated `~/.claude` state. Your project mounts at `/workspace` (read/write). Localhost `~/.claude` mounts read-only at `/mnt/localhost-claude`—entrypoint script creates symlinks to sync select configs.

**User mapping**: Container user matches host UID/GID via `--userns=keep-id`. Files Claude creates in `/workspace` are owned by you on the host.

**Network**: Uses `--network=host` for unrestricted access to VPN resources and localhost services.

**Build caching**: Containerfile uses version pins for Claude Code and gcloud. UID/GID build args declared late to maximize cache hits.

## Usage

See [CONTRIBUTING.md](../CONTRIBUTING.md#isolated-development) for installation steps.

### CLI

```bash
claude-isolated /path/to/project
```

First run builds image and creates volume. Subsequent runs use cached image.

**Attach additional shell:**
```bash
claude-isolated-shell /path/to/project
```

Useful for running debug tools or monitoring while Claude operates.

**Rebuild:**
```bash
claude-isolated --rebuild /path/to/project
```

Use when:
- Adding tools to Containerfile
- Fixing permission errors
- Claude Code not working

### VS Code

1. Command Palette → "Dev Containers: Reopen in Container"
2. Select devcontainer.json from plugin directory
3. VS Code builds and attaches

**Note**: VS Code requires `~/.claude` and `~/.claude.json` to exist. Create empty placeholders if missing:
```bash
mkdir -p ~/.claude && touch ~/.claude.json
```

**Podman users**: Configure Dev Containers extension to use Podman instead of Docker:
```json
{
  "dev.containers.dockerPath": "podman"
}
```

## Customization

**Add tools**: Edit `devcontainer/Containerfile` and add packages to `microdnf install` line. Rebuild with `--rebuild`.

**Sync additional files**: Edit `LINKS` array in `devcontainer/scripts/entrypoint.sh`. Supports globs.

**Install marketplaces/plugins**: Edit `MARKETPLACES` and `PLUGINS` arrays in entrypoint script. Runs on every launch (idempotent).

**Vertex AI**: Container mounts `~/.config/gcloud` read-only. Configure on host, credentials sync automatically. Set `CLAUDE_CODE_USE_VERTEX`, `CLOUD_ML_REGION`, `ANTHROPIC_VERTEX_PROJECT_ID` environment variables on host.

## Implementation Details

**Volume mount strategy**:
- `claude-home` volume → `/home/claude-user` (persistent isolated state)
- `<project>` → `/workspace` (your repository, read/write)
- `~/.claude` → `/mnt/localhost-claude:ro` (config source)
- `~/.config/gcloud` → `/home/claude-user/.config/gcloud:ro` (Vertex AI credentials)
- `~/.gitconfig*` → `/home/claude-user/.gitconfig*:ro` (git identity)

**SELinux**: Enforcement disabled (`--security-opt label=disable`). Podman's `:z` relabel flag conflicts with `--userns=keep-id`.

**Container naming**: Uses MD5 hash of project path. Allows multiple isolated environments for different projects.
