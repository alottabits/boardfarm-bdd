# Practical Example: Implementing the Compositional UI Architecture

This document provides a complete, working example of the compositional architecture, showing how code is organized between the `lib` and `devices` directories.

## File Structure

```
boardfarm/
└── boardfarm3/
    ├── devices/
    │   └── acs.py                     # All ACS-specific components & composite class
    ├── lib/
    │   └── gui/
    │       ├── gui_helper.py          # WebDriver factory
    │       └── base_gui_component.py  # Generic, reusable base class for GUI components
    └── templates/
        └── acs.py                     # The abstract ACS interface

boardfarm-bdd/
└── tests/
    ├── ui_helpers/
    │   └── acs_ui_selectors.yaml      # Test artifact: UI selectors
    └── step_defs/
        └── reboot_steps.py            # Consumes the device components
```

## Step 1: Framework `lib` - Create the Generic Base Component

This class is vendor-agnostic and lives in its own file in the `lib` directory.

```python
# In boardfarm/boardfarm3/lib/gui/base_gui_component.py
import yaml
from selenium.webdriver.support.ui import WebDriverWait

class BaseGuiComponent:
    """Generic component provided by the framework. Knows how to load YAML."""
    def __init__(self, driver, selector_file: str):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        with open(selector_file) as f:
            self.selectors = yaml.safe_load(f)

    def _get_locator(self, selector_path: str, **kwargs) -> tuple:
        # ... logic to parse "dot.path" from self.selectors ...
        pass
```

## Step 2: Framework `devices` - Define Specific Components and the Composite Class

All code specific to GenieACS is co-located in its device file.

```python
# In boardfarm/boardfarm3/devices/genie_acs.py

from boardfarm3.templates.acs import ACS
from boardfarm3.devices.base_devices import LinuxDevice, BoardfarmDevice
from boardfarm3.lib.gui.base_gui_component import BaseGuiComponent
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy

# Component 1: The NBI Implementation (specific to GenieACS)
class GenieAcsNbi(LinuxDevice, ACS):
    """Implements the ACS template for the GenieACS NBI."""
    def Reboot(self, cpe_id, ...):
        # ... specific POST request logic for GenieACS ...
    # ... all other ACS abstract methods ...

# Component 2: The GUI Implementation (specific to GenieACS)
class GenieAcsGui(BaseGuiComponent):
    """Implements UI actions by inheriting from the generic base component."""
    def login(self, username, password):
        # ... uses self._get_locator("login.username_field") ...
        pass
    def click_reboot_button(self):
        locator = self._get_locator("device_details.reboot_button")
        # ... wait for and click element ...
        pass

# Component 3: The Final Composite Device Class
class GenieACS(BoardfarmDevice):
    """Assembled from its specific interface components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The NBI component is a core part of the device.
        self.nbi = GenieAcsNbi(*args, **kwargs)
        # The GUI component is initialized on demand via the factory.
        self.gui: GenieAcsGui | None = None
    
    def init_gui(self, selector_file: str, headless: bool = True) -> GenieAcsGui:
        """Factory for the GUI component."""
        if self.gui is None:
            # 1. Use the factory from gui_helper.py to get a driver
            driver_factory = GuiHelperNoProxy(headless=headless)
            driver = driver_factory.get_web_driver()
            
            # 2. Instantiate the GUI component with the driver
            self.gui = GenieAcsGui(driver, selector_file)
        return self.gui
```

## Step 3: Test Suite - Create the Selector YAML Artifact

This file is the only thing that needs to change when the ACS UI is updated.

```yaml
# In boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"
```

## Step 4: Test Suite - Use the Device Components in BDD Steps

The step definitions are now very clear. They access the appropriate component (`.nbi` or `.gui`) on the device fixture.

```python
# In boardfarm-bdd/tests/step_defs/reboot_steps.py

from pytest_bdd import when
# Assume 'acs' is a fixture that returns an instance of the composite GenieACS class
from boardfarm.devices.genie_acs import GenieACS 

@when("the operator reboots the CPE via the NBI")
def reboot_via_nbi(acs: GenieACS, cpe):
    """Interact with the NBI component."""
    acs.nbi.Reboot(cpe_id=cpe.cpe_id)

@when("the operator reboots the CPE via the UI")
def reboot_via_gui(acs: GenieACS, cpe):
    """Initialize and interact with the GUI component."""
    selector_path = "tests/ui_helpers/acs_ui_selectors.yaml"
    
    # Initialize the gui component with the test suite's artifact
    gui = acs.init_gui(selector_file=selector_path)
    
    # Use the component's methods
    gui.login()
    gui.navigate_to_device(cpe.cpe_id)
    gui.click_reboot_button()
```

This example demonstrates the clean separation and clear division of responsibilities that makes this architecture easy to maintain and scale.
