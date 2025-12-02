# Implementation Plan: Scalable GUI Testing Architecture

## 1. Objective

This document outlines the phased implementation plan for refactoring the `boardfarm` framework and its device classes to adopt the new compositional architecture for scalable UI testing. The goal is to create a standardized, maintainable, and robust system for testing devices with web interfaces.

## 2. Final Architecture Recap

The agreed-upon architecture is a **principled compositional model**:

-   **Generic Components in `lib`**: The `boardfarm/lib/` directory will contain generic, reusable base classes, specifically `BaseGuiHelper` for UI interactions.
-   **Specific Implementations in `devices`**: All vendor-specific logic will reside in the `boardfarm/devices/` directory. Each complex device file will define its interface components (`Nbi`, `Gui`, `Hw`, `Sw`) and assemble them into a final composite device class.
-   **Test-Owned UI Configuration**: All UI selectors (the most volatile part) will be stored in `selectors.yaml` files within the test suite that uses them (e.g., `boardfarm-bdd`). These are treated as test artifacts.

## 3. Phased Implementation Plan

The implementation will proceed in four distinct phases.

---

### Phase 1: Framework Foundation

**Goal**: Build the generic, reusable components that will form the foundation of all UI testing.

**Tasks**:

1.  **Create `BaseGuiComponent` Class**:
    -   [ ] Create a new file: `boardfarm/boardfarm3/lib/gui/base_gui_component.py`.
    -   [ ] Implement the `BaseGuiComponent` class within this file.
    -   **Key functionality**:
        -   Accept an existing Selenium WebDriver instance in its constructor.
        -   Load and parse a `selectors.yaml` file provided in the constructor.
        -   Provide a generic `_get_locator()` method.
    -   [ ] Ensure `gui_helper.py` remains as the primary factory for creating WebDriver instances.

2.  **Create UI Discovery Tools**:
    -   [ ] Create a new directory: `boardfarm/boardfarm3/tools/ui_automation/`.
    -   [ ] Create a discovery script: `discover_ui.py`.
        -   **Key functionality**: Crawls a web UI and generates a detailed JSON map of all pages, elements, and selectors.
    -   [ ] Create a generator script: `generate_selectors.py`.
        -   **Key functionality**: Converts the JSON map from the discovery tool into the clean, human-readable `selectors.yaml` format.

**Deliverables**:
-   `base_gui_helper.py` class.
-   `discover_ui.py` and `generate_selectors.py` command-line tools.

---

### Phase 2: Device Refactoring (Pilot with GenieACS)

**Goal**: Refactor the `GenieACS` device as the first implementation of the new compositional pattern.

**Tasks**:

1.  **Refactor `devices/genie_acs.py`**:
    -   [ ] **Create `GenieAcsNbi` Component**: Create a `GenieAcsNbi` class within the file that inherits from `LinuxDevice` and the `ACS` template. Move all existing NBI-related methods (`Reboot`, `SPV`, `_request_post`, etc.) into this class.
    -   [ ] **Create `GenieAcsGui` Component**: Create a `GenieAcsGui` class that inherits from `BaseGuiHelper`. Add specific action methods like `login()` and `click_reboot_button()` that use the inherited `_get_locator` method.
    -   [ ] **Create Composite `GenieACS` Class**: Redefine the main `GenieACS` class to be a composite container.
        -   It should instantiate `GenieAcsNbi` in its constructor as `self.nbi`.
        -   It should define the `init_gui(selector_file)` factory method to instantiate and return the `GenieAcsGui` component.

**Deliverables**:
-   A fully refactored `boardfarm/boardfarm3/devices/genie_acs.py` file that clearly shows the three-class (`Nbi`, `Gui`, `Composite`) structure.

---

### Phase 3: Test Suite Integration (Pilot with `boardfarm-bdd`)

**Goal**: Validate the new architecture by integrating it into the `boardfarm-bdd` test suite for a real test case.

**Tasks**:

1.  **Generate Selector Artifact**:
    -   [ ] Use the new `discover_ui.py` and `generate_selectors.py` tools to create the first `acs_selectors.yaml` file.
    -   [ ] Place this file in `boardfarm-bdd/tests/ui_helpers/acs_selectors.yaml` and commit it.

2.  **Refactor BDD Test**:
    -   [ ] Choose a simple UI-based test scenario (e.g., "Reboot via UI").
    -   [ ] Remove any old UI testing fixtures from `conftest.py` if they exist.
    -   [ ] Update the step definition to use the new compositional pattern:
        1.  Get the `acs` device fixture (which is now the composite `GenieACS` object).
        2.  Call `acs.init_gui(selector_file="path/to/acs_selectors.yaml")` to get the configured GUI component.
        3.  Use the returned `gui` object to perform UI actions (`gui.login()`, etc.).

3.  **Validate**:
    -   [ ] Run the refactored test and ensure it passes, confirming that the entire architecture works end-to-end.

**Deliverables**:
-   A version-controlled `acs_selectors.yaml` file in the `boardfarm-bdd` repository.
-   An updated BDD step definition file demonstrating the new testing pattern.
-   A successful test run.

---

### Phase 4: Expansion and Full Automation

**Goal**: Apply the new pattern to other devices and automate the maintenance workflow.

**Tasks**:

1.  **Refactor Other Devices**:
    -   [ ] Apply the same compositional pattern to `AxirosACS`, creating `AxirosAcsNbi` and `AxirosAcsGui` (inherits from `BaseGuiComponent`) components.
    -   [ ] Apply the pattern to `prplos_cpe`, creating `PrplosGui` (inherits from `BaseGuiComponent`) to complement the existing `PrplOSx86HW` and `PrplOSSW` components.

2.  **Implement CI/CD Workflow**:
    -   [ ] Create a new CI workflow (e.g., GitHub Actions) in the `boardfarm-bdd` repository.
    -   [ ] The workflow should run on a schedule (e.g., nightly).
    -   [ ] **Workflow steps**:
        1.  Run `discover_ui.py` against a staging environment to get a `current_ui.json`.
        2.  Run a `ui_change_detector.py` tool to compare this against a committed `baseline_ui.json`.
        3.  If changes are detected, run `generate_selectors.py` to create an updated `acs_selectors.yaml`.
        4.  Automatically create a pull request with the updated YAML file and the change report.

**Deliverables**:
-   Refactored `AxirosACS` and `prplos_cpe` device classes.
-   A fully functional CI workflow that automates UI test maintenance.

---
## 4. Timeline (Suggested)

-   **Week 1**: Complete Phase 1.
-   **Week 2**: Complete Phase 2.
-   **Week 3**: Complete Phase 3.
-   **Week 4-5**: Begin Phase 4, starting with device refactoring.
-   **Week 6**: Implement and test the CI/CD automation workflow.
