"""
Autonomous Functional Tester State

Simplified state management for autonomous functional test generation.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models.models import PlannedIssue, PlannedTask, RequirementsDocument


class AutonomousFunctionalTesterInput(BaseInputState):
    """Input state for autonomous functional tester."""
    
    project_name: str = Field(
        description="The name of the project."
    )
    requirements_document: RequirementsDocument = Field(
        description="The project's requirements document."
    )
    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The task to be processed by the functional tester."
    )
    current_planned_issue: Optional[PlannedIssue] = Field(
        default=None,
        description="Optional issue to be resolved (for issue resolution mode)."
    )


class AutonomousFunctionalTesterOutput(BaseOutputState):
    """Output state from autonomous functional tester."""
    
    current_planned_task: PlannedTask = Field(
        description="The processed task with updated status."
    )
    test_scenarios: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Generated test scenarios organized by feature/module."
    )
    functional_test_code: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated functional test code files."
    )
    test_framework_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Test framework configuration."
    )
    atomic_tasks_executed: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of atomic tasks that were executed."
    )
    execution_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of the execution including success/failure details."
    )


class AutonomousFunctionalTesterState(BaseState):
    """
    Simplified state for autonomous functional tester.
    
    No fixed stages or operational modes - just task processing state.
    """
    
    # Input fields
    project_name: str = Field(
        default="",
        description="The name of the project."
    )
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="The project's requirements document."
    )
    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The task being processed."
    )
    current_planned_issue: Optional[PlannedIssue] = Field(
        default=None,
        description="Optional issue being resolved."
    )
    
    # Output fields
    test_scenarios: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Generated test scenarios."
    )
    functional_test_code: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated test code files."
    )
    test_framework_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Test framework configuration."
    )
    
    # Processing state
    current_test_generation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current test generation context and intermediate data."
    )
    atomic_tasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of atomic tasks from task breakdown."
    )
    execution_log: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Log of execution steps and results."
    )
    
    # No operational_mode or current_mode_stage - autonomous operation!