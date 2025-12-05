# Research: Agentic Development Practices for Claude Code

## Research Objective
Research agentic development practices, particularly implementing them via Claude Code, focusing on Anthropic's official documentation and practical examples to learn how to build good, reliable agents.

## Executive Summary

This research investigated agentic development practices for Claude Code by examining Anthropic's official documentation, three key reference repositories, and community best practices. The findings reveal a consistent architectural pattern built around the "agent loop" (gather context → take action → verify work → repeat), emphasizing single-responsibility subagents coordinated by orchestrators, progressive disclosure for token efficiency, and strict permission controls for production safety.

Key architectural patterns emerged across sources: modular skill-based design, multi-stage workflows with quality gates, and hybrid model orchestration (Haiku for deterministic tasks, Sonnet for complex reasoning). The most successful agents follow test-driven development, maintain isolated contexts per subagent, and use memory systems for learning. Production deployments require container-based sandboxing, careful permission scoping, and automated testing gates.

The transition from Claude Code SDK to Claude Agent SDK represents a broader vision beyond coding, with agents now being used for research, content creation, and general automation. The ecosystem supports cross-platform skills (Claude.ai, Claude Code, Claude Agent SDK, Developer Platform) with consistent APIs and progressive loading mechanisms.

## Findings

### Official Documentation

- **Source**: Building agents with the Claude Agent SDK - [https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
  **Author**: Anthropic Engineering Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Core agent loop: gather context → take action → verify work → repeat
    - Context gathering uses "agentic search", subagents for parallel operations, and context compaction
    - Actions implemented through precise tools, bash scripts, code generation, and MCP integrations
    - Verification via linting, visual checks, and optional AI judging
    - Production rule: give each subagent one job, let orchestrators coordinate
    - Built-in features include error handling, session management, and automatic context compaction

- **Source**: Claude Code: Best practices for agentic coding - [https://www.anthropic.com/engineering/claude-code-best-practices](https://www.anthropic.com/engineering/claude-code-best-practices)
  **Author**: Anthropic Engineering Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Setup via CLAUDE.md file for bash commands, style guidelines, testing instructions, and repository etiquette
    - Workflow pattern: explore → plan → code → commit
    - Test-driven development: write tests first, confirm failure, implement to pass, verify no overfitting
    - Visual iteration using screenshots, design mocks, and tools like Puppeteer
    - Advanced techniques: multi-Claude workflows, custom slash commands, git worktrees, headless mode, subagents
    - Optimization: be specific, course-correct early, use /clear for context, leverage checklists and visual references

- **Source**: Subagents - Claude Code Docs - [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Subagents operate in separate context windows with specific purposes
    - Created via `/agents` command with name, description, and optional configurations
    - Configuration options: project/user-level, custom tool access, model selection (sonnet/opus/haiku), skills, permission modes
    - Built-in types: general-purpose (complex tasks), plan (planning mode research), explore (lightweight file searching)
    - Best practices: focused single-purpose, detailed system prompts, limited tool access, version control project subagents
    - Use cases: code review, debugging, data analysis, task-specific research

- **Source**: Agent Skills - Overview - [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Modular capabilities extending Claude via filesystem-based architecture
    - Benefits: specialize Claude, reduce repetitive instructions, compose workflows, progressive loading
    - Structure: SKILL.md with YAML frontmatter (name, description), instructions, examples, resources
    - Progressive loading: metadata (~100 tokens always), instructions (<5k when triggered), resources (unlimited as needed)
    - Supported platforms: Claude API, Claude Code, Claude Agent SDK, Claude.ai
    - Pre-built skills: PowerPoint, Excel, Word, PDF
    - Security: use only trusted sources, audit contents, be cautious with dependencies

- **Source**: Hosting the Agent SDK - Claude Docs - [https://platform.claude.com/docs/en/agent-sdk/hosting](https://platform.claude.com/docs/en/agent-sdk/hosting)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Runtime requirements: Python 3.10+/Node.js 18+, Claude Code CLI
    - Resources: 1GiB RAM, 5GiB disk, 1 CPU recommended
    - Network: outbound HTTPS to api.anthropic.com
    - Container-based sandboxing for isolation, resource limits, network control, ephemeral filesystems
    - Deployment patterns: ephemeral (new per task), long-running (persistent), hybrid (resumable), single container (multi-agent)
    - Recommended providers: Cloudflare, Modal, Daytona, E2B, Fly Machines, Vercel
    - Cost: ~$0.05/hour for containers, tokens are primary expense
    - Configure maxTurns to prevent infinite loops

### Source Code Repositories

- **Source**: superpowers - [https://github.com/obra/superpowers](https://github.com/obra/superpowers)
  **Author**: obra
  **Date**: Active development
  **Activity**: Multiple stars, recent commits
  **Key points**:
    - "Subagent-driven-development" approach with collaborative agents
    - Agents work autonomously for extended periods while adhering to initial plan
    - Emphasizes test-driven development and RED-GREEN-REFACTOR cycle
    - Work broken into small tasks (2-5 minutes each)
    - Philosophy: "evidence over claims", "systematic over ad-hoc", complexity reduction
    - Skills are composable, modular building blocks triggering automatically during development stages
    - Meta-skills exist for creating and testing new skills
    - Workflow stages: brainstorming, planning, execution, code review, branch management
    - Mandatory workflow skills, not mere suggestions

- **Source**: agentic-development-plugins - [https://github.com/jsell-rh/agentic-development-plugins](https://github.com/jsell-rh/agentic-development-plugins)
  **Author**: jsell-rh
  **Date**: Active development
  **Activity**: Active commits
  **Key points**:
    - Zero-assumption development with strict quality gates
    - Spec-driven code generation with atomic commits per task
    - Self-learning agent memory system tracking patterns, solutions, mistakes, standards
    - Memory limit: 50 entries per agent with timestamp, pattern, action, context
    - Multi-stage workflow: requirements refinement → spec generation → development management → task assignment → specialized execution → spec alignment review
    - Token-efficient context management
    - Technical defaults: Red Hat UBI9, Python 3.13+, Pydantic, FastAPI with subrouter pattern, Konflux/Tekton CI/CD
    - System designed for "spec-driven development orchestration" with zero-assumption execution

- **Source**: agents - [https://github.com/wshobson/agents](https://github.com/wshobson/agents)
  **Author**: wshobson
  **Date**: Active development
  **Activity**: Active commits
  **Key points**:
    - Granular design: single responsibility per plugin, average 3.4 components per plugin
    - Minimal token usage with completely isolated agents, commands, and skills
    - Progressive disclosure model: metadata (always loaded) → instructions (on demand) → resources (when needed)
    - Hybrid model orchestration: 47 Haiku agents for fast deterministic tasks, 97 Sonnet agents for complex reasoning
    - 47 specialized skills across 14 plugins following progressive disclosure
    - Repository structure: .claude-plugin/marketplace.json catalog, plugins/ with agents/commands/skills subdirectories
    - Design philosophy: "mix and match for complex workflows" with 100% agent accessibility across plugins
    - Three-tier knowledge architecture for efficient token management

### Community/Third-party

- **Source**: Best practices for Claude Code subagents - [https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
  **Author**: PubNub
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Subagents are specialized assistants with customized system prompts, tools, and separate context windows
    - Each operates in isolated context space preventing cross-contamination
    - Architecture patterns: three-stage pipeline (PM spec → architect review → implementer/tester), specialized roles, parallel processing
    - File structure uses YAML frontmatter with name, description, tools field
    - Discovered from project's .claude/agents/ directory or user scope
    - Best practices: one clear goal per agent, action-oriented descriptions, scoped tool access
    - PM & Architect are read-heavy (search, docs via MCP); Implementer gets Edit/Write/Bash; Release gets minimal tools

- **Source**: Claude Agent SDK Best Practices for AI Agent Development (2025) - [https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
  **Author**: Skywork AI
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Production agents: give each subagent one job, orchestrator coordinates with global planning/delegation/state
    - Permission sprawl is fastest path to unsafe autonomy - treat tool access like production IAM
    - Start from deny-all, allowlist only needed commands/directories
    - Require explicit confirmations for sensitive actions (git push, infrastructure changes)
    - Block dangerous commands (rm -rf, sudo)
    - Gate deployments with automated tests, stage rollouts with feature flags, set rollback triggers
    - Deploy small and iterate - learn more from one production deployment than 10 prototypes
    - Dominant cost is tokens; containers ~$0.05/hour minimum
    - Set maxTurns to prevent infinite loops

- **Source**: VoltAgent/awesome-claude-code-subagents - [https://github.com/VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)
  **Author**: VoltAgent
  **Date**: Active
  **Activity**: Production-ready collection
  **Key points**:
    - Definitive collection of production-ready Claude Code subagents
    - 100+ specialized AI agents for full-stack development, DevOps, data science, business operations
    - Organized by domain with specific use cases
    - Community-contributed and maintained

- **Source**: How Anthropic teams use Claude Code - [https://www.anthropic.com/news/how-anthropic-teams-use-claude-code](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)
  **Author**: Anthropic
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Claude Code used internally for deep research, video creation, note-taking, non-coding applications
    - Originally built for developer productivity, now broader vision
    - Renaming from "Claude Code SDK" to "Claude Agent SDK" reflects this expansion
    - Internal teams use for diverse workflows beyond traditional coding

- **Source**: Building effective agents (Research) - [https://www.anthropic.com/research/building-effective-agents](https://www.anthropic.com/research/building-effective-agents)
  **Author**: Anthropic Research Team
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - Research and planning crucial first steps - prevents jumping straight to coding
    - Planning significantly improves performance for problems requiring deeper thinking
    - Feedback loop pattern central to agent effectiveness
    - Context management and verification essential components

## Architectural Patterns Summary

### The Agent Loop (Universal Pattern)
1. **Gather Context**: Agentic search, subagents for parallel operations, context compaction
2. **Take Action**: Tools, bash scripts, code generation, MCP integrations
3. **Verify Work**: Linting, visual checks, tests, AI judging
4. **Repeat**: Iterative refinement

### Multi-Agent Orchestration Patterns

**Three-Stage Pipeline**:
- PM/Spec: Requirements gathering, clarifying questions, status management
- Architect: Design validation, platform constraints, ADR production
- Implementer/Tester: Code/test implementation, documentation updates

**Specialized Roles**:
- Product Spec (requirements)
- Architect (validation)
- Implementer (build & test)
- QA (verification)
- Orchestrator (coordination, global planning, state management)

**Parallel Processing**:
- Primary agent identifies tasks
- Dedicated subagent per task/file
- Concurrent execution for speed

### Progressive Disclosure (Token Efficiency)
1. **Metadata**: Always loaded (~100 tokens) - name, description, triggers
2. **Instructions**: Loaded on demand (<5k tokens) - detailed how-to
3. **Resources**: Loaded as needed (unlimited) - examples, templates, data

### Hybrid Model Strategy
- **Haiku**: Fast deterministic tasks (47 agents in wshobson example)
- **Sonnet**: Complex reasoning and architecture (97 agents in wshobson example)
- Strategic assignment based on task complexity

### Memory Systems
- Track observed patterns, effective solutions, common mistakes, project standards
- Limit entries (e.g., 50 per agent) for manageability
- Include timestamp, pattern, action, context
- Enable self-learning and continuous improvement

## Implementation Best Practices

### Agent Design
- **Single Responsibility**: One clear goal, input, output, and handoff rule per agent
- **Focused Scope**: Limit tool access to only what's needed
- **Isolation**: Separate context windows prevent cross-contamination
- **Action-Oriented**: Descriptions should be imperative and specific

### Tool Permissions (Production IAM Approach)
- Start from deny-all
- Allowlist only necessary commands/directories
- PM & Architect: read-heavy (search, docs via MCP)
- Implementer: Edit, Write, Bash, UI testing
- Release: minimal required tools
- Require confirmations for sensitive actions (git push, infrastructure)
- Block dangerous commands (rm -rf, sudo)

### Development Workflow
- **Research & Plan First**: Prevents premature coding, improves outcomes
- **Test-Driven Development**: Write tests → confirm failure → implement → verify
- **Incremental**: Small tasks (2-5 minutes), continuous refinement
- **Evidence Over Claims**: Validate assumptions, test rigorously

### Context Management
- Use CLAUDE.md for bash commands, style guidelines, testing instructions, repository etiquette
- Leverage /clear to maintain focused context
- Memory.md documents capture project state for continuity across sessions
- Progressive loading minimizes token usage

### Production Deployment
- **Container Sandboxing**: Process isolation, resource limits, network control, ephemeral filesystems
- **Security**: Deny-all permissions, explicit allowlists, confirmation gates
- **Testing**: Automated tests gate deployments
- **Deployment Strategy**: Feature flags for staged rollouts, rollback triggers on anomalies
- **Monitoring**: Set maxTurns to prevent loops, monitor container health
- **Cost**: Tokens primary expense (~$0.05/hour for container minimum)

### Quality Gates
- Spec-driven development with validation at each stage
- Code review between tasks
- Test output must be pristine
- Alignment reviews against specifications

## Technical Stack Patterns

### Repository Structure
```
project/
├── .claude/
│   ├── agents/           # Project-level subagents
│   ├── commands/         # Custom slash commands
│   └── skills/           # Domain-specific knowledge
├── .claude-plugin/
│   └── marketplace.json  # Plugin catalog
└── CLAUDE.md            # Project instructions
```

### Skill Structure
```
skill-name/
├── SKILL.md             # Main file with YAML frontmatter + instructions
├── templates/           # Optional templates
└── resources/           # Optional additional resources
```

### Common Tech Choices (from examples)
- Python 3.10+ or Node.js 18+
- Container runtimes: Docker, Podman
- Sandboxes: Cloudflare, Modal, Daytona, E2B, Fly, Vercel
- API frameworks: FastAPI with subrouter pattern
- CI/CD: Konflux, Tekton, GitHub Actions

## Key Learnings for Building Better Agents

1. **Start with Architecture**: Define orchestrator + specialized subagents before coding
2. **Progressive Disclosure**: Load only what's needed when needed
3. **Strict Permissions**: Treat tool access like production IAM from day one
4. **Test Gates**: Quality gates at every stage prevent downstream issues
5. **Memory Systems**: Self-learning agents improve over time
6. **Context Isolation**: Separate windows prevent interference
7. **Hybrid Models**: Match model to task complexity
8. **Deploy Small**: Learn from production faster than from prototypes
9. **Evidence-Based**: Validate assumptions, don't assume success
10. **Skills Over Prompts**: Reusable, composable skills beat repeated instructions

## Sources

**Official Anthropic Documentation:**
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Agent Skills - Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Hosting the Agent SDK](https://platform.claude.com/docs/en/agent-sdk/hosting)
- [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [How Anthropic teams use Claude Code](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)
- [Building effective agents (Research)](https://www.anthropic.com/research/building-effective-agents)

**Reference Repositories:**
- [obra/superpowers](https://github.com/obra/superpowers)
- [jsell-rh/agentic-development-plugins](https://github.com/jsell-rh/agentic-development-plugins)
- [wshobson/agents](https://github.com/wshobson/agents)
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)

**Community Resources:**
- [Best practices for Claude Code subagents - PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
- [Claude Agent SDK Best Practices (2025) - Skywork AI](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
- [Optimizing Agentic Coding - AIM Multiple](https://research.aimultiple.com/agentic-coding/)
- [How to Use Claude Code Subagents - GoatReview](https://goatreview.com/how-to-use-claude-code-subagents-tutorial/)
- [Claude Agent SDK Tutorial - DataCamp](https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk)

## Metadata
- **agent-type**: web-research-agent-v1
- **Research Date**: 2025-12-05
- **Search Queries**: "Anthropic Claude Code agents building documentation 2025", "Claude Agent SDK official documentation", "agentic development workflows Claude best practices", "Claude Code subagent patterns architecture examples", "Claude Agent SDK production deployment best practices"
- **Agent Model**: claude-sonnet-4-5@20250929
