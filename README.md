# Project Brief

With this project, we aim to create a consistent set of system requirements as use cases and their corresponding automated test cases. The automated tests leverage `pytest-bdd` in combination with `boardfarm`.

Capturing requirements in Markdown formatted use cases allows the organization to use Git as the version control system of the requirements, enabling us to treat documentation, test cases and reports with the same collaborative processes as code.
With the standardization of the test interface by Boardfarm, LLMs have a clear reference to translate BDD scenario steps into python code for execution. Pytest-bdd provides a powerful execution and reporting engine in this setup.

<figure style="margin-bottom: 20px;">
    <img src="./docs/Requirements_and_Test_framework.excalidraw.png" alt="Process flow">
    <figcaption>Process Flow</figcaption>
</figure>

Many thanks to Mike Vogel who inspired me to pursue this requirements structure. Please see details of his approach here: [Agile Requirements Framework](https://globallyunique.github.io/agile-requirements-framework/)


*Important note: this project is still very much under development, references mentioned here may not be correct yet....*

## Standards and Conventions

To ensure consistency and portability, this project adheres to the following standards:

-   **Requirements Use Cases:** All use cases are written following the structure defined in the `requirements/template/Use Case Template (reflect the goal).md`.

-   **Step Definition Collection:** All step definitions (the code representing the test step) are collected in one [folder](./tests/step_defs/). This allows all scenarios to leverage the same test step definitions. The objective is to achieve maximum re-use of the test steps.

-   **Step Definition Type Hinting:** All step definitions and fixtures that interact with testbed devices must use Python type hints. These hints should leverage the specific device templates (Abstract Base Classes) provided by `boardfarm`. These templates can be found in the `boardfarm/boardfarm3/templates/` directory and help ensure code quality and maintainability.

-   **Synchronization of Artifacts:** The use case requirement documents (`.md`), BDD scenarios (`.feature`), and step definition implementations (`.py`) must be kept in sync at all times. Any change in logic or abstraction level in one artifact must be propagated to the others to maintain consistency and ensure the documentation accurately reflects the executable tests.

-   **Guarantee Verification Rule:** Each BDD scenario must explicitly check the use case's Success Guarantees on success paths and Minimal Guarantees on use case failure paths, ensuring consistent verification aligned with the requirement specification.


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
