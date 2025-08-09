# GenPod AI Backend - Complete Setup and Usage Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Basic Usage](#basic-usage)
6. [Advanced Features](#advanced-features)
7. [Commands Reference](#commands-reference)
8. [Troubleshooting](#troubleshooting)

---

## Overview

GenPod is an AI-powered code generation platform that leverages multiple specialized agents (Supervisor, Architect, Planner, Coder, Tests Generator, Reviewer, and Research agents) to automatically generate complete applications from natural language descriptions. The system uses LangGraph for orchestration and supports multiple LLM providers (OpenAI, Anthropic, Google, Ollama).

### Key Features
- **Multi-Agent Architecture**: Specialized agents for different aspects of software development
- **RAG Support**: Vector database integration for context-aware generation
- **Multiple LLM Providers**: Supports OpenAI, Anthropic, Google Gemini, and Ollama
- **Real-time Progress Monitoring**: Track generation progress with detailed insights
- **Session Management**: Resume interrupted generations
- **Extensible Design**: Easy to add new agents and capabilities

---

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Python Version**: 3.12.x (mandatory)
- **Memory**: Minimum 8GB RAM recommended
- **Storage**: At least 10GB free space for models and generated code

### Required Dependencies
```bash
# Check Python version
python3 --version  # Must be 3.12.x

# Install pip if not present
sudo apt update
sudo apt install python3-pip python3-venv

# Install build essentials (for some Python packages)
sudo apt install build-essential
```

### API Keys Required
At least one of the following LLM provider API keys:
- **OpenAI API Key**: For GPT models
- **Anthropic API Key**: For Claude models
- **Google API Key**: For Gemini models
- **Ollama**: Local installation (no API key needed)

---

## Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd genpod-ai-backend-sup
```

### Step 2: Make Install Script Executable
```bash
chmod +x install.sh
```

### Step 3: Run the Installation Script
```bash
./install.sh
```

The installation script will:
1. **Clean Previous Installations**: Remove any existing GenPod installations
2. **Copy Source Files**: Install GenPod to `/usr/local/bin/genpod_src` (or `~/.local/bin/genpod_src` if no sudo)
3. **Create Virtual Environment**: Set up Python 3.12 virtual environment
4. **Install Dependencies**: Install all required Python packages
5. **Configure GenPod**: Create configuration file at `~/.config/genpod/config.yml`

### Step 4: Interactive Configuration

During installation, you'll be prompted for several paths:

#### 1. SQLite3 Database Path
- **Purpose**: Stores application metadata, logs, and generation history
- **Default**: `~/genpod/sqlite3.db`
- **Example Input**: Press Enter for default or provide custom path
```
Enter SQLite3 database path: [Press Enter for default]
```

#### 2. Code Output Directory Path
- **Purpose**: Directory where generated applications will be saved
- **Default**: `~/genpod/output`
- **Example Input**: 
```
Enter code output directory path: /home/user/projects/generated
```

#### 3. GenPod Configuration File Path
- **Purpose**: Main configuration file for LLM settings and agent configurations
- **Default**: `~/genpod/genpod_config.yml`
- **Example Input**: Press Enter for default
```
Enter Genpod configuration file path: [Press Enter for default]
```

#### 4. Vector Database Path (Currently Required but Unused)
- **Purpose**: Originally for RAG vector storage (marked for removal)
- **Current Status**: Must provide a path but it's not actively used
- **Example Input**: 
```
Enter vector database path: /tmp/vector_db
```
> **Note**: This requirement will be removed in future versions

### Step 5: Create GenPod Configuration File

After installation, create the main GenPod configuration file at the path specified during setup (default: `~/genpod/genpod_config.yml`):

```yaml
# ~/genpod/genpod_config.yml
schema_version: '1.0'

default:
  llm_config:
    provider: openai  # or anthropic, google, ollama
    model: gpt-4o-2024-11-20  # or your preferred model
    config:
      temperature: 0.3
      max_retries: 3
      streaming: true
  max_retries: 3
  retry_backoff: 3
  max_graph_recursion_limit: 1000

providers:
  openai:
    setting:
      api_key: $OPENAI_API_KEY  # Reference to environment variable
      max_retries: 3
      retry_backoff: 1
    models:
      gpt-4o-2024-11-20:
        description: "GPT-4 Optimized"
      gpt-3.5-turbo:
        description: "GPT-3.5 Turbo"
  
  anthropic:
    setting:
      api_key: $ANTHROPIC_API_KEY
    models:
      claude-3-5-sonnet-20241022:
        description: "Claude 3.5 Sonnet"
  
  google:
    setting:
      api_key: $GOOGLE_API_KEY
    models:
      gemini-2.0-flash:
        description: "Gemini 2.0 Flash"

agents:
  supervisor:
    description: "Oversees and coordinates task execution"
  architect:
    description: "Designs system architecture and requirements"
  planner:
    description: "Creates project timeline and task breakdown"
  coder:
    description: "Implements the actual code"
  tests_generator:
    description: "Creates unit and integration tests"
  reviewer:
    description: "Reviews code quality and suggests improvements"
  research:
    description: "Conducts online research for technical solutions"
  rag_middleware:
    description: "Manages RAG operations"

# Optional: RAG agents configuration
rag_agents: {}
```

### Step 6: Set Environment Variables

Create a `.env` file in your home directory or export these variables:

```bash
# ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GOOGLE_API_KEY="your-google-api-key"

# Optional: Logger configuration
export LOGGER_LEVEL="INFO"
export LOGGER_DIR="~/genpod/logs"
export LOGGER_CONSOLE_ENABLED="true"
```

### Step 7: Verify Installation
```bash
# Check if GenPod is installed correctly
genpod --version

# Expected output:
# Genpod CLI version v0.0.2
```

---

## Configuration

### Configuration File Location
The main configuration is stored at `~/.config/genpod/config.yml` and contains:

```yaml
# Path configuration created during installation
sqlite3_database_path: '/home/user/genpod/sqlite3.db'
code_output_directory: '/home/user/genpod/output'
genpod_configuration_file_path: '/home/user/genpod/genpod_config.yml'
vector_database_path: '/tmp/vector_db'  # Currently unused
```

### LLM Provider Configuration

#### OpenAI Configuration
```yaml
providers:
  openai:
    setting:
      api_key: $OPENAI_API_KEY
    models:
      gpt-4o-2024-11-20:
        description: "Latest GPT-4"
```

#### Anthropic Configuration
```yaml
providers:
  anthropic:
    setting:
      api_key: $ANTHROPIC_API_KEY
    models:
      claude-3-5-sonnet-20241022:
        description: "Claude 3.5 Sonnet"
```

#### Ollama Configuration (Local)
```yaml
providers:
  ollama:
    setting:
      base_url: "http://localhost:11434"
    models:
      llama3:
        description: "Llama 3 70B"
```

### Agent-Specific Overrides

You can override LLM settings for specific agents:

```yaml
agents:
  architect:
    llm_config:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
      config:
        temperature: 0.5
    description: "Uses Claude for architectural design"
  
  coder:
    llm_config:
      provider: openai
      model: gpt-4o-2024-11-20
      config:
        temperature: 0.2
    description: "Uses GPT-4 for code generation"
```

---

## Basic Usage

### Starting GenPod Interactive Mode

```bash
genpod
```

This will display:
```
 ██████╗ ███████╗███╗   ██╗██████╗  ██████╗ ██████╗ 
██╔════╝ ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗
██║  ███╗█████╗  ██╔██╗ ██║██████╔╝██║   ██║██║  ██║
██║   ██║██╔══╝  ██║╚██╗██║██╔═══╝ ██║   ██║██║  ██║
╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██████╔╝
 ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═════╝ 
                                             v0.0.2

Welcome to Genpod v0.0.2!
Type '.help' to see a list of available commands.

Enter your User ID to log in: 
```

### Step 1: Login
When prompted, enter any numeric user ID (this is a placeholder for future authentication):
```
Enter your User ID to log in: 12345
✅ Successfully logged in as User ID: 12345
```

### Step 2: Create a New Project
```
genpod> .add_project
Enter the project name (at least 3 characters): MyAwesomeApp
Enter the project description (at least 10 characters): A web application for task management with user authentication
Project 'MyAwesomeApp' (ID: 1) has been successfully created.
```

### Step 3: Generate Application
```
genpod> .generate 1
Enter 1 to provide input via file, or 2 to enter manually: 2
Enter your project idea (at least 10 characters): Create a REST API with FastAPI that includes user authentication, 
task CRUD operations, and SQLite database integration. Include proper error handling and input validation.

Application registered with the database.
Assigned Application ID: 1
You can locate this application under Project ID: 1.
Application generation will begin in approximately 5 seconds. Please wait...
```

### Step 4: Monitor Progress (In Another Terminal)
Open a new terminal and run:
```bash
genpod
genpod> .progress 1 1  # .progress <project_id> <application_id>
```

This will display real-time progress including:
- Project overview and completion percentage
- Agent activities and current status
- Tasks breakdown and completion
- Token usage and cost metrics
- File generation progress

---

## Advanced Features

### Resume an Interrupted Generation

If generation is interrupted, you can resume:
```
genpod> .resume
Available projects for User ID 12345:
1. MyAwesomeApp - A web application for task management
Select project ID: 1

Available applications:
1. Application ID: 1 - Status: IN_PROGRESS
Select application ID: 1

Resuming application generation...
```

### Provide Input via File

Instead of typing project requirements, you can provide them via file:
```
genpod> .generate 1
Enter 1 to provide input via file, or 2 to enter manually: 1
Enter the path to your input file: /path/to/requirements.txt
```

File format example (`requirements.txt`):
```
Create a comprehensive e-commerce platform with the following features:

1. User Management:
   - Registration and login with JWT authentication
   - User profiles and preferences
   - Role-based access control (admin, seller, buyer)

2. Product Catalog:
   - Product listings with categories
   - Search and filtering capabilities
   - Product reviews and ratings

3. Shopping Cart:
   - Add/remove items
   - Quantity management
   - Price calculations

4. Order Processing:
   - Checkout workflow
   - Payment integration (mock)
   - Order history

5. Technical Requirements:
   - FastAPI backend
   - SQLAlchemy ORM
   - PostgreSQL database
   - Comprehensive API documentation
   - Unit tests for all endpoints
```

### View Application Insights

The progress command shows detailed metrics:
```
genpod> .progress 1 1
```

Displays:
- **Project Overview**: Application name, status, completion percentage
- **Agent Activity**: Current agent working, recent actions
- **Tasks Status**: Planned vs completed tasks
- **Files Generated**: List of created files
- **Token Usage**: Consumption and estimated costs per model
- **Issues Tracker**: Any problems encountered

---

## Commands Reference

### Interactive Mode Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `.login` | Log in to GenPod (currently any numeric ID) | `.login` |
| `.logout` | Log out from current session | `.logout` |
| `.add_project` | Create a new project | `.add_project` |
| `.generate <project_id>` | Generate application for project | `.generate 1` |
| `.resume` | Resume interrupted generation | `.resume` |
| `.progress <project_id> <application_id>` | Monitor generation progress | `.progress 1 1` |
| `.clear` | Clear terminal screen | `.clear` |
| `.version` | Display GenPod version | `.version` |
| `.help` | Show help message | `.help` |
| `.quit` or `.exit` | Exit GenPod | `.quit` |

### Command Line Flags

| Flag | Description | Usage |
|------|-------------|-------|
| `--version` | Display version and exit | `genpod --version` |
| `--help` | Show help message and exit | `genpod --help` |

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Python Version Error
**Problem**: "Python 3.12.x required"
```bash
# Solution: Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

#### 2. Configuration File Not Found
**Problem**: "Configuration file not found at ~/.config/genpod/config.yml"
```bash
# Solution: Re-run installation
./install.sh
```

#### 3. API Key Not Set
**Problem**: "No API key found for provider"
```bash
# Solution: Set environment variables
export OPENAI_API_KEY="your-key"
# Add to ~/.bashrc for persistence
```

#### 4. Virtual Environment Not Found
**Problem**: "Virtual environment not found"
```bash
# Solution: Navigate to installation directory and recreate
cd /usr/local/bin/genpod_src
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 5. Database Connection Error
**Problem**: "Database initialization error"
```bash
# Solution: Check database path permissions
chmod 755 ~/genpod
# Or specify a different path during installation
```

#### 6. Generation Stuck or Slow
**Problem**: Application generation taking too long
- Check API rate limits for your LLM provider
- Monitor token usage with `.progress` command
- Consider using a faster model for initial iterations
- Check network connectivity

#### 7. No Output Generated
**Problem**: Generation completes but no files created
```bash
# Check output directory permissions
ls -la ~/genpod/output/
# Check logs for errors
tail -f ~/genpod/logs/application.log
```

### Log Files

GenPod creates detailed logs for debugging:
- **Location**: `~/genpod/logs/` (or path specified in LOGGER_DIR)
- **Main Log**: `application.log`
- **Log Level**: Set via `LOGGER_LEVEL` environment variable

View logs:
```bash
# Real-time log monitoring
tail -f ~/genpod/logs/application.log

# Search for errors
grep ERROR ~/genpod/logs/application.log

# View specific agent logs
grep "supervisor" ~/genpod/logs/application.log
```

### Getting Help

1. **Check Logs**: Most issues are logged with detailed error messages
2. **Verify Configuration**: Ensure all paths and API keys are correct
3. **Test API Keys**: Try a simple API call to verify credentials
4. **Community Support**: Check project issues on GitHub

---

## Best Practices

### 1. Project Descriptions
- Be specific and detailed in your requirements
- Include technical specifications (framework, database, etc.)
- Mention any specific features or constraints
- Break down complex requirements into sections

### 2. Resource Management
- Monitor token usage to control costs
- Use appropriate models for different tasks
- Set reasonable recursion limits
- Clean up old projects periodically

### 3. Configuration Optimization
```yaml
# Optimize for speed vs quality
default:
  llm_config:
    provider: openai
    model: gpt-3.5-turbo  # Faster, cheaper for prototyping
    config:
      temperature: 0.2  # Lower for more deterministic output
      max_retries: 2    # Reduce for faster failures
```

### 4. Development Workflow
1. Start with simple projects to test configuration
2. Use `.progress` to understand agent behaviors
3. Iterate on prompts based on output quality
4. Save successful prompts for reuse

---

## Appendix

### A. File Structure After Installation

```
~/
├── .config/
│   └── genpod/
│       └── config.yml          # Main configuration
├── genpod/
│   ├── sqlite3.db              # Database
│   ├── output/                 # Generated applications
│   │   └── YYYY-MM-DD_HH-MM-SS/
│   │       └── [generated files]
│   ├── logs/                   # Application logs
│   └── genpod_config.yml       # LLM configuration
└── .genpod_session             # Session file (temporary)

/usr/local/bin/ (or ~/.local/bin/)
├── genpod                      # CLI executable
└── genpod_src/                 # Source code
    ├── .venv/                  # Virtual environment
    ├── main.py                 # Entry point
    ├── agents/                 # Agent implementations
    ├── configs/                # Configuration modules
    └── ...
```

### B. Environment Variables Reference

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `GENPOD_CONFIG` | Path to config.yml | Set by genpod.sh | Yes |
| `OPENAI_API_KEY` | OpenAI API access | None | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API access | None | If using Anthropic |
| `GOOGLE_API_KEY` | Google API access | None | If using Google |
| `LOGGER_LEVEL` | Logging verbosity | INFO | No |
| `LOGGER_DIR` | Log file directory | output/logs | No |
| `LOGGER_CONSOLE_ENABLED` | Console output | false | No |

### C. Database Schema

GenPod uses SQLite with the following main tables:
- **projects**: Project metadata
- **applications**: Application generation records
- **application_sessions**: Agent session tracking
- **application_llm_metrics**: Token usage and costs
- **tasks**: Generated task tracking
- **planned_tasks**: Planned task records
- **issues**: Issue tracking

### D. Supported LLM Models

#### OpenAI
- gpt-4o-2024-11-20
- gpt-4o-2024-08-06
- gpt-3.5-turbo
- o1-preview-2024-09-12
- o1-mini-2024-09-12

#### Anthropic
- claude-3-5-sonnet-20241022
- claude-3-5-sonnet-20240620
- claude-instant-1.2

#### Google
- gemini-2.0-flash
- gemini-2.0-flash-lite
- gemini-2.5-pro-preview-05-06
- gemini-2.5-flash-preview-04-17

#### Ollama (Local)
- llama3
- mistral
- codellama
- [Any locally installed model]

---

## Conclusion

GenPod provides a powerful platform for AI-driven application generation. With proper configuration and understanding of the workflow, you can generate complete applications from natural language descriptions. The multi-agent architecture ensures comprehensive coverage of all aspects of software development, from architecture design to testing.

For updates and additional features, check the project repository and documentation regularly.