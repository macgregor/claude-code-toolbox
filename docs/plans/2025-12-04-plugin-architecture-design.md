# Claude Code Toolbox Plugin Architecture Design

**Date:** 2025-12-04
**Status:** Validated

## Historical Context
I started out building a similar "ai-toolbox" repo not publicly published that quickly became a mess. I needed to move the claude specific parts to a public repo and adapt some hacky stuff to the claude code plugin system which i was unaware of initially. 

I did a planning session with Claude who had access to this private repo to come up with a migration plan.

## Problem

The ai-toolbox repo currently symlinks `~/.claude` to the entire repo directory. This approach causes two problems:

1. Claude Code state files (debug/, file-history/, history.jsonl) pollute the repo
2. The .gitignore must exclude these state files, adding maintenance burden

The installation also bundles work-specific content (RHOAISTRAT-752/) with shareable Claude Code configuration.

## Solution

Convert the shareable Claude Code configuration into a proper plugin. Separate personal context (CLAUDE.md) from the plugin using a simple symlink.

## Repository Structure

```
claude-code-toolbox/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest with MCP config
├── agents/                   # Custom agents
├── skills/                   # Agent skills
├── commands/                 # Slash commands
├── hooks/
│   └── hooks.json           # Hook definitions
├── scripts/                  # Scripts called by hooks
├── docs/                     # Documentation
├── CLAUDE.md                 # Personal context (symlinked separately)
└── README.md                 # Installation and usage
```

## Migration from ai-toolbox

**Move to new repo:**
- `ai-toolbox/claude/agents/` → `agents/`
- `ai-toolbox/claude/skills/` → `skills/`
- `ai-toolbox/claude/commands/` → `commands/`
- `ai-toolbox/claude/hooks/` → `hooks/` + `scripts/`
- `ai-toolbox/claude/.mcp.json` contents → `plugin.json` mcpServers section
- `ai-toolbox/claude/CLAUDE.md` → `CLAUDE.md`

**Leave in ai-toolbox:**
- RHOAISTRAT-752/ (work-specific)
- Runtime state directories (debug/, file-history/, etc.)

## Plugin Manifest

The `plugin.json` uses explicit paths for all components:

```json
{
  "name": "claude-code-toolbox",
  "version": "1.0.0",
  "description": "Agents, skills, commands, and MCP servers for productive Claude Code workflows",
  "author": {
    "name": "Matthew Stratto"
  },
  "homepage": "https://github.com/macgregor/claude-code-toolbox",
  "repository": "https://github.com/macgregor/claude-code-toolbox",
  "license": "MIT",

  "agents": [
    "./agents/code-reviewer.md"
  ],
  "skills": [
    "./skills/brainstorming/SKILL.md",
    "./skills/executing-plans/SKILL.md",
    "./skills/writing-plans/SKILL.md"
  ],
  "commands": [
    "./commands/brainstorm.md",
    "./commands/execute-plan.md",
    "./commands/write-plan.md"
  ],

  "mcpServers": {
    "mcp-atlassian": { ... },
    "github": { ... },
    "gdrive": { ... },
    "chrome-devtools": { ... }
  }
}
```

MCP servers are configured directly in plugin.json, not in a separate .mcp.json file. This follows the pattern used by the episodic-memory plugin.

## Hooks Configuration

The `hooks/hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` to reference scripts:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/episodic-memory-sync-wrapper.sh",
            "async": true
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "mcp__chrome-devtools__*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/ensure-chrome-debug.sh"
          }
        ]
      }
    ]
  }
}
```

Both hook scripts migrate from ai-toolbox:
- `episodic-memory-sync-wrapper.sh` - Background sync wrapper for episodic-memory plugin
- `ensure-chrome-debug.sh` - Ensures Chrome runs with remote debugging for MCP

## Installation

Users install via README instructions (no installation script):

```bash
# Clone the repo
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox

# Option A: Install directly
claude plugin install .

# Option B: Symlink for easier development
ln -s $(pwd) ~/.claude/plugins/claude-code-toolbox
claude plugin install ~/.claude/plugins/claude-code-toolbox

# Optional: Symlink CLAUDE.md for personal context
ln -s $(pwd)/CLAUDE.md ~/.claude/CLAUDE.md
```

## Development Workflow

After installation, the development workflow is:

1. Edit any file in the repo (agents, skills, commands, hooks, plugin.json)
2. Save changes
3. Run `/plugin reload claude-code-toolbox` in Claude Code
4. Changes are live

No commit, push, or reinstall required. The reload command reads files from disk.

## README Structure

The README will include:

1. **Overview** - What the plugin provides and why use it
2. **Installation** - Commands to clone, install, and optionally symlink CLAUDE.md
3. **Usage** - How to reload after changes, MCP server prerequisites
4. **Development/Customization** - How to add agents/skills/commands, reminder to update plugin.json

The README omits a "What's Included" section. Users can browse the repository files to see what's available.

## Trade-offs

**Benefits:**
- Proper packaging for sharing
- Official Claude Code extension mechanism
- No repo state pollution
- Clear separation of personal context from shareable config

**Costs:**
- Requires `/plugin reload` after changes (vs instant availability with full symlink)
- Must update plugin.json when adding new agents/skills/commands
- MCP servers configuration format differs from standalone .mcp.json

## Open Questions

None. Design is validated and ready for implementation.
