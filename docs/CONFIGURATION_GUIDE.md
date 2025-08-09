# GenPod AI Backend - Complete Configuration Guide

## Table of Contents
1. [Configuration Overview](#configuration-overview)
2. [Configuration Files](#configuration-files)
3. [Environment Variables](#environment-variables)
4. [Configuration Loading](#configuration-loading)
5. [Agent Configuration](#agent-configuration)
6. [MCP Configuration](#mcp-configuration)
7. [Database Configuration](#database-configuration)

## Configuration Overview

The GenPod AI Backend uses a hierarchical configuration system with multiple sources:
- Environment variables (`.env` file)
- YAML configuration files (`genpod.config.yml`, `a2a.config.yml`, `mcp.config.yml`)
- Command-line arguments (for specific scripts)
- Default values in code

## Configuration Files

### 1. **genpod.config.yml**
Main project configuration file defining LLM providers, agents, and default settings.

**Structure:**
```yaml
default:
  llm_config:
    provider: <provider_name>
    model: <model_name>
    config: {}
  max_retries: <number>
  retry_backoff: <seconds>
  max_graph_recursion_limit: <number>

providers:
  <provider_name>:
    setting:
      api_key: $ENV_VAR_NAME
      max_retries: <number>
      retry_backoff: <seconds>
    models:
      <model_name>:
        description: <description>
        api_key: $ENV_VAR_NAME  # Optional override

agents:
  <agent_alias>:
    description: <description>
    llm_config:  # Optional override
      provider: <provider>
      model: <model>

rag_agents:
  <rag_agent_name>:
    description: <description>
    rag_type: <langchain_vector|llama_index>
    vector_database_path: <path>
    collection_name: <name>
    recursion_limit: <number>
    llm_config: {}  # Optional
    config_path: <path>  # Required for llama_index
```

### 2. **a2a.config.yml**
A2A (Agent-to-Agent) protocol configuration for distributed agent communication.

**Structure:**
```yaml
server:
  host: <hostname>
  port: <port_number>
  timeout: <seconds>

agents:
  <agent_name>:
    endpoint: <url>
    timeout: <seconds>
    max_retries: <number>

protocol:
  version: <version>
  encoding: <encoding_type>
```

### 3. **mcp.config.yml**
MCP (Model Context Protocol) server configurations for external integrations.

**Structure:**
```yaml
schema_version: '1.0'

mcp:
  enabled: true
  connection_timeout: 30
  max_retries: 3
  
mcp_servers:
  locagent:
    enabled: true
    description: "LocAgent MCP server for codebase analysis"
    transport: "stdio"
    command: "locagent-mcp"
    args: ["--locagent-path", "<path>"]
  
  chroma:
    enabled: true
    description: "Chroma MCP server for vector database"
    transport: "stdio"
    command: "chroma-mcp"
    args: ["--host", "0.0.0.0", "--port", "8000"]
  
  taskmaster:
    enabled: true
    description: "Task-Master MCP server"
    transport: "stdio"
    command: "npx"
    args: ["-y", "--package=task-master-ai", "task-master-ai"]
```

### 4. **.env**
Environment variables for API keys and sensitive configuration.

**Environment Variables:**
```bash
# Configuration Paths
GENPOD_CONFIG=/home/$USER/.config/genpod/config.yml  # Path to agent configuration (created by install.sh)
MCP_CONFIG_PATH=/path/to/mcp.config.yml  # Optional, for MCP configuration override

# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
SEMGREP_APP_TOKEN=your_semgrep_token

# Logger Configuration
LOGGER_LEVEL=INFO  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOGGER_FORMAT=json  # Format: json or plain
LOGGER_DIR=/path/to/logs  # Directory for log files
LOGGER_CONSOLE_ENABLED=true  # Enable console logging
LOGGER_MAX_BYTES=1048576  # Max log file size before rotation (default: 25MB)
LOGGER_BACKUP_COUNT=5  # Number of backup files to keep
LOGGER_DEFAULT_FILE_NAME=application.log  # Default log filename
LOGGER_NAME=Genpod  # Logger name
LOGGER_CLEAN_ENABLED=true  # Enable automatic log directory cleanup
LOGGER_CLEAN_COUNT=2  # Number of log directories to keep
LOGGER_CONFIG_FILE=logger_config.yaml  # Path to logger YAML config (optional)

# Representation Configuration
AUTO_REPR_PRETTY=true  # Enable pretty formatting for auto_repr decorator
AUTO_REPR_UNWRAP_ENUMS=true  # Unwrap enum values in representations

# Phoenix Monitoring
PHOENIX_PROJECT_NAME=Genpod  # Project name for Phoenix monitoring

# GitHub Integration
GITHUB_TOKEN=your_github_token  # GitHub personal access token

# Functional Tester Agent
FUNCTIONAL_TESTER_PORT=8011  # Port for functional tester A2A server
```

## Environment Variables

### Core Configuration
- **GENPOD_CONFIG** (Required): Path to agent configuration file created by install.sh at `~/.config/genpod/config.yml`
- **MCP_CONFIG_PATH** (Optional): Override path for MCP configuration

### API Keys
- **OPENAI_API_KEY**: OpenAI API key for GPT models
- **ANTHROPIC_API_KEY**: Anthropic API key for Claude models
- **GOOGLE_API_KEY**: Google API key for Gemini models
- **SEMGREP_APP_TOKEN**: Semgrep token for code analysis

### Logger Configuration (Correct Names)
- **LOGGER_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **LOGGER_FORMAT**: Log format (json, plain)
- **LOGGER_DIR**: Directory for log files
- **LOGGER_CONSOLE_ENABLED**: Enable console logging (true/false)
- **LOGGER_MAX_BYTES**: Maximum log file size in bytes before rotation
- **LOGGER_BACKUP_COUNT**: Number of rotated backup files to retain
- **LOGGER_DEFAULT_FILE_NAME**: Default name for log file
- **LOGGER_NAME**: Name of the logger
- **LOGGER_CLEAN_ENABLED**: Enable automatic cleaning of old log directories
- **LOGGER_CLEAN_COUNT**: Maximum number of log directories to keep
- **LOGGER_CONFIG_FILE**: Path to YAML config file for logger (optional)

### Auto Representation Configuration
- **AUTO_REPR_PRETTY**: Enable pretty formatting for auto_repr decorator (true/false)
- **AUTO_REPR_UNWRAP_ENUMS**: Unwrap enum values in representations (true/false)

### External Services
- **PHOENIX_PROJECT_NAME**: Project name for Phoenix monitoring
- **GITHUB_TOKEN**: GitHub personal access token for GitHub operations
- **FUNCTIONAL_TESTER_PORT**: Port for functional tester A2A server (default: 8011)

## Important Notes on Environment Variables

### GENPOD_CONFIG
**GENPOD_CONFIG** is the primary configuration environment variable:
- Created by: `install.sh` during installation
- Default location: `~/.config/genpod/config.yml`
- Used by: `main.py` and all `scripts/run_*_a2a.py` files
- Purpose: Points to the agent configuration file that defines LLM models and agent settings

## Configuration Loading

### 1. **ProjectConfig Class** (`configs/project_config.py`)
Main configuration loader that:
- Reads genpod.config.yml
- Resolves environment variables (replaces $ENV_VAR with actual values)
- Validates configuration using Pydantic models
- Instantiates LLM instances for agents
- Manages RAG agent configurations

### 2. **ProjectEnvironment Class** (`configs/project_environment.py`) - OBSOLETE
**Note**: This class is no longer in use and remains in the codebase for historical reasons only.

### 3. **A2AConfigLoader Class** (`core/a2a/config.py`)
A2A protocol configuration loader that:
- Loads a2a.config.yml
- Manages agent endpoints
- Configures protocol settings
- Handles timeout and retry configurations

### 4. **MCPConfigManager Class** (`core/mcp/config_manager.py`)
MCP configuration manager (Singleton) that:
- Loads mcp.config.yml
- Validates server configurations
- Manages transport-specific settings
- Provides enabled server discovery

## Agent Configuration

### Standard Agents
Pre-configured agents with specific roles:
- **supervisor**: Project orchestration
- **architect**: Requirements and architecture
- **coder**: Code generation
- **planner**: Task planning
- **tests_generator**: Unit test generation
- **reviewer**: Code review
- **rag_middleware**: RAG agent coordination
- **research**: Online research

### RAG Agents
Dynamically configured agents for retrieval-augmented generation:
- **langchain_vector_rag**: LangChain-based RAG
- **llama_index_vector_rag**: LlamaIndex-based RAG
- Custom RAG agents defined in configuration

## MCP Configuration

### Transport Types
- **stdio**: Standard input/output communication
- **http**: HTTP-based communication
- **websocket**: WebSocket communication
- **sandbox**: E2B sandbox environment

### Server Types
- **locagent**: Codebase analysis and navigation
- **chroma**: Vector database operations
- **taskmaster**: Task management and PRD parsing

## Database Configuration

### SQLite Database
- **Location**: `output/database/genpod.db`
- **Purpose**: Stores project state, agent outputs, and conversation history
- **Configuration**: No additional configuration needed (embedded database)

### Vector Databases
- **ChromaDB**: For vector embeddings and semantic search
- **Configuration**: Specified in RAG agent settings
- **Collections**: Defined per RAG agent in genpod.config.yml

## Configuration Hierarchy

1. **Default Values**: Hardcoded in Python classes
2. **Configuration Files**: Override defaults
3. **Environment Variables**: Override configuration files
4. **Command-line Arguments**: Override everything (where applicable)

## Best Practices

1. **Security**:
   - Never commit .env files to version control
   - Use environment variables for all sensitive data
   - Rotate API keys regularly

2. **Organization**:
   - Keep configuration files in version control (without secrets)
   - Use meaningful names for agents and servers
   - Document custom configurations

3. **Validation**:
   - Always validate configuration on startup
   - Use Pydantic models for type safety
   - Implement fallback mechanisms for optional settings

4. **Performance**:
   - Set appropriate timeouts for agents
   - Configure retry settings based on network reliability
   - Adjust recursion limits based on task complexity

## Configuration Examples

### Minimal Configuration
```yaml
# genpod.config.yml
default:
  llm_config:
    provider: openai
    model: gpt-3.5-turbo
    config: {}
  max_retries: 3
  retry_backoff: 1

providers:
  openai:
    setting:
      api_key: $OPENAI_API_KEY

agents:
  supervisor:
    description: "Project supervisor"
```

### Advanced Configuration with RAG
```yaml
# genpod.config.yml
default:
  llm_config:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    config:
      temperature: 0.7
  max_retries: 5
  retry_backoff: 2
  max_graph_recursion_limit: 5000

providers:
  anthropic:
    setting:
      api_key: $ANTHROPIC_API_KEY
    models:
      claude-3-5-sonnet-20241022:
        description: "Claude 3.5 Sonnet"

rag_agents:
  custom_rag:
    description: "Custom knowledge base"
    rag_type: langchain_vector
    vector_database_path: /path/to/vector/db
    collection_name: knowledge_base
    recursion_limit: 3000
    llm_config:
      provider: openai
      model: gpt-4o-2024-11-20
```

## Complete Environment Variables Reference

### Configuration Variables

| Variable | Required | Default | Description | Used By |
|----------|----------|---------|-------------|---------|
| GENPOD_CONFIG | Yes | - | Path to genpod.config.yml | main.py, run scripts |
| GENPOD_CONFIG_PATH | Yes | - | Path to genpod.config.yml | ProjectEnvironment |
| MCP_CONFIG_PATH | No | mcp.config.yml | Path to MCP config | MCPConfigManager |

### API Keys

| Variable | Required | Default | Description | Used By |
|----------|----------|---------|-------------|---------|
| OPENAI_API_KEY | No | - | OpenAI API key | LLM providers |
| ANTHROPIC_API_KEY | No | - | Anthropic API key | LLM providers |
| GOOGLE_API_KEY | No | - | Google API key | LLM providers |
| SEMGREP_APP_TOKEN | No | - | Semgrep token | Code analysis tools |

### Logger Configuration

| Variable | Required | Default | Description | Used By |
|----------|----------|---------|-------------|---------|
| LOGGER_LEVEL | No | INFO | Log level | Logger |
| LOGGER_FORMAT | No | json | Log format (json/plain) | Logger |
| LOGGER_DIR | No | output/logs | Log directory | Logger |
| LOGGER_CONSOLE_ENABLED | No | false | Console logging | Logger |
| LOGGER_MAX_BYTES | No | 26214400 | Max log file size | Logger |
| LOGGER_BACKUP_COUNT | No | 5 | Backup files count | Logger |
| LOGGER_DEFAULT_FILE_NAME | No | application.log | Log filename | Logger |
| LOGGER_NAME | No | Genpod | Logger name | Logger |
| LOGGER_CLEAN_ENABLED | No | false | Auto cleanup | Logger |
| LOGGER_CLEAN_COUNT | No | 2 | Directories to keep | Logger |
| LOGGER_CONFIG_FILE | No | logger_config.yaml | YAML config path | Logger |

### Decorator Configuration

| Variable | Required | Default | Description | Used By |
|----------|----------|---------|-------------|---------|
| AUTO_REPR_PRETTY | No | false | Pretty formatting | auto_repr decorator |
| AUTO_REPR_UNWRAP_ENUMS | No | false | Unwrap enums | auto_repr decorator |

### External Services

| Variable | Required | Default | Description | Used By |
|----------|----------|---------|-------------|---------|
| PHOENIX_PROJECT_NAME | No | - | Phoenix project name | Monitoring |
| GITHUB_TOKEN | No | - | GitHub PAT | GitHub operations |
| FUNCTIONAL_TESTER_PORT | No | 8011 | A2A server port | Functional tester |

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**:
   - Error: `MandatoryValueNotFound`
   - Solution: Ensure all required variables are set in .env

2. **Invalid Configuration Path**:
   - Error: `InvalidPathError`
   - Solution: Check GENPOD_CONFIG_PATH points to valid file

3. **API Key Not Found**:
   - Warning: `No API key found for provider`
   - Solution: Set appropriate environment variable or add to config

4. **MCP Server Not Found**:
   - Error: `command not found`
   - Solution: Ensure MCP server binaries are installed and in PATH

5. **Vector Database Connection**:
   - Error: `vector_database_path does not exist`
   - Solution: Create directory or update path in configuration
