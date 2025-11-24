# Scalable UI Testing Approach - Minimal Maintenance Strategy

## Problem Statement

UI elements change frequently, sometimes even between builds of the same version. Embedding UI-specific details in the boardfarm device classes creates:
- **High maintenance burden** - Every UI change requires updating core framework code
- **Poor portability** - UI specifics are tied to specific GenieACS versions
- **Tight coupling** - Device class becomes dependent on fragile UI selectors
- **Version conflicts** - Different GenieACS versions have different UIs

## Recommended Architecture: Test-Layer UI Abstraction

### Core Principle

**Keep UI specifics in test artifacts, not in boardfarm framework code.**

```
┌─────────────────────────────────────────────────────────────┐
│ Boardfarm Framework (boardfarm/boardfarm3/)                │
│ - Device classes provide ONLY protocol-level methods       │
│ - No UI knowledge, no selectors, no page objects           │
│ - Stable, version-agnostic interface                       │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Uses
                            │
┌─────────────────────────────────────────────────────────────┐
│ Test Layer (boardfarm-bdd/)                                │
│ - Step definitions handle UI interactions                  │
│ - UI helpers/fixtures provide UI automation                │
│ - Selectors stored in configuration/data files             │
│ - Easy to update, version-specific                         │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Overview

### Layer 1: Boardfarm Device Class (Stable, UI-Agnostic)

```python
# boardfarm/boardfarm3/devices/genie_acs.py

class GenieACS(LinuxDevice, ACS):
    """GenieACS device class - NBI API only, NO UI code."""
    
    # ✅ Keep these - stable NBI methods
    def Reboot(self, CommandKey: str = "reboot", cpe_id: str | None = None):
        """Execute Reboot via NBI API."""
        # ... NBI implementation ...
    
    def GPV(self, param, timeout=None, cpe_id=None):
        """Get parameter values via NBI API."""
        # ... NBI implementation ...
    
    # ❌ Remove these - no UI methods in device class
    # def Reboot_UI(self, ...):  # DON'T DO THIS
    # def _init_ui_helper(self): # DON'T DO THIS
```

### Layer 2: Test Fixtures (UI Infrastructure)

```python
# boardfarm-bdd/tests/conftest.py

import pytest
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy

@pytest.fixture(scope="session")
def acs_ui_driver(acs):
    """Provide WebDriver for ACS UI automation."""
    gui_helper = GuiHelperNoProxy(default_delay=20, headless=True)
    driver = gui_helper.get_web_driver()
    
    # Navigate to ACS
    base_url = f"http://{acs.config.get('ipaddr')}:{acs.config.get('http_port')}"
    driver.get(base_url)
    
    yield {
        "driver": driver,
        "base_url": base_url,
        "username": acs.config.get("http_username", "admin"),
        "password": acs.config.get("http_password", "admin"),
    }
    
    driver.quit()


@pytest.fixture
def acs_ui_helpers(acs_ui_driver):
    """Provide UI helper functions."""
    from boardfarm_bdd.tests.ui_helpers.acs_ui_helpers import ACSUIHelpers
    return ACSUIHelpers(acs_ui_driver)
```

### Layer 3: UI Helpers (Reusable UI Actions)

```python
# boardfarm-bdd/tests/ui_helpers/acs_ui_helpers.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import yaml
from pathlib import Path


class ACSUIHelpers:
    """Reusable UI helper functions for ACS.
    
    Selectors are loaded from YAML config files, making them easy to update
    without changing code.
    """
    
    def __init__(self, ui_driver_info: dict):
        self.driver = ui_driver_info["driver"]
        self.base_url = ui_driver_info["base_url"]
        self.username = ui_driver_info["username"]
        self.password = ui_driver_info["password"]
        self.wait = WebDriverWait(self.driver, 20)
        
        # Load selectors from config
        self.selectors = self._load_selectors()
    
    def _load_selectors(self) -> dict:
        """Load UI selectors from YAML config."""
        config_path = Path(__file__).parent / "acs_ui_selectors.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def login(self) -> None:
        """Login to ACS UI."""
        self.driver.get(f"{self.base_url}/login")
        
        # Use selectors from config
        username_field = self.wait.until(
            EC.presence_of_element_located(
                self._get_locator("login.username_field")
            )
        )
        username_field.send_keys(self.username)
        
        password_field = self.driver.find_element(
            *self._get_locator("login.password_field")
        )
        password_field.send_keys(self.password)
        
        login_btn = self.driver.find_element(
            *self._get_locator("login.login_button")
        )
        login_btn.click()
        
        self.wait.until(lambda d: "/login" not in d.current_url)
    
    def navigate_to_device(self, cpe_id: str) -> None:
        """Navigate to device details page."""
        self.driver.get(f"{self.base_url}/devices")
        
        # Search for device
        search_box = self.wait.until(
            EC.presence_of_element_located(
                self._get_locator("device_list.search_box")
            )
        )
        search_box.clear()
        search_box.send_keys(cpe_id)
        
        # Click on device
        device_link = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_list.device_link", cpe_id=cpe_id)
            )
        )
        device_link.click()
        
        self.wait.until(EC.url_contains(f"/devices/{cpe_id}"))
    
    def click_reboot_button(self) -> None:
        """Click the Reboot button on device details page."""
        reboot_btn = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_details.reboot_button")
            )
        )
        reboot_btn.click()
        
        # Handle confirmation dialog if present
        try:
            confirm_btn = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    self._get_locator("device_details.confirm_button")
                )
            )
            confirm_btn.click()
        except:
            pass  # No confirmation dialog
    
    def _get_locator(self, selector_path: str, **kwargs) -> tuple:
        """Get locator from config with optional formatting.
        
        Args:
            selector_path: Dot-notation path to selector (e.g., "login.username_field")
            **kwargs: Variables to format into selector (e.g., cpe_id="ABC-123")
        
        Returns:
            Tuple of (By.TYPE, selector_string)
        """
        # Navigate nested dict using dot notation
        parts = selector_path.split(".")
        value = self.selectors
        for part in parts:
            value = value[part]
        
        # Format selector with kwargs if provided
        if kwargs:
            selector = value["selector"].format(**kwargs)
        else:
            selector = value["selector"]
        
        # Convert string to By constant
        by_type = getattr(By, value["by"].upper())
        
        return (by_type, selector)
```

### Layer 4: Selector Configuration (Easy to Update)

```yaml
# boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml

# GenieACS UI Selectors
# Update this file when UI changes - no code changes needed!

version: "1.2.8"  # GenieACS version these selectors are for
last_updated: "2025-11-24"

login:
  username_field:
    by: "name"
    selector: "username"
  password_field:
    by: "css_selector"
    selector: "input[type='password']"
  login_button:
    by: "css_selector"
    selector: "button[type='submit']"

device_list:
  search_box:
    by: "css_selector"
    selector: "input[placeholder*='Search']"
  device_link:
    by: "css_selector"
    selector: "a[href='/devices/{cpe_id}']"
  refresh_button:
    by: "css_selector"
    selector: "button[title='Refresh']"

device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"
  confirm_button:
    by: "css_selector"
    selector: "button.confirm"
  refresh_button:
    by: "css_selector"
    selector: "button[title='Refresh']"
  device_id_header:
    by: "css_selector"
    selector: "h3.device-id"
```

### Layer 5: Step Definitions (Business Logic)

```python
# boardfarm-bdd/tests/step_defs/reboot_ui_steps.py

from pytest_bdd import given, when, then, scenario

@scenario('../features/Remote CPE Reboot UI.feature', 
          'UC-12347-UI: Successful Remote Reboot via UI')
def test_reboot_via_ui():
    """Test reboot via GenieACS UI."""
    pass


@when("the operator initiates a reboot task via the ACS UI for the CPE")
def operator_initiates_reboot_ui(acs, cpe, acs_ui_helpers, bf_context):
    """Operator clicks Reboot button in GenieACS UI.
    
    This step uses UI helpers to interact with the ACS UI.
    No UI code in the device class - all UI logic is here in the test layer.
    """
    # Get CPE ID
    cpe_id = f"{cpe.config['oui']}-{cpe.config['product_class']}-{cpe.config['serial']}"
    
    # Use UI helpers (not device class methods)
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device(cpe_id)
    acs_ui_helpers.click_reboot_button()
    
    bf_context.reboot_command_key = "reboot_ui_test"


# For comparison, NBI version uses device class method
@when("the operator initiates a reboot task on the ACS for the CPE")
def operator_initiates_reboot_nbi(acs, cpe, bf_context):
    """Operator initiates reboot via NBI API.
    
    This uses the stable device class method - no UI involved.
    """
    cpe_id = f"{cpe.config['oui']}-{cpe.config['product_class']}-{cpe.config['serial']}"
    
    # Use device class NBI method (stable, version-agnostic)
    acs.Reboot(cpe_id=cpe_id, CommandKey="reboot_nbi_test")
    
    bf_context.reboot_command_key = "reboot_nbi_test"
```

## Benefits of This Approach

### 1. **Minimal Maintenance**

When UI changes:
```bash
# Only update the YAML file - no code changes!
vim boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml

# Change:
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"  # Old selector

# To:
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[data-action='reboot']"  # New selector
```

### 2. **Maximum Portability**

Support multiple GenieACS versions:
```yaml
# acs_ui_selectors_v1.2.yaml
version: "1.2.8"
device_details:
  reboot_button:
    selector: "button[title='Reboot']"

# acs_ui_selectors_v1.3.yaml
version: "1.3.0"
device_details:
  reboot_button:
    selector: "button[data-action='reboot']"
```

```python
# Load version-specific selectors
def _load_selectors(self) -> dict:
    acs_version = self._detect_acs_version()
    config_path = Path(__file__).parent / f"acs_ui_selectors_v{acs_version}.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
```

### 3. **Clean Separation**

```
boardfarm/                    # Framework - stable, version-agnostic
└── boardfarm3/
    └── devices/
        └── genie_acs.py      # Only NBI methods, no UI code

boardfarm-bdd/                # Tests - version-specific, easy to update
├── tests/
│   ├── ui_helpers/
│   │   ├── acs_ui_helpers.py          # Reusable UI functions
│   │   ├── acs_ui_selectors.yaml      # Easy to update selectors
│   │   └── acs_ui_selectors_v1.3.yaml # Version-specific selectors
│   └── step_defs/
│       └── reboot_ui_steps.py         # Business logic
```

### 4. **Easy Testing**

Test UI helpers independently:
```python
# boardfarm-bdd/tests/test_ui_helpers.py

def test_acs_ui_helpers_login(acs_ui_helpers):
    """Test login helper."""
    acs_ui_helpers.login()
    assert "/login" not in acs_ui_helpers.driver.current_url

def test_acs_ui_helpers_navigate(acs_ui_helpers):
    """Test navigation helper."""
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device("ABC-CPE-123")
    assert "/devices/ABC-CPE-123" in acs_ui_helpers.driver.current_url
```

## Automated Selector Updates

### Discovery Tool Integration

Use the discovery tool to generate selector configs:

```python
# boardfarm-bdd/tools/generate_selector_config.py

import json
import yaml

def generate_selector_config(discovery_json: str, output_yaml: str):
    """Generate selector YAML from discovery JSON."""
    
    with open(discovery_json) as f:
        data = json.load(f)
    
    selectors = {"version": "auto-generated", "last_updated": "2025-11-24"}
    
    for page in data["pages"]:
        page_type = page["page_type"]
        selectors[page_type] = {}
        
        # Add button selectors
        for btn in page.get("buttons", []):
            if btn.get("css_selector"):
                name = sanitize_name(btn.get("text") or btn.get("title"))
                selectors[page_type][f"{name}_button"] = {
                    "by": "css_selector",
                    "selector": btn["css_selector"]
                }
        
        # Add input selectors
        for inp in page.get("inputs", []):
            if inp.get("css_selector"):
                name = sanitize_name(inp.get("name") or inp.get("placeholder"))
                selectors[page_type][f"{name}_field"] = {
                    "by": "css_selector",
                    "selector": inp["css_selector"]
                }
    
    with open(output_yaml, "w") as f:
        yaml.dump(selectors, f, default_flow_style=False)

# Usage:
# python tools/generate_selector_config.py \
#   --input ui_discovery.json \
#   --output tests/ui_helpers/acs_ui_selectors.yaml
```

## Version Management Strategy

### Option 1: Version Detection

```python
class ACSUIHelpers:
    def _detect_acs_version(self) -> str:
        """Detect GenieACS version from UI."""
        # Check version from footer, API, or config
        try:
            version_element = self.driver.find_element(By.CSS_SELECTOR, ".version")
            return version_element.text
        except:
            return "default"
    
    def _load_selectors(self) -> dict:
        """Load version-specific selectors."""
        version = self._detect_acs_version()
        
        # Try version-specific config first
        version_config = Path(__file__).parent / f"acs_ui_selectors_v{version}.yaml"
        if version_config.exists():
            with open(version_config) as f:
                return yaml.safe_load(f)
        
        # Fall back to default
        default_config = Path(__file__).parent / "acs_ui_selectors.yaml"
        with open(default_config) as f:
            return yaml.safe_load(f)
```

### Option 2: Environment Configuration

```python
# boardfarm-bdd/bf_config/inventory.yaml

acs:
  name: "genieacs"
  type: "genie_acs"
  ipaddr: "192.168.1.100"
  http_port: 3000
  ui_version: "1.2.8"  # Specify which selector config to use
```

```python
class ACSUIHelpers:
    def __init__(self, ui_driver_info: dict, acs_config: dict):
        # ...
        self.selectors = self._load_selectors(acs_config.get("ui_version", "default"))
```

## Comparison: Old vs New Approach

### ❌ Old Approach (High Maintenance)

```python
# boardfarm/boardfarm3/devices/genie_acs.py
class GenieACS(LinuxDevice, ACS):
    def Reboot_UI(self, cpe_id):
        # UI code in device class - hard to maintain
        self._ui_helper.click_button("button[title='Reboot']")  # Breaks when UI changes
```

**Problems:**
- UI selectors in framework code
- Requires framework update for UI changes
- Hard to support multiple versions
- Tight coupling

### ✅ New Approach (Low Maintenance)

```python
# boardfarm-bdd/tests/ui_helpers/acs_ui_helpers.py
class ACSUIHelpers:
    def click_reboot_button(self):
        # Selector loaded from config - easy to update
        reboot_btn = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_details.reboot_button")
            )
        )
        reboot_btn.click()
```

```yaml
# boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"  # Easy to update!
```

**Benefits:**
- Selectors in config file
- Update YAML, not code
- Version-specific configs
- Loose coupling

## Migration Path

### Step 1: Create UI Helpers

```bash
mkdir -p boardfarm-bdd/tests/ui_helpers
touch boardfarm-bdd/tests/ui_helpers/__init__.py
touch boardfarm-bdd/tests/ui_helpers/acs_ui_helpers.py
touch boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml
```

### Step 2: Add Fixtures

```python
# boardfarm-bdd/tests/conftest.py
@pytest.fixture(scope="session")
def acs_ui_driver(acs):
    # ... (see above)

@pytest.fixture
def acs_ui_helpers(acs_ui_driver):
    # ... (see above)
```

### Step 3: Update Step Definitions

```python
# Change from:
@when("operator initiates reboot via UI")
def step(acs, cpe):
    acs.Reboot_UI(cpe_id)  # ❌ Device class method

# To:
@when("operator initiates reboot via UI")
def step(acs, cpe, acs_ui_helpers):
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device(cpe_id)
    acs_ui_helpers.click_reboot_button()  # ✅ UI helper
```

### Step 4: Remove UI Code from Device Class

```python
# boardfarm/boardfarm3/devices/genie_acs.py
class GenieACS(LinuxDevice, ACS):
    # Remove:
    # def Reboot_UI(self, ...):
    # def _init_ui_helper(self):
    
    # Keep only NBI methods:
    def Reboot(self, CommandKey="reboot", cpe_id=None):
        # ... NBI implementation ...
```

## Recommended File Structure

```
boardfarm-bdd/
├── tests/
│   ├── conftest.py                          # Fixtures for UI driver
│   ├── ui_helpers/
│   │   ├── __init__.py
│   │   ├── acs_ui_helpers.py                # Reusable UI functions
│   │   ├── acs_ui_selectors.yaml            # Default selectors
│   │   ├── acs_ui_selectors_v1.2.yaml       # Version 1.2 selectors
│   │   └── acs_ui_selectors_v1.3.yaml       # Version 1.3 selectors
│   ├── step_defs/
│   │   ├── reboot_steps.py                  # NBI steps
│   │   └── reboot_ui_steps.py               # UI steps (uses helpers)
│   └── features/
│       └── Remote CPE Reboot UI.feature
└── tools/
    ├── ui_discovery_complete.py             # Discovery tool
    └── generate_selector_config.py          # Generate YAML from discovery
```

## Summary: Why This Approach is Most Scalable

### ✅ Lowest Maintenance
- **Selectors in YAML** - Update config, not code
- **No framework changes** - UI changes don't affect boardfarm
- **Automated discovery** - Generate configs from UI scans

### ✅ Maximum Portability
- **Version-specific configs** - Support multiple GenieACS versions
- **Environment-based selection** - Choose config per testbed
- **Fallback mechanism** - Default config if version not found

### ✅ Clean Architecture
- **Separation of concerns** - Framework vs. test layer
- **Loose coupling** - UI changes don't break framework
- **Testable components** - UI helpers can be tested independently

### ✅ Future-Proof
- **Easy to extend** - Add new UI actions without framework changes
- **Version migration** - Smooth transition between GenieACS versions
- **Tool integration** - Discovery tool generates configs automatically

## Conclusion

**Keep UI specifics in the test layer, not in boardfarm framework.**

This approach gives you:
1. **Minimal maintenance** - Update YAML configs, not Python code
2. **Maximum portability** - Support multiple versions easily
3. **Clean separation** - Framework stays stable, tests stay flexible
4. **Automated updates** - Discovery tool generates selector configs

The boardfarm device class remains focused on stable NBI methods, while the test layer handles all UI variability through easily-updatable configuration files.
