# pytest-bdd Getting Started

This guide covers how to set up and run pytest-bdd tests with boardfarm integration.

## Installation

Install the pytest-bdd dependencies using the optional dependency group:

```bash
# From project root
pip install -e ".[pytest]"
```

This installs:
- `pytest` - Test framework
- `pytest-bdd` - BDD plugin for pytest
- `pytest-boardfarm3` - Boardfarm integration
- `pytest-html` - HTML report generation
- `pytest-cov` - Coverage reporting

## Project Structure

```
boardfarm-bdd/
├── tests/
│   ├── conftest.py          # Fixtures and pytest-bdd configuration
│   ├── pytest.ini           # pytest settings
│   ├── features/            # Gherkin feature files
│   │   ├── Remote CPE Reboot.feature
│   │   ├── UC-12348 User makes a one-way call.feature
│   │   └── ...
│   ├── step_defs/           # Step definition implementations
│   │   ├── acs_steps.py
│   │   ├── cpe_steps.py
│   │   └── ...
│   └── unit/                # Unit tests for step definitions
│       └── test_step_defs/
└── requirements/            # Use case specifications
```

## Running Tests

### Basic Execution

```bash
# Run all tests with boardfarm testbed
pytest tests/features/ \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json \
    --legacy \
    --save-console-logs=./logs/

# Run from project root (uses pytest.ini settings)
pytest --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json
```

### Running Specific Features

```bash
# Run a specific feature file
pytest tests/features/Remote\ CPE\ Reboot.feature \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json

# Run by scenario name pattern
pytest -k "UC12347Main" \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json
```

### Required Boardfarm Options

| Option | Description | Example |
|--------|-------------|---------|
| `--board-name` | Board configuration name | `prplos-docker-1` |
| `--env-config` | Environment config JSON | `bf_config/boardfarm_env_example.json` |
| `--inventory-config` | Inventory config JSON | `bf_config/boardfarm_config_example.json` |
| `--legacy` | Use legacy boardfarm mode | (flag) |
| `--save-console-logs` | Directory for console logs | `./logs/` |

## Writing Tests

### 1. Create a Feature File

Feature files define test scenarios in Gherkin syntax:

```gherkin
# tests/features/My_Feature.feature
Feature: My Feature Description
  As a user
  I want to do something
  So that I achieve a goal

  Background:
    Given a CPE is online and fully provisioned

  Scenario: UC-XXXXX-Main: Main Success Scenario
    Given some precondition
    When an action is performed
    Then the expected result occurs
```

### 2. Implement Step Definitions

Step definitions translate Gherkin steps to Python code:

```python
# tests/step_defs/my_steps.py
from pytest_bdd import given, when, then, parsers

from boardfarm3.templates.cpe import CPE
from boardfarm3.use_cases import cpe as cpe_use_cases


@given("a CPE is online and fully provisioned")
def cpe_online(cpe: CPE):
    """Verify CPE is online."""
    assert cpe_use_cases.is_online(cpe), "CPE should be online"


@when("an action is performed")
def perform_action(cpe: CPE):
    """Perform the test action."""
    cpe_use_cases.some_operation(cpe)


@then("the expected result occurs")
def verify_result(cpe: CPE):
    """Verify the expected outcome."""
    result = cpe_use_cases.get_result(cpe)
    assert result == expected_value
```

### 3. Use Boardfarm Fixtures

pytest-boardfarm3 provides fixtures for device access:

```python
from boardfarm3.templates.cpe import CPE
from boardfarm3.templates.acs import ACS


def my_step(cpe: CPE, acs: ACS):
    """Access devices via fixtures."""
    # Use devices through use_cases
    from boardfarm3.use_cases import acs as acs_use_cases
    version = acs_use_cases.get_parameter_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )
```

## Architecture

Tests follow the 4-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Feature Files (.feature)                               │
│  - Gherkin scenarios                                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Step Definitions (step_defs/*.py)                      │
│  - Thin wrappers calling use_cases                      │
│  - Use pytest-boardfarm3 fixtures                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  boardfarm3.use_cases                                   │
│  - Reusable test operations                             │
│  - Single source of truth for test logic                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Device Templates                                       │
│  - Low-level device operations                          │
│  - Provided by boardfarm                                │
└─────────────────────────────────────────────────────────┘
```

## Reporting

```bash
# Generate HTML report
pytest --html=report.html --self-contained-html \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json

# Generate JUnit XML (for CI/CD)
pytest --junitxml=test-results.xml \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json
```

## Further Reading

- [Step Migration Guide](../step_migration_guide.md) - How to write step definitions
- [Use Case Architecture](../use_case_architecture.md) - Architecture overview
- [Unit Testing Step Definitions](../../tests/unit/test_step_defs/README.md) - Testing steps
