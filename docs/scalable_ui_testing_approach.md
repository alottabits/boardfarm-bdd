# A Compositional Architecture for Scalable UI Testing

## Problem Statement

UI-based testing is notoriously brittle due to frequent changes in the presentation layer. This proposal adopts a standardization of the test interfaces while supporting the dynamic nature of the UI presentation layer. This includes the make-up of the pages as well as the possible navigation paths the UI supports.

## Recommended Architecture: Principled Composition and Convention

We will adopt a compositional pattern that aligns with the project's existing conventions: generic libraries in `lib`, and specific implementations in `devices`.

### Core Architectural Principles

1. **Generic Components in `lib`**: The `boardfarm/boardfarm3/lib/` directory contains generic, reusable components. For UI testing, this includes a `BaseGuiHelper`.
2. **Specific Implementations in `devices`**: The `boardfarm/boardfarm3/devices/` directory contains vendor-specific implementations. For a given device, this file will contain:
   * A specific **NBI/API component class** (e.g., `GenieAcsNbi`).
   * A specific **GUI component class** (e.g., `GenieAcsGui`), which inherits from `BaseGuiHelper`.
   * The final **composite device class** (e.g., `GenieACS`) assembled from these components.
3. **Decouple UI Artifacts**: The `gui` component is always configured by two files that live in the test suite as test artifacts:
   * `selectors.yaml`: A map of human-readable names to specific element locators. This decouples the tests from CSS selectors, IDs, or XPaths.
   * `navigation.yaml`: A map of unique, self-documenting path names to a specific, multi-step user journey.

## Decoupling Navigation from Actions: The Two-Artifact System

To achieve maximum flexibility and maintainability, we separate the "what" from the "how".

- **`selectors.yaml` (The "What")**: This artifact maps a name to a specific UI element. It is a dictionary of locators.
- **`navigation.yaml` (The "How")**: This artifact maps a unique, self-documenting path name to a specific, multi-step user journey.

The path names in `navigation.yaml` are designed to be descriptive and unique, acting as the key that links a BDD scenario's intent to a concrete implementation.

A typical `selector.yaml` is organized by page:
```yaml
# boardfarm-bdd/tests/ui_helpers/acs_selectors.yaml
home_page:
  main_menu:
    devices_link:
      by: "id"
      selector: "devices-menu-item"

device_list_page:
  search_bar:
    by: "css_selector"
    selector: "input.search"
  first_row_link:
    by: "xpath"
    selector: "//tbody/tr[1]/td[1]/a"

device_details_page:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"
```

A typical `navigation.yaml` now uses descriptive, unique names for each path:
```yaml
# boardfarm-bdd/tests/ui_helpers/acs_navigation.yaml
navigation_paths:

  # Path 1: The most direct route via the main menu and search
  Path_Home_to_DeviceDetails_via_Search:
    - action: click
      target: main_menu.devices_link
    - action: type
      target: device_list.search_bar
      value: "{{ cpe_id }}"
    - action: click
      target: device_list.first_row_link

  # Path 2: An alternative route via a "Recent Devices" dashboard widget
  Path_Home_to_DeviceDetails_via_DashboardWidget:
    - action: click
      target: home_page.dashboard_widget.first_device_link
```

### `selectors.yaml`: Structure and Best Practices

To ensure the artifacts are clear and scalable, we follow a strict convention for `selectors.yaml`:

1.  **Pages as Top-Level Keys**: The file is organized by pages or major, reusable components. Each top-level key represents a page (e.g., `login_page`, `home_page`).
2.  **Locators Only**: The sole purpose of this file is to map a name to a locator (`by` and `selector`). It should **never** contain behavioral information like `navigates_to` or other logic. This enforces a strict separation of concerns.

This structure allows for clear, dot-notated references (e.g., `home_page.main_menu.devices_link`) and prevents the responsibilities of the two artifacts from bleeding into one another.

## Architecture Overview: The ACS Example

### Layer 1: Framework `lib` - The Generic Base Component

The `BaseGuiComponent` is simplified. Its role is to be a direct engine for executing a named path.

```python
# boardfarm/boardfarm3/lib/gui/base_gui_component.py
import yaml
from selenium.webdriver.support.ui import WebDriverWait

class BaseGuiComponent:
    """Generic, reusable UI component provided by the framework."""
    def __init__(self, driver, selector_file: str, navigation_file: str):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        with open(selector_file) as f:
            self.selectors = yaml.safe_load(f)
        with open(navigation_file) as f:
            self.navigation = yaml.safe_load(f)

    def _get_locator(self, selector_path: str, **kwargs) -> tuple:
        # ... generic logic to parse dot-notation from self.selectors ...
        pass

    def navigate_path(self, path_name: str, **kwargs):
        """Executes a single, uniquely named path from the navigation artifact."""
        path_steps = self.navigation["navigation_paths"].get(path_name)
        if not path_steps:
            raise ValueError(f"Path '{path_name}' not found in navigation.yaml")
        # ... logic to execute steps ...
```

### Layer 2: Framework `devices` - The Specific Implementation

The specific GUI component (`GenieAcsGui`) no longer needs a complex `navigate_to` method. It can rely on the generic `navigate_path` from the base class, as the BDD step will provide the full, unique path name.

```python
# boardfarm/boardfarm3/devices/genie_acs.py
from boardfarm3.templates.acs import ACS
from boardfarm3.devices.base_devices import LinuxDevice, BoardfarmDevice
from boardfarm3.lib.gui.base_gui_component import BaseGuiComponent
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy

# Component 1: The NBI Implementation (specific to GenieACS)
class GenieAcsNbi(LinuxDevice, ACS):
    # ...

# Component 2: The GUI Implementation (specific to GenieACS)
class GenieAcsGui(BaseGuiComponent):
    """
    Implements device-specific UI actions.
    Inherits the generic navigate_path() engine from the base component.
    """
    def login(self, username, password):
        # ... uses self._get_locator("login.username_field") ...
    
    def click_reboot_button(self):
        # ... uses self._get_locator("device_details.reboot_button") ...

# Component 3: The Composite Device
class GenieACS(BoardfarmDevice):
    """Assembled from its specific interface components."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nbi = GenieAcsNbi(*args, **kwargs)
        self.gui: GenieAcsGui | None = None

    def init_gui(
        self, selector_file: str, navigation_file: str, headless: bool = True
    ) -> GenieAcsGui:
        """Factory for the GUI component."""
        if self.gui is None:
            driver_factory = GuiHelperNoProxy(headless=headless)
            driver = driver_factory.get_web_driver()
            self.gui = GenieAcsGui(driver, selector_file, navigation_file)
        return self.gui
```

### Layer 3: Test Suite - The Test Artifacts & Consumers

The BDD scenario now explicitly states which user journey is being tested by referencing the unique path name. This makes the test's intent clear and self-documenting.

```gherkin
# boardfarm-bdd/tests/features/reboot.feature
Feature: Device Reboot

  Scenario Outline: A user can reboot a device regardless of how they navigated to it
    Given the user navigates to the device details using path "<path_name>"
    When the user clicks the reboot button
    Then the device should reboot

    Examples:
      | path_name                                       |
      | "Path_Home_to_DeviceDetails_via_Search"         |
      | "Path_Home_to_DeviceDetails_via_DashboardWidget"|
```

```python
# boardfarm-bdd/tests/step_defs/acs_steps.py
@given('the user navigates to the device details using path "{path_name}"')
def navigate_with_path(acs: GenieACS, path_name: str, cpe):
    gui = acs.init_gui(
        selector_file="path/to/selectors.yaml",
        navigation_file="path/to/navigation.yaml"
    )
    gui.navigate_path(path_name, cpe_id=cpe.cpe_id)


@when("the operator clicks the reboot button")
def click_reboot(acs: GenieACS):
    # Assumes previous navigation step has already run and initialized the GUI
    acs.gui.click_reboot_button()
```

## Architectural Rationale: The Role of Test Artifacts

A core principle of this architecture is the strict **separation of code (logic) from configuration (data)**. The Python files contain the logic, while the YAML files contain the data. This separation is a deliberate design choice that provides critical, long-term advantages.

### 1. Test Determinism and Stability

BDD scenarios for use cases must be **deterministic**. By codifying a specific user journey in `navigation.yaml` under a unique name, we create a stable contract for our tests.

### 2. Ease of Maintenance and Accessibility

YAML is simple and accessible. By externalizing the volatile parts of UI testing into YAML files, we lower the barrier to maintenance for the entire team.

### 3. Robust Automation and Tooling

The framework's automation tools can safely generate and manage `.yaml` files. This is far more robust than attempting to programmatically modify Python code.

### The Maintainability of the "Flat Name" Key

The unique path name (e.g., `Path_Home_to_DeviceDetails_via_Search`) acts as a key that is present in both the `.feature` file and the `navigation.yaml` file. This is by design. The name represents a stable, business-readable *intent*. The definition of that path in the YAML file represents the volatile *implementation*.

When the UI changes, the implementation can be updated in one central place (`navigation.yaml`) without ever needing to change the test scenarios that rely on the stable intent. This centralizes the cost of maintenance and prevents code rot across numerous `.feature` files.

## Advantages of This Architecture

1. **Consistency**: Follows the established project convention of `lib` for generics and `devices` for specifics.
2. **Cohesion**: All code for a specific device is located in a single, predictable file.
3. **Clarity**: The BDD scenarios are explicit and self-documenting about the exact user journey under test.
4. **Maintainability**: The volatile implementation of a navigation path is centralized in `navigation.yaml`, decoupled from the stable intent defined in the `.feature` file.
