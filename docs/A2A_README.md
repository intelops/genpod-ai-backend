# A2A Protocol Integration for GenPod Agents

This directory contains A2A (Agent-to-Agent) protocol wrappers for GenPod agents, enabling them to communicate via standardized JSON-RPC protocol.

## Architecture

### Base Infrastructure (`core/a2a/`)
- **BaseA2AExecutor**: Template method pattern for consistent agent wrapping
- **A2AConfigLoader**: Configuration management with validation
- **MessageExtractor/ResponseFormatter**: Reusable utilities for protocol translation
- **TaskManager**: Simplified task lifecycle management
- **BaseAgentCardBuilder**: Standardized agent card creation

### Agent Wrappers
Each agent has an `{agent_name}_a2a_server.py` file that:
1. Extends `BaseA2AExecutor` with agent-specific implementation
2. Implements input extraction and output formatting
3. Uses configuration from `a2a.config.yml`
4. Integrates with SQLite database using AsyncEngine
5. Provides agent capabilities via standardized agent cards

## Configuration

All A2A settings are in `a2a.config.yml` at the project root:
```yaml
agents:
  architect:
    enabled: true
    host: "0.0.0.0"
    port: 8001
    description: "Architecture design agent"
    timeout:
      blocking: 600  # 10 minutes
  coder:
    enabled: true
    host: "0.0.0.0"
    port: 8002
    description: "Code implementation agent"
  planner:
    enabled: true
    host: "0.0.0.0"
    port: 8003
    description: "Task planning and work package creation"
  # ... other agents
```

### Starting Individual Agents
```bash
# Architect Agent
python scripts/run_architect_a2a.py

# Coder Agent
python scripts/run_coder_a2a.py

# Planner Agent
python scripts/run_planner_a2a.py

# Reviewer Agent
python scripts/run_reviewer_a2a.py

# Supervisor Agent
python scripts/run_supervisor_a2a.py

# Research Agent
python scripts/run_research_a2a.py

# Tests Generator Agent
python scripts/run_tests_generator_a2a.py

# RAG Agents
python scripts/run_langchain_vector_rag_a2a.py
python scripts/run_llama_index_vector_rag_a2a.py
python scripts/run_rag_middleware_a2a.py
```

### Starting All Agents
```bash
python scripts/run_all_a2a_servers.py
```

## Testing

### Unit Tests
Each agent has comprehensive tests in `{agent_name}/tests/`:
```bash
# Run individual agent tests
pytest agents/architect/tests/test_architect_a2a_server.py -v
pytest agents/coder/tests/test_coder_a2a_server.py -v
pytest agents/planner/tests/test_planner_a2a_server.py -v

# Run all A2A tests
pytest agents/*/tests/test_*_a2a_server.py -v
```

### Integration Testing

#### Example: Testing Architect Agent
```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "message_id": "msg-001",
        "role": "user",
        "context_id": "ctx-001",
        "parts": [{
          "text": "Design a REST API"
        }, {
          "data": {
            "agent_input": {
              "user_prompt": "Design a REST API for blog",
              "project_status": "NEW",
              "project_directory": "/tmp/test",
              "current_task": {
                "task_id": "task-001",
                "task_status": "NEW",
                "description": "Design API"
              },
              "chat_history": [],
              "additional_information": "",
              "requested_standards": "",
              "license_header": ""
            }
          }
        }]
      }
    },
    "id": "req-001"
  }'
```

#### Python Integration Test
```python
import httpx
import asyncio

async def test_architect():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/",
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "message_id": "test-001",
                        "role": "user",
                        "context_id": "context-001",
                        "parts": [{
                            "text": "Design a REST API"
                        }, {
                            "data": {
                                "agent_input": {
                                    "user_prompt": "Design a REST API",
                                    "project_status": "NEW",
                                    "project_directory": "/tmp/test",
                                    "current_task": {
                                        "task_id": "task-001",
                                        "task_status": "NEW",
                                        "description": "Design API"
                                    },
                                    "chat_history": [],
                                    "additional_information": "",
                                    "requested_standards": "",
                                    "license_header": ""
                                }
                            }
                        }]
                    },
                    "configuration": {"blocking": True}
                },
                "id": 1
            }
        )
        print(response.json())

asyncio.run(test_architect())
```

## Common Issues and Solutions

### 1. DatabaseTaskStore Error
**Error**: `'str' object has no attribute 'begin'`
**Solution**: Ensure all A2A servers use `create_async_engine` instead of passing string URLs to DatabaseTaskStore

### 2. Thread ID Error
**Error**: `Graph thread_id has not been initialized`
**Solution**: Thread ID is managed by the A2A executor using task_id. Do not set it manually in run scripts.

## Design Principles

1. **SOLID Principles**: 
   - Single Responsibility: Each class has one clear purpose
   - Open/Closed: Base classes are extended, not modified
   - Liskov Substitution: All agents work through BaseA2AExecutor interface
   - Interface Segregation: Agents only implement required methods
   - Dependency Inversion: Depend on abstractions (base classes)

2. **DRY (Don't Repeat Yourself)**: 
   - Shared functionality in base classes
   - Reusable utilities for common operations
   - Configuration-driven to avoid duplication

3. **Configuration-Driven**: 
   - No hardcoded values
   - All settings in configuration files
   - Environment-based configuration loading

4. **Testable**: 
   - Comprehensive test coverage with mocks
   - Unit tests for individual components
   - Integration tests for end-to-end flows

5. **Maintainable**: 
   - Clear separation of concerns
   - Consistent patterns across all agents
   - Well-documented interfaces

## Agent Status

| Agent | Status | Port | Description |
|-------|--------|------|-------------|
| Architect | ✅ Complete | 8001 | Architecture design and requirements generation |
| Coder | ✅ Complete | 8002 | Code implementation and generation |
| Planner | ✅ Complete | 8003 | Task planning and work package creation |
| Reviewer | ✅ Complete | 8004 | Code review and issue detection |
| Supervisor | ✅ Complete | 8005 | Multi-agent orchestration and coordination |
| Tests Generator | ✅ Complete | 8006 | Test suite generation |
| Research | ✅ Complete | 8007 | Documentation and research tasks |
| LangChain Vector RAG | ✅ Complete | 8008 | LangChain-based vector retrieval |
| Llama Index Vector RAG | ✅ Complete | 8009 | Llama Index-based vector retrieval |
| RAG Middleware | ✅ Complete | 8010 | RAG coordination and routing |

## API Endpoints

All agents expose the following endpoints:

- `POST /` - Main JSON-RPC endpoint for agent communication
- `GET /health` - Health check endpoint
- `GET /agent` - Agent card with capabilities (if configured)

## Project Structure

```
agents/
├── {agent_name}/
│   ├── _internal/
│   │   ├── {agent}_graph.py         # LangGraph definition
│   │   ├── {agent}_state.py         # State models
│   │   ├── {agent}_work_flow.py     # Workflow logic
│   │   └── {agent}_node_enum.py     # Node definitions
│   ├── {agent}_agent.py             # Core agent implementation
│   ├── {agent}_a2a_server.py        # A2A wrapper
│   └── tests/
│       └── test_{agent}_a2a_server.py

core/a2a/
├── base/
│   ├── executor.py                  # BaseA2AExecutor
│   └── agent_card.py               # Agent card builder
├── config/
│   ├── loader.py                    # Configuration loading
│   └── models.py                    # Config models
├── utils/
│   ├── extractors.py                # Message extraction
│   └── formatters.py                # Response formatting
└── task/
    └── manager.py                   # Task management

scripts/
├── run_{agent}_a2a.py               # Individual agent runners
└── run_all_a2a_servers.py          # Run all agents
```

## Contributing

When adding a new agent to the A2A protocol:

1. Create `{agent}_a2a_server.py` extending `BaseA2AExecutor`
2. Implement required abstract methods:
   - `_extract_input()` - Extract and validate input
   - `_execute_agent()` - Run the agent logic
   - `_format_response()` - Format output for A2A

3. Create agent card builder extending `BaseAgentCardBuilder`
4. Add configuration to `a2a.config.yml`
5. Create run script in `scripts/`
6. Add comprehensive tests
7. Update this documentation

## License

See LICENSE file in the project root.