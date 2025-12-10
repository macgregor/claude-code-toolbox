# Research: Claude Code Hook System - Discovery, SubagentStart, and Lifecycle

## Research Objective
Research Claude Code's hook system comprehensively, focusing on: (1) How to discover available hook events authoritatively since documentation becomes outdated, (2) The SubagentStart hook added in v2.0.43, (3) Deep dive on the anthropics/claude-code repository, and (4) Implementation details about when hooks fire and what data/context is available.

## Executive Summary
Claude Code's hook system provides 12 lifecycle events for automated workflow control, with official TypeScript type definitions serving as the authoritative source for available hooks. The Agent SDK TypeScript documentation defines the complete `HookEvent` union type including PreToolUse, PostToolUse, PostToolUseFailure, Notification, UserPromptSubmit, SessionStart, SessionEnd, Stop, SubagentStart, SubagentStop, PreCompact, and PermissionRequest. The SubagentStart hook was added in version 2.0.43 (confirmed in CHANGELOG.md) and fires when a subagent begins execution, providing `agent_id` and `agent_type` fields to distinguish between different subagent invocations.

For discovering available hooks, the most reliable methods are: (1) The TypeScript Agent SDK type definitions at platform.claude.com/docs/en/agent-sdk/typescript which export the complete `HookEvent` type and individual `*HookInput` interfaces, (2) The JSON Schema at schemastore.org/claude-code-settings.json for CLI hook configuration, and (3) Monitoring the CHANGELOG.md in the anthropics/claude-code GitHub repository for new hook additions. Hook execution follows a predictable lifecycle: SessionStart runs once per main session (not per subagent), hooks execute in parallel when multiple matchers apply, and all hooks receive common fields including session_id, transcript_path, cwd, and permission_mode.

The distinction between SubagentStart and detecting subagent initialization is critical: SubagentStart fires specifically when a subagent (spawned via Task tool) begins execution and includes agent-specific metadata (agent_id, agent_type), while PreToolUse with a Task tool matcher fires before the Task tool is invoked but lacks subagent-specific context. For multi-agent observability, SubagentStart enables tracking individual subagent lifecycles, while SessionStart fires only once for the parent session regardless of how many subagents are spawned.

## Findings

### Official Documentation

- **Source**: Hooks Reference - Claude Code Docs
  **URL**: https://code.claude.com/docs/en/hooks
  **Author**: Anthropic
  **Date**: 2025-12
  **Activity**: N/A
  **Key points**:
    - Documents 10 hook events: PreToolUse, PermissionRequest, PostToolUse, Notification, UserPromptSubmit, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd
    - All hooks receive common fields: session_id, transcript_path, cwd, permission_mode, hook_event_name
    - Hooks execute in parallel when multiple matchers apply, with 60-second default timeout per hook
    - Exit code 2 blocks operation and shows error message to agent, enabling quality gates
    - SessionStart stdout gets added to context, useful for environment setup and context loading
    - PreToolUse and PermissionRequest hooks can return permission decisions (allow/deny/ask)
    - PostToolUse supports providing feedback or additional context after tool completion

- **Source**: Agent SDK Reference - TypeScript
  **URL**: https://platform.claude.com/docs/en/agent-sdk/typescript
  **Author**: Anthropic
  **Date**: 2025-12
  **Activity**: N/A
  **Key points**:
    - Defines authoritative HookEvent union type with 12 events including SubagentStart and PostToolUseFailure
    - SubagentStartHookInput type includes: hook_event_name: 'SubagentStart', agent_id: string, agent_type: string
    - All hook inputs extend BaseHookInput with session_id, transcript_path, cwd, optional permission_mode
    - HookCallback type signature: (input: HookInput, toolUseID: string | undefined, options: { signal: AbortSignal }) => Promise<HookJSONOutput>
    - TypeScript SDK enables in-process hooks as JS/TS functions, unlike CLI hooks that execute bash commands
    - Complete type definitions for all 12 hook input types with event-specific properties

- **Source**: JSON Schema for Claude Code Settings
  **URL**: https://www.schemastore.org/claude-code-settings.json
  **Author**: SchemaStore Community (maintained)
  **Date**: 2025-12
  **Activity**: N/A
  **Key points**:
    - Defines hooks configuration structure for settings.json
    - Each hook event can have multiple matchers with optional matcher string for tool name patterns
    - Hook types include "command" (bash) and "prompt" (LLM-based evaluation)
    - Lists 9 hook events: PreToolUse, PostToolUse, Notification, UserPromptSubmit, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd
    - Note: Schema may lag behind latest TypeScript SDK which includes SubagentStart and PostToolUseFailure

- **Source**: Get Started with Claude Code Hooks
  **URL**: https://docs.claude.com/en/docs/claude-code/hooks-guide
  **Author**: Anthropic
  **Date**: 2025-12
  **Activity**: N/A
  **Key points**:
    - Hooks are user-defined shell commands executing at lifecycle events for deterministic control
    - Prompt-based hooks use LLM for context-aware decisions, currently supported for Stop and SubagentStop
    - Environment variables available during execution include session_id, transcript_path, cwd
    - SessionStart hook includes CLAUDE_ENV_FILE variable for setting session-wide environment variables
    - Hook execution flow: SessionStart → UserPromptSubmit → PreToolUse → tool execution → PostToolUse
    - PreToolUse runs after Claude creates tool parameters but before processing the tool call

### Source Code Repositories

- **Source**: anthropics/claude-code
  **URL**: https://github.com/anthropics/claude-code
  **Author**: Anthropic
  **Date**: 2025-12 (active development)
  **Activity**: Public repository, active commits
  **Key points**:
    - CHANGELOG.md at github.com/anthropics/claude-code/blob/main/CHANGELOG.md is authoritative source for version history
    - Version 2.0.43 entry explicitly states: "Added the `SubagentStart` hook event"
    - Also added in v2.0.43: permissionMode field for custom agents, tool_use_id field for PreToolUse/PostToolUse hooks
    - Version 2.0.30 added prompt-based stop hooks, v2.0.41 added model parameter for prompt-based hooks
    - Repository contains examples in /plugins directory including hookify and agent-sdk-dev
    - Hookify plugin demonstrates event-based hook patterns for bash, file, stop, prompt, and all event types

- **Source**: disler/claude-code-hooks-multi-agent-observability
  **URL**: https://github.com/disler/claude-code-hooks-multi-agent-observability
  **Author**: disler
  **Date**: 2025-12
  **Activity**: Active project demonstrating real-time hook monitoring
  **Key points**:
    - Implements hooks for 9 events: PreToolUse, PostToolUse, UserPromptSubmit, Notification, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd
    - Uses Python scripts in .claude/hooks/ directory to capture hook events and send to observability server
    - Hook configuration in .claude/settings.json demonstrates multiple hooks per event with matchers
    - Example PreToolUse hook shows access to tool_name and tool_input fields in payload
    - Demonstrates parallel hook execution pattern with validation hook + event tracking hook on same event
    - WebSocket-based real-time visualization with session-based filtering and color coding

- **Source**: disler/claude-code-hooks-mastery
  **URL**: https://github.com/disler/claude-code-hooks-mastery
  **Author**: disler
  **Date**: 2025-12
  **Activity**: Educational repository with hook examples
  **Key points**:
    - Comprehensive examples of all hook event types with practical use cases
    - PreToolUse examples for tool validation, permission control, and blocking dangerous operations
    - PostToolUse examples for logging, feedback, and additional context injection
    - SessionStart examples for environment setup, dependency installation, context loading
    - SubagentStop examples for handoff protocols and parent context bridging
    - Demonstrates hook output format with hookSpecificOutput for additionalContext field

### Community/Third-party

- **Source**: Claude Code Changelog
  **URL**: https://claudelog.com/claude-code-changelog/
  **Author**: ClaudeLog Community
  **Date**: 2025-12
  **Activity**: N/A
  **Key points**:
    - Community-maintained changelog tracking Claude Code version history through December 2025
    - Confirms v2.0.43 added SubagentStart hook event
    - Historical context: v1.0.38 released hooks feature, v1.0.41 split Stop into Stop and SubagentStop
    - v1.0.59 added PermissionRequest hooks for automated permission decisions
    - Useful for tracking when new hooks are introduced across versions

- **Source**: Advanced Claude Code Hooks - Controlling Sub-Agent Behavior
  **URL**: https://ltscommerce.dev/articles/claude-code-hooks-subagent-control.html
  **Author**: LTSCommerce
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Explains subagent detection via parent process ID (PPID) examination
    - SubagentStop fires when subagent (Task tool) completes with stop_hook_active boolean payload
    - Demonstrates using PreToolUse hook with Task tool matcher to intercept subagent creation
    - Key distinction: PreToolUse fires before Task tool invocation, SubagentStart fires after subagent initializes
    - Practical examples of controlling subagent behavior through hook return values (allow/deny/ask)

- **Source**: Claude Code Hooks Guide (Elixir SDK)
  **URL**: https://hexdocs.pm/claude_agent_sdk/hooks_guide.html
  **Author**: HexDocs
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Documents 8 hook events with detailed lifecycle timing
    - SessionStart fires when Claude Code starts new session or resumes existing one
    - Source field indicates startup, resume, or clear to distinguish session initialization types
    - SessionStart output additionalContext adds string to Claude's context window
    - Stop and SubagentStop hooks can control continuation with block permission
    - PreToolUse runs after Claude creates tool parameters but before processing

- **Source**: Feature Request - SessionStart and SessionEnd Lifecycle Hooks
  **URL**: https://github.com/anthropics/claude-code/issues/4318
  **Author**: GitHub Community
  **Date**: 2024-2025
  **Activity**: N/A
  **Key points**:
    - Historical context for SessionStart hook introduction
    - Community discussion about session lifecycle tracking requirements
    - Use cases: loading development context, git status, recent issues, dependency installation
    - CLAUDE_ENV_FILE variable specific to SessionStart for session-wide environment setup
    - Clarifies that SessionStart fires once per session, not per subagent invocation

- **Source**: SubagentStop Hook Cannot Identify Specific Subagent
  **URL**: https://github.com/anthropics/claude-code/issues/7881
  **Author**: GitHub Community
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Issue tracking problem: multiple subagents share same session_id in SubagentStop hook
    - Explains need for SubagentStart hook to provide agent_id for distinguishing subagent instances
    - Context for why SubagentStart was added in v2.0.43 with agent_id and agent_type fields
    - Demonstrates real-world need for tracking individual subagent lifecycles in multi-agent systems
    - SubagentStart addresses observability gap for parallel subagent execution tracking

## Sources
- https://code.claude.com/docs/en/hooks
- https://platform.claude.com/docs/en/agent-sdk/typescript
- https://www.schemastore.org/claude-code-settings.json
- https://docs.claude.com/en/docs/claude-code/hooks-guide
- https://github.com/anthropics/claude-code
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://github.com/disler/claude-code-hooks-multi-agent-observability
- https://github.com/disler/claude-code-hooks-mastery
- https://claudelog.com/claude-code-changelog/
- https://ltscommerce.dev/articles/claude-code-hooks-subagent-control.html
- https://hexdocs.pm/claude_agent_sdk/hooks_guide.html
- https://github.com/anthropics/claude-code/issues/4318
- https://github.com/anthropics/claude-code/issues/7881
- https://github.com/anthropics/claude-code/issues/6223
- https://github.com/anthropics/claude-code/issues/5812
- https://code.claude.com/docs/en/sub-agents
- https://www.arsturn.com/blog/a-beginners-guide-to-using-subagents-and-hooks-in-claude-code
- https://claudelog.com/mechanics/task-agent-tools/
- https://medium.com/@sampan090611/experiences-on-claude-codes-subagent-and-little-tips-for-using-claude-code-c4759cd375a7

## Metadata
- **Research Date**: 2025-12-10T00:00:00Z
- **Search Queries**: claude code hooks SubagentStart v2.0.43 changelog, anthropics claude code github hook events typescript types, claude code hooks.json schema available events 2025, claude code hook lifecycle SessionStart SubagentStop execution order, claude code programmatically discover available hooks events, site:github.com/anthropics/claude-code SubagentStart hook payload typescript, SubagentStart claude code when fires trigger conditions, claude code SessionStart fires once per session or per subagent, claude code PreToolUse hook Task tool subagent start detection, claude code SubagentStart vs PreToolUse Task tool when trigger, SubagentStartHookInput typescript claude code agent sdk, claude code hooks execution order PreToolUse SessionStart timing lifecycle
- **Agent Model**: claude-sonnet-4-5@20250929
