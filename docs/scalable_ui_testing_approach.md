# A Compositional Architecture for Scalable UI Testing

## Problem Statement

Device classes can become monolithic when they support multiple interfaces (hardware console, software API, web UI). Furthermore, UI-based testing is notoriously brittle due to frequent changes in the presentation layer.

## Recommended Architecture: Principled Composition and Convention

We will adopt a compositional pattern that aligns with the project's existing conventions: generic libraries in `lib`, and specific implementations in `devices`.

### Core Architectural Principles

1.  **Generic Components in `lib`**: The `boardfarm/boardfarm3/lib/` directory contains generic, reusable components. For UI testing, this includes a `BaseGuiHelper`.
2.  **Specific Implementations in `devices`**: The `boardfarm/boardfarm3/devices/` directory contains vendor-specific implementations. For a given device, this file will contain:
    *   A specific **NBI/API component class** (e.g., `GenieAcsNbi`).
    *   A specific **GUI component class** (e.g., `GenieAcsGui`), which inherits from `BaseGuiHelper`.
    *   The final **composite device class** (e.g., `GenieACS`) assembled from these components.
3.  **Decouple UI Selectors**: The `gui` component is always configured by a `selectors.yaml` file that lives in the test suite as a test artifact.

```
┌─────────────────────────────────────────────────────────────┐
│ boardfarm/boardfarm3/lib/                                  │
│ - Contains generic BaseGuiHelper (loads YAML, finds elements)│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ boardfarm/boardfarm3/devices/                              │
│ - Contains composite device classes (e.g., GenieACS)       │
│ - Contains specific components (e.g., GenieAcsNbi, GenieAcsGui)│
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Consumes
                            │
┌─────────────────────────────────────────────────────────────┐
│ Test Layer (e.g., boardfarm-bdd)                           │
│ - Owns and maintains the selector.yaml file as an artifact │
│ - Passes the selector file path to device.init_gui(...)    │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Overview: The ACS Example

### Layer 1: Framework `lib` - The Generic Base Component

This class is vendor-agnostic and lives in its own file to separate it from the WebDriver factories.

```python
# boardfarm/boardfarm3/lib/gui/base_gui_component.py
import yaml
from selenium.webdriver.support.ui import WebDriverWait

class BaseGuiComponent:
    """Generic, reusable UI component provided by the framework."""
    def __init__(self, driver, selector_file: str):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        with open(selector_file) as f:
            self.selectors = yaml.safe_load(f)

    def _get_locator(self, selector_path: str, **kwargs) -> tuple:
        # ... generic logic to parse dot-notation from self.selectors ...
        pass
```

### Layer 2: Framework `devices` - The Specific Implementation

All code specific to GenieACS is co-located in its device file.

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
    """Implements UI actions by inheriting from the generic base component."""
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

    def init_gui(self, selector_file: str, headless: bool = True) -> GenieAcsGui:
        """Factory for the GUI component."""
        if self.gui is None:
            # 1. Use the factory from gui_helper.py to get a driver
            driver_factory = GuiHelperNoProxy(headless=headless)
            driver = driver_factory.get_web_driver()
            
            # 2. Instantiate the specific GUI component with the driver and selector file
            self.gui = GenieAcsGui(driver, selector_file)
        return self.gui
```

### Layer 3: Test Suite - The Test Artifacts & Consumers

The test suite provides the configuration and uses the composite device.

```python
# boardfarm-bdd/tests/ui_helpers/acs_selectors.yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"

# boardfarm-bdd/tests/step_defs/acs_steps.py
@when("the operator reboots via UI")
def reboot_via_gui(acs: GenieACS): # acs is the composite device fixture
    gui = acs.init_gui(selector_file="path/to/selectors.yaml")
    gui.click_reboot_button()

@when("the operator reboots via NBI")
def reboot_via_nbi(acs: GenieACS):
    acs.nbi.Reboot(...)
```

## Advantages of This Architecture

1.  **Consistency**: Follows the established project convention of `lib` for generics and `devices` for specifics.
2.  **Cohesion**: All code for a specific device is located in a single, predictable file.
3.  **Clarity**: The compositional pattern (`acs.nbi`, `acs.gui`) makes test code self-documenting.
4.  **Maintainability**: UI changes are isolated to the YAML test artifacts, protecting the framework from churn.

This architecture provides the ideal balance of standardization, flexibility, and maintainability.
