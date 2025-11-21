# Project Brief

With this project, we aim to create a consistent set of system requirements as use cases and their corresponding automated test cases. The automated tests leverage `pytest-bdd` in combination with `boardfarm`.

Capturing requirements in Markdown formatted use cases allows the organization to use Git as the version control system of the requirements, enabling us to treat documentation, test cases and reports with the same collaborative processes as code.
With the standardization of the test interface by Boardfarm, LLMs have a clear reference to translate BDD scenario steps into python code for execution. Pytest-bdd provides a powerful execution and reporting engine in this setup.

![Process Flow](./docs/Requirements_and_Test_framework.excalidraw.png)

Many thanks to Mike Vogel who inspired me to pursue this requirements structure. 
Please see details of his approach here: [Agile Requirements Framework](https://globallyunique.github.io/agile-requirements-framework/)


*Important note: this project is still very much under development, references mentioned here may not be correct yet....*

## Standards and Conventions

To ensure consistency and portability, this project adheres to the following standards:

-   **Requirements Use Cases:** All use cases are written following the structure defined in the `requirements/template/Use Case Template (reflect the goal).md`.

-   **Step Definition Collection:** All step definitions (the code representing the test step) are collected in one [folder](./tests/step_defs/). This allows all scenarios to leverage the same test step definitions. The objective is to achieve maximum re-use of the test steps.

-   **Step Definition Type Hinting:** All step definitions and fixtures that interact with testbed devices must use Python type hints. These hints should leverage the specific device templates (Abstract Base Classes) provided by `boardfarm`. These templates can be found in the `boardfarm/boardfarm3/templates/` directory and help ensure code quality and maintainability.

-   **Synchronization of Artifacts:** The use case requirement documents (`.md`), BDD scenarios (`.feature`), and step definition implementations (`.py`) must be kept in sync at all times. Any change in logic or abstraction level in one artifact must be propagated to the others to maintain consistency and ensure the documentation accurately reflects the executable tests.

-   **Guarantee Verification Rule:** Each BDD scenario must explicitly check the use case's Success Guarantees on success paths and Minimal Guarantees on use case failure paths, ensuring consistent verification aligned with the requirement specification.

-   **Configuration Cleanup Rule:** All step definitions that modify CPE configuration must capture original values before making changes and store them in `bf_context.original_config` using the standardized structure. This enables automatic cleanup after each scenario, ensuring test isolation. See [Configuration Cleanup Process](./docs/Configuration%20Cleanup%20Process.md) for detailed guidelines.


## Test-bed

The networked components for the testbed are arranged using Raikou.
See [Raikou](https://github.com/lgirdk/raikou-factory) for details.
Our testbed is based on [](./raikou/config.json) and [](./raikou/docker-compose.yaml) with details on the component docker files to be found in [](./raikou/components/)

Boardfarm is used to further configure the details where necessary of the component configurations, load files, for instance, on a TFTP server, create settings on a CPE, etc.
The boardfarm configuration files we are using are located at: [](./bf_configs)

A description of the network topology used can be found in [Testbed Network Topology](./docs/Testbed%20Network%20Topology.md)

## Development Workflow

This section outlines the step-by-step process for adding new automated tests to the project, ensuring they align with our standards for quality and maintainability.

### 1. Write the Use Case

The foundation of every test is a well-defined requirement.

-   **Create the File:** Start by creating a new Markdown file in `./requirements/`.
-   **Follow the Template:** Use the structure defined in `./docs/Use Case Template (reflect the goal).md` to ensure all necessary components (Goal, Scope, Actors, Guarantees, etc.) are captured.

### 2. Create BDD Scenarios

Translate the use case into executable specifications.

-   **Create a Feature File:** Add a new `.feature` file in `./tests/features/` that corresponds to the use case.
-   **Write Scenarios:** Using Gherkin syntax (`Given`, `When`, `Then`), write scenarios that cover the Main Success Scenario and all Extensions from the use case document.
-   **Tag Scenarios:** Add tags to each scenario to link it back to the specific section of the use case document (e.g., `@UC-12345-Main`, `@UC-12345-7.a`).
-   **Verify Guarantees:** Ensure the `Then` steps in your scenarios explicitly verify the Success Guarantees (on success paths) and Minimal Guarantees (on failure paths) defined in the use case.

### 3. Prepare the Testbed and Artifacts

Ensure the test environment has all the necessary components and files.

-   **Environment:** The testbed is orchestrated by Raikou and Boardfarm. Make sure that the respective configuration files are in place.
-   **Test Artifacts:** If your test requires specific files (e.g., firmware images, configuration files), place them in the `./tests/test_artifacts/` directory. The step definitions will be responsible for transferring these artifacts to the correct component in the testbed (e.g., copying a firmware image to the TFTP server running on the `wan` container).

### 4. Implement Step Definitions

Write the code that brings the BDD scenarios to life.

-   **Centralized Definitions:** All step definitions are collected in the `./tests/step_defs/` folder. This allows all scenarios to leverage the same test step definitions.
-   **Implement New Steps:** For any new steps in your `.feature` file, create corresponding Python functions decorated with `@given`, `@when`, or `@then` in the appropriate file within the step definitions folder.
-   **Reuse Existing Steps:** Before writing a new function, check if an existing step definition can be reused.
-   **Interact with Devices:** Use the `pytest-boardfarm` fixtures (e.g., `CPE`, `ACS`, `WAN`) to interact with the devices in the testbed.
-   **Use Type Hinting:** Adhere to the project standard of using Python type hints for all fixtures and function arguments to ensure code quality.

### 5. (optional) Install Boardfarm from Local Source

To ensure that any local modifications to the `boardfarm` source code (like bug fixes or custom device drivers) are used during test execution, it must be installed in "editable" mode.

-   **Activate Virtual Environment:** Make sure you have activated the Python virtual environment for the BDD tests (e.g., `source .venv/bin/activate`).
-   **Uninstall Existing Version:** If `boardfarm3` is already installed, remove it first: `pip uninstall -y boardfarm3`
-   **Install in Editable Mode:** From the project root, run the following command: `pip install -e <boardfarm directory>`

This will create a link to the local `boardfarm` directory, so any changes made to the source will be immediately available without needing to reinstall.

## pytest-bdd Test Execution

This section provides practical examples for running pytest-bdd tests with boardfarm testbed integration.

### Required Boardfarm Options

When running tests with the boardfarm testbed, you must include these options:

- `--board-name`: Name of the board configuration to use (e.g., `prplos-docker-1`)
- `--env-config`: Path to the boardfarm environment configuration JSON file
- `--inventory-config`: Path to the boardfarm inventory configuration JSON file
- `--legacy`: Use legacy boardfarm mode
- `--save-console-logs`: Directory to save console logs

### Basic Test Execution

```bash
# Run all tests with boardfarm testbed
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/

# Run tests from a specific feature file
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  tests/features/Remote\ CPE\ Reboot.feature

# Run tests with verbose output and show print statements
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -v -s
```

### Filtering Tests with `-k` Option

The `-k` option allows you to filter tests by matching against test names, scenario names, and tags. You can combine multiple patterns using **boolean operators** (OR, AND, NOT).

> **Note on Scenario Names**: When using `-k` to filter scenarios, the scenario names from the feature file are condensed by removing hyphens and dots. For example:
> - Feature file: `Scenario: UC-12347-Main: Successful Remote Reboot` → Filter: `UC12347Main`
> - Feature file: `Scenario: UC-12347-3.a: CPE Not Connected` → Filter: `UC123473a`
> - Feature file: `Scenario: UC-12347-6.a: CPE Rejects Reboot RPC` → Filter: `UC123476a`

#### Boolean Operators

```bash
# OR operator - matches tests containing EITHER pattern
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347Main or UC123473a"

# AND operator - matches tests containing BOTH patterns
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347 and Main"

# NOT operator - excludes tests matching a pattern
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347 and not UC123473a"
```

#### Examples for Remote CPE Reboot Feature

```bash
# Run only the main scenario
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347Main" -v -s

# Run main scenario AND 3.a extension
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347Main or UC123473a" -v -s

# Run all UC-12347 scenarios
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC12347" -v -s

# Run specific extensions (3.a and 6.a)
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC123473a or UC123476a" -v -s
```

#### Substring Matching

The `-k` option uses substring matching, so you can use partial patterns:

```bash
# Matches all scenarios with "12347" and "a" (all extensions)
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "12347 and a" -v -s

# Matches all reboot-related tests
pytest --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "Reboot" -v -s
```

### Logging and Debugging

```bash
# Enable DEBUG logging for both pytest and test output
pytest --log-level=DEBUG \
  --log-cli-level=DEBUG \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC123473a" -v -s

# Run with HTML report generation
pytest --log-level=DEBUG \
  --log-cli-level=DEBUG \
  --html=report.html \
  --self-contained-html \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC123473a" -v -s
```

### Reporting

```bash
# Generate HTML report with test results
pytest --html=report.html \
  --self-contained-html \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -v -s

# Generate JUnit XML report (for CI/CD integration)
pytest --junitxml=test-results.xml \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -v -s

# Show test durations
pytest --durations=10 \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -v -s
```

### Complete Example

Here's a complete example command that includes all common options:

```bash
pytest --log-level=DEBUG \
  --log-cli-level=DEBUG \
  --html=report.html \
  --self-contained-html \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  -k "UC123473a" \
  -v -s
```
