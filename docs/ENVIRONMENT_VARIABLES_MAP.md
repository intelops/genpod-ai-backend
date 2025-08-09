# Complete Environment Variables Map - GenPod AI Backend

## Overview
This document provides a comprehensive map of ALL environment variables used in the GenPod AI Backend project, including their exact file locations, line numbers, and purposes.

---

## 1. GENPOD_CONFIG
**Purpose**: Path to the main GenPod configuration file (genpod.config.yml)  
**Type**: Required  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `main.py` | 48 | `os.getenv("GENPOD_CONFIG")` | Main application entry point, loads configuration |
| `main.py` | 50 | Error message | Critical error if not set |
| `scripts/run_supervisor_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for supervisor |
| `scripts/run_architect_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for architect |
| `scripts/run_planner_a2a.py` | 27 | `os.getenv("GENPOD_CONFIG")` | Load configuration for planner |
| `scripts/run_coder_a2a.py` | 27 | `os.getenv("GENPOD_CONFIG")` | Load configuration for coder |
| `scripts/run_reviewer_a2a.py` | 27 | `os.getenv("GENPOD_CONFIG")` | Load configuration for reviewer |
| `scripts/run_tests_generator_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for tests generator |
| `scripts/run_research_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for research |
| `scripts/run_rag_middleware_a2a.py` | 31 | `os.getenv("GENPOD_CONFIG")` | Load configuration for RAG middleware |
| `scripts/run_langchain_vector_rag_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for LangChain RAG |
| `scripts/run_llama_index_vector_rag_a2a.py` | 30 | `os.getenv("GENPOD_CONFIG")` | Load configuration for LlamaIndex RAG |
| `scripts/run_all_a2a_servers.py` | 131 | `os.getenv("GENPOD_CONFIG")` | Check before starting all servers |
| `.env` | 22 | Definition | Development environment value |

---

## 2. GENPOD_CONFIG_PATH (OBSOLETE)
**Purpose**: Was used by ProjectEnvironment class (no longer active)  
**Type**: OBSOLETE - DO NOT USE  
**Status**: This variable and the ProjectEnvironment class are no longer in use

### File Locations (for reference only):

| File | Line | Usage | Context |
|------|------|-------|---------|
| `configs/project_environment.py` | 29-32 | Field definition | OBSOLETE - Not used |
| `configs/project_environment.py` | 44-68 | Validator | OBSOLETE - Not used |
| `configs/project_environment.py` | 89 | `os.getenv(var)` | OBSOLETE - Not used |

---

## 3. MCP_CONFIG_PATH
**Purpose**: Path to MCP (Model Context Protocol) configuration file  
**Type**: Optional  
**Default**: `mcp.config.yml` in project root

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `core/mcp/config_manager.py` | 81 | `os.getenv('MCP_CONFIG_PATH')` | Override default config path |
| `core/mcp/config_manager.py` | 82-86 | Path validation | Checks if file exists |

---

## 4. OPENAI_API_KEY
**Purpose**: OpenAI API key for GPT models  
**Type**: Optional (required for OpenAI models)  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `genpod.config.yml` | 62 | `$OPENAI_API_KEY` | Configuration template reference |
| `configs/project_config.py` | 418 | `os.getenv(api[1:], None)` | Dynamic resolution from $ prefix |
| `configs/project_environment.py` | 34-37 | Field definition | Optional field in model |
| `tools/generate_project_documentation.py` | 195 | `os.getenv("OPENAI_API_KEY")` | Validation check |
| `scripts/run_functional_tester_autonomous_a2a.py` | 42 | `os.getenv("OPENAI_API_KEY")` | Direct usage |
| `.env` | 1 | Definition | Development environment value |

---

## 5. ANTHROPIC_API_KEY
**Purpose**: Anthropic API key for Claude models  
**Type**: Optional (required for Anthropic models)  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `genpod.config.yml` | 101 | `$ANTHROPIC_API_KEY` | Configuration template reference |
| `configs/project_config.py` | 418 | `os.getenv(api[1:], None)` | Dynamic resolution from $ prefix |
| `.env` | 2 | Definition | Development environment value |

---

## 6. GOOGLE_API_KEY
**Purpose**: Google API key for Gemini models  
**Type**: Optional (required for Google models)  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `genpod.config.yml` | 118 | `$GOOGLE_API_KEY` | Configuration template reference |
| `configs/project_config.py` | 418 | `os.getenv(api[1:], None)` | Dynamic resolution from $ prefix |

---

## 7. SEMGREP_APP_TOKEN
**Purpose**: Semgrep token for code analysis  
**Type**: Optional  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `tools/semgrep.py` | 28 | `os.environ['SEMGREP_APP_TOKEN'] = login_token` | Sets token for Semgrep |
| `configs/project_environment.py` | 39-42 | Field definition | Optional field in model |
| `.env` | 4 | Definition | Development environment value |

---

## 8. FUNCTIONAL_TESTER_PORT
**Purpose**: Port for functional tester A2A server  
**Type**: Optional  
**Default**: 8011

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `scripts/run_functional_tester_autonomous_a2a.py` | 69 | `int(os.getenv("FUNCTIONAL_TESTER_PORT", "8011"))` | Port configuration with default |

---

## 9. GITHUB_TOKEN
**Purpose**: GitHub personal access token  
**Type**: Optional  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `.env` | 25 | Definition | Development environment value |

---

## 10. LOGGER_LEVEL
**Purpose**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)  
**Type**: Optional  
**Default**: INFO

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 87 | `os.environ.get("LOGGER_LEVEL", config["level"])` | Sets logging level |
| `utils/logger.py` | 22 | Documentation | Describes environment variable |
| `.env` | 14 | Definition | Development environment value |

---

## 11. LOGGER_FORMAT
**Purpose**: Log format (json or plain)  
**Type**: Optional  
**Default**: json

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 88 | `os.environ.get("LOGGER_FORMAT", config["format"])` | Sets log format |
| `utils/logger.py` | 24 | Documentation | Describes environment variable |

---

## 12. LOGGER_DIR
**Purpose**: Directory for log files  
**Type**: Optional  
**Default**: output/logs

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 89 | `os.environ.get("LOGGER_DIR", config["dir"])` | Sets log directory |
| `utils/logger.py` | 26 | Documentation | Describes environment variable |
| `.env` | 15 | Definition | Development environment value |

---

## 13. LOGGER_CONSOLE_ENABLED
**Purpose**: Enable console logging  
**Type**: Optional  
**Default**: false

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 90 | `os.environ.get("LOGGER_CONSOLE_ENABLED", str(config["console_enabled"]))` | Enable/disable console |
| `utils/logger.py` | 28 | Documentation | Describes environment variable |
| `.env` | 19 | Definition | Development environment value |

---

## 14. LOGGER_MAX_BYTES
**Purpose**: Maximum log file size before rotation  
**Type**: Optional  
**Default**: 26214400 (25MB)

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 91 | `int(os.environ.get("LOGGER_MAX_BYTES", config["max_bytes"]))` | Sets max file size |
| `utils/logger.py` | 30 | Documentation | Describes environment variable |
| `.env` | 16 | Definition | Development environment value |

---

## 15. LOGGER_BACKUP_COUNT
**Purpose**: Number of rotated backup files to retain  
**Type**: Optional  
**Default**: 5

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 92 | `int(os.environ.get("LOGGER_BACKUP_COUNT", config["backup_count"]))` | Sets backup count |
| `utils/logger.py` | 32 | Documentation | Describes environment variable |

---

## 16. LOGGER_DEFAULT_FILE_NAME
**Purpose**: Default name for log file  
**Type**: Optional  
**Default**: application.log

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 93 | `os.environ.get("LOGGER_DEFAULT_FILE_NAME", config["default_file_name"])` | Sets log filename |
| `utils/logger.py` | 34 | Documentation | Describes environment variable |

---

## 17. LOGGER_NAME
**Purpose**: Name of the logger  
**Type**: Optional  
**Default**: Genpod

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 94 | `os.environ.get("LOGGER_NAME", config["logger_name"])` | Sets logger name |
| `utils/logger.py` | 36 | Documentation | Describes environment variable |

---

## 18. LOGGER_CLEAN_ENABLED
**Purpose**: Enable automatic cleaning of old log directories  
**Type**: Optional  
**Default**: false

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 95 | `os.environ.get("LOGGER_CLEAN_ENABLED", str(config["clean_enabled"]))` | Enable/disable cleanup |
| `utils/logger.py` | 38 | Documentation | Describes environment variable |
| `.env` | 17 | Definition | Development environment value |

---

## 19. LOGGER_CLEAN_COUNT
**Purpose**: Maximum number of log directories to keep  
**Type**: Optional  
**Default**: 2

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 96 | `int(os.environ.get("LOGGER_CLEAN_COUNT", config["clean_count"]))` | Sets cleanup count |
| `utils/logger.py` | 40 | Documentation | Describes environment variable |
| `.env` | 18 | Definition | Development environment value |

---

## 20. LOGGER_CONFIG_FILE
**Purpose**: Path to YAML config file for logger  
**Type**: Optional  
**Default**: logger_config.yaml

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/logger.py` | 77 | `os.environ.get("LOGGER_CONFIG_FILE", "logger_config.yaml")` | Sets config file path |
| `utils/logger.py` | 41 | Documentation | Describes environment variable |

---

## 21. AUTO_REPR_PRETTY
**Purpose**: Enable pretty formatting for auto_repr decorator  
**Type**: Optional  
**Default**: False

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/decorators.py` | 109 | `os.environ.get("AUTO_REPR_PRETTY", "False")` | Enable pretty formatting |
| `utils/decorators.py` | 88 | Documentation | Describes environment variable |
| `.env` | 7 | Definition | Development environment value |

---

## 22. AUTO_REPR_UNWRAP_ENUMS
**Purpose**: Unwrap enum values in representations  
**Type**: Optional  
**Default**: False

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `utils/decorators.py` | 110 | `os.environ.get("AUTO_REPR_UNWRAP_ENUMS", "False")` | Enable enum unwrapping |
| `utils/decorators.py` | 89 | Documentation | Describes environment variable |
| `.env` | 8 | Definition | Development environment value |

---

## 23. PHOENIX_PROJECT_NAME
**Purpose**: Project name for Phoenix monitoring  
**Type**: Optional  
**Default**: None

### File Locations and Usage:

| File | Line | Usage | Context |
|------|------|-------|---------|
| `.env` | 11 | Definition | Development environment value |

---

## File Management Summary

### Files That READ Environment Variables:
1. **Python Files** (15 files):
   - `main.py` - Application entry point
   - `configs/project_config.py` - Configuration management
   - `configs/project_environment.py` - Environment validation
   - `core/mcp/config_manager.py` - MCP configuration
   - `utils/logger.py` - Logger configuration
   - `utils/decorators.py` - Decorator configuration
   - `tools/semgrep.py` - Semgrep integration
   - `tools/generate_project_documentation.py` - Documentation generation
   - All `scripts/run_*_a2a.py` files - A2A server runners

2. **Configuration Files** (2 files):
   - `genpod.config.yml` - References env vars with $ syntax
   - `.env` - Defines actual values

3. **Test Files**: None currently

### Files That WRITE Environment Variables:
1. **Python Files** (1 file):
   - `tools/semgrep.py` - Sets SEMGREP_APP_TOKEN

### Configuration Validation Files:
1. **configs/project_environment.py** - Validates required environment variables
2. **core/mcp/config_manager.py** - Validates MCP configuration path

---

## Key Findings

1. **GENPOD_CONFIG**: Primary configuration variable created by install.sh at `~/.config/genpod/config.yml`
2. **GENPOD_CONFIG_PATH**: OBSOLETE - Was used by ProjectEnvironment class which is no longer active
3. **Logger Variables**: All use LOGGER_ prefix

## Recommendations

1. **Remove Obsolete Code**: Remove ProjectEnvironment class and GENPOD_CONFIG_PATH references
2. **Centralize Management**: Create a single environment management module
3. **Clean Up**: Remove all GENPOD_CONFIG_PATH usage from the codebase
4. **Update Documentation**: Keep documentation in sync with actual usage