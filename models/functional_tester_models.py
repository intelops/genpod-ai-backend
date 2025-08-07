"""
Data models for the Functional Tester agent.

This module defines the data structures used by the Functional Tester agent
for generating functional and integration tests.
"""
import os
from typing import Dict, List, Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TestScenarioType(str, Enum):
    """Types of functional test scenarios."""
    E2E = "end_to_end"
    INTEGRATION = "integration"
    API = "api"
    UI = "ui"
    WORKFLOW = "workflow"


class TestStep(BaseModel):
    """Represents a single step in a test scenario."""
    
    step_number: int = Field(
        description="Sequential number of this step in the scenario",
        ge=1
    )
    
    action: str = Field(
        description="The action to be performed in this step",
        min_length=5,
        example="Click on the login button"
    )
    
    expected_result: str = Field(
        description="The expected outcome after performing the action",
        min_length=5,
        example="Login form should be displayed with username and password fields"
    )
    
    test_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Test data required for this step",
        example={"username": "test_user", "password": "test_pass123"}
    )
    
    assertions: List[str] = Field(
        default_factory=list,
        description="List of assertions to validate the expected result",
        example=["assert login_form.is_displayed()", "assert username_field.is_enabled()"]
    )


class TestScenario(BaseModel):
    """Represents a complete functional test scenario."""
    
    scenario_id: str = Field(
        description="Unique identifier for this scenario",
        pattern="^[a-zA-Z][a-zA-Z0-9_-]*$",
        example="user_login_success"
    )
    
    scenario_name: str = Field(
        description="Human-readable name for the scenario",
        min_length=5,
        example="Successful User Login"
    )
    
    scenario_type: TestScenarioType = Field(
        description="Type of functional test scenario",
        example=TestScenarioType.E2E
    )
    
    description: str = Field(
        description="Detailed description of what this scenario tests",
        min_length=20,
        example="Validates that a registered user can successfully log in with valid credentials"
    )
    
    preconditions: List[str] = Field(
        default_factory=list,
        description="Prerequisites that must be met before running this scenario",
        example=["User account exists in database", "Application is running"]
    )
    
    test_steps: List[TestStep] = Field(
        description="Sequential steps to execute this scenario",
        min_items=1
    )
    
    postconditions: List[str] = Field(
        default_factory=list,
        description="Expected state after scenario completion",
        example=["User is logged in", "User dashboard is displayed"]
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing and filtering scenarios",
        example=["authentication", "smoke", "critical"]
    )


class FunctionalTestSuite(BaseModel):
    """Represents a collection of test scenarios for a feature or module."""
    
    suite_name: str = Field(
        description="Name of the test suite",
        min_length=3,
        example="Authentication Test Suite"
    )
    
    feature_under_test: str = Field(
        description="The feature or module being tested",
        min_length=3,
        example="User Authentication"
    )
    
    test_scenarios: List[TestScenario] = Field(
        description="List of test scenarios in this suite",
        min_items=1
    )
    
    setup_steps: List[str] = Field(
        default_factory=list,
        description="Common setup steps for all scenarios in this suite",
        example=["Initialize test database", "Start application server"]
    )
    
    teardown_steps: List[str] = Field(
        default_factory=list,
        description="Common cleanup steps after all scenarios",
        example=["Clear test data", "Stop application server"]
    )


class TestFrameworkConfig(BaseModel):
    """Configuration for the functional test framework."""
    
    framework: str = Field(
        description="Test framework to use",
        example="pytest"
    )
    
    test_runner_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for the test runner",
        example={"parallel": True, "workers": 4, "timeout": 300}
    )
    
    environment_config: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables and configuration",
        example={"BASE_URL": "http://localhost:8000", "DB_NAME": "test_db"}
    )
    
    browser_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Browser configuration for UI tests",
        example={"browser": "chrome", "headless": True, "window_size": "1920x1080"}
    )
    
    api_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="API configuration for API tests",
        example={"base_url": "http://api.example.com", "timeout": 30, "verify_ssl": True}
    )
    
    reporting_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Test reporting configuration",
        example={"format": "html", "output_dir": "reports/", "include_screenshots": True}
    )


class FunctionalTestCode(BaseModel):
    """Generated functional test code with metadata."""
    
    test_files: Dict[str, str] = Field(
        description="Dictionary mapping file paths to test code content",
        example={
            "/tests/functional/test_authentication.py": "import pytest\n\ndef test_login():\n    pass"
        }
    )
    
    config_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Configuration files for the test framework",
        example={
            "/tests/conftest.py": "import pytest\n\n@pytest.fixture\ndef browser():\n    pass"
        }
    )
    
    helper_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Helper utilities and page objects",
        example={
            "/tests/pages/login_page.py": "class LoginPage:\n    pass"
        }
    )
    
    data_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Test data files",
        example={
            "/tests/data/users.json": '{"test_user": {"username": "test", "password": "pass123"}}'
        }
    )
    
    commands_to_execute: Dict[str, str] = Field(
        default_factory=dict,
        description="Commands to set up and run the tests",
        example={
            "/tests/": "pip install -r requirements.txt",
            "/tests/functional/": "pytest -v --html=report.html"
        }
    )
    
    @field_validator('test_files')
    def validate_test_files(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that test files have proper paths and content."""
        if not v:
            raise ValueError("At least one test file must be generated")
            
        for file_path, content in v.items():
            if not os.path.isabs(file_path):
                raise ValueError(f"'{file_path}' must be an absolute path")
            if not content.strip():
                raise ValueError(f"Test file '{file_path}' cannot be empty")
                
        return v


class FunctionalTestGenerationOutput(BaseModel):
    """Complete output from functional test generation."""
    
    test_suites: List[FunctionalTestSuite] = Field(
        description="Generated test suites with scenarios",
        min_items=1
    )
    
    test_code: FunctionalTestCode = Field(
        description="Generated test code files"
    )
    
    framework_config: TestFrameworkConfig = Field(
        description="Test framework configuration"
    )
    
    execution_plan: List[str] = Field(
        default_factory=list,
        description="Step-by-step plan for executing the tests",
        example=[
            "1. Install test dependencies",
            "2. Set up test environment",
            "3. Run smoke tests",
            "4. Run full test suite",
            "5. Generate test report"
        ]
    )