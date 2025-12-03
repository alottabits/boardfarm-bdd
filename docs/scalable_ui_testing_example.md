# Practical Example: Implementing the "Flat Name" UI Architecture

This document provides a complete, working example of the compositional architecture using the "Flat Name" convention for navigation paths.

## File Structure

The file structure remains the same, with a clear separation between framework `lib`, framework `devices`, and test suite artifacts.

```
boardfarm/
└── boardfarm3/
    ├── devices/
    │   └── acs.py
    ├── lib/
    │   └── gui/
    │       ├── gui_helper.py
    │       └── base_gui_component.py
    └── templates/
        └── acs.py

boardfarm-bdd/
└── tests/
    ├── ui_helpers/
    │   ├── acs_ui_selectors.yaml
    │   └── acs_ui_navigation.yaml
    └── step_defs/
        └── reboot_steps.py
```

## Step 1: Framework `lib` - Create the Generic Base Component

The `BaseGuiComponent` is a simple engine that takes a path name and executes it.

```python
# In boardfarm/boardfarm3/lib/gui/base_gui_component.py
import yaml
from selenium.webdriver.support.ui import WebDriverWait

class BaseGuiComponent:
    """Generic component. Knows how to execute a named path from a YAML file."""
    def __init__(self, driver, selector_file: str, navigation_file: str):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        with open(selector_file) as f:
            self.selectors = yaml.safe_load(f)
        with open(navigation_file) as f:
            self.navigation = yaml.safe_load(f)

    def _get_locator(self, selector_path: str, **kwargs) -> tuple:
        # ... logic to parse "dot.path" from self.selectors ...
        pass

    def navigate_path(self, path_name: str, **kwargs):
        """Executes a single, uniquely named path from the navigation artifact."""
        path_steps = self.navigation["navigation_paths"].get(path_name)
        if not path_steps:
            raise ValueError(f"Path '{path_name}' not found in navigation.yaml")
        for step in path_steps:
            # ... logic to interpret the action (click, type, etc.) ...
            # ... and substitute kwargs into templated values ...
            pass
```

## Step 2: Framework `devices` - Define the Composite Class

The specific component (`GenieAcsGui`) is very lean. It contains device-specific actions but inherits the generic `navigate_path` engine.

```python
# In boardfarm/boardfarm3/devices/genie_acs.py
from boardfarm3.templates.acs import ACS
from boardfarm3.devices.base_devices import LinuxDevice, BoardfarmDevice
from boardfarm3.lib.gui.base_gui_component import BaseGuiComponent
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy

# Component 1: The NBI Implementation
class GenieAcsNbi(LinuxDevice, ACS):
    # ...

# Component 2: The GUI Implementation
class GenieAcsGui(BaseGuiComponent):
    """Implements UI actions and inherits the navigation engine."""
    def click_reboot_button(self):
        locator = self._get_locator("device_details.reboot_button")
        # ... wait for and click element ...
        pass

# Component 3: The Final Composite Device Class
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

## Step 3: Test Suite - Create the Navigation YAML Artifact

This file defines the implementation of each user journey, using unique, descriptive names.

```yaml
# In boardfarm-bdd/tests/ui_helpers/acs_ui_navigation.yaml
navigation_paths:

  Path_Home_to_DeviceDetails_via_Search:
    - action: click
      target: main_menu.devices_link
    - action: type
      target: device_list.search_bar
      value: "{{ cpe_id }}" # Templated value
    - action: click
      target: device_list.first_row_link
```

## Step 4: Test Suite - Create the Selector YAML Artifact

This file provides the dictionary of UI elements, organized by page or component. It should only contain locator data.

```yaml
# In boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml

# Top-level keys correspond to pages or reusable components.
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

## Step 5: Test Suite - Write the BDD Scenario

The scenario is now explicit about the path being tested. This is the "stable intent".

```gherkin
# In boardfarm-bdd/tests/features/reboot.feature
Feature: Device Reboot

  Scenario: A user can reboot a device via the standard search path
    Given the user navigates to the device details using path "Path_Home_to_DeviceDetails_via_Search"
    When the operator clicks the reboot button on the UI
    Then the device should reboot
```

## Step 6: Test Suite - Implement the BDD Step Definition

The step definition is a simple one-liner that passes the path name from the Gherkin step directly to the GUI component's engine.

```python
# In boardfarm-bdd/tests/step_defs/reboot_steps.py
from pytest_bdd import given, when
from boardfarm.devices.genie_acs import GenieACS 

@given('the user navigates to the device details using path "{path_name}"')
def navigate_to_device_page(acs: GenieACS, path_name: str, cpe):
    """Initializes GUI and handles navigation."""
    selector_path = "tests/ui_helpers/acs_ui_selectors.yaml"
    navigation_path = "tests/ui_helpers/acs_ui_navigation.yaml"
    
    gui = acs.init_gui(
        selector_file=selector_path,
        navigation_file=navigation_path
    )
    
    gui.navigate_path(path_name, cpe_id=cpe.cpe_id)

@when("the operator clicks the reboot button on the UI")
def click_reboot_button_on_ui(acs: GenieACS):
    """Performs the specific action on the page."""
    acs.gui.click_reboot_button()
```
