"""Functional Tester Prompts

Defines prompts for functional test generation.
"""

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, RagInstructionsPrompt, PromptTemplateAdapter
from models.functional_tester_models import FunctionalTestSuite, FunctionalTestCode, TestFrameworkConfig
from utils.decorators import auto_repr


@auto_repr
class FunctionalTesterPrompts:
    """
    Prompts for functional test generation using language models.
    """

    def __init__(self, use_rag: bool = False):
        """
        Initialize the functional tester prompts.
        
        Args:
            use_rag (bool): Whether to use RAG for prompt enhancement.
        """
        self.use_rag = use_rag
        self._init_prompts()

    def _init_prompts(self):
        """Initialize all prompt objects"""
        # Scenario generation prompt
        scenario_template = PromptTemplate(
            template=self._get_scenario_generation_template(),
            input_variables=[
                'project_name',
                'project_path', 
                'requirements_document',
                'task',
                'error_message'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=FunctionalTestSuite
                ).get_format_instructions()
            }
        )
        self.scenario_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(scenario_template),
            use_rag=self.use_rag
        )

        # Test code generation prompt
        test_code_template = PromptTemplate(
            template=self._get_functional_test_generation_template(),
            input_variables=[
                'project_name',
                'project_path',
                'requirements_document',
                'task',
                'test_scenarios',
                'error_message'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=FunctionalTestCode
                ).get_format_instructions()
            }
        )
        self.functional_test_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(test_code_template),
            use_rag=self.use_rag
        )

        # Test code prompt (alias for compatibility)
        self.functional_test_code_prompt = self.functional_test_generation_prompt

        # Config generation prompt
        config_template = PromptTemplate(
            template=self._get_test_config_generation_template(),
            input_variables=[
                'project_name',
                'project_path',
                'requirements_document',
                'test_code_summary',
                'error_message'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TestFrameworkConfig
                ).get_format_instructions()
            }
        )
        self.test_config_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(config_template),
            use_rag=self.use_rag
        )

        # Framework detection prompt
        framework_detection_template = PromptTemplate(
            template=self._get_framework_detection_template(),
            input_variables=['project_name', 'project_path']
        )
        self.framework_detection_prompt = Prompt(
            adapter=PromptTemplateAdapter(framework_detection_template)
        )

        # Learning from codebase prompt  
        learning_template = PromptTemplate(
            template=self._get_learning_template(),
            input_variables=['project_name', 'project_path']
        )
        self.learning_prompt = Prompt(
            adapter=PromptTemplateAdapter(learning_template)
        )

        # Best practices prompt
        best_practices_template = PromptTemplate(
            template=self._get_best_practices_template(),
            input_variables=['tech_stack']
        )
        self.best_practices_prompt = Prompt(
            adapter=PromptTemplateAdapter(best_practices_template)
        )

    def _get_scenario_generation_template(self) -> str:
        """Generate test scenarios based on requirements."""
        return """You are an expert QA engineer specializing in functional and integration testing.

Project Name: {project_name}
Project Path: {project_path}

Requirements Document:
{requirements_document}

Task Description:
{task}

Previous Error (if any):
{error_message}

Generate a comprehensive FunctionalTestSuite that validates the functionality from an end-user perspective.

The test suite should include:
1. suite_name: A descriptive name for this test suite
2. feature_under_test: The main feature or module being tested
3. test_scenarios: A list of TestScenario objects, each containing:
   - scenario_id: Unique identifier (e.g., "user_login_success")
   - scenario_name: Human-readable name
   - scenario_type: One of [e2e, integration, api, ui, workflow]
   - description: What this scenario validates
   - preconditions: Prerequisites before running
   - test_steps: List of TestStep objects with:
     - step_number: Sequential number
     - action: What to do
     - expected_result: What should happen
     - test_data: Any required test data
     - assertions: List of assertions to validate
   - postconditions: Expected state after completion
   - tags: Categories like ["smoke", "critical", "regression"]
4. setup_steps: Common setup for all scenarios
5. teardown_steps: Common cleanup steps

Focus on:
- Complete user workflows and journeys
- Integration points between components
- Both happy paths and edge cases
- Error handling and boundary conditions
- Performance and security considerations where applicable

Generate scenarios that thoroughly validate the feature works correctly from the user's perspective.
"""

    def _get_functional_test_generation_template(self) -> str:
        """Generate functional test code based on scenarios."""
        return """You are an expert test automation engineer.

Project Name: {project_name}
Project Path: {project_path}

Requirements Document:
{requirements_document}

Task Description:
{task}

Test Scenarios:
{test_scenarios}

Previous Error (if any):
{error_message}

Generate a FunctionalTestCode object containing complete, production-ready functional test code.

IMPORTANT: Be completely framework-agnostic and adaptive:

IF existing test patterns are found:
- Follow the project's existing conventions and style
- Use the same testing frameworks and libraries
- Match the existing test structure and naming patterns
- Maintain consistency with current test organization

IF NO existing test patterns are found:
- Analyze the project's technology stack (language, frameworks, build tools)
- Research and recommend the current best practices for that stack
- Choose the most suitable modern testing framework
- Establish clean, maintainable patterns for future tests
- Consider: ease of use, community support, CI/CD integration, and performance

For example:
- Node.js project → Consider Jest, Mocha, or Vitest based on 2024 best practices
- Python project → Consider pytest, unittest, or newer alternatives
- Java project → Consider JUnit 5, TestNG, or emerging frameworks
- Always prefer modern, actively maintained frameworks

The output should include:
1. test_files: Dictionary mapping file paths to test code
   - Adapt to the project's existing test framework and patterns
   - Follow detected naming conventions and directory structure
   - Implement all test scenarios using project-appropriate methods
   - Match the project's code style and documentation patterns
   
2. config_files: Configuration files needed
   - pytest.ini or similar test runner config
   - conftest.py with fixtures and hooks
   - Environment configuration files
   
3. helper_files: Support utilities
   - Page objects for UI tests
   - API client wrappers
   - Test data builders
   - Common utility functions
   
4. data_files: Test data files
   - JSON/YAML files with test data
   - CSV files for data-driven tests
   - Mock response files
   
5. commands_to_execute: Setup and execution commands
   - Dependency installation
   - Environment setup
   - Test execution commands

Adaptive practices:

When existing patterns exist:
- Detect and follow the project's test patterns exactly
- Use the same assertion libraries and helpers
- Match error handling and logging approaches
- Follow naming conventions precisely
- Maintain test organization consistency

When NO patterns exist (greenfield):
- Research current best practices for the detected tech stack
- Choose modern, well-supported testing frameworks
- Establish clear naming conventions (e.g., *.test.ts for TypeScript, test_*.py for Python)
- Create maintainable test structure for future developers
- Add helpful comments explaining the chosen approach
- Include setup documentation for the testing framework

Always:
- Ensure tests are independent and can run in any order
- Make tests readable and self-documenting
- Consider CI/CD pipeline integration
- Optimize for both developer experience and test performance

Generate test code that either seamlessly integrates with existing patterns OR establishes 
excellent patterns for a new test suite, based on current industry best practices.
"""

    def _get_test_config_generation_template(self) -> str:
        """Generate test framework configuration."""
        return """You are an expert in test automation frameworks and configuration.

Project Name: {project_name}
Project Path: {project_path}

Requirements Document:
{requirements_document}

Generated Test Code Summary:
{test_code_summary}

Previous Error (if any):
{error_message}

Generate a TestFrameworkConfig object that adapts to the project's existing setup.

IMPORTANT: Detect and adapt to the project's existing configuration:
- Check for existing test configurations (pytest.ini, jest.config.js, etc.)
- Detect CI/CD configurations (.github/workflows, .gitlab-ci.yml, etc.)
- Identify environment variable patterns
- Match existing configuration structure

The configuration should include:

1. framework: The detected or most suitable test framework for this project

2. test_runner_config: Runner-specific settings
   - parallel: Enable parallel execution
   - workers: Number of parallel workers
   - timeout: Test timeout in seconds
   - retry_count: Number of retries for failed tests
   - verbose: Logging verbosity level

3. environment_config: Environment variables and settings
   - BASE_URL: Application base URL
   - API_BASE_URL: API endpoint base
   - DB_CONNECTION: Test database connection
   - TEST_ENV: Environment name (dev/staging/prod)
   - LOG_LEVEL: Application log level

4. browser_config: For UI tests (if applicable)
   - browser: Browser type (chrome/firefox/safari)
   - headless: Run in headless mode
   - window_size: Browser window dimensions
   - implicit_wait: Default wait timeout
   - screenshot_on_failure: Capture screenshots
   - video_recording: Enable video recording

5. api_config: For API tests (if applicable)
   - base_url: API base URL
   - timeout: Request timeout
   - verify_ssl: SSL verification
   - headers: Default headers
   - auth_type: Authentication method

6. reporting_config: Test reporting settings
   - format: Report format (html/xml/json)
   - output_dir: Report output directory
   - include_screenshots: Include screenshots in report
   - include_logs: Include test logs
   - email_notifications: Email report settings
   - metrics_collection: Performance metrics

Consider:
- Environment-specific configurations
- Security best practices (no hardcoded credentials)
- Performance optimization settings
- Integration with CI/CD tools
- Test data management strategies
- Cleanup and teardown procedures

Generate configuration that makes the tests reliable, scalable, and easy to maintain.
"""

    def _get_scenario_generation_for_issue_template(self) -> str:
        """Generate updated test scenarios for resolving issues."""
        return """You are an expert QA engineer helping to resolve functional test issues.

File Content:
{file_content}

Issue Details:
{issue_details}

Project Name: {project_name}
Project Path: {project_path}

Requirements Document:
{requirements_document}

Previous Error (if any):
{error_message}

Analyze the issue and generate updated test scenarios that:
1. Address the reported problem
2. Improve test coverage
3. Handle edge cases that were missed
4. Ensure proper validation

Provide updated scenarios with clear improvements.
"""

    def _get_framework_detection_template(self) -> str:
        """Detect testing frameworks in the project."""
        return """Analyze this project and detect testing frameworks and patterns.

Project: {project_name}
Path: {project_path}

Look for:
1. Test framework dependencies (package.json, requirements.txt, pom.xml, etc.)
2. Existing test file patterns and conventions
3. Test runner configurations
4. CI/CD test commands
5. Code style and conventions

Return a JSON with:
- detected_frameworks: List of testing frameworks found
- test_patterns: Existing test file patterns
- conventions: Project-specific conventions
- recommended_approach: Best approach for new tests
"""

    def _get_learning_template(self) -> str:
        """Learn from existing tests in the codebase."""
        return """Analyze existing tests in this project to learn patterns and conventions.

Project: {project_name}
Path: {project_path}

Find and analyze:
1. Existing test files (look for common patterns like *test*, *spec*, test_*, etc.)
2. Test structure and organization
3. Assertion patterns and matchers used
4. Mocking/stubbing approaches
5. Test data management patterns
6. Common test utilities and helpers

Return JSON insights about:
- Test file naming conventions
- Test method/function patterns
- Common test setup/teardown patterns
- Assertion styles
- Any project-specific test utilities
"""

    def _get_best_practices_template(self) -> str:
        """Get modern best practices for a tech stack."""
        return """Recommend modern testing best practices for this technology stack.

Technology Stack: {tech_stack}
Year: 2024

Provide recommendations for:
1. Best testing framework(s) currently popular and well-maintained
2. Recommended project structure for tests
3. Naming conventions
4. Essential testing utilities/libraries
5. CI/CD integration approach

Return JSON with specific, actionable recommendations.
"""

    def _get_functional_test_generation_for_issue_template(self) -> str:
        """Generate updated functional test code for resolving issues."""
        return """You are an expert test automation engineer resolving test issues.

File Content:
{file_content}

Issue Details:
{issue_details}

Project Name: {project_name}
Project Path: {project_path}

Requirements Document:
{requirements_document}

Updated Test Scenarios:
{test_scenarios}

Previous Error (if any):
{error_message}

Generate updated functional test code that:
1. Fixes the identified issues
2. Implements the updated scenarios
3. Improves test reliability
4. Adds better error handling
5. Enhances test maintainability

Provide corrected and improved test code.
"""