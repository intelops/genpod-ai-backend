"""
Configuration loader for A2A protocol.

Implements Single Responsibility Principle - only responsible for loading and parsing config.
"""

import os
from pathlib import Path
from typing import Optional

from core.a2a.config.models import A2AConfig, AgentConfig
from core.a2a.exceptions import A2AConfigError
from utils.yaml_utils import read_yaml
from utils.logger import logger


class A2AConfigLoader:
    """
    Loads and manages A2A configuration.
    
    This class follows the Singleton pattern to ensure only one config instance
    exists throughout the application lifecycle.
    """
    
    _instance: Optional['A2AConfigLoader'] = None
    _config: Optional[A2AConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, config_path: Optional[str] = None) -> A2AConfig:
        """
        Load A2A configuration from YAML file.
        
        Args:
            config_path: Optional path to config file. If not provided,
                        looks for 'a2a.config.yml' in project root.
                        
        Returns:
            A2AConfig instance
            
        Raises:
            A2AConfigError: If config file not found or invalid
        """
        if self._config is not None:
            return self._config
            
        if config_path is None:
            # Look for a2a.config.yml in project root
            config_path = self._find_config_file()
            
        if not os.path.exists(config_path):
            raise A2AConfigError(f"Configuration file not found: {config_path}")
            
        try:
            logger.info(f"Loading A2A configuration from: {config_path}")
            config_data = read_yaml(config_path)
            self._config = A2AConfig(**config_data)
            logger.info(f"Loaded configuration for {len(self._config.agents)} agents")
            return self._config
        except Exception as e:
            raise A2AConfigError(f"Failed to load configuration: {str(e)}")
    
    def _find_config_file(self) -> str:
        """
        Find a2a.config.yml file in project root.
        
        Returns:
            Path to config file
            
        Raises:
            A2AConfigError: If config file not found
        """
        # Start from current file location and go up
        current_dir = Path(__file__).parent
        
        # Go up to find project root (where a2a.config.yml should be)
        for _ in range(5):  # Limit search depth
            config_path = current_dir / "a2a.config.yml"
            if config_path.exists():
                return str(config_path)
            current_dir = current_dir.parent
            
        raise A2AConfigError(
            "Could not find a2a.config.yml in project root. "
            "Please create the configuration file or specify its path."
        )
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            AgentConfig instance or None if not found
        """
        if self._config is None:
            self.load()
        return self._config.get_agent_config(agent_name)
    
    def reset(self):
        """Reset the configuration (useful for testing)."""
        self._config = None