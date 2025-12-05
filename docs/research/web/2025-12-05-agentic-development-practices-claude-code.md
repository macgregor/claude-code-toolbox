# Research: Agentic Development Practices for Claude Code

## Research Objective
Research agentic development practices, particularly implementing them via Claude Code, focusing on Anthropic's official documentation and practical examples to learn how to build good, reliable agents. Examine sample repositories (obra/superpowers, jsell-rh/agentic-development-plugins, wshobson/agents) and find good information sources to help build better agents.

## Executive Summary

This research investigated agentic development practices for Claude Code by examining Anthropic's official documentation, three reference repositories, and community best practices. The findings reveal a consistent architectural pattern built around the "agent loop" (gather context → take action → verify work → repeat), emphasizing single-responsibility subagents coordinated by orchestrators, progressive disclosure for token efficiency, and strict permission controls for production safety.

Key architectural patterns emerged: modular skill-based design, multi-stage workflows with quality gates, and hybrid model orchestration (Haiku for deterministic tasks, Sonnet for complex reasoning). The most successful agents follow test-driven development, maintain isolated contexts per subagent, and implement memory systems for continuous learning. Production deployments require container-based sandboxing, careful permission scoping, and automated testing gates.

The Claude Code SDK has evolved into the Claude Agent SDK, reflecting a broader vision beyond coding—agents are now used for research, content creation, and general automation. The ecosystem supports cross-platform skills (Claude.ai, Claude Code, Claude Agent SDK, Developer Platform) with consistent APIs and progressive loading mechanisms optimized for token efficiency.

## Findings

### Official Documentation

- **Source**: Building agents with the Claude Agent SDK - [https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
  **Author**: Anthropic Engineering Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Core agent loop: gather context → take action → verify work → repeat
    - Context gathering: agentic file system search, subagents for parallel retrieval, context compaction
    - Action taking: precise tools, bash scripting, dynamic code generation, MCP integrations
    - Work verification: clear rules, code linting, visual feedback, optional secondary LLM judging
    - Agent types: finance, personal assistant, customer support, deep research
    - Goal: "give your agents a computer, allowing them to work like humans do"

- **Source**: Claude Code: Best practices for agentic coding - [https://www.anthropic.com/engineering/claude-code-best-practices](https://www.anthropic.com/engineering/claude-code-best-practices)
  **Author**: Anthropic Engineering Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Setup: CLAUDE.md files for bash commands, style guidelines, testing instructions
    - Workflow patterns: explore → plan → code → commit
    - Test-driven development: write tests first, confirm failure, implement, verify no overfitting
    - Visual iteration: screenshots, design mocks, browser automation
    - Advanced: multi-Claude verification, git worktrees, custom slash commands, headless mode, MCP servers
    - Optimization: be specific, provide context/images, course-correct early, use /clear, leverage checklists

- **Source**: Building effective agents (Research) - [https://www.anthropic.com/research/building-effective-agents](https://www.anthropic.com/research/building-effective-agents)
  **Author**: Anthropic Research Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Agent definitions: workflows (predefined paths) vs agents (dynamic process control)
    - Core principles: maintain simplicity, prioritize transparency, carefully craft agent-computer interfaces
    - Workflow patterns: augmented LLM, prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer
    - Use cases: best for open-ended problems with unpredictable steps
    - Cautions: higher costs, potential compounding errors, extensive testing required
    - Promising domains: customer support and coding tasks

- **Source**: Agent SDK overview - Claude Docs - [https://platform.claude.com/docs/en/agent-sdk/overview](https://platform.claude.com/docs/en/agent-sdk/overview)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Built on agent harness powering Claude Code
    - Features: context management with automatic compaction, rich tool ecosystem (file ops, code execution, web search, MCP), advanced permissions, built-in error handling/session management, automatic prompt caching
    - SDKs: Python (pip install claude-agent-sdk), TypeScript/Node (npm install @anthropic-ai/claude-agent-sdk)
    - Renamed from "Claude Code SDK" to reflect broader vision
    - Documentation at docs.claude.com and platform.claude.com/docs

- **Source**: Subagents - Claude Code Docs - [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Specialized assistants with distinct system prompts, curated permissions, isolated context windows
    - Clear role definition: one goal, input, output, handoff rule per subagent
    - Tool scoping: PM/Architect (read-heavy), Implementer (Edit/Write/Bash), Release (minimal)
    - Context isolation prevents pollution, enables parallelization
    - Common pipeline: pm-spec → architect-review → implementer-tester
    - File structure: Markdown with YAML frontmatter in .claude/agents/
    - Model selection: sonnet/opus/haiku aliases, 'inherit', or default

### Source Code Repositories

- **Source**: superpowers - [https://github.com/obra/superpowers](https://github.com/obra/superpowers)
  **Author**: obra
  **Date**: 2025
  **Activity**: Active development, multiple stars
  **Key points**:
    - Philosophy: "evidence over claims", systematic over ad-hoc, complexity reduction
    - Workflow: brainstorming → planning → execution → code review → branch management
    - Planning: breaks work into 2-5 minute tasks with exact file paths and verification steps
    - Execution: RED-GREEN-REFACTOR TDD cycle, subagent-driven development
    - Skills: composable, trigger automatically during development stages, includes meta-skills
    - Mandatory workflows, not suggestions
    - Supports autonomous work for extended periods while adhering to plans
    - YAGNI principle (You Aren't Gonna Need It)

- **Source**: agentic-development-plugins - [https://github.com/jsell-rh/agentic-development-plugins](https://github.com/jsell-rh/agentic-development-plugins)
  **Author**: jsell-rh
  **Date**: 2025
  **Activity**: Active commits
  **Key points**:
    - Zero-assumption development with strict quality gates (Gates 0, 3, 6, 7)
    - Spec-driven development with atomic commits per task
    - Agent types: process agents (workflow management), specialized agents (Python/FastAPI/Deployment/Security/Documentation experts)
    - Memory system: each agent maintains markdown file tracking patterns, solutions, mistakes, project standards
    - Workflow stages: repo setup → spec generation → development management → task execution → atomic commits
    - Tech stack: Red Hat UBI9, Python 3.13+, Pydantic, FastAPI, Konflux CI/CD
    - Token-efficient context management
    - Self-learning capability through persistent memory

- **Source**: agents - [https://github.com/wshobson/agents](https://github.com/wshobson/agents)
  **Author**: wshobson
  **Date**: 2025
  **Activity**: Active commits
  **Key points**:
    - Granular design: single responsibility per plugin, average 3.4 components
    - Progressive disclosure: metadata (always) → instructions (on-demand) → resources (as-needed)
    - Hybrid model orchestration: 47 Haiku agents (fast deterministic), 97 Sonnet agents (complex reasoning)
    - Workflow pattern: Sonnet (planning) → Haiku (execution) → Sonnet (review)
    - Plugin structure: agents/, commands/, skills/ directories
    - 100% agent accessibility across plugins
    - Minimal token usage through strategic loading
    - Composable across workflows

### Community/Third-party

- **Source**: Best practices for Claude Code subagents - [https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
  **Author**: PubNub
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Benefits: reproducibility through codified steps, separation of concerns, governance/safety via scoped tools
    - Early subagent use preserves main context availability
    - Subagents enable parallelization and context management
    - Recommended: generate initial subagents with Claude, then iterate to personalize
    - Action-oriented descriptions critical
    - File structure enables discovery from .claude/agents/

- **Source**: Claude Agent SDK Best Practices for AI Agent Development (2025) - [https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
  **Author**: Skywork AI
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Production rule: one job per subagent, orchestrator coordinates
    - Permission management: deny-all approach, allowlist only necessary commands/directories
    - Deployment gates: automated tests, feature flags for rollouts, rollback triggers
    - Testing in sandboxed environments essential
    - Deploy small and iterate: learn more from one production deployment than 10 prototypes
    - Continuous refinement based on actual usage patterns

- **Source**: VoltAgent/awesome-claude-code-subagents - [https://github.com/VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)
  **Author**: VoltAgent
  **Date**: 2025
  **Activity**: Production-ready collection
  **Key points**:
    - 100+ specialized agents for full-stack development, DevOps, data science, business operations
    - Community-contributed and maintained
    - Production-ready patterns and examples
    - Organized by domain with specific use cases

- **Source**: Optimizing Agentic Coding: How to use Claude Code - [https://research.aimultiple.com/agentic-coding/](https://research.aimultiple.com/agentic-coding/)
  **Author**: AIM Multiple Research
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Research and planning crucial—prevents jumping straight to coding
    - Planning significantly improves performance for problems requiring deeper thinking
    - Autonomous mode (--dangerously-skip-permissions) useful but risky—use in containers without internet
    - Memory.md documents for project state continuity across sessions
    - Dedicated memory documents function as continuity layer for distributed development

## Sources

**Official Anthropic Documentation:**
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Building effective agents (Research)](https://www.anthropic.com/research/building-effective-agents)
- [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [GitHub - anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)

**Reference Repositories:**
- [obra/superpowers](https://github.com/obra/superpowers)
- [jsell-rh/agentic-development-plugins](https://github.com/jsell-rh/agentic-development-plugins)
- [wshobson/agents](https://github.com/wshobson/agents)
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)

**Community Resources:**
- [Best practices for Claude Code subagents - PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
- [Claude Agent SDK Best Practices (2025) - Skywork AI](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
- [Optimizing Agentic Coding - AIM Multiple](https://research.aimultiple.com/agentic-coding/)

## Metadata
- **agent-type**: web-research-agent-v1-7k9p3x2m
- **Research Date**: 2025-12-05T02:14:00Z
- **Search Queries**: "Anthropic Claude Code agents building documentation 2025", "Claude Agent SDK official documentation", "agentic development workflows Claude best practices", "Claude Code subagent patterns best practices 2025"
- **Agent Model**: claude-sonnet-4-5@20250929
