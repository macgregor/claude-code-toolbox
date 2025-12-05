# Research: Claude Code Features and Architecture

## Research Objective
Comprehensive analysis of the Claude Code runtime environment and available features for plugin development, including agents, subagents, hooks, plugins, skills, and slash commands, to understand implementation options for developing features in this plugin.

## Executive Summary

Claude Code provides a sophisticated, modular plugin ecosystem built on six core extension mechanisms: Skills, Subagents, Hooks, Plugins, Slash Commands, and MCP (Model Context Protocol) servers. These components work together to create a flexible, context-aware development environment where AI capabilities can be customized, automated, and shared across teams.

The architecture prioritizes context efficiency and separation of concerns. Skills activate automatically based on task context, subagents provide isolated workspaces with specialized expertise, hooks enable deterministic workflow automation, and plugins package these components for easy distribution. The Model Context Protocol serves as a universal adapter connecting external tools and data sources. Configuration is hierarchical (enterprise → user → project) with CLAUDE.md files providing persistent project context.

Community adoption is strong with multiple marketplace repositories hosting hundreds of plugins. Official documentation is comprehensive, covering component structure, YAML frontmatter schemas, lifecycle events, and best practices. Notable patterns include the three-tier skill architecture (metadata/instructions/resources), hybrid model orchestration (Haiku for execution, Sonnet for planning/review), and plugin templates for rapid development. The ecosystem emphasizes single-responsibility components, clear descriptions for automatic activation, and version-controlled configuration.

## Findings

### Official Documentation

- **Source**: Agent Skills Documentation
  **URL**: https://code.claude.com/docs/en/skills
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Skills are directories with SKILL.md and optional supporting files
    - YAML frontmatter includes name, description, allowed-tools
    - Auto-discovered and invoked by Claude based on context matching
    - Stored in ~/.claude/skills/ (personal) or .claude/skills/ (project)
    - No explicit user invocation required

- **Source**: Subagents Documentation
  **URL**: https://code.claude.com/docs/en/sub-agents
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Specialized AI assistants with separate context windows
    - Created via /agents command or manual .md files
    - YAML frontmatter: name, description, tools, model
    - Can be invoked automatically by Claude or explicitly by user
    - Built-in subagents: general-purpose, plan, explore

- **Source**: Hooks Guide
  **URL**: https://code.claude.com/docs/en/hooks-guide
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - 10 lifecycle events: PreToolUse, PostToolUse, UserPromptSubmit, PermissionRequest, Notification, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd
    - Configured in hooks.json with matchers for specific tools
    - Support allow/deny/ask decision types
    - Enable deterministic workflow automation
    - Security consideration: hooks run with current environment credentials

- **Source**: Plugin Marketplaces Documentation
  **URL**: https://docs.claude.com/en/docs/claude-code/plugin-marketplaces
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - marketplace.json defines plugin catalog structure
    - plugin.json at .claude-plugin/ contains metadata
    - Plugins bundle commands, agents, MCP servers, hooks
    - Install via /plugin command
    - strict flag controls manifest inheritance

- **Source**: Claude Code Plugins Announcement
  **URL**: https://www.claude.com/blog/claude-code-plugins
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Plugins now in public beta
    - Single command installation
    - Work across terminal and VS Code
    - Enable team standardization and workflow sharing
    - Four core components: commands, subagents, MCP servers, hooks

- **Source**: Claude Code Best Practices
  **URL**: https://www.anthropic.com/engineering/claude-code-best-practices
  **Author**: Anthropic Engineering
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Context management is critical for performance
    - Use CLAUDE.md for project-level persistent context
    - Chop tasks into smaller chunks, clear context frequently
    - Store repeated workflows as slash commands in .claude/commands/
    - Hierarchical configuration: enterprise → user → project

- **Source**: Claude Code Sandboxing Architecture
  **URL**: https://www.anthropic.com/engineering/claude-code-sandboxing
  **Author**: Anthropic Engineering
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Built on Linux bubblewrap and MacOS seatbelt
    - Filesystem isolation restricts directory access
    - Network isolation controls server connections
    - Reduces permission prompts by 84% in internal usage
    - Automatic allow/block decisions with permission fallback

### Source Code Repositories

- **Source**: anthropics/claude-code
  **URL**: https://github.com/anthropics/claude-code
  **Author**: Anthropic
  **Date**: 2025 (actively maintained)
  **Activity**: Official repository
  **Key points**:
    - Official Claude Code source repository
    - Contains example plugins in plugins/ directory
    - Demonstrates plugin structure and best practices
    - Node.js/TypeScript codebase with React/Ink for UI
    - Documentation for plugin development

- **Source**: anthropics/skills
  **URL**: https://github.com/anthropics/skills
  **Author**: Anthropic
  **Date**: 2025 (actively maintained)
  **Activity**: Official skills repository
  **Key points**:
    - Public repository for official Claude Code skills
    - Categories: Creative & Design, Development & Technical, Enterprise & Communication, Document Skills
    - Example SKILL.md structures
    - Reference implementations for common patterns
    - Demonstrates context-aware skill activation

- **Source**: jeremylongshore/claude-code-plugins-plus
  **URL**: https://github.com/jeremylongshore/claude-code-plugins-plus
  **Author**: Jeremy Longshore
  **Date**: October 2025 launch, actively maintained
  **Activity**: 254 total plugins (249 AI Instruction, 5 MCP Server)
  **Key points**:
    - Largest community plugin hub
    - 185 plugins include Agent Skills
    - First 100% compliant with Anthropic 2025 Skills schema
    - Includes plugin templates: minimal, command, agent, full
    - Comprehensive development guidelines

- **Source**: wshobson/agents
  **URL**: https://github.com/wshobson/agents
  **Author**: William Hobson
  **Date**: 2025 (actively maintained)
  **Activity**: 85 specialized agents across 63 plugins
  **Key points**:
    - Domain-expert agents (architecture, programming, infrastructure, QA, data/AI, docs, business, SEO)
    - Three-tier architecture: metadata/instructions/resources
    - Hybrid model orchestration: 47 Haiku agents, 97 Sonnet agents
    - Single-responsibility design principle
    - Typical workflow: Sonnet (planning) → Haiku (execution) → Sonnet (review)

- **Source**: obra/superpowers
  **URL**: https://github.com/obra/superpowers
  **Author**: Jesse Vincent (obra)
  **Date**: 2025 (actively maintained)
  **Activity**: Popular skills repository
  **Key points**:
    - Production-ready skills for development workflows
    - Skills: brainstorming, writing-plans, executing-plans, code-review, git-worktrees
    - Progressive disclosure pattern for complex workflows
    - Demonstrates skill-to-skill coordination
    - Emphasizes TDD and incremental development

- **Source**: disler/claude-code-hooks-mastery
  **URL**: https://github.com/disler/claude-code-hooks-mastery
  **Author**: David Disler
  **Date**: 2025
  **Activity**: Hooks demonstration repository
  **Key points**:
    - Captures all 8 hook lifecycle events with JSON payloads
    - Example hooks: logging, formatting, notifications, file protection
    - Demonstrates PreToolUse and PostToolUse patterns
    - Security considerations documented
    - Practical examples of workflow automation

### Community/Third-party

- **Source**: Understanding Claude Code's Full Stack: MCP, Skills, Subagents, and Hooks Explained
  **URL**: https://alexop.dev/posts/understanding-claude-code-full-stack/
  **Author**: Alex Opoku (alexop.dev)
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Comprehensive technical breakdown of Claude Code architecture
    - Explains interaction between MCP, CLAUDE.md, subagents, hooks, plugins, and skills
    - MCP acts as universal adapter for APIs, databases, external tools
    - Subagents prevent "context poisoning" via separate context windows
    - Emphasizes context efficiency and separation of concerns

- **Source**: Building My First Claude Code Plugin
  **URL**: https://alexop.dev/posts/building-my-first-claude-code-plugin/
  **Author**: Alex Opoku (alexop.dev)
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Step-by-step plugin development tutorial
    - Covers plugin.json schema and marketplace.json configuration
    - Demonstrates slash command creation
    - Explains component discovery and activation
    - Practical examples with code snippets

- **Source**: ClaudeLog - Claude Code Docs, Guides, Tutorials & Best Practices
  **URL**: https://claudelog.com/
  **Author**: ClaudeLog Community
  **Date**: 2025 (continuously updated)
  **Activity**: N/A
  **Key points**:
    - Community-driven documentation and changelog
    - Real-world usage patterns and optimization techniques
    - Expert insights from production deployments
    - FAQ section covering hooks, skills, configuration
    - Troubleshooting guides for common issues

- **Source**: Understanding Claude Code: Skills vs Commands vs Subagents vs Plugins
  **URL**: https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins
  **Author**: Young Leaders Tech
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Clear differentiation between plugin components
    - When to use each component type
    - Decision tree for choosing right extension mechanism
    - Examples of appropriate use cases
    - Common anti-patterns to avoid

- **Source**: My 7 Essential Claude Code Best Practices for Production-Ready AI in 2025
  **URL**: https://www.eesel.ai/blog/claude-code-best-practices
  **Author**: eesel AI
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Production deployment strategies
    - Context management optimization
    - Security considerations for enterprise use
    - Performance tuning techniques
    - Team collaboration patterns

- **Source**: Cooking with Claude Code: The Complete Guide
  **URL**: https://www.siddharthbharath.com/claude-code-the-complete-guide/
  **Author**: Siddharth Bharath
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Complete tutorial building personal finance tracker
    - Introduces all Claude Code features through practical example
    - Usage patterns and workflow tips
    - Integration with external tools and APIs
    - Deployment and maintenance guidance

- **Source**: Plugin Structure Reference
  **URL**: https://claude-plugins.dev/skills/@anthropics/claude-code/plugin-structure
  **Author**: claude-plugins.dev
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Detailed plugin.json schema documentation
    - Directory structure conventions
    - Component path configuration
    - Manifest field reference
    - Validation rules and requirements

## Sources
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks-guide
- https://docs.claude.com/en/docs/claude-code/plugin-marketplaces
- https://www.claude.com/blog/claude-code-plugins
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://www.anthropic.com/engineering/claude-code-sandboxing
- https://github.com/anthropics/claude-code
- https://github.com/anthropics/skills
- https://github.com/jeremylongshore/claude-code-plugins-plus
- https://github.com/wshobson/agents
- https://github.com/obra/superpowers
- https://github.com/disler/claude-code-hooks-mastery
- https://alexop.dev/posts/understanding-claude-code-full-stack/
- https://alexop.dev/posts/building-my-first-claude-code-plugin/
- https://claudelog.com/
- https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins
- https://www.eesel.ai/blog/claude-code-best-practices
- https://www.siddharthbharath.com/claude-code-the-complete-guide/
- https://claude-plugins.dev/skills/@anthropics/claude-code/plugin-structure

## Metadata
- **Research Date**: 2025-12-05T15:22:00Z
- **Search Queries**: Claude Code official documentation plugins agents skills hooks 2025, Claude Code plugin development guide subagents slash commands, Claude Code runtime environment features architecture, Claude Code hooks documentation PreToolUse PostToolUse lifecycle events, site:github.com Claude Code plugin examples repository, "Claude Code" plugin.json schema marketplace.json format structure, "Claude Code" best practices blog tutorial 2025
- **Agent Model**: claude-sonnet-4-5@20250929
