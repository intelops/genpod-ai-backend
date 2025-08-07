#!/usr/bin/env python3
"""
Run script for Tests Generator A2A server.

This script starts the Tests Generator agent with A2A protocol support.
Uses the same configuration approach as the main project.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import uvicorn
from agents.tests_generator.tests_generator_agent import TestsGeneratorAgent
from agents.tests_generator.tests_generator_a2a_server import create_tests_generator_a2a_app
from configs.project_config import ProjectConfig
from core.a2a import A2AConfigLoader
from database.sqlite import SQLite
from utils.logger import logger
from utils.yaml_utils import read_yaml


def main():
    """Main entry point for running Tests Generator A2A server."""
    try:
        # Load setup configuration from environment
        setup_config_path = os.getenv("GENPOD_CONFIG")
        if not setup_config_path:
            logger.error("The environment variable 'GENPOD_CONFIG' is not set.")
            sys.exit(1)
        
        logger.info(f"Loading setup configuration from: {setup_config_path}")
        setup_config = read_yaml(setup_config_path)
        
        # Get database path from setup config
        db_path = setup_config.get('sqlite3_database_path')
        if not db_path:
            logger.error("Database path missing in setup configuration.")
            sys.exit(1)
        
        # Initialize database
        logger.info(f"Using database: {db_path}")
        db = SQLite(db_path)
        db.create_tables()
        
        # Load project configuration
        genpod_config_path = setup_config.get('genpod_configuration_file_path')
        project_config = ProjectConfig(genpod_config_path)
        project_config.load_config()
        logger.info("Project configuration loaded successfully.")
        
        # Load A2A configuration
        logger.info("Loading A2A configuration...")
        a2a_config_loader = A2AConfigLoader()
        a2a_config = a2a_config_loader.load()
        agent_config = a2a_config.get_agent_config("tests_generator")
        
        if not agent_config or not agent_config.enabled:
            logger.error("Tests Generator agent is not enabled in a2a.config.yml")
            sys.exit(1)
        
        # Get tests generator agent configuration
        tests_generator_info = project_config.agents.tests_generator
        if not tests_generator_info:
            logger.error("Tests Generator configuration not found in project config")
            sys.exit(1)
        
        # Create Tests Generator agent using the same approach as Team class
        logger.info("Creating Tests Generator agent...")
        tests_generator = TestsGeneratorAgent(
            id=tests_generator_info.agent_id,
            name=tests_generator_info.agent_name,
            description=tests_generator_info.description,
            llm=tests_generator_info.llm,
            recursion_limit=tests_generator_info.recursion_limit,
            persistence_db_path=db_path,  # Use same DB as project
            use_rag=tests_generator_info.use_rag
        )
        
        # Create A2A app
        logger.info("Creating A2A application...")
        app = create_tests_generator_a2a_app(tests_generator, db_path)
        
        # Run the server
        logger.info(f"Starting Tests Generator A2A server on {agent_config.host}:{agent_config.port}")
        uvicorn.run(
            app,
            host=agent_config.host,
            port=agent_config.port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down Tests Generator A2A server...")
    except Exception as e:
        logger.error(f"Failed to start Tests Generator A2A server: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()