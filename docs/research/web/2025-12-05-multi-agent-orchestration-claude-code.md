# Research: Multi-Agent Orchestration Patterns for Claude Code CLI

## Research Objective
Investigate multi-agent orchestration patterns for Claude Code CLI (markdown-based agents, NOT SDK/API usage), with emphasis on finding quality code repositories demonstrating practical implementations. Focus on discovering new repositories beyond previously documented ones (obra/superpowers, jsell-rh/agentic-development-plugins, wshobson/agents), examining orchestration patterns including handoffs, state management, coordination mechanisms, and validation gates.

## Executive Summary
This research uncovered a vibrant ecosystem of multi-agent orchestration implementations for Claude Code CLI, with over 15 high-quality repositories demonstrating diverse coordination patterns. The most common architectural pattern is hub-and-spoke coordination, where a central orchestrator agent routes tasks to specialized worker agents, preventing peer-to-peer communication chaos. Key technical innovations include file-based state management (JSON artifacts, lock files, queue systems), lifecycle hook integration for agent handoffs (particularly SubagentStop hooks), and quality gates with validation thresholds between agent phases.

Three dominant orchestration approaches emerged: (1) Sequential workflows with specialized agents handling distinct SDLC phases (planning → development → validation), popularized by zhsama/claude-sub-agent's quality gate pattern; (2) Parallel coordination using channel-based communication and git worktree isolation for concurrent agent work, exemplified by nwiizo/ccswarm's Rust implementation; (3) Swarm intelligence with mesh topology and SQLite-based memory systems enabling cross-session persistence, as demonstrated by ruvnet/claude-flow. Advanced implementations leverage hooks for observability (disler/claude-code-hooks-multi-agent-observability), context engineering for collective behavior (vanzan01/claude-code-sub-agent-collective), and multi-model orchestration across different AI systems (catlog22/Claude-Code-Workflow).

The research reveals that successful multi-agent systems share common characteristics: explicit handoff contracts between agents, external memory systems for state persistence (CLAUDE.md files, SQLite databases, JSON artifacts), progressive disclosure to manage token usage, and hybrid model strategies using Sonnet for planning/review and Haiku for execution. Validation emerges as critical, with implementations using quality gates (typically 80-95% thresholds), hooks that block completion until standards are met, and LLM-as-judge patterns for evaluating agent outputs. These patterns enable handling tasks of arbitrary complexity through distributed, self-coordinating agent networks.

## Findings

### Official Documentation

- **Source**: Subagents - Claude Code Docs
  **URL**: https://code.claude.com/docs/en/sub-agents
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Subagents are specialized AI assistants with separate context windows, customized system prompts, and configurable tools
    - YAML frontmatter configuration with fields: name, description, tools, model, permissionMode
    - Context preservation by preventing main conversation pollution through isolated contexts
    - Automatic delegation based on task description or explicit invocation via @mention
    - Resumable agents can continue previous conversations for multi-turn workflows
    - Built-in agents: General-Purpose, Plan, Explore for common orchestration patterns

- **Source**: Hooks Reference - Claude Code Docs
  **URL**: https://code.claude.com/docs/en/hooks
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Hooks are automated commands executing at specific lifecycle points: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, SessionStart, PreCompact, Notification
    - SubagentStop hooks enable agent coordination by printing next steps to STDOUT, surfacing them in Claude transcript
    - Exit Code 2 blocks subagent stoppage and shows error to subagent, enabling quality gates
    - Prompt-based hooks supported for Stop and SubagentStop, enabling context-aware agent handoff decisions
    - Hooks provide deterministic control without interrupting workflow

- **Source**: How We Built Our Multi-Agent Research System
  **URL**: https://www.anthropic.com/engineering/multi-agent-research-system
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Orchestrator-worker pattern: lead agent coordinates specialized subagents operating in parallel
    - Each subagent provides separation of concerns to reduce path dependency
    - Memory mechanisms store essential context; agents spawn fresh subagents with clean contexts when limits reached
    - End-state evaluation using LLM-as-judge for accuracy and completeness instead of turn-by-turn analysis
    - Parallel tool calling improves speed and performance
    - Checkpoints validate specific state changes in multi-agent workflows

- **Source**: Claude Code: Best Practices for Agentic Coding
  **URL**: https://www.anthropic.com/engineering/claude-code-best-practices
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Use subagents for complex problems, especially early in tasks to verify details or investigate questions
    - Multiple Claude instances can work simultaneously on different problem parts
    - Recommended pattern: one Claude writes code, another Claude verifies with independent subagents
    - Use /clear to reset context windows and prevent information overload
    - Create documents or GitHub issues as checkpoints to reset if implementation goes wrong
    - Git worktrees maintain independent task contexts for parallel agent work

- **Source**: Manage Claude's Memory - Claude Code Docs
  **URL**: https://code.claude.com/docs/en/memory
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - All memory files automatically loaded into Claude Code's context when launched
    - Hierarchical memory structure: enterprise, project, and user-level locations
    - Project memory stored in ./CLAUDE.md or ./.claude/CLAUDE.md
    - Memory files act as external state persistence for multi-agent coordination
    - Enables context sharing across agent sessions and handoffs

### Source Code Repositories

- **Source**: ruvnet/claude-flow
  **URL**: https://github.com/ruvnet/claude-flow
  **Author**: ruvnet
  **Date**: 2024-2025
  **Activity**: Active development, recent commits
  **Key points**:
    - Leading agent orchestration platform with multi-agent swarm intelligence and mesh topology coordination
    - SQLite-based memory system with 12 specialized tables (memory_store, sessions, agents, tasks, agent_memory, shared_state, events, patterns, performance_metrics, workflow_state, swarm_topology, consensus_state)
    - MCP protocol integration with 100+ coordination tools: swarm_init, agent_spawn, task_orchestrate
    - Cross-session state management enabling workflow recovery and persistent agent coordination
    - Hive-mind architecture with queen-led coordination and worker agents
    - 64-agent system designed for enterprise-grade orchestration
    - Natural language triggers for automatic agent skill activation

- **Source**: nwiizo/ccswarm
  **URL**: https://github.com/nwiizo/ccswarm
  **Author**: nwiizo
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Rust-native multi-agent orchestration with type-state pattern for compile-time state validation
    - Channel-based communication architecture without shared state or locks for zero-cost abstractions
    - Git worktree isolation enabling parallel agent development without conflicts
    - WebSocket-based Agent Client Protocol (ACP) for real-time multi-agent communication
    - Defined agent roles: Frontend, Backend, DevOps, QA, Search, Master
    - Master Claude analyzes and assigns tasks semantically with dependency resolution
    - Goal-driven planning with milestone tracking and intelligent task prediction

- **Source**: zhsama/claude-sub-agent
  **URL**: https://github.com/zhsama/claude-sub-agent
  **Author**: zhsama
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Multi-phase AI-driven development workflow with quality gates at each phase
    - Planning Phase: spec-analyst, spec-architect, spec-planner with Quality Gate 1 (95% threshold)
    - Development Phase: spec-developer, spec-tester with Quality Gate 2 (80% threshold)
    - Validation Phase: spec-reviewer, spec-validator with Quality Gate 3 (85% threshold)
    - Structured artifact communication between agents (requirements → architecture → code → tests → review)
    - Orchestrator manages workflow progression based on quality gate validation
    - Demonstrates end-to-end SDLC automation through specialized agent coordination

- **Source**: mbruhler/claude-orchestration
  **URL**: https://github.com/mbruhler/claude-orchestration
  **Author**: mbruhler
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Declarative workflow orchestration with syntax: sequential (→), parallel (||), conditional (~>)
    - Parallel investigation pattern for simultaneous exploration: [Explore:code || general-purpose:logs || general-purpose:commits]
    - Auto-activating skills organized in categories: creating-workflows, executing-workflows, managing-agents, debugging-workflows
    - Permanent vs ephemeral agent management with automatic cleanup of temp agents
    - Temp agents can be promoted to permanent status based on utility
    - Built-in agents for complex task orchestration (general-purpose, explore agents)
    - Variable passing between workflow steps enables dynamic coordination

- **Source**: baryhuang/claude-code-by-agents
  **URL**: https://github.com/baryhuang/claude-code-by-agents
  **Author**: baryhuang
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Desktop app and API for multi-agent workspace with local and remote agent coordination
    - @mention routing mechanism for direct task assignment to specific agents
    - Orchestrator automatically analyzes requests and creates execution plans
    - File-based inter-agent communication with automatic dependency passing
    - Frontend → Main Backend (Orchestrator) → Multiple Agents architecture
    - Supports heterogeneous computing environments (localhost, mac-mini, cloud instances)
    - No additional API keys required, uses existing Claude Code authentication

- **Source**: yzyydev/claude_code_sub_agents
  **URL**: https://github.com/yzyydev/claude_code_sub_agents
  **Author**: yzyydev
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Transforms single-threaded AI into distributed, self-coordinating agent network
    - Three core command modules: start.md (infinite loop orchestrator), solve.md (parallel case processor), prime.md (context management)
    - Wave-based agent deployment (1-5 agents per wave) prevents context saturation
    - Progressive summarization maintains context through iterations
    - Strategic coordination prevents duplicate concepts across parallel agent streams
    - Handles tasks of arbitrary complexity and scale through dynamic agent deployment
    - Context optimization through proactive capacity monitoring and compression

- **Source**: Dicklesworthstone/claude_code_agent_farm
  **URL**: https://github.com/Dicklesworthstone/claude_code_agent_farm
  **Author**: Dicklesworthstone
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Parallel processing of up to 50 Claude Code agents simultaneously
    - /coordination directory with active work registry, completed work log, agent-specific locks, planned work queue
    - Advanced locking system prevents agent work conflicts
    - Supports 34 different technology stacks
    - Three workflow types: bug fixing (parallel resolution), best practices (systematic implementation), cooperative agents (strategic improvements)
    - Agents generate unique identities, check for conflicts, create lock files, register work plans
    - Intelligent work distribution with adaptive idle timeout management

- **Source**: bwads001/claude-code-agents
  **URL**: https://github.com/bwads001/claude-code-agents
  **Author**: bwads001
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Multi-agent orchestration with specialized agents and workflow modes (Research, Planning, Execution)
    - Automated quality gates reduce tokens by 60% while maintaining 100% pattern consistency
    - Pure orchestration philosophy: hooks handle repetitive tasks, agents handle specialized work
    - Sequential coordination: project-manager → backend-engineer → frontend-specialist → quality-reviewer
    - Human-Guided Context Orchestration through ai-docs/ knowledge persistence system
    - Automatic context injection for agents reduces context pollution in main thread
    - Workflow-specific modes provide different agent capabilities based on development phase

- **Source**: vanzan01/claude-code-sub-agent-collective
  **URL**: https://github.com/vanzan01/claude-code-sub-agent-collective
  **Author**: vanzan01
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Context engineering research applied to create agent collective behavior
    - Hub-and-spoke coordination with central @task-orchestrator routing work to specialists
    - CLAUDE.md acts as behavioral operating system with prime directives overriding defaults
    - Context7 integration pulls real, current documentation for research-driven intelligence
    - ResearchDrivenAnalyzer assesses task complexity for intelligent task breakdown
    - Hook systems enforce development rules with quality gates blocking completion until standards met
    - Handoff contracts preserve context between agent transitions
    - TDD methodology enforced across collective through behavioral constraints

- **Source**: catlog22/Claude-Code-Workflow
  **URL**: https://github.com/catlog22/Claude-Code-Workflow
  **Author**: catlog22
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - JSON-driven multi-agent framework with context-first architecture
    - Multi-model orchestration leveraging Gemini (analysis), Codex (implementation), Qwen (additional tasks)
    - 4-tier layered memory system for contextual documentation gathered before implementation
    - Task states stored in .task/IMPL-*.json files ensuring single source of truth
    - Autonomous multi-stage orchestration chain-invokes specialized sub-commands and agents
    - Workflow types: Lite-Plan (exploration), Lite-Fix (bug diagnosis), Full Workflow (comprehensive planning)
    - Zero-intervention execution for complex workflows
    - Role-based agents (@code-developer, @test-fix-agent) emulate real software team

- **Source**: disler/claude-code-hooks-multi-agent-observability
  **URL**: https://github.com/disler/claude-code-hooks-multi-agent-observability
  **Author**: disler
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Real-time monitoring for multi-agent systems through hook event tracking
    - Architecture: Claude Agents → Hook Scripts → HTTP POST → Bun Server → SQLite → WebSocket → Vue Client
    - Tracks PreToolUse, PostToolUse, UserPromptSubmit events with detailed context
    - Session-based color coding and event filtering for multi-agent visualization
    - Security features: blocks dangerous commands, validates inputs, prevents sensitive file access
    - Tech stack: Bun + TypeScript + SQLite (server), Vue 3 + Vite (client), Python with Astral uv (hooks)
    - Enables debugging complex multi-agent interactions through comprehensive event logging

- **Source**: avivl/claude-007-agents
  **URL**: https://github.com/avivl/claude-007-agents
  **Author**: avivl
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Unified orchestration system with 112+ specialized agents across 14 categories
    - Parallel Coordinator manages multi-agent execution
    - Vibe Coding Coordinator conducts 15-20 minute autonomous development preparation
    - Task Orchestrator analyzes dependencies and coordinates specialized agents
    - Built-in resilience engineering: circuit breakers, automatic recovery, fault tolerance
    - Structured JSON logging with contextual information for observability
    - Intelligent bootstrap system auto-configures agents based on project stack detection
    - Model Context Protocol (MCP) provides organizational memory

- **Source**: smtg-ai/claude-squad
  **URL**: https://github.com/smtg-ai/claude-squad
  **Author**: smtg-ai
  **Date**: 2024-2025
  **Activity**: Active development
  **Key points**:
    - Multi-AI agent management across different systems: Claude Code, Aider, Codex, Gemini, OpenCode, Amp
    - tmux creates isolated terminal sessions for each agent
    - Git worktrees isolate codebases so each session works on its own branch
    - Enables working on multiple tasks simultaneously with complete isolation
    - TUI interface for easy navigation and management across AI agents
    - Session management: create, delete, commit/push, checkpoint, pause, resume
    - Review changes before applying them to main branch
    - No conflicts through isolated git workspaces per agent/task

### Community/Third-party

- **Source**: Best Practices for Claude Code Subagents
  **URL**: https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
  **Author**: PubNub
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Start with simple two-subagent configurations before attempting complex orchestrations
    - Focus subagents on genuinely distinct domains with natural boundaries (frontend/backend, security/performance)
    - Hooks can attach to SubagentStop event, reading queue files and printing next command to surface in transcript
    - Register Stop hook as safety net alongside SubagentStop for robust agent coordination
    - Exit Code 2 in hooks blocks subagent completion and shows error, enabling quality gates
    - Test-driven handoff validation ensures work completion or explicit handoff to next agent

- **Source**: How to Use Claude Code Subagents to Parallelize Development
  **URL**: https://zachwills.net/how-to-use-claude-code-subagents-to-parallelize-development/
  **Author**: Zach Wills
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Parallelized development gives each specialist its own dedicated context window
    - Product-manager uses full 200k context for user needs and business logic
    - Senior-software-engineer receives final ticket with fresh 200k context for implementation
    - Preserves quality of each step by preventing context pollution
    - Separation of concerns enables PM to ask, Architect to validate, Implementer to build/test, QA to verify
    - Subagents and hooks codify repeatable steps in multi-agent workflows

- **Source**: Guide to Claude Code Subagents & Hooks for Automation
  **URL**: https://www.arsturn.com/blog/a-beginners-guide-to-using-subagents-and-hooks-in-claude-code
  **Author**: Arsturn
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Custom subagents are specialized AI assistants invoked to handle specific task types
    - Provide task-specific configurations with customized system prompts, tools, and separate context window
    - Enable more efficient problem-solving through specialization
    - Hooks provide automated commands at lifecycle points for deterministic agent control
    - Combined subagents + hooks create powerful automation without workflow interruption

- **Source**: Memory System - Claude Flow Wiki
  **URL**: https://github.com/ruvnet/claude-flow/wiki/Memory-System
  **Author**: ruvnet
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - SQLite database at .swarm/memory.db provides persistent multi-agent memory
    - 12 specialized tables handle different memory aspects for agent coordination
    - WAL mode enables concurrent access for multiple agents
    - Session management supports creation, resumption, and workflow recovery
    - Shared state updates enable cross-agent communication and coordination
    - Event logging captures inter-agent interactions for debugging and analysis
    - Consensus state tracking enables distributed agent synchronization

- **Source**: Feature Request: Allow Hooks to Bridge Context Between Sub-Agents and Parent Agents
  **URL**: https://github.com/anthropics/claude-code/issues/5812
  **Author**: Community discussion
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Community identified need for better context bridging between agents
    - Current limitation: subagent context not automatically available to parent
    - Workaround: use hooks to write context to files for parent agent access
    - Discussion highlights importance of explicit handoff contracts
    - File-based state management emerges as common pattern for agent coordination

- **Source**: Context Management Bug: Loss of Context Requiring Complex Workaround Systems
  **URL**: https://github.com/anthropics/claude-code/issues/1345
  **Author**: Community discussion
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Users building sophisticated external memory systems as workarounds for context loss
    - Multi-agent architectures used to compensate for context management limitations
    - Three-tiered memory architectures: long-term, short-term, and session records
    - 62-agent collaborative systems built specifically to handle context challenges
    - Community consensus: external state persistence essential for complex multi-agent workflows

- **Source**: Agent Usage Guide - Claude Flow Wiki
  **URL**: https://github.com/ruvnet/claude-flow/wiki/Agent-Usage-Guide
  **Author**: ruvnet
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Optimized for concurrent agent deployment supporting 8+ agents with proper coordination
    - Concurrent deployment in single message for large projects
    - Natural language triggers activate agent skills automatically
    - Swarm initialization supports mesh topology with configurable max agents
    - Agent spawning syntax: agent_spawn <role> <task description>
    - Status monitoring tracks all active agents and their current tasks

## Sources

### Official Documentation
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://code.claude.com/docs/en/memory

### Source Code Repositories
- https://github.com/ruvnet/claude-flow
- https://github.com/nwiizo/ccswarm
- https://github.com/zhsama/claude-sub-agent
- https://github.com/mbruhler/claude-orchestration
- https://github.com/baryhuang/claude-code-by-agents
- https://github.com/yzyydev/claude_code_sub_agents
- https://github.com/Dicklesworthstone/claude_code_agent_farm
- https://github.com/bwads001/claude-code-agents
- https://github.com/vanzan01/claude-code-sub-agent-collective
- https://github.com/catlog22/Claude-Code-Workflow
- https://github.com/disler/claude-code-hooks-multi-agent-observability
- https://github.com/avivl/claude-007-agents
- https://github.com/smtg-ai/claude-squad
- https://github.com/wshobson/agents
- https://github.com/lst97/claude-code-sub-agents

### Community/Third-party
- https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
- https://zachwills.net/how-to-use-claude-code-subagents-to-parallelize-development/
- https://www.arsturn.com/blog/a-beginners-guide-to-using-subagents-and-hooks-in-claude-code
- https://github.com/ruvnet/claude-flow/wiki/Memory-System
- https://github.com/anthropics/claude-code/issues/5812
- https://github.com/anthropics/claude-code/issues/1345
- https://github.com/ruvnet/claude-flow/wiki/Agent-Usage-Guide
- https://github.com/ruvnet/claude-flow/wiki/Agent-System-Overview

## Metadata
- **Research Date**: 2025-12-05T17:10:00Z
- **Search Queries**: Claude Code CLI multi-agent orchestration patterns github 2024 2025, .claude/agents markdown multi-agent coordination github, Claude Code plugin subagent orchestration workflow examples, anthropic claude code agent handoff state management, Claude Code hooks lifecycle events agent coordination SubagentStop, Claude Code agent memory systems external state persistence patterns, site:github.com .claude/agents multiple agents coordination examples, Claude Code agent handoff coordination file-based state management 2024, Claude Code validation gates multi-agent workflow patterns github, agent orchestration claude code markdown YAML frontmatter examples
- **Agent Model**: claude-sonnet-4-5@20250929
