#!/usr/bin/env python3
"""
Run the Autonomous Functional Tester Agent with A2A Protocol
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.functional_tester.functional_tester_autonomous_agent import AutonomousFunctionalTesterAgent
from agents.functional_tester.functional_tester_autonomous_a2a_server import (
    create_autonomous_functional_tester_a2a_app
)
from llms import llm_factory
from utils.logger import logger


def main():
    """Main entry point for running the Functional Tester A2A server"""
    
    # Configuration
    agent_id = "functional-tester-001"
    agent_name = "Autonomous Functional Tester"
    agent_description = "Adaptive functional test generation for any framework"
    
    # Database path
    db_path = os.path.join(project_root, "data", "functional_tester.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize LLM
    logger.info("Initializing LLM...")
    llm = llm_factory(
        provider="openai",
        model="gpt-4o",
        model_config={
            "temperature": 0.7,
            "api_key": os.getenv("OPENAI_API_KEY")
        },
        max_retries=3,
        retry_backoff=1.0
    )
    
    # Create agent
    logger.info("Creating Autonomous Functional Tester agent...")
    agent = AutonomousFunctionalTesterAgent(
        id=agent_id,
        name=agent_name,
        description=agent_description,
        llm=llm,
        recursion_limit=10,
        persistence_db_path=db_path,
        use_rag=False,
        use_mcp=True
    )
    
    # Create A2A app
    logger.info("Creating A2A application...")
    app = create_autonomous_functional_tester_a2a_app(
        functional_tester_agent=agent,
        db_path=db_path
    )
    
    # Get port from config or use default
    port = int(os.getenv("FUNCTIONAL_TESTER_PORT", "8011"))
    
    logger.info(f"Starting Autonomous Functional Tester A2A server on port {port}")
    logger.info(f"Agent capabilities: {agent.get_capabilities()}")
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()