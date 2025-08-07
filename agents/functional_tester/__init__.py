"""Functional Tester Agent

This agent is responsible for generating functional test suites that validate
complete features and workflows from a user perspective.

Two versions are available:
- FunctionalTesterAgent: Traditional workflow-based agent
- AutonomousFunctionalTesterAgent: Modern autonomous agent with adaptive capabilities
"""

from agents.functional_tester.functional_tester_autonomous_agent import AutonomousFunctionalTesterAgent
from agents.functional_tester._internal.functional_tester_autonomous_state import (
    AutonomousFunctionalTesterInput,
    AutonomousFunctionalTesterOutput,
    AutonomousFunctionalTesterState
)

__all__ = [
    # Autonomous
    "AutonomousFunctionalTesterAgent",
    "AutonomousFunctionalTesterInput",
    "AutonomousFunctionalTesterOutput", 
    "AutonomousFunctionalTesterState"
]