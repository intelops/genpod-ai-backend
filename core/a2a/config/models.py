"""
Pydantic models for A2A configuration validation.

These models ensure type safety and validation for configuration data.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator


# Removed TaskStoreConfig - we use existing SQLite instance directly


class TimeoutConfig(BaseModel):
    """Timeout configuration for agent operations."""
    blocking: int = Field(default=600, ge=1, description="Timeout in seconds for blocking calls")
    streaming: int = Field(default=1800, ge=1, description="Timeout in seconds for streaming")


class EventQueueConfig(BaseModel):
    """Configuration for event queue."""
    max_size: int = Field(default=1000, ge=100)
    timeout: float = Field(default=0.5, ge=0.1, description="Queue polling timeout in seconds")


class MonitoringConfig(BaseModel):
    """Configuration for monitoring and metrics."""
    metrics_enabled: bool = False
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    trace_enabled: bool = False
    trace_endpoint: Optional[str] = None


class ServiceDiscoveryConfig(BaseModel):
    """Configuration for service discovery."""
    enabled: bool = True
    registry_url: str = "http://localhost:8000/registry"
    health_check_interval: int = Field(default=30, ge=5, description="Health check interval in seconds")


class AgentConfig(BaseModel):
    """Configuration for individual agent."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(ge=1024, le=65535)
    description: str
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    
    class Config:
        extra = "forbid"  # Prevent unknown fields


class A2AConfig(BaseModel):
    """Root configuration for A2A protocol."""
    default_timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    event_queue: EventQueueConfig = Field(default_factory=EventQueueConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    service_discovery: ServiceDiscoveryConfig = Field(default_factory=ServiceDiscoveryConfig)
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)
    
    def get_enabled_agents(self) -> Dict[str, AgentConfig]:
        """Get all enabled agents."""
        return {name: config for name, config in self.agents.items() if config.enabled}