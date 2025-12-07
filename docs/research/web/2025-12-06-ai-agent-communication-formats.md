# Research: AI Agent Communication Formats and Structured Output Best Practices

## Research Objective
Investigate best practices for structured AI-to-AI communication, markdown compression and condensed formatting techniques, optimization strategies for AI consumption versus human consumption, and standardized formats for agent-to-agent data exchange.

## Executive Summary
The landscape of AI agent communication has rapidly evolved in 2025, with three major open protocols emerging as standards: Google's Agent2Agent (A2A) Protocol using JSON-RPC 2.0 over HTTPS, Anthropic's Model Context Protocol (MCP) for standardized context provision, and IBM's Agent Communication Protocol (ACP) which has merged into A2A under the Linux Foundation. All three protocols rely on JSON-RPC 2.0 as the primary message format, with structured JSON schemas enforcing data validation and type safety. Major AI providers including Anthropic (Claude) and OpenAI (GPT-4) have released structured output capabilities in 2024-2025 that guarantee schema compliance, enabling reliable machine-to-machine communication.

For output formatting, research demonstrates that Markdown is approximately 15% more token-efficient than JSON for LLM communication, though model preferences vary—GPT-4 favors Markdown while GPT-3.5-turbo prefers JSON, with performance differences reaching up to 42% on specific tasks. The emerging AGENTS.md standard provides a lightweight, project-specific instruction format that agents can quickly parse without verbose documentation. When strict schema validation is required, JSON Schema with strict mode (available in Claude Sonnet/Opus/Haiku 4.x and GPT-4o models) provides guaranteed structural compliance, though at the cost of reduced flexibility compared to extended thinking modes.

Production implementations demonstrate practical patterns: GitHub's official MCP server showcases repository intelligence and CI/CD integration, A2A protocol implementations span five major programming languages with active community adoption, and the Agent Data Protocol (ADP) provides a unified trajectory-based representation for agent training data. The key tradeoff in agent communication is between human readability (favoring Markdown) and machine validation (favoring JSON Schema), with best practices recommending format selection based on specific use case requirements rather than universal rules.

## Findings

### Official Documentation

- **Source**: Structured outputs - Claude Documentation
  **URL**: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  **Author**: Anthropic
  **Date**: 2025-11
  **Activity**: N/A
  **Key points**:
    - JSON Schema-based structured outputs available in Claude Sonnet 4.5, Opus 4.1, Opus 4.5, and Haiku 4.5
    - Use `anthropic-beta: structured-outputs-2025-11-13` header with `output_format` parameter
    - SDK support for Pydantic (Python) and Zod (TypeScript) for schema definition
    - Keep schemas simple, avoid recursive schemas and complex constraints
    - Set `additionalProperties: false` for strict validation
    - Schema compilation is cached for 24 hours, first compilation has higher latency
    - Incompatible with citations and message prefilling

- **Source**: Structured model outputs - OpenAI API Documentation
  **URL**: https://platform.openai.com/docs/guides/structured-outputs
  **Author**: OpenAI
  **Date**: 2024-08
  **Activity**: N/A
  **Key points**:
    - Structured Outputs ensure model-generated outputs exactly match provided JSON Schemas
    - Available in gpt-4o-mini, gpt-4o-2024-08-06, and all models after gpt-4-0613
    - Enable by setting `strict: true` parameter in API call
    - Use `json_schema` option for response_format parameter
    - Guarantees schema adherence unlike older JSON mode which only ensured valid JSON
    - Supports both response format and function calling patterns

- **Source**: Model Context Protocol Introduction
  **URL**: https://www.anthropic.com/news/model-context-protocol
  **Author**: Anthropic
  **Date**: 2024-11
  **Activity**: N/A
  **Key points**:
    - Open standard for secure, two-way connections between AI applications and data sources
    - Client-server architecture: AI apps use MCP clients to connect to MCP servers
    - Uses JSON-RPC for standardized communication between clients and servers
    - Primitives include Prompts, Resources, Tools (server-side) and Roots, Sampling (client-side)
    - SDKs available in Python, TypeScript, C#, and Java
    - Pre-built servers for Google Drive, Slack, GitHub, Git, Postgres, Puppeteer

- **Source**: Agent2Agent (A2A) Protocol Specification
  **URL**: https://a2a-protocol.org/latest/specification/
  **Author**: Google / Linux Foundation
  **Date**: 2025-04
  **Activity**: N/A
  **Key points**:
    - Open protocol enabling communication between opaque agentic applications
    - Uses JSON-RPC 2.0 over HTTP(S) for all requests and responses
    - Supports agent discovery via "Agent Cards" with capability descriptions
    - Flexible interaction patterns: synchronous request/response, streaming (SSE), async push notifications
    - Rich data exchange handling text, files, and structured JSON data
    - Core operations include SendMessage, streaming, task management (get, list, cancel)
    - Maintains context via `contextId` for multi-turn interactions

- **Source**: Agent Communication Protocol Welcome
  **URL**: https://agentcommunicationprotocol.dev/introduction/welcome
  **Author**: IBM BeeAI / Linux Foundation
  **Date**: 2024-12
  **Activity**: N/A
  **Key points**:
    - REST-based API enabling communication across different frameworks and platforms
    - Supports synchronous and asynchronous interactions with streaming support
    - Multimodal message support: structured data, plain text, images, embeddings
    - Stateful and stateless operation patterns, online and offline agent discovery
    - SDKs available in Python and TypeScript
    - ACP has merged with A2A under Linux Foundation umbrella
    - Designed for flexible agent replacement and multi-agent collaboration

- **Source**: Building Effective Agents - Anthropic Engineering
  **URL**: https://www.anthropic.com/engineering/building-effective-agents
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Start with simplest solution, only add complexity when it demonstrably improves outcomes
    - Explicitly show agent's planning steps for transparency
    - Create clear, well-documented tool interfaces with examples and edge cases
    - Use workflows for predictable tasks, agents for open-ended problems
    - Workflow patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer
    - Agents have higher costs and potential for compounding errors
    - Maintain human oversight, especially for critical tasks

### Source Code Repositories

- **Source**: GitHub MCP Server
  **URL**: https://github.com/github/github-mcp-server
  **Author**: GitHub
  **Date**: 2025-10
  **Activity**: Active development, last commit October 2025
  **Key points**:
    - Official MCP server from GitHub for repository intelligence and automation
    - OAuth authentication via https://api.githubcopilot.com/mcp/
    - Features: code search, file streaming, PR/issue management, CI/CD visibility, security insights
    - Requires Docker installation and GitHub Personal Access Token
    - Server instructions enable new model interaction patterns
    - Consolidated tools for reduced footprint and easier configuration

- **Source**: Model Context Protocol Servers
  **URL**: https://github.com/modelcontextprotocol/servers
  **Author**: Anthropic / MCP Community
  **Date**: 2025-12
  **Activity**: Active community development, updated December 2025
  **Key points**:
    - Collection of reference MCP server implementations
    - Pre-built servers for Google Drive, Slack, GitHub, Git, Postgres, Puppeteer
    - Demonstrates protocol implementation patterns across different data sources
    - Official SDKs available in TypeScript, Go (with Google), Kotlin (with JetBrains)
    - Community-maintained awesome-mcp-servers lists with curated collections

- **Source**: A2A Protocol Samples
  **URL**: https://github.com/a2aproject/a2a-samples
  **Author**: A2A Project / Linux Foundation
  **Date**: 2025-11
  **Activity**: 1,056 stars, updated November 2025
  **Key points**:
    - Official sample implementations demonstrating A2A protocol mechanics
    - Examples: Hello World Agent, CurrencyAgent, GitHub Agent, Travel Planner
    - Language-specific SDKs: Python (a2a-python), JavaScript (a2a-js), Go (a2a-go), C#/.NET (a2a-dotnet), Java (a2a-java)
    - All SDKs updated December 2025 with active maintenance
    - Includes a2a-inspector tool for validation and compliance checking

- **Source**: Agent Communication Protocol
  **URL**: https://github.com/i-am-bee/acp
  **Author**: IBM BeeAI
  **Date**: 2024-12
  **Activity**: Last updated December 2024 (merged into A2A)
  **Key points**:
    - Python SDK with server implementation, client libraries, and model definitions
    - Example implementations: Simple echo agent, RAG agent with CrewAI, Smolagents chaining
    - REST-based endpoints following standard HTTP patterns
    - Supports single-agent and multi-agent architectures
    - Protocol contributed to A2A under Linux Foundation
    - Ready-to-run code samples for quick implementation

- **Source**: Anthropic Structured Outputs Course
  **URL**: https://github.com/anthropics/courses/blob/master/tool_use/03_structured_outputs.ipynb
  **Author**: Anthropic
  **Date**: 2024
  **Activity**: Part of official Anthropic courses repository
  **Key points**:
    - Demonstrates using tool definitions to enforce JSON structure
    - Claude responds with tool call format matching the defined schema
    - Technique leverages tool use mechanics for consistent JSON responses
    - Provides code examples for Python SDK implementation
    - Shows how to design precise tool schemas for structured data extraction

### Community/Third-party

- **Source**: Agent Data Protocol: Unifying Datasets for Diverse, Effective Fine-tuning of LLM Agents
  **URL**: https://arxiv.org/html/2510.24702v1
  **Author**: arXiv Research Paper
  **Date**: 2024-10
  **Activity**: N/A
  **Key points**:
    - Standardized representation language for agent data (ADP)
    - Unifies datasets into Trajectory objects with Actions and Observations
    - Action types: API actions, code actions, message actions
    - Observation types: text observations, web observations (HTML, accessibility tree, URL)
    - Serves as "interlingua" between diverse agent datasets and training pipelines
    - Reduces conversion complexity from quadratic O(D×A) to linear O(D+A) effort
    - Enables large-scale diverse data generation for agent training

- **Source**: Does Prompt Formatting Have Any Impact on LLM Performance?
  **URL**: https://arxiv.org/html/2411.10541v1
  **Author**: arXiv Research Paper
  **Date**: 2024-11
  **Activity**: N/A
  **Key points**:
    - Prompt format significantly impacts GPT-based model performance
    - Performance variations up to 40% for GPT-3.5-turbo across different formats
    - 42% accuracy difference between JSON and Markdown on specific tasks
    - GPT-3.5-turbo preferred JSON formats, GPT-4 favored Markdown
    - Larger models (GPT-4) more robust to format changes than smaller models
    - No single format excels universally across all tasks
    - Recommends testing models with diverse prompt formats for accurate capability assessment

- **Source**: Markdown is 15% more token efficient than JSON
  **URL**: https://community.openai.com/t/markdown-is-15-more-token-efficient-than-json/841742
  **Author**: OpenAI Developer Community
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Markdown uses 11,612 tokens vs JSON's 13,869 tokens for same data (15% efficiency)
    - Markdown and XML more token-efficient than JSON
    - LLMs process Markdown with reduced cognitive load compared to nested JSON/XML tags
    - Markdown preferred for readability, simplicity, and token efficiency
    - Best for general content: blogs, documentation, FAQs, structured instructions
    - JSON/XML better for strict data structuring in data-heavy scenarios

- **Source**: Improve your AI code output with AGENTS.md
  **URL**: https://www.builder.io/blog/agents-md
  **Author**: Builder.io
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - AGENTS.md is project-wide markdown file providing guidelines for AI agents
    - Serves as "README for AI agents" with default project-specific instructions
    - Keep it small, scoped, and clear
    - Include dos/don'ts with version-specific instructions and preferred libraries
    - Provide file-scoped commands (type check, format, lint, test per file)
    - Avoids repetitive explanations and reduces agent discovery time
    - Growing standard for centralized agent instruction management

- **Source**: Markdown for Prompt Engineering Best Practices
  **URL**: https://tenacity.io/snippets/supercharge-ai-prompts-with-markdown-for-better-results/
  **Author**: Tenacity
  **Date**: 2024
  **Activity**: N/A
  **Key points**:
    - Use headings (##) to separate instructions from context
    - Use bulleted lists instead of run-on sentences for requirements
    - Markdown is easy to read for people unfamiliar with structured formats
    - Lightweight formatting focused on clarity
    - Combines structure with readability
    - Widely supported across AI platforms
    - Recommended starting point for prompt engineering

- **Source**: Exploring How to Produce Structured Output with AI Agents
  **URL**: https://medium.com/@sainitesh/exploring-how-to-produce-structured-output-with-ai-agents-5d35a0b0d195
  **Author**: Sai Nitesh Palamakula / Medium
  **Date**: 2025-11
  **Activity**: N/A
  **Key points**:
    - Structured output transforms agents from conversational tools to automation components
    - Enables seamless integration with downstream systems and schema validation
    - Enables machine-to-machine communication with predictable formats
    - Schema validation catches errors early in processing pipeline
    - JSON or typed objects required for API and dashboard integration
    - Structured output essential for building reliable agentic workflows

- **Source**: MCP vs A2A: A Guide to AI Agent Communication Protocols
  **URL**: https://auth0.com/blog/mcp-vs-a2a/
  **Author**: Auth0 Engineering Blog
  **Date**: 2025
  **Activity**: N/A
  **Key points**:
    - MCP focuses on AI-to-data-source connections, A2A on agent-to-agent communication
    - Both use JSON-RPC for standardized communication
    - MCP primitives: Prompts, Resources, Tools (server) and Roots, Sampling (client)
    - A2A supports agent discovery, flexible interactions, rich data exchange
    - 85% of enterprises expected to implement AI agents by end-2025
    - Protocols enable scalable, interoperable, secure agentic ecosystems
    - Complementary protocols addressing different aspects of agent architecture

## Sources
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- https://platform.openai.com/docs/guides/structured-outputs
- https://www.anthropic.com/news/model-context-protocol
- https://a2a-protocol.org/latest/specification/
- https://agentcommunicationprotocol.dev/introduction/welcome
- https://www.anthropic.com/engineering/building-effective-agents
- https://github.com/github/github-mcp-server
- https://github.com/modelcontextprotocol/servers
- https://github.com/a2aproject/a2a-samples
- https://github.com/i-am-bee/acp
- https://github.com/anthropics/courses/blob/master/tool_use/03_structured_outputs.ipynb
- https://arxiv.org/html/2510.24702v1
- https://arxiv.org/html/2411.10541v1
- https://community.openai.com/t/markdown-is-15-more-token-efficient-than-json/841742
- https://www.builder.io/blog/agents-md
- https://tenacity.io/snippets/supercharge-ai-prompts-with-markdown-for-better-results/
- https://medium.com/@sainitesh/exploring-how-to-produce-structured-output-with-ai-agents-5d35a0b0d195
- https://auth0.com/blog/mcp-vs-a2a/
- https://medium.com/@sainitesh/exploring-how-to-produce-structured-output-with-ai-agents-5d35a0b0d195
- https://onereach.ai/blog/power-of-multi-agent-ai-open-protocols/
- https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- https://www.ibm.com/think/topics/ai-agent-protocols
- https://www.ibm.com/think/topics/agent-communication-protocol
- https://github.com/punkpeye/awesome-mcp-servers
- https://github.com/wong2/awesome-mcp-servers
- https://github.com/ai-boost/awesome-a2a
- https://adasci.org/a-practitioners-guide-to-agent-communication-protocol-acp/

## Metadata
- **Research Date**: 2025-12-06T19:30:00Z
- **Search Queries**: AI agent communication formats structured output 2025, markdown compression techniques AI consumption 2024 2025, agent-to-agent data exchange standardized formats LLM, Anthropic Claude structured output best practices documentation, OpenAI structured outputs JSON schema GPT-4 documentation, LLM prompt engineering structured output markdown vs JSON efficiency, AI agent markdown formatting best practices condensed output, Model Context Protocol MCP Anthropic documentation communication format, Google A2A protocol agent-to-agent communication JSON-RPC specification, GitHub MCP server examples implementation 2025, A2A protocol implementation examples GitHub 2025, agent communication protocol ACP examples implementation
- **Agent Model**: claude-sonnet-4-5@20250929
