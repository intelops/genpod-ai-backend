#!/usr/bin/env python3
"""
Run script for RAG Middleware A2A server.

This script starts the RAG Middleware agent with A2A protocol support.
Uses the same configuration approach as the main project.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import uvicorn
from agents.rag_middleware.rag_middleware import RAGMiddleware
from agents.rag_middleware.rag_middleware_a2a_server import create_rag_middleware_a2a_app
from agents.research.research_agent import ResearchAgent
from configs.project_config import ProjectConfig
from core.a2a import A2AConfigLoader
from database.sqlite import SQLite
from utils.logger import logger
from utils.yaml_utils import read_yaml


def main():
    """Main entry point for running RAG Middleware A2A server."""
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
        agent_config = a2a_config.get_agent_config("rag_middleware")
        
        if not agent_config or not agent_config.enabled:
            logger.error("RAG Middleware agent is not enabled in a2a.config.yml")
            sys.exit(1)
        
        # Get rag middleware agent configuration
        middleware_info = project_config.agents.rag_middleware
        if not middleware_info:
            logger.error("RAG Middleware configuration not found in project config")
            sys.exit(1)
        
        # Create Research agent first (required by RAG Middleware)
        research_info = project_config.agents.research
        if not research_info:
            logger.error("Research agent configuration not found in project config")
            sys.exit(1)
            
        logger.info("Creating Research agent for RAG Middleware...")
        research_agent = ResearchAgent(
            id=research_info.agent_id,
            name=research_info.agent_name,
            description=research_info.description,
            llm=research_info.llm,
            recursion_limit=research_info.recursion_limit,
            persistence_db_path=db_path
        )
        
        # Create RAG Middleware agent using the same approach as Team class
        logger.info("Creating RAG Middleware agent...")
        rag_middleware = RAGMiddleware(
            id=middleware_info.agent_id,
            name=middleware_info.agent_name,
            description=middleware_info.description,
            llm=middleware_info.llm,
            research_agent=research_agent,
            recursion_limit=middleware_info.recursion_limit,
            persistence_db_path=db_path  # Use same DB as project
        )
        
        # Create A2A app
        logger.info("Creating A2A application...")
        app = create_rag_middleware_a2a_app(rag_middleware, db_path)
        
        # Run the server
        logger.info(f"Starting RAG Middleware A2A server on {agent_config.host}:{agent_config.port}")
        uvicorn.run(
            app,
            host=agent_config.host,
            port=agent_config.port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down RAG Middleware A2A server...")
    except Exception as e:
        logger.error(f"Failed to start RAG Middleware A2A server: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()