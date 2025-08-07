#!/usr/bin/env python3
"""
Master script to run all A2A servers.

This script starts all enabled A2A agent servers based on configuration.
Each agent runs in its own process on a different port.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.a2a import A2AConfigLoader
from utils.logger import logger


class A2AServerManager:
    """Manages multiple A2A server processes."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.config_loader = A2AConfigLoader()
        
    def start_all_servers(self):
        """Start all enabled A2A servers."""
        try:
            # Load A2A configuration
            config = self.config_loader.load()
            enabled_agents = config.get_enabled_agents()
            
            if not enabled_agents:
                logger.error("No agents are enabled in a2a.config.yml")
                return
            
            logger.info(f"Starting {len(enabled_agents)} A2A servers...")
            
            # Start each enabled agent
            for agent_name, agent_config in enabled_agents.items():
                self._start_agent_server(agent_name, agent_config)
            
            logger.info("All A2A servers started successfully")
            logger.info("Press Ctrl+C to stop all servers")
            
            # Wait for interrupt
            try:
                while True:
                    asyncio.run(asyncio.sleep(1))
            except KeyboardInterrupt:
                logger.info("Shutting down all A2A servers...")
                self.stop_all_servers()
                
        except Exception as e:
            logger.error(f"Failed to start A2A servers: {str(e)}")
            self.stop_all_servers()
            sys.exit(1)
    
    def _start_agent_server(self, agent_name: str, agent_config):
        """Start a single agent server."""
        script_path = Path(__file__).parent / f"run_{agent_name}_a2a.py"
        
        if not script_path.exists():
            logger.warning(f"Run script not found for {agent_name}: {script_path}")
            return
        
        try:
            logger.info(f"Starting {agent_name} A2A server on port {agent_config.port}...")
            
            # Start the process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy()
            )
            
            self.processes[agent_name] = process
            
            # Give it a moment to start
            asyncio.run(asyncio.sleep(0.5))
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Failed to start {agent_name} server:")
                if stderr:
                    logger.error(stderr.decode())
            else:
                logger.info(f"{agent_name} server started (PID: {process.pid})")
                
        except Exception as e:
            logger.error(f"Error starting {agent_name} server: {str(e)}")
    
    def stop_all_servers(self):
        """Stop all running servers."""
        for agent_name, process in self.processes.items():
            if process.poll() is None:  # Still running
                logger.info(f"Stopping {agent_name} server (PID: {process.pid})...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {agent_name} server")
                    process.kill()
        
        self.processes.clear()
        logger.info("All A2A servers stopped")
    
    def check_server_status(self) -> Dict[str, str]:
        """Check the status of all servers."""
        status = {}
        for agent_name, process in self.processes.items():
            if process.poll() is None:
                status[agent_name] = "running"
            else:
                status[agent_name] = f"stopped (exit code: {process.returncode})"
        return status


def main():
    """Main entry point."""
    # Check for GENPOD_CONFIG environment variable
    if not os.getenv("GENPOD_CONFIG"):
        logger.error("The environment variable 'GENPOD_CONFIG' is not set.")
        logger.info("Please set it to the path of your setup configuration file.")
        sys.exit(1)
    
    # Create and run server manager
    manager = A2AServerManager()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received interrupt signal")
        manager.stop_all_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all servers
    manager.start_all_servers()


if __name__ == "__main__":
    main()