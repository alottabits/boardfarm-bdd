# Project Brief

With this project, we aim to create a consistent set of system requirements as use cases and their corresponding automated test cases. The automated tests leverage `pytest-bdd` in combination with `boardfarm`.

## Standards and Conventions

To ensure consistency and portability, this project adheres to the following standards:

-   **Requirements Use Cases:** All use cases are written following the structure defined in the `requirements/template/Use Case Template (reflect the goal).md`.

-   **Step Definition Collection:** All step definitions are collected in one file. This allows all scenarios to leverage the same test setp definitions. The objective is to achieve maximum re-use of the test steps.

-   **Step Definition Type Hinting:** All step definitions and fixtures that interact with testbed devices must use Python type hints. These hints should leverage the specific device templates (Abstract Base Classes) provided by `boardfarm`. These templates can be found in the `boardfarm/boardfarm3/templates/` directory and help ensure code quality and maintainability.

-   **Synchronization of Artifacts:** The use case requirement documents (`.md`), BDD scenarios (`.feature`), and step definition implementations (`.py`) must be kept in sync at all times. Any change in logic or abstraction level in one artifact must be propagated to the others to maintain consistency and ensure the documentation accurately reflects the executable tests.

-   **Guarantee Verification Rule:** Each BDD scenario must explicitly check the use case's Success Guarantees on success paths and Minimal Guarantees on failure paths, ensuring consistent verification aligned with the requirement specification.

## Test-bed

The networked components for the testbed are arranged for with Raikou
See [Raikou](https://github.com/lgirdk/raikou-factory) for details
Our testbed is based on [](./raikou/config.json) and [](./raikou/docker-compose.yaml) with details on the component docker files to be found in [](./raikou/components/)

Boardfarm is used to further configure the details where necessary of the component configurations, load files for instance on a TFPT server, create settings on a CPE etc.
The boardfarm configuration files we are using are located at: [](./bf_configs)


## Development Workflow

This section outlines the step-by-step process for adding new automated tests to the project, ensuring they align with our standards for quality and maintainability.

### 1. Write the Use Case

The foundation of every test is a well-defined requirement.

-   **Create the File:** Start by creating a new Markdown file in `boardfarm-tests/bdd/requirements/Requirements_Use_Cases/`.
-   **Follow the Template:** Use the structure defined in `bdd/requirements/Use Case Template (reflect the goal).md` to ensure all necessary components (Goal, Scope, Actors, Guarantees, etc.) are captured.

### 2. Create BDD Scenarios

Translate the use case into executable specifications.

-   **Create a Feature File:** Add a new `.feature` file in `boardfarm-tests/bdd/tests/features/` that corresponds to the use case.
-   **Write Scenarios:** Using Gherkin syntax (`Given`, `When`, `Then`), write scenarios that cover the Main Success Scenario and all Extensions from the use case document.
-   **Tag Scenarios:** Add tags to each scenario to link it back to the specific section of the use case document (e.g., `@UC-12345-Main`, `@UC-12345-7.a`).
-   **Verify Guarantees:** Ensure the `Then` steps in your scenarios explicitly verify the Success Guarantees (on success paths) and Minimal Guarantees (on failure paths) defined in the use case.

### 3. Prepare the Testbed and Artifacts

Ensure the test environment has all the necessary components and files.

-   **Environment:** The testbed is orchestrated by Raikou, using the configurations in `raikou/examples/double_hop/`. The boardfarm inventory at `boardfarm-tests/bdd/test_infra/bf_configs/boardfarm_config_example.json` defines how boardfarm connects to these components.
-   **Test Artifacts:** If your test requires specific files (e.g., firmware images, configuration files), place them in the `boardfarm-tests/bdd/test_infra/` directory. The step definitions will be responsible for transferring these artifacts to the correct component in the testbed (e.g., copying a firmware image to the TFTP server running on the `wan` container).

### 4. Implement Step Definitions

Write the code that brings the BDD scenarios to life.

-   **Centralized Definitions:** All step definitions are located in a single file: `boardfarm-tests/bdd/tests/conftest.py`.
-   **Implement New Steps:** For any new steps in your `.feature` file, create corresponding Python functions decorated with `@given`, `@when`, or `@then`.
-   **Reuse Existing Steps:** Before writing a new function, check if an existing step definition can be reused.
-   **Interact with Devices:** Use the `pytest-boardfarm` fixtures (e.g., `CPE`, `ACS`, `WAN`) to interact with the devices in the testbed.
-   **Use Type Hinting:** Adhere to the project standard of using Python type hints for all fixtures and function arguments to ensure code quality.

### 5. Install Boardfarm from Local Source

To ensure that any local modifications to the `boardfarm` source code (like bug fixes or custom device drivers) are used during test execution, it must be installed in "editable" mode.

-   **Activate Virtual Environment:** Make sure you have activated the Python virtual environment for the BDD tests (e.g., `source .venv/bin/activate`).
-   **Uninstall Existing Version:** If `boardfarm3` is already installed, remove it first: `pip uninstall -y boardfarm3`
-   **Install in Editable Mode:** From the project root, run the following command: `pip install -e boardfarm/`

This will create a link to the local `boardfarm` directory, so any changes made to the source will be immediately available without needing to reinstall.

## Build System & Environment Notes

This section documents key lessons learned from debugging the Docker Compose build process for the Raikou testbed.

-   **Debian Buster Dependencies**:
    -   The `wan` container **must** use `debian:buster-20220316-slim`. The `aftr` package it contains fails to compile on newer Debian releases (e.g., Bookworm) due to kernel incompatibilities.
    -   Any Dockerfile using a `buster` base image must modify its `sources.list` to point to the Debian archives, as the standard repositories are no longer active. Example:
        ```dockerfile
        RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
            sed -i 's|security.debian.org|archive.debian.org|g' /etc/apt/sources.list && \
            sed -i '/buster-updates/d' /etc/apt/sources.list
        ```

-   **Docker Compose Build Order**:
    -   The testbed containers depend on a locally-built base image (`ssh:v1.2.0`). Docker Compose may incorrectly try to pull this from Docker Hub instead of building it first, causing a race condition and "pull access denied" errors.
    -   **Solution**: Always use a two-step build process:
        1.  Build the base SSH image first: `docker compose -f <compose-file> build ssh`
        2.  Build and start the rest of the services: `docker compose -f <compose-file> up -d --build`

-   **Bash in Slim Images**:
    -   The `debian:bookworm-slim` image (and other `slim` variants) does **not** include `/bin/bash`.
    -   Be vigilant for scripts that use a `#!/bin/bash` shebang. This includes not just `ENTRYPOINT` or `CMD` scripts, but also any helper scripts they might call (e.g., `isolate_docker_iface`).
    -   If bash is required, use the full `debian:bookworm` base image instead of the `slim` variant.

-   **Persistent Caching Issues**:
    -   During debugging, the build process encountered a persistent `spawn /bin/bash ENOENT` error that was not resolved by fixing Dockerfiles or scripts.
    -   This indicated a deeply corrupted Docker cache. The `docker builder prune` command was not sufficient to fix it.
    -   **Solution**: If you encounter inexplicable and persistent build errors, perform a full manual cleanup:
        1.  Delete all containers (`docker rm -f $(docker ps -a -q)`)
        2.  Delete all Docker images (`docker rmi -f $(docker images -a -q)`)
        3.  Prune the build cache (`docker builder prune -a`)
        4.  Rebuild the testbed from scratch using the two-step process described above.

