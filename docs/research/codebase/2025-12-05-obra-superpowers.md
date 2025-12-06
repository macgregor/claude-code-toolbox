# Codebase Analysis: Superpowers

## Research Objective
https://github.com/obra/superpowers

## Executive Summary

Superpowers is a comprehensive software development workflow system for AI coding agents, built around a library of composable "skills" that enforce best practices through mandatory protocols. The system transforms ad-hoc agent behavior into structured, test-driven workflows that emphasize systematic debugging, design-first planning, and autonomous subagent-driven development. Rather than allowing agents to immediately jump into code, Superpowers enforces a disciplined workflow: brainstorming and design refinement, implementation planning with detailed task breakdown, TDD-enforced red-green-refactor cycles, and automated code review checkpoints between tasks.

The architecture is cross-platform, supporting three AI coding environments: Claude Code (via native plugin system), Codex (via Node.js integration), and OpenCode (via JavaScript plugin). The core abstraction is the "skill" - a markdown document with YAML frontmatter that agents check and execute at relevant workflow stages. Skills are organized as a library covering testing (TDD, async patterns, anti-patterns), debugging (systematic root cause analysis, verification protocols), collaboration (brainstorming, planning, code review), and meta-skills (writing new skills, testing skills with subagents). A shared ES module library (lib/skills-core.js) provides skill discovery, path resolution, and frontmatter parsing across all platforms.

The system's key characteristic is its enforcement mechanism: skills are not suggestions but mandatory protocols that agents must check and follow. Session hooks inject the "using-superpowers" skill into agent context at startup, establishing the fundamental rule that agents must check for applicable skills before performing any task. This transforms agent behavior from reactive coding to process-driven development, enabling multi-hour autonomous work sessions while maintaining code quality through automated review gates and test-first discipline.

## Overview
- **Purpose**: Structured software development workflow system for AI coding agents, enforcing TDD, systematic debugging, and design-first practices through composable skills
- **Maintainer**: Jesse Vincent (obra)
- **Repository**: https://github.com/obra/superpowers

## Tech Stack
- JavaScript (ES6+ modules)
- Node.js
- Bash
- Markdown
- YAML (frontmatter)
- Git
- JSON

## Architecture Patterns

- **Plugin Architecture**: Multi-platform plugin system with platform-specific adapters (Claude Code native, OpenCode JavaScript, Codex Node.js)
- **Skill-Based Composition**: Modular workflow components (skills) with YAML metadata and markdown content, organized in hierarchical directories
- **Session Hook Pattern**: Bootstrap injection at session creation to establish agent protocols via SessionStart hooks
- **Shared Core Library**: Cross-platform ES module (skills-core.js) providing common skill discovery, path resolution, and parsing logic
- **Shadowing/Override Pattern**: Personal skills can override superpowers skills via path resolution hierarchy
- **Document-Driven Configuration**: Skills defined as markdown files with structured frontmatter (name, description)
- **Polyglot Hook Wrapper**: Cross-platform shell script wrapper for Windows/Linux/macOS compatibility
- **Namespace-Based Discovery**: Skills referenced with optional "superpowers:" prefix for explicit sourcing

## Integration Points

- **Claude Code Plugin System**: Native marketplace integration via plugin.json/marketplace.json, SessionStart hooks, and command registration
- **OpenCode Plugin API**: JavaScript plugin with custom tools (use_skill, find_skills), message insertion for context persistence, and event hooks (session.created, session.compacted)
- **Codex Integration**: Manual bootstrap via AGENTS.md, unified Node.js script (superpowers-codex) for skill discovery and execution
- **Session Hooks**: JSON-based hook configuration (hooks/hooks.json) triggering on startup/resume/clear/compact events
- **Skill Tool Interface**: Agents interact via Skill tool, Read tool (legacy), or platform-specific custom tools
- **Git Worktree Integration**: Commands create isolated development branches for parallel work
- **Command Interface**: Slash commands (/superpowers:brainstorm, /superpowers:write-plan, /superpowers:execute-plan) mapped to skill workflows
- **Subagent Protocol**: Skills dispatch fresh subagents for task execution with code review checkpoints

## Related Repositories
- https://github.com/obra/superpowers-marketplace - Plugin marketplace for Claude Code distribution
- https://github.com/sponsors/obra - Project sponsorship page

## Metadata
- **Analysis Date**: 2025-12-05T20:54:00Z
- **Agent Model**: claude-sonnet-4-5@20250929
