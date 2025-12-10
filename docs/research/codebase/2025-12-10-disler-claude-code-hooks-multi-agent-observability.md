# Claude Code Multi-Agent Observability System

## 1. Overview

### Project Purpose
A comprehensive real-time monitoring and visualization system for Claude Code agents, designed to capture, store, and display hook events across multiple concurrent agent sessions.

### Key Features
- Real-time WebSocket event streaming
- Multi-agent event tracking
- Comprehensive hook event monitoring
- Configurable filtering and visualization

### Technical Stack
- **Server**: Bun, TypeScript, SQLite
- **Client**: Vue 3, TypeScript, Vite, Tailwind CSS
- **Hooks**: Python 3.8+, Astral uv
- **Communication Protocols**: HTTP REST, WebSocket

## 2. Architecture Overview

### System Components
1. **Hook System** (`.claude/hooks/`)
   - Intercept Claude Code lifecycle events
   - Send events to central observability server
   - Provide event validation and filtering

2. **Event Server** (`apps/server/`)
   - Bun-powered TypeScript server
   - SQLite event storage (WAL mode)
   - WebSocket real-time broadcasting
   - RESTful event management endpoints

3. **Visualization Client** (`apps/client/`)
   - Vue 3 single-page application
   - Real-time event timeline
   - Advanced filtering capabilities
   - Responsive design with dark/light themes

### Data Flow
```
Claude Agents → Hook Scripts → HTTP POST → Bun Server → SQLite → WebSocket → Vue Client
```

## 3. Hook Implementation Details

### Supported Hook Types
- `PreToolUse`: Before tool execution
- `PostToolUse`: After tool completion
- `Notification`: User interactions
- `Stop`: Response completion
- `SubagentStop`: Subagent task finished
- `PreCompact`: Context compaction
- `UserPromptSubmit`: User prompt logging
- `SessionStart/End`: Session lifecycle tracking

### Event Capture Mechanism
- Lightweight Python scripts in `.claude/hooks/`
- Universal `send_event.py` for event transmission
- Configurable via `settings.json`
- Optional chat history and summarization

## 4. Server Architecture

### HTTP Endpoints
- `POST /events`: Receive new events
- `GET /events/recent`: Retrieve recent events
- `GET /events/filter-options`: Get available filtering options
- WebSocket `/stream`: Real-time event broadcasting

### WebSocket Implementation
- Persistent connections for real-time updates
- Automatic client management
- Initial event replay on connection
- Error and disconnection handling

### Database Design
- SQLite with Write-Ahead Logging (WAL)
- Event storage with comprehensive metadata
- Supports paginated and filtered event retrieval

## 5. Client Features

### Visualization Capabilities
- Dual-color event representation
- Live pulse chart with session coloring
- Multi-criteria filtering
- Chat transcript viewer
- Responsive, animated interface

### Performance Optimizations
- Configurable maximum displayed events
- Canvas-based real-time charting
- WebSocket-driven updates
- Efficient event aggregation

## 6. Integration Patterns

### Setup Requirements
- Claude Code (official CLI)
- Python 3.8+
- Astral uv package manager
- Bun or npm/yarn

### Configuration
- Copy `.claude` directory to project root
- Update `settings.json` with project-specific hooks
- Set environment variables for API keys

## 7. Security Considerations

### Built-in Protections
- Command execution validation
- Prevent access to sensitive files
- Input sanitization
- Configurable event filtering

## 8. Future Potential

### Expansion Opportunities
- Multi-model support
- Enhanced visualization features
- More granular event tracking
- Cross-project observability

## 9. Metadata
- **Analyzed On**: 2025-12-10
- **Repository**: [claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)
- **Key Contributors**: Dan Disler (@disler)
- **Version Analyzed**: Latest GitHub HEAD

## 10. Conclusion

A sophisticated, real-time observability solution for Claude Code agents that provides unprecedented insight into multi-agent workflows, enabling developers to understand, debug, and optimize agentic coding environments.
