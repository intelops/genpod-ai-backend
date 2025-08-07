"""
Autonomous Functional Tester Workflow

This module implements an autonomous workflow for functional test generation
using TaskMaster for task breakdown and LLM-driven decision making.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum

from agents.functional_tester._internal.functional_tester_prompt import FunctionalTesterPrompts
from agents.functional_tester._internal.functional_tester_autonomous_state import AutonomousFunctionalTesterState
from core.decorators import handle_errors_and_reset, record_node
from core.workflow import BaseWorkFlow
from core.mcp.mcp_task_handler import mcp_task_handler
from llms.llm import LLM
from models.constants import Status
from models.functional_tester_models import (
    FunctionalTestSuite, FunctionalTestCode, TestFrameworkConfig
)
from tools.code import CodeFileWriter
from utils.logger import logger


class AtomicTaskType(str, Enum):
    """Types of atomic tasks the functional tester can handle"""
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    LEARN_FROM_CODEBASE = "learn_from_codebase"
    GENERATE_SCENARIOS = "generate_scenarios"
    GENERATE_TEST_CODE = "generate_test_code"
    GENERATE_CONFIG = "generate_config"
    WRITE_FILE = "write_file"
    VALIDATE_OUTPUT = "validate_output"


class AutonomousFunctionalTesterWorkFlow(BaseWorkFlow[FunctionalTesterPrompts]):
    """
    Autonomous workflow for functional test generation.
    
    This workflow uses TaskMaster to break down high-level tasks and
    executes them autonomously without predetermined stages.
    """
    
    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool = False):
        super().__init__(agent_id, agent_name, FunctionalTesterPrompts(use_rag), llm, use_rag)
        
    def is_suitable_task(self, state: AutonomousFunctionalTesterState) -> bool:
        """
        Determine if the current task is suitable for functional testing.
        
        Args:
            state: Current workflow state
            
        Returns:
            bool: True if task requires functional testing
        """
        task = state.current_planned_task
        logger.info(f"Analyzing task suitability: {task.task_id}")
        
        # For now, let's assume all tasks are suitable for functional testing
        # This simplifies the workflow while we test the core functionality
        # TODO: Implement proper suitability check using LLM
        
        # Simple heuristic: if task description contains testing-related keywords
        task_desc_lower = task.description.lower() if task.description else ""
        testing_keywords = ["test", "testing", "e2e", "functional", "integration", "ui", "api", "validation"]
        
        is_suitable = any(keyword in task_desc_lower for keyword in testing_keywords) or True  # Default to True for now
        
        logger.info(f"Task suitability result: {'Suitable' if is_suitable else 'Not suitable'}")
        return is_suitable
    
    def breakdown_task_with_taskmaster(self, state: AutonomousFunctionalTesterState) -> List[Dict[str, Any]]:
        """
        Use TaskMaster MCP to break down the task into atomic steps.
        
        Args:
            state: Current workflow state
            
        Returns:
            List of atomic tasks
        """
        task = state.current_planned_task
        logger.info(f"Breaking down task using TaskMaster: {task.task_id}")
        
        try:
            # Prepare context for TaskMaster
            context = {
                "project_name": state.project_name,
                "requirements": state.requirements_document.to_markdown() if state.requirements_document else "",
                "task_description": task.description,
                "test_type": "functional",
                "project_path": os.path.join(state.project_directory, state.project_name)
            }
            
            # Use TaskMaster to break down the task
            task_description = f"""Break down this functional testing task into atomic steps:
            
Task: {task.description}
Project: {state.project_name}

Please break this down into specific atomic tasks such as:
1. Analyze requirements and identify test scenarios
2. Generate test scenarios for each feature
3. Generate test code for the scenarios
4. Create test configuration
5. Write all files to appropriate locations

Return a structured list of atomic tasks."""
            
            # Run the async method synchronously
            result = asyncio.run(mcp_task_handler.execute_task(
                task=task_description,
                context=context,
                llm=self.llm
            ))
            
            if result.success and result.result:
                # Parse the result into atomic tasks
                atomic_tasks = self._parse_atomic_tasks(result.result)
                logger.info(f"Successfully broke down task into {len(atomic_tasks)} atomic tasks")
                return atomic_tasks
            else:
                logger.warning(f"TaskMaster failed to break down task: {result.error}")
                # Fallback to default atomic tasks
                return self._get_default_atomic_tasks(state)
                
        except Exception as e:
            logger.error(f"Error using TaskMaster: {e}")
            # Fallback to default atomic tasks
            return self._get_default_atomic_tasks(state)
    
    def _parse_atomic_tasks(self, taskmaster_result: Any) -> List[Dict[str, Any]]:
        """Parse TaskMaster result into structured atomic tasks"""
        atomic_tasks = []
        
        # Handle different possible response formats
        if isinstance(taskmaster_result, list):
            for idx, task in enumerate(taskmaster_result):
                if isinstance(task, dict):
                    atomic_tasks.append(task)
                else:
                    # Convert string tasks to dict format
                    atomic_tasks.append({
                        "id": f"task_{idx}",
                        "type": self._infer_task_type(str(task)),
                        "description": str(task),
                        "status": "pending"
                    })
        elif isinstance(taskmaster_result, str):
            # Parse string response into tasks
            lines = taskmaster_result.strip().split('\n')
            for idx, line in enumerate(lines):
                if line.strip():
                    atomic_tasks.append({
                        "id": f"task_{idx}",
                        "type": self._infer_task_type(line),
                        "description": line.strip(),
                        "status": "pending"
                    })
        
        return atomic_tasks
    
    def _infer_task_type(self, task_description: str) -> str:
        """Infer atomic task type from description"""
        description_lower = task_description.lower()
        
        if "analyz" in description_lower or "requirement" in description_lower:
            return AtomicTaskType.ANALYZE_REQUIREMENTS
        elif "scenario" in description_lower:
            return AtomicTaskType.GENERATE_SCENARIOS
        elif "test code" in description_lower or "generate code" in description_lower:
            return AtomicTaskType.GENERATE_TEST_CODE
        elif "config" in description_lower or "setup" in description_lower:
            return AtomicTaskType.GENERATE_CONFIG
        elif "write" in description_lower or "save" in description_lower:
            return AtomicTaskType.WRITE_FILE
        elif "validat" in description_lower or "check" in description_lower:
            return AtomicTaskType.VALIDATE_OUTPUT
        else:
            return AtomicTaskType.GENERATE_TEST_CODE
    
    def _get_default_atomic_tasks(self, state: AutonomousFunctionalTesterState) -> List[Dict[str, Any]]:
        """Get default atomic tasks for functional testing"""
        tasks = [
            {
                "id": "task_1",
                "type": AtomicTaskType.ANALYZE_REQUIREMENTS,
                "description": "Analyze requirements and project context",
                "status": "pending"
            },
            {
                "id": "task_2",
                "type": AtomicTaskType.LEARN_FROM_CODEBASE,
                "description": "Learn from existing tests or establish new patterns",
                "status": "pending"
            },
            {
                "id": "task_3", 
                "type": AtomicTaskType.GENERATE_SCENARIOS,
                "description": "Generate comprehensive test scenarios",
                "status": "pending"
            },
            {
                "id": "task_4",
                "type": AtomicTaskType.GENERATE_TEST_CODE,
                "description": "Generate functional test code",
                "status": "pending"
            },
            {
                "id": "task_5",
                "type": AtomicTaskType.GENERATE_CONFIG,
                "description": "Generate test framework configuration",
                "status": "pending"
            },
            {
                "id": "task_6",
                "type": AtomicTaskType.WRITE_FILE,
                "description": "Write all generated files",
                "status": "pending"
            }
        ]
        return tasks
    
    def execute_atomic_task(self, atomic_task: Dict[str, Any], state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """
        Execute a single atomic task.
        
        Args:
            atomic_task: The atomic task to execute
            state: Current workflow state
            
        Returns:
            Task execution result
        """
        task_type = atomic_task.get("type", "")
        logger.info(f"Executing atomic task: {atomic_task['id']} - {task_type}")
        
        try:
            if task_type == AtomicTaskType.ANALYZE_REQUIREMENTS:
                result = self._analyze_requirements(state)
            elif task_type == AtomicTaskType.LEARN_FROM_CODEBASE:
                result = self._learn_from_codebase(state)
            elif task_type == AtomicTaskType.GENERATE_SCENARIOS:
                result = self._generate_scenarios(state)
            elif task_type == AtomicTaskType.GENERATE_TEST_CODE:
                result = self._generate_test_code(state)
            elif task_type == AtomicTaskType.GENERATE_CONFIG:
                result = self._generate_config(state)
            elif task_type == AtomicTaskType.WRITE_FILE:
                result = self._write_files(state)
            elif task_type == AtomicTaskType.VALIDATE_OUTPUT:
                result = self._validate_output(state)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            atomic_task["status"] = "completed" if result.get("success") else "failed"
            atomic_task["result"] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing atomic task {atomic_task['id']}: {e}")
            atomic_task["status"] = "failed"
            atomic_task["error"] = str(e)
            return {"success": False, "error": str(e)}
    
    def _analyze_requirements(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Analyze requirements and detect existing frameworks"""
        logger.debug("Analyzing requirements and project context")
        
        try:
            # Use MCP or LLM to analyze the project
            context = {
                "project_name": state.project_name,
                "project_path": os.path.join(state.project_directory, state.project_name)
            }
            
            analysis_result = self.invoke(
                prompt=self.prompts.framework_detection_prompt,
                prompt_inputs=context,
                response_type="json"
            )
            
            # Store analysis for adaptive generation
            detected_frameworks = analysis_result.response.get('detected_frameworks', [])
            has_existing_tests = len(detected_frameworks) > 0 or analysis_result.response.get('test_patterns', {})
            
            state.current_test_generation["requirements_analysis"] = {
                "project_context": analysis_result.response,
                "adaptive_approach": True,
                "framework_agnostic": True,
                "has_existing_tests": has_existing_tests,
                "greenfield_testing": not has_existing_tests
            }
            
            if has_existing_tests:
                logger.info(f"Detected existing test frameworks: {detected_frameworks}")
            else:
                logger.info("No existing test patterns found - will establish new testing framework")
            
        except Exception as e:
            logger.warning(f"Framework detection failed, will adapt during generation: {e}")
            state.current_test_generation["requirements_analysis"] = {
                "adaptive_approach": True,
                "framework_agnostic": True,
                "detection_failed": True
            }
        
        return {"success": True, "message": "Requirements and context analyzed"}
    
    def _get_modern_best_practices(self, tech_stack: str) -> Dict[str, Any]:
        """Get modern best practices for a given tech stack when no patterns exist"""
        try:
            result = self.invoke(
                prompt=self.prompts.best_practices_prompt,
                prompt_inputs={"tech_stack": tech_stack},
                response_type="json"
            )
            return result.response
        except Exception as e:
            logger.warning(f"Failed to get best practices: {e}")
            return {
                "framework": "Choose based on language",
                "structure": "Follow language conventions",
                "naming": "Use descriptive test names"
            }
    
    def _learn_from_codebase(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Learn from existing tests and patterns in the codebase"""
        logger.debug("Learning from existing tests in the codebase")
        
        try:
            context = {
                "project_name": state.project_name,
                "project_path": os.path.join(state.project_directory, state.project_name)
            }
            
            # Use MCP to analyze existing tests
            try:
                result = asyncio.run(mcp_task_handler.execute_task(
                    task="Analyze existing test patterns in the codebase",
                    context=context,
                    llm=self.llm
                ))
                learning_data = result.result if result.success else {}
            except Exception as mcp_error:
                logger.debug(f"MCP not available, using LLM directly: {mcp_error}")
                # Fallback to LLM analysis
                learning_result = self.invoke(
                    prompt=self.prompts.learning_prompt,
                    prompt_inputs=context,
                    response_type="json"
                )
                learning_data = learning_result.response
            
            # Store learnings for use in generation
            if "requirements_analysis" not in state.current_test_generation:
                state.current_test_generation["requirements_analysis"] = {}
            
            state.current_test_generation["requirements_analysis"]["learned_patterns"] = learning_data
            logger.info("Successfully learned from existing codebase patterns")
            
            return {"success": True, "patterns_learned": True}
            
        except Exception as e:
            logger.warning(f"Learning from codebase failed, will proceed with adaptive generation: {e}")
            return {"success": True, "message": "Will adapt during generation"}
    
    def _generate_scenarios(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Generate test scenarios"""
        logger.debug("Generating test scenarios")
        
        try:
            # Ensure project directory exists
            if not hasattr(state, 'project_directory') or not state.project_directory:
                state.project_directory = os.getcwd()
            
            # Use existing prompt to generate scenarios
            llm_output = self.invoke_with_pydantic_model(
                self.prompts.scenario_generation_prompt,
                {
                    'project_name': state.project_name,
                    'project_path': os.path.join(state.project_directory, state.project_name),
                    'requirements_document': state.requirements_document.to_markdown() if state.requirements_document else "",
                    'task': state.current_planned_task.description,
                    'error_message': ""
                },
                FunctionalTestSuite
            )
            
            # Store generated scenarios
            state.current_test_generation['test_suites'] = [llm_output.response]
            state.test_scenarios = {
                llm_output.response.suite_name: [
                    scenario.model_dump() for scenario in llm_output.response.test_scenarios
                ]
            }
            
            return {"success": True, "scenarios_count": len(llm_output.response.test_scenarios)}
            
        except Exception as e:
            logger.error(f"Error generating scenarios: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_test_code(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Generate functional test code adaptively"""
        logger.debug("Generating functional test code with adaptive approach")
        
        try:
            if not state.test_scenarios:
                return {"success": False, "error": "No test scenarios available"}
            
            # Include context analysis for adaptive generation
            context_analysis = state.current_test_generation.get("requirements_analysis", {})
            
            # Enhanced prompt inputs with project context
            prompt_inputs = {
                'project_name': state.project_name,
                'project_path': os.path.join(state.project_directory, state.project_name),
                'requirements_document': state.requirements_document.to_markdown() if state.requirements_document else "",
                'task': state.current_planned_task.description,
                'test_scenarios': json.dumps(state.test_scenarios, indent=2),
                'error_message': "",
                'project_context': json.dumps(context_analysis.get("project_context", {}), indent=2) if context_analysis else ""
            }
            
            # Add project context to prompt if available
            if context_analysis:
                if "project_context" in context_analysis:
                    prompt_inputs['detected_frameworks'] = context_analysis["project_context"].get("detected_frameworks", [])
                    prompt_inputs['existing_patterns'] = context_analysis["project_context"].get("test_patterns", {})
                
                # Add greenfield indicator
                if context_analysis.get("greenfield_testing", False):
                    prompt_inputs['greenfield_mode'] = True
                    prompt_inputs['instruction'] = "No existing tests found. Please establish modern best practices for this project."
            
            # Use existing prompt to generate test code
            llm_output = self.invoke_with_pydantic_model(
                self.prompts.functional_test_generation_prompt,
                prompt_inputs,
                FunctionalTestCode
            )
            
            # Store generated code
            test_code = llm_output.response
            state.current_test_generation['functional_test_code'] = test_code.test_files
            state.current_test_generation['config_files'] = test_code.config_files
            state.current_test_generation['helper_files'] = test_code.helper_files
            state.current_test_generation['data_files'] = test_code.data_files
            
            return {"success": True, "files_count": len(test_code.test_files)}
            
        except Exception as e:
            logger.error(f"Error generating test code: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_config(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Generate test framework configuration"""
        logger.debug("Generating test framework configuration")
        
        try:
            # Create test code summary
            test_code_summary = {
                "test_files": len(state.current_test_generation.get('functional_test_code', {})),
                "config_files": len(state.current_test_generation.get('config_files', {})),
                "helper_files": len(state.current_test_generation.get('helper_files', {})),
                "test_suites": [suite.suite_name for suite in state.current_test_generation.get('test_suites', [])]
            }
            
            # Use existing prompt to generate config
            llm_output = self.invoke_with_pydantic_model(
                self.prompts.test_config_generation_prompt,
                {
                    'project_name': state.project_name,
                    'project_path': os.path.join(state.project_directory, state.project_name),
                    'requirements_document': state.requirements_document.to_markdown() if state.requirements_document else "",
                    'test_code_summary': json.dumps(test_code_summary, indent=2),
                    'error_message': ""
                },
                TestFrameworkConfig
            )
            
            state.current_test_generation['test_framework_config'] = llm_output.response
            
            return {"success": True, "config_generated": True}
            
        except Exception as e:
            logger.error(f"Error generating config: {e}")
            return {"success": False, "error": str(e)}
    
    def _write_files(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Write all generated files to disk"""
        logger.debug("Writing generated files")
        
        files_written = 0
        errors = []
        
        # Collect all files to write
        files_to_write = {
            **state.current_test_generation.get('functional_test_code', {}),
            **state.current_test_generation.get('config_files', {}),
            **state.current_test_generation.get('helper_files', {}),
            **state.current_test_generation.get('data_files', {})
        }
        
        # Write each file
        for file_path, content in files_to_write.items():
            try:
                if not os.path.isabs(file_path):
                    full_path = os.path.join(state.project_directory, state.project_name, file_path)
                else:
                    full_path = file_path
                
                result = CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": content,
                    "file_path": full_path
                })
                
                if result[0]:  # Error
                    errors.append(f"Failed to write {full_path}: {result[1]}")
                else:
                    files_written += 1
                    
            except Exception as e:
                errors.append(f"Exception writing {file_path}: {str(e)}")
        
        # Write test configuration
        if state.current_test_generation.get('test_framework_config'):
            try:
                config_path = os.path.join(
                    state.project_directory,
                    state.project_name,
                    "tests/functional/config/test_config.json"
                )
                
                config_data = state.current_test_generation['test_framework_config']
                if hasattr(config_data, 'model_dump'):
                    config_data = config_data.model_dump()
                
                result = CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": json.dumps(config_data, indent=2),
                    "file_path": config_path
                })
                
                if not result[0]:
                    files_written += 1
                    
            except Exception as e:
                errors.append(f"Exception writing config: {str(e)}")
        
        # Update state
        state.functional_test_code = files_to_write
        state.test_framework_config = state.current_test_generation.get('test_framework_config', {})
        
        return {
            "success": len(errors) == 0,
            "files_written": files_written,
            "errors": errors
        }
    
    def _validate_output(self, state: AutonomousFunctionalTesterState) -> Dict[str, Any]:
        """Validate the generated output"""
        logger.debug("Validating generated output")
        
        # Basic validation
        has_scenarios = bool(state.test_scenarios)
        has_test_code = bool(state.functional_test_code)
        has_config = bool(state.test_framework_config)
        
        is_valid = has_scenarios and has_test_code
        
        return {
            "success": is_valid,
            "validation": {
                "has_scenarios": has_scenarios,
                "has_test_code": has_test_code,
                "has_config": has_config
            }
        }
    
    @record_node("AUTONOMOUS_PROCESS")
    def process_task(self, state: AutonomousFunctionalTesterState) -> AutonomousFunctionalTesterState:
        """
        Main autonomous task processing method.
        
        This replaces the fixed workflow with dynamic task execution.
        """
        logger.info(f"Starting autonomous task processing for task: {state.current_planned_task.task_id}")
        
        # Step 1: Check task suitability
        if not self.is_suitable_task(state):
            logger.info("Task not suitable for functional testing, abandoning")
            state.current_planned_task.task_status = Status.ABANDONED
            return state
        
        # Step 2: Break down task using TaskMaster
        logger.info("Breaking down task into atomic steps")
        atomic_tasks = self.breakdown_task_with_taskmaster(state)
        
        # Step 3: Execute each atomic task
        all_success = True
        for atomic_task in atomic_tasks:
            logger.info(f"Executing atomic task: {atomic_task['description']}")
            result = self.execute_atomic_task(atomic_task, state)
            
            if not result.get("success"):
                logger.error(f"Atomic task failed: {atomic_task['id']} - {result.get('error')}")
                all_success = False
                # Decide whether to continue or stop on failure
                if atomic_task.get("critical", True):
                    break
        
        # Step 4: Set final task status
        if all_success:
            state.current_planned_task.task_status = Status.DONE
            state.current_planned_task.is_test_code_generated = True
            logger.info("All atomic tasks completed successfully")
        else:
            state.current_planned_task.task_status = Status.INCOMPLETE
            logger.warning("Some atomic tasks failed, marking as incomplete")
        
        return state
    
    def router(self, state: AutonomousFunctionalTesterState) -> str:
        """
        Simple router for autonomous workflow.
        
        Since we have a single processing node, always route to it or exit.
        """
        if state.current_planned_task.task_status in [Status.NEW, Status.INPROGRESS]:
            return "process"
        else:
            return "exit"
    
    def entry_node(self, state: AutonomousFunctionalTesterState) -> AutonomousFunctionalTesterState:
        """Simple entry node that just returns state"""
        logger.debug("Entering autonomous functional tester workflow")
        return state
    
    def exit_node(self, state: AutonomousFunctionalTesterState) -> AutonomousFunctionalTesterState:
        """Simple exit node that returns final state"""
        logger.debug("Exiting autonomous functional tester workflow")
        return state