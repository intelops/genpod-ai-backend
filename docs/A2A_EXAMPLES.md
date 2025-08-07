# A2A Agent Examples and Troubleshooting Guide

This guide provides practical examples for running GenPod A2A agents with working payloads and common troubleshooting solutions.

## Configuration Setup

### Environment Configuration

The GenPod system requires a configuration file that will be installed to your user environment by the `install.sh` script:

**Location:** `~/.config/genpod/config.development.yml`

```yaml
# Genpod Configuration File
# This file contains key paths required by Genpod to function properly.

# SQLite3 Database Path
# Stores:
#   - Metadata (logs, generation records, indexes)
#   - Historical data like generation timestamps.
sqlite3_database_path: '/home/username/projects/genpod/output/database/genpod.db'

# Code Output Directory Path
# Stores all generated code files such as Python, JSON, and configurations.
code_output_directory: '/home/username/projects/genpod/output/projects'

# Genpod Configuration File Path
# Stores advanced settings for Genpod, including:
#   - Language model configurations
#   - Token usage limits and retry policies.
genpod_configuration_file_path: '/home/username/projects/genpod/genpod.config.yml'
```

**Important Notes:**
- This file will be created automatically by `install.sh` script
- The implementation of this configuration approach might need to be reconsidered for better portability
- All paths should be absolute paths on your system


### Main Configuration File

The `genpod.config.yml` file referenced above contains the core agent configurations:

```yaml
# -------------------------------------------------------------------
# Genpod configuration
# -------------------------------------------------------------------

schema_version: '1.0'

default:
  # Default LLM config used when agent‑specific overrides are absent
  llm_config:
    provider: openai
    model: gpt-4o-2024-11-20
    config:
      top_p: 0.4
      temperature: 0.3
      max_retries: 3
      streaming: true
  max_retries: 3               # Fallback retry count
  retry_backoff: 3             # Fallback backoff in seconds
  max_graph_recursion_limit: 1000

agents:
  architect:
    llm_config:
      provider: openai
      model: gpt-4o-2024-11-20
      config:
        top_p: 0.4
        temperature: 0.5
        max_retries: 3
    description: Designs the high-level system and architecture
  coder:
    description: Writes and optimizes code
  planner:
    description: Manages planning and task prioritization
  # ... other agents
```

### Setting the GENPOD_CONFIG Environment Variable

```bash
export GENPOD_CONFIG=~/.config/genpod/config.development.yml
```

## Starting A2A Servers

### Starting Individual Agents

Open separate terminal windows for each agent you want to run:

```bash
# Terminal 1 - Architect Agent (Port 8001)
python scripts/run_architect_a2a.py

# Terminal 2 - Coder Agent (Port 8002)
python scripts/run_coder_a2a.py

# Terminal 3 - Planner Agent (Port 8003)
python scripts/run_planner_a2a.py

# Terminal 4 - Reviewer Agent (Port 8004)
python scripts/run_reviewer_a2a.py
```

### Starting All Agents at Once

```bash
python scripts/run_all_a2a_servers.py
```

## Working Examples

### 1. Architect Agent Example

The Architect agent designs system architecture and generates requirements documents.

#### Save as `architect_request.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "message_id": "msg-arch-001",
      "role": "user",
      "context_id": "context-001",
      "parts": [
        {
          "text": "Create a REST API for a blog application with user authentication, posts, comments, and categories. Use Node.js with Express and MongoDB."
        },
        {
          "data": {
            "agent_input": {
              "user_prompt": "Create a REST API for a blog application with user authentication, posts, comments, and categories. Use Node.js with Express and MongoDB.",
              "project_status": "INITIAL",
              "project_directory": "/tmp/test_architect_project",
              "current_task": {
                "task_id": "arch-task-001",
                "task_status": "NEW",
                "description": "Design and architect the blog REST API application"
              },
              "chat_history": [],
              "additional_information": "This is a test project for demonstrating the Architect agent capabilities. Please include best practices for REST API design, proper error handling, and security considerations.",
              "requested_standards": "Follow RESTful conventions, use JWT for authentication, implement proper input validation and sanitization",
              "license_header": "// Copyright (c) 2024 Test Organization\n// Licensed under MIT License"
            }
          }
        }
      ]
    },
    "configuration": {
      "max_tokens": 4000,
      "temperature": 0.7
    }
  },
  "id": "req-001"
}
```

#### Run Command:
```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d @architect_request.json | python -m json.tool
```

### 2. Coder Agent Example

The Coder agent implements code based on requirements and architecture specifications.

#### Save as `coder_request.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "message_id": "msg-coder-001",
      "role": "user",
      "context_id": "coder-context-001",
      "parts": [
        {
          "text": "Implement the blog REST API based on the provided requirements and architecture."
        },
        {
          "data": {
            "agent_input": {
              "user_prompt": "Implement the blog REST API with user authentication, posts, comments, and categories using Node.js, Express, and MongoDB.",
              "project_status": "EXECUTING",
              "project_directory": "/tmp/test_coder_project",
              "current_task": {
                "task_id": "coder-task-001",
                "task_status": "NEW",
                "description": "Implement the blog REST API application"
              },
              "chat_history": [],
              "project_name": "blog-rest-api",
              "requirements_document": {
                "project_summary": "A comprehensive blog REST API supporting user authentication, blog posts, comments, and categories.",
                "tech_stack": "Node.js v18+, Express.js 4.x, MongoDB 6.0+, Mongoose ODM, JWT for authentication, bcrypt for password hashing, Jest for testing",
                "system_architecture": "RESTful API with MVC pattern, JWT-based authentication, MongoDB for data persistence",
                "file_structure": "src/\n├── controllers/\n├── models/\n├── routes/\n├── middleware/\n├── utils/\n└── config/",
                "microservice_design": "Monolithic REST API with modular structure",
                "tasks_summary": "1. Setup Express server\n2. Configure MongoDB connection\n3. Implement authentication\n4. Create CRUD operations for posts, comments, categories",
                "code_standards": "ESLint configuration, Prettier formatting, JSDoc comments for all functions",
                "implementation_plan": "Phase 1: Setup and authentication\nPhase 2: Core features\nPhase 3: Testing and documentation",
                "license_terms": "MIT License"
              },
              "license_url": "https://opensource.org/licenses/MIT",
              "license_header": "// Copyright (c) 2024 Test Organization\n// Licensed under MIT License",
              "functions_skeleton": {
                "auth": {
                  "register": "async (req, res) => { /* Register new user */ }",
                  "login": "async (req, res) => { /* Authenticate user */ }",
                  "logout": "async (req, res) => { /* Logout user */ }"
                },
                "posts": {
                  "create": "async (req, res) => { /* Create new post */ }",
                  "getAll": "async (req, res) => { /* Get all posts */ }",
                  "getById": "async (req, res) => { /* Get post by ID */ }",
                  "update": "async (req, res) => { /* Update post */ }",
                  "delete": "async (req, res) => { /* Delete post */ }"
                }
              },
              "test_code": {
                "auth": "describe('Authentication', () => { /* Test auth endpoints */ })",
                "posts": "describe('Posts API', () => { /* Test posts endpoints */ })"
              },
              "current_planned_task": {
                "task_id": "task-001",
                "description": "Implement authentication module",
                "status": "INPROGRESS",
                "is_function_generation_required": false
              },
              "current_planned_issue": {
                "issue_id": "issue-001",
                "description": "No issues currently",
                "status": "NONE",
                "is_function_generation_required": false
              },
              "current_issue": {
                "issue_id": "issue-001",
                "description": "No issues",
                "severity": "NONE"
              }
            }
          }
        }
      ]
    },
    "configuration": {
      "max_tokens": 4000,
      "temperature": 0.7
    }
  },
  "id": "req-coder-001"
}
```

#### Run Command:
```bash
curl -X POST http://localhost:8002/ \
  -H "Content-Type: application/json" \
  -d @coder_request.json | python -m json.tool
```

### 3. Planner Agent Example

The Planner agent creates detailed task plans and work packages.

#### Save as `planner_request.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "message_id": "msg-planner-001",
      "role": "user",
      "context_id": "planner-context-001",
      "parts": [
        {
          "text": "Plan the tasks and work packages for the blog REST API project based on requirements."
        },
        {
          "data": {
            "agent_input": {
              "user_prompt": "Create a detailed plan with tasks and work packages for implementing a blog REST API with user authentication, posts, comments, and categories using Node.js, Express, and MongoDB.",
              "project_status": "PLANNING",
              "project_directory": "/tmp/test_planner_project",
              "current_task": {
                "task_id": "planner-task-001",
                "task_status": "INPROGRESS",
                "description": "Create project plan and work packages"
              },
              "chat_history": [],
              "deliverable_list": {
                "next": 0,
                "items": [
                  {
                    "task_id": "TASK-001",
                    "task_name": "Setup Project Infrastructure",
                    "task_description": "Initialize Node.js project, configure Express server, and set up MongoDB connection",
                    "task_status": "NEW",
                    "deliverable": "Basic project structure with configured server and database"
                  },
                  {
                    "task_id": "TASK-002",
                    "task_name": "Implement Authentication System",
                    "task_description": "Create user registration, login, logout with JWT tokens",
                    "task_status": "NEW",
                    "deliverable": "Complete authentication system with JWT"
                  },
                  {
                    "task_id": "TASK-003",
                    "task_name": "Develop Blog Post APIs",
                    "task_description": "Create CRUD operations for blog posts",
                    "task_status": "NEW",
                    "deliverable": "RESTful endpoints for blog post management"
                  },
                  {
                    "task_id": "TASK-004",
                    "task_name": "Implement Comments System",
                    "task_description": "Add commenting functionality to blog posts",
                    "task_status": "NEW",
                    "deliverable": "Comment system with nested replies support"
                  },
                  {
                    "task_id": "TASK-005",
                    "task_name": "Create Categories Management",
                    "task_description": "Implement category system for organizing posts",
                    "task_status": "NEW",
                    "deliverable": "Category management with post categorization"
                  }
                ]
              },
              "issue_list": {
                "next": 0,
                "items": []
              },
              "requirements_document": {
                "project_summary": "A comprehensive blog REST API supporting user authentication, blog posts, comments, and categories.",
                "tech_stack": "Node.js v18+, Express.js 4.x, MongoDB 6.0+, Mongoose ODM, JWT for authentication, bcrypt for password hashing, Jest for testing",
                "system_architecture": "RESTful API with MVC pattern, JWT-based authentication, MongoDB for data persistence",
                "file_structure": "src/\n├── controllers/\n├── models/\n├── routes/\n├── middleware/\n├── utils/\n├── config/\n└── tests/",
                "microservice_design": "Monolithic REST API with modular structure for potential future microservices migration",
                "tasks_summary": "1. Project setup and configuration\n2. Database schema design\n3. Authentication implementation\n4. Blog post CRUD operations\n5. Comments system\n6. Categories management\n7. API documentation\n8. Testing suite",
                "code_standards": "ESLint configuration, Prettier formatting, JSDoc comments for all functions, RESTful naming conventions",
                "implementation_plan": "Phase 1: Infrastructure setup (1 week)\nPhase 2: Core authentication (1 week)\nPhase 3: Blog functionality (2 weeks)\nPhase 4: Comments and categories (1 week)\nPhase 5: Testing and documentation (1 week)",
                "license_terms": "MIT License"
              },
              "human_feedback": "Please ensure each task has clear acceptance criteria and estimated effort. Include security considerations for authentication and data validation.",
              "additional_information": "The project should follow REST best practices, include proper error handling, input validation, and rate limiting. Consider scalability for handling high traffic.",
              "current_issue": {
                "issue_id": "ISSUE-000",
                "issue_description": "No current issues",
                "issue_severity": "NONE",
                "issue_status": "NEW"
              }
            }
          }
        }
      ]
    },
    "configuration": {
      "max_tokens": 4000,
      "temperature": 0.7
    }
  },
  "id": "req-planner-001"
}
```

#### Run Command:
```bash
curl -X POST http://localhost:8003/ \
  -H "Content-Type: application/json" \
  -d @planner_request.json | python -m json.tool
```

### 4. Reviewer Agent Example

The Reviewer agent analyzes code for quality, security issues, and compliance.

#### Save as `reviewer_request.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "message_id": "msg-reviewer-001",
      "role": "user",
      "context_id": "reviewer-context-001",
      "parts": [
        {
          "text": "Review the blog REST API project for code quality, security issues, and adherence to requirements."
        },
        {
          "data": {
            "agent_input": {
              "user_prompt": "Review the blog REST API implementation for code quality, security vulnerabilities, performance issues, and compliance with requirements.",
              "project_status": "REVIEWING",
              "project_directory": "/tmp/test_reviewer_project",
              "current_task": {
                "task_id": "reviewer-task-001",
                "task_status": "INPROGRESS",
                "description": "Review project code and generate issues report"
              },
              "chat_history": [],
              "project_name": "blog-rest-api",
              "license_header": "// Copyright (c) 2024 Test Organization\n// Licensed under MIT License",
              "requirements_document": {
                "project_summary": "A comprehensive blog REST API supporting user authentication, blog posts, comments, and categories.",
                "tech_stack": "Node.js v18+, Express.js 4.x, MongoDB 6.0+, Mongoose ODM, JWT for authentication, bcrypt for password hashing, Jest for testing",
                "system_architecture": "RESTful API with MVC pattern, JWT-based authentication, MongoDB for data persistence",
                "file_structure": "src/\n├── controllers/\n│   ├── authController.js\n│   ├── postController.js\n│   ├── commentController.js\n│   └── categoryController.js\n├── models/\n│   ├── User.js\n│   ├── Post.js\n│   ├── Comment.js\n│   └── Category.js\n├── routes/\n│   ├── authRoutes.js\n│   ├── postRoutes.js\n│   ├── commentRoutes.js\n│   └── categoryRoutes.js\n├── middleware/\n│   ├── authMiddleware.js\n│   ├── errorHandler.js\n│   └── validation.js\n├── utils/\n│   ├── jwtUtils.js\n│   └── dbConnection.js\n├── config/\n│   └── config.js\n└── tests/\n    ├── auth.test.js\n    ├── posts.test.js\n    └── integration.test.js",
                "microservice_design": "Monolithic REST API with modular structure",
                "tasks_summary": "All core tasks completed: authentication, posts CRUD, comments, categories",
                "code_standards": "ESLint configuration, Prettier formatting, JSDoc comments for all functions, RESTful naming conventions, comprehensive error handling",
                "implementation_plan": "Phase 1: Infrastructure setup - COMPLETED\nPhase 2: Core authentication - COMPLETED\nPhase 3: Blog functionality - COMPLETED\nPhase 4: Comments and categories - COMPLETED\nPhase 5: Testing and documentation - IN PROGRESS",
                "license_terms": "MIT License"
              },
              "previous_issues": {
                "next": 0,
                "items": [
                  {
                    "issue_id": "PREV-001",
                    "issue_description": "Missing input validation on user registration endpoint",
                    "issue_severity": "HIGH",
                    "issue_status": "NEW",
                    "issue_type": "SECURITY",
                    "affected_files": ["src/controllers/authController.js"],
                    "recommended_fix": "Add validation middleware for email format and password strength"
                  },
                  {
                    "issue_id": "PREV-002",
                    "issue_description": "No rate limiting implemented on API endpoints",
                    "issue_severity": "MEDIUM",
                    "issue_status": "NEW",
                    "issue_type": "SECURITY",
                    "affected_files": ["src/middleware/"],
                    "recommended_fix": "Implement express-rate-limit middleware"
                  }
                ]
              }
            }
          }
        }
      ]
    },
    "configuration": {
      "max_tokens": 4000,
      "temperature": 0.7
    }
  },
  "id": "req-reviewer-001"
}
```

#### Run Command:
```bash
curl -X POST http://localhost:8004/ \
  -H "Content-Type: application/json" \
  -d @reviewer_request.json | python -m json.tool
```

## Quick Test with Single File

### What Goes Into test_request.json

**Note:** The `test_request.json` file is simply a convenience file for holding your test payloads when using curl commands. It's not a standard or requirement - just a placeholder to avoid typing long JSON payloads directly in the terminal.

When creating your test payload, it needs to follow the A2A protocol format:

1. **JSON-RPC wrapper** (standard protocol):
   - `jsonrpc`: "2.0"
   - `method`: "message/send" 
   - `id`: Any identifier for the request

2. **A2A message format** (what the agents expect):
   - `message_id`: Unique identifier for this message
   - `role`: "user" for incoming requests
   - `context_id`: Session identifier
   - `parts`: Array with text description and agent_input data

3. **Agent-specific data** (varies per agent):
   - Each agent needs different fields in `agent_input`
   - See the examples above for each agent's requirements
   - Common fields: `user_prompt`, `project_status`, `project_directory`, `current_task`

**Example Structure:**
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "message_id": "msg-001",
      "role": "user",
      "context_id": "ctx-001",
      "parts": [
        {"text": "Human-readable request"},
        {"data": {"agent_input": {/* Agent-specific fields */}}}
      ]
    }
  },
  "id": "req-001"
}
```

**Important**: You must update the `agent_input` fields for each agent type. Simply reusing the same payload across different agents will fail due to missing required fields. The `test_request.json` file is just a convenience - you can also pass JSON directly to curl or save different files for each agent.

### Testing Workflow

1. Choose your approach:
   - Option A: Create one `test_request.json` and update it for each agent
   - Option B: Create separate files (`architect_request.json`, `coder_request.json`, etc.)
   - Option C: Pass JSON directly in curl command
2. Start the target agent server
3. Send the request using curl
4. If using Option A, update the payload for the next agent

```bash
# Test Architect (update test_request.json with architect payload)
curl -X POST http://localhost:8001/ -H "Content-Type: application/json" -d @test_request.json | python -m json.tool

# Test Coder (update test_request.json with coder payload)
curl -X POST http://localhost:8002/ -H "Content-Type: application/json" -d @test_request.json | python -m json.tool

# Test Planner (update test_request.json with planner payload)
curl -X POST http://localhost:8003/ -H "Content-Type: application/json" -d @test_request.json | python -m json.tool

# Test Reviewer (update test_request.json with reviewer payload)
curl -X POST http://localhost:8004/ -H "Content-Type: application/json" -d @test_request.json | python -m json.tool
```

## Troubleshooting

### Common Errors and Solutions

#### 1. DatabaseTaskStore Error
**Error:**
```
'str' object has no attribute 'begin'
```

**Cause:** The A2A server is passing a string URL instead of an AsyncEngine object to DatabaseTaskStore.

**Solution:** 
- Ensure the A2A server creates an AsyncEngine:
```python
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
task_store = DatabaseTaskStore(engine)
```

#### 2. Thread ID and GenpodContext Issues

**Error 1: Thread ID Not Initialized**
```
Graph thread_id has not been initialized. Ensure that set_thread_id() is called with a valid thread ID before invoking agents invoke.
```

**Error 2: GenpodContext Singleton Issues**
```
AttributeError: 'NoneType' object has no attribute 'get_config'
OR
GenpodContext singleton not initialized
OR
Cannot access project_directory from GenpodContext
```

**Root Cause - Tight Coupling with Monolithic Architecture:**

The GenPod agents were originally designed as part of a monolithic application where:
- Thread IDs were managed globally by the main application
- `GenpodContext` was a singleton initialized once at application startup via `apis/main.py`
- The singleton held global application state like:
  - Project directory paths
  - Configuration settings
  - Database connections
  - LLM configurations
- Agents accessed this singleton directly: `GenpodContext.get_instance().project_directory`

When wrapped with A2A protocol for microservice deployment, this tight coupling causes issues because:
- Each A2A server runs independently without the monolithic `apis/main.py` initialization
- The GenpodContext singleton is never initialized in the A2A server startup
- Agents crash when trying to access the uninitialized singleton
- The context was meant to be shared across the entire application, not per-request

**Why This Wasn't Handled Initially:**

The initial A2A implementation focused on protocol translation but didn't account for the monolithic dependencies:
- Run scripts (`run_*_a2a.py`) initially had hardcoded `set_thread_id()` calls
- This was a temporary workaround that didn't scale
- The proper solution requires handling these dependencies in the A2A executor

**Current Implementation in A2A Executors:**

The A2A executors currently handle initialization like this:

```python
# Example from actual A2A executor implementations
class ArchitectA2AExecutor(BaseA2AExecutor):
    async def _execute_agent(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        # The agent is invoked directly without thread_id initialization
        # This works because the A2A SDK handles task management separately
        return await self.agent.invoke(agent_input)
```

**What was actually fixed:**
- Removed hardcoded `set_thread_id()` calls from run scripts
- Let the A2A SDK handle task persistence through DatabaseTaskStore
- Fixed DatabaseTaskStore to use AsyncEngine instead of string URLs

**Workaround for GenpodContext (if needed):**

If agents still require GenpodContext singleton, initialize it in the A2A server startup:

```python
# In run_*_a2a.py scripts (temporary workaround)
from core.context import GenpodContext

async def main():
    # Initialize GenpodContext once at startup
    context = GenpodContext.get_instance()
    context.initialize(
        config_path=os.getenv('GENPOD_CONFIG'),
        project_directory='/tmp/default_project'  # Default until overridden
    )
    
    # Start A2A server
    executor = AgentA2AExecutor()
    await executor.run()
```

**Proper Solution Architecture:**

1. **Remove Singleton Dependencies**: Refactor agents to not depend on GenpodContext singleton
2. **Pass Data Explicitly**: All required data should come through agent_input
3. **A2A Executor Handles State**: Let the A2A SDK manage task state through DatabaseTaskStore
4. **Stateless Agents**: Each request should be self-contained with all needed data

**Suggestions for Better Architecture:**

1. **Eliminate GenpodContext Singleton**:
   - Refactor agents to receive all data through parameters
   - Remove `GenpodContext.get_instance()` calls from agent code
   - Pass project paths, configs, etc. in agent_input

2. **Example Refactoring**:
   ```python
   # OLD (relies on singleton)
   class CoderAgent:
       def generate_code(self):
           context = GenpodContext.get_instance()
           output_dir = context.project_directory
           config = context.llm_config
           # ... use singleton data
   
   # NEW (explicit parameters)
   class CoderAgent:
       def generate_code(self, agent_input):
           output_dir = agent_input['project_directory']
           config = agent_input.get('llm_config', self.default_config)
           # ... use passed data
   ```

3. **Configuration Strategy**:
   - Load config once in A2A executor
   - Pass relevant config in agent_input
   - Don't rely on global config files

4. **State Management**:
   - Use A2A's DatabaseTaskStore for persistence
   - Keep agents stateless between requests
   - Each request carries its complete context

#### 3. Missing EXIT Node
**Error:**
```
KeyError: 'exit'
```

**Cause:** The agent's graph is trying to route to an 'exit' node that doesn't exist in the conditional edges.

**Solution:**
- Ensure the graph includes EXIT in conditional edges from ENTRY node:
```python
add_conditional_edges(
    str(NodeEnum.ENTRY),
    router_function,
    {
        # ... other routes
        str(NodeEnum.EXIT): str(NodeEnum.EXIT)
    }
)
```

#### 4. Environment Variable Not Set
**Error:**
```
The environment variable 'GENPOD_CONFIG' is not set.
```

**Solution:**
```bash
export GENPOD_CONFIG=/path/to/your/setup.yml
```

#### 5. Port Already in Use
**Error:**
```
[Errno 48] Address already in use
```

**Solution:**
```bash
# Find and kill the process using the port
lsof -i :8001  # Replace with the port number
kill -9 <PID>  # Replace with the process ID
```

## Testing Response

A successful response should look like:
```json
{
  "id": "req-001",
  "jsonrpc": "2.0",
  "result": {
    "contextId": "context-001",
    "history": [...],
    "id": "task-uuid",
    "kind": "task",
    "status": {
      "state": "completed",
      "timestamp": "2025-08-07T18:00:00.000000+00:00"
    }
  }
}
```

## Tips for Testing

1. **Start Small:** Test with the Architect agent first as it has the simplest requirements
2. **Check Logs:** Agent logs provide detailed information about what's happening
3. **Validate JSON:** Use a JSON validator before sending requests
4. **Monitor Resources:** Some agents may require significant memory/CPU for LLM operations
5. **Use Mock LLMs:** For testing, configure agents to use mock LLMs to avoid API costs

## Agent Port Reference

| Agent | Port | Status Endpoint |
|-------|------|-----------------|
| Architect | 8001 | http://localhost:8001/health |
| Coder | 8002 | http://localhost:8002/health |
| Planner | 8003 | http://localhost:8003/health |
| Reviewer | 8004 | http://localhost:8004/health |
| Supervisor | 8005 | http://localhost:8005/health |
| Tests Generator | 8006 | http://localhost:8006/health |
| Research | 8007 | http://localhost:8007/health |
| LangChain Vector RAG | 8008 | http://localhost:8008/health |
| Llama Index Vector RAG | 8009 | http://localhost:8009/health |
| RAG Middleware | 8010 | http://localhost:8010/health |

## Next Steps

1. Customize the payloads for your specific use case
2. Chain agents together for complex workflows
3. Integrate with your CI/CD pipeline
4. Monitor agent performance and optimize configurations

For more information, see the main [A2A README](./A2A_README.md).