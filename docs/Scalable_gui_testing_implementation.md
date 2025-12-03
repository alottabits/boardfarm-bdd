# Implementation Plan: Scalable GUI Testing Architecture

## 1. Objective

This document outlines the phased implementation plan for refactoring `boardfarm` to adopt the "Flat Name" compositional architecture for scalable and maintainable UI testing.

## 2. Final Architecture Recap

-   **Generic Components in `lib`**: `BaseGuiComponent` will be a simple engine that executes uniquely named paths.
-   **Specific Implementations in `devices`**: `GenieAcsGui` will contain device-specific actions (e.g., `click_reboot_button`) and inherit the generic `navigate_path` engine.
-   **Test-Owned UI Configuration**: `selectors.yaml` will map element names, and `navigation.yaml` will map unique, descriptive path names (e.g., `Path_Home_to_DeviceDetails_via_Search`) to their step-by-step implementation.
-   **BDD Scenarios**: The `.feature` files will explicitly reference the full path name to make the test's intent clear.

## 3. Phased Implementation Plan

---

### Phase 1: Framework Foundation

**Goal**: Build the generic `BaseGuiComponent` and the tools to generate the YAML artifacts.

**Tasks**:

1.  **Create `BaseGuiComponent` Class**:
    -   [ ] Create `boardfarm/boardfarm3/lib/gui/base_gui_component.py`.
    -   [ ] Implement the `BaseGuiComponent` to load both `selectors.yaml` and `navigation.yaml`.
    -   [ ] Implement the generic `navigate_path(path_name)` method to execute a named path.

2.  **Create UI Discovery & Pathfinding Tools**:
    -   [ ] Create a `ui_discovery.py` tool to generate the `ui_map.json`.
    -   [ ] Create a `path_analyzer.py` tool that loads the `ui_map.json` and finds all possible paths between two points.
    -   [ ] Create a `navigation_generator.py` tool that takes the output of the path analyzer and generates the `navigation.yaml` entries with descriptive "Flat Names".

---

### Phase 2: Device Refactoring (Pilot with GenieACS)

**Goal**: Refactor `GenieACS` to be the first implementation of the new pattern.

**Tasks**:

1.  **Refactor `devices/genie_acs.py`**:
    -   [ ] **Create `GenieAcsNbi` Component** (as before).
    -   [ ] **Create `GenieAcsGui` Component**: This class will inherit from `BaseGuiComponent` and contain only device-specific UI actions (like `click_reboot_button`). It will *not* contain high-level navigation logic.
    -   [ ] **Create Composite `GenieACS` Class**: This will assemble the `nbi` and `gui` components and include the `init_gui(...)` factory method.

---

### Phase 3: Test Suite Integration (Pilot with `boardfarm-bdd`)

**Goal**: Validate the architecture end-to-end with a real BDD test case.

**Tasks**:

1.  **Generate UI Artifacts**:
    -   [ ] Use the new `path_analyzer.py` and `navigation_generator.py` tools to create the first `acs_navigation.yaml` with descriptive path names.
    -   [ ] Commit `acs_selectors.yaml` and `acs_navigation.yaml` to the repo.

2.  **Refactor BDD Test**:
    -   [ ] Create a `.feature` file with a `Scenario Outline` that uses the unique path names from the new `navigation.yaml`.
    -   [ ] Implement a simple `given` step that calls `gui.navigate_path(path_name)`, passing the name from the Gherkin step directly to the engine.

3.  **Validate**:
    -   [ ] Run the test and ensure it passes.

---

### Phase 4: Expansion and Full Automation

**Goal**: Apply the pattern to other devices and automate the maintenance workflow.

**Tasks**:

1.  **Refactor Other Devices**:
    -   [ ] Apply the pattern to `AxirosACS` and `prplos_cpe`.

2.  **Implement CI/CD Workflow**:
    -   [ ] Create a CI workflow that runs `ui_discovery.py` and `ui_change_detector.py`.
    -   [ ] If changes are detected, the workflow should automatically run `navigation_generator.py` to suggest updates to `navigation.yaml` and create a pull request for human review.
