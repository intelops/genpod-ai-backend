#!/usr/bin/env python3
"""
Run script for Coder A2A server.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import uvicorn
from agents.coder.coder_agent import CoderAgent
from agents.coder.coder_a2a_server import create_coder_a2a_app
from configs.project_config import ProjectConfig
from core.a2a import A2AConfigLoader
from database.sqlite import SQLite
from utils.logger import logger
from utils.yaml_utils import read_yaml


def main():
    """Main entry point for running Coder A2A server."""
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
        agent_config = a2a_config.get_agent_config("coder")
        
        if not agent_config or not agent_config.enabled:
            logger.error("Coder agent is not enabled in a2a.config.yml")
            sys.exit(1)
        
        # Get coder agent configuration
        coder_info = project_config.agents.coder
        if not coder_info:
            logger.error("Coder configuration not found in project config")
            sys.exit(1)
        
        # Create Coder agent
        logger.info("Creating Coder agent...")
        coder = CoderAgent(
            id=coder_info.agent_id,
            name=coder_info.agent_name,
            description=coder_info.description,
            llm=coder_info.llm,
            recursion_limit=coder_info.recursion_limit,
            persistence_db_path=db_path,
            use_rag=coder_info.use_rag
        )

        # Create A2A app
        logger.info("Creating A2A application...")
        app = create_coder_a2a_app(coder, db_path)
        
        # Run the server
        logger.info(f"Starting Coder A2A server on {agent_config.host}:{agent_config.port}")
        uvicorn.run(
            app,
            host=agent_config.host,
            port=agent_config.port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down Coder A2A server...")
    except Exception as e:
        logger.error(f"Failed to start Coder A2A server: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()