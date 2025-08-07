"""
Base agent card builder for A2A protocol.

Implements Builder pattern for constructing agent cards.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider


class BaseAgentCardBuilder(ABC):
    """
    Abstract builder for creating agent cards.
    
    This class follows the Builder pattern, allowing step-by-step
    construction of agent cards while ensuring consistency.
    """
    
    def __init__(self, agent_name: str, version: str = "1.0.0"):
        """
        Initialize the builder.
        
        Args:
            agent_name: Name of the agent
            version: Version of the agent
        """
        self.agent_name = agent_name
        self.version = version
        self.skills: List[AgentSkill] = []
        self.description: Optional[str] = None
        self.url: Optional[str] = None
        self.capabilities: Optional[AgentCapabilities] = None
        self.provider: Optional[AgentProvider] = None
    
    def with_description(self, description: str) -> 'BaseAgentCardBuilder':
        """Set agent description."""
        self.description = description
        return self
    
    def with_url(self, url: str) -> 'BaseAgentCardBuilder':
        """Set agent URL."""
        self.url = url
        return self
    
    def with_capabilities(
        self,
        streaming: bool = True,
        push_notifications: bool = False,
        state_transition_history: bool = True
    ) -> 'BaseAgentCardBuilder':
        """Set agent capabilities."""
        self.capabilities = AgentCapabilities(
            streaming=streaming,
            push_notifications=push_notifications,
            state_transition_history=state_transition_history
        )
        return self
    
    def with_provider(
        self,
        organization: str = "GenPod AI",
        url: str = "https://genpod.ai"
    ) -> 'BaseAgentCardBuilder':
        """Set provider information."""
        self.provider = AgentProvider(
            organization=organization,
            url=url
        )
        return self
    
    def add_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        tags: List[str],
        examples: Optional[List[str]] = None
    ) -> 'BaseAgentCardBuilder':
        """Add a skill to the agent."""
        skill = AgentSkill(
            id=skill_id,
            name=name,
            description=description,
            tags=tags,
            examples=examples or []
        )
        self.skills.append(skill)
        return self
    
    def build(self) -> AgentCard:
        """
        Build the agent card.
        
        Returns:
            Complete AgentCard instance
        
        Raises:
            ValueError: If required fields are not set
        """
        # Validate required fields
        if not self.description:
            self.description = f"{self.agent_name} agent for GenPod AI"
            
        if not self.url:
            raise ValueError("Agent URL must be set using with_url()")
            
        if not self.capabilities:
            self.capabilities = AgentCapabilities(
                streaming=True,
                push_notifications=False,
                state_transition_history=True
            )
            
        if not self.provider:
            self.provider = AgentProvider(
                organization="GenPod AI",
                url="https://genpod.ai"
            )
        
        # Ensure we have default skills
        if not self.skills:
            self.skills = self._default_skills()
        
        return AgentCard(
            name=f"GenPod {self.agent_name} Agent",
            description=self.description,
            version=self.version,
            url=self.url,
            preferred_transport="JSONRPC",
            skills=self.skills,
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
            capabilities=self.capabilities,
            provider=self.provider
        )
    
    @abstractmethod
    def _default_skills(self) -> List[AgentSkill]:
        """
        Define default skills for the agent.
        
        Subclasses must implement this to provide agent-specific skills.
        
        Returns:
            List of default skills
        """
        pass