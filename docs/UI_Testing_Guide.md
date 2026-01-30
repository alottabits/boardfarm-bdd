# UI Testing Guide for Test Authors

## Overview

This guide explains how to use Boardfarm's automated UI discovery tools to develop BDD scenarios, feature files, and step definitions.

## Prerequisites

### Installation

GUI testing requires the StateExplorer packages for state-machine-based UI testing:

```bash
# 1. Install StateExplorer packages (from the req-tst workspace)
pip install -e ../StateExplorer/packages/model-resilience-core
pip install -e ../StateExplorer/packages/aria-state-mapper

# 2. Install Playwright browsers
playwright install chromium

# 3. Install boardfarm-bdd with GUI dependencies
pip install -e ".[gui]"        # GUI dependencies only
pip install -e ".[full]"       # Both frameworks + GUI
pip install -e ".[pytest,gui]" # pytest-bdd + GUI
```

### StateExplorer Packages

| Package | Description |
|---------|-------------|
| `model-resilience-core` | Platform-agnostic state fingerprinting and matching algorithms |
| `aria-state-mapper` | Web UI state mapping using Playwright and accessibility trees |

These packages provide:
- **Automated UI Discovery** - Crawl web applications to build state graphs
- **State Fingerprinting** - Identify UI states using accessibility trees
- **Resilient Element Matching** - Find elements even when selectors change
- **Navigation Path Finding** - Compute optimal paths between UI states

### Boardfarm's Standardization Philosophy

Boardfarm provides **stable, standardized test interfaces** that remain consistent across different device implementations. This applies to both machine-to-machine APIs and GUI interactions:

**Example - Standard Test Interface:**
```python
# M2M API (works for any CPE implementation)
cpe.reboot()
cpe.get_wan_status()

# GUI API (works for any ACS implementation)  
acs.gui.navigate_to_device_list()
acs.gui.reboot_device()
```

**The Implementation Varies, The Interface Doesn't:**
- For CPE: Implementation might use TR-069, SSH, REST API
- For ACS GUI: Implementation might be GenieACS, AxirosACS, custom ACS
- **Tests don't care** - they use the standard interface

### How UI Discovery Fits In

The UI discovery tools **automatically generate mapping artifacts** that connect your stable test interface to the actual UI:

```
Standard Interface          Mapping Artifacts          Actual UI
(What tests use)           (Auto-generated)          (Device-specific)

gui.reboot_device()   →    selectors.yaml      →    <button class="btn-reboot">
                           navigation.yaml           Click "Devices" → Click "Actions"
```

This maintains **separation of concerns**:
- **Tests** describe *what* to do (business logic)
- **Artifacts** describe *how* to do it (UI specifics)
- **Tools** keep artifacts synchronized with UI

The framework automatically discovers your application's UI structure and generates test artifacts (`selectors.yaml` and `navigation.yaml`) that make this pattern work seamlessly.

## Complete Architecture: Template to Test

### The Full Path

```
1. Define Template (Once)
   ↓
   devices/acs_template/gui_component.py
   - Standard interface: navigate_to_device_list(), reboot_device(), etc.
   
2. Discover Actual UI (Per Device Type)
   ↓
   ui_discovery.py → ui_map.json (graph)
   
3. Generate Mapping Artifacts
   ↓
   selector_generator.py → selectors.yaml (elements)
   navigation_generator.py → navigation.yaml (paths)
   
4. Implement Device Class
   ↓
   devices/genieacs/genieacs_gui.py
   - Inherits from template
   - Implements methods using artifacts
   
5. Use in Tests
   ↓
   features/device_management.feature
   steps/device_steps.py
   - Use standard interface only
```

### Component Structure Example

Following Boardfarm's compositional pattern (same as CPE devices):

```
devices/
├── acs_template/                    # 1. Template (stable interface)
│   ├── gui_component.py            # Standard GUI methods
│   │   - navigate_to_device_list()
│   │   - search_device(device_id)
│   │   - reboot_device()
│   ├── nbi_component.py            # Standard NBI methods
│   └── acs_device.py               # Composite: .gui + .nbi
│
├── genieacs/                        # 2. Implementation
│   ├── genieacs_gui.py             # Implements template
│   ├── genieacs_nbi.py
│   ├── genieacs_device.py
│   ├── selectors.yaml              # 3. Mapping (generated)
│   └── navigation.yaml
│
└── axirosacs/                        # Alternative implementation
    ├── axirosacs_gui.py
    ├── selectors.yaml              # Different UI, same interface
    └── navigation.yaml
```

**Key Concepts:**
- **Template**: Defines *what* operations are available (interface)
- **Artifacts**: Define *how* to perform operations on specific UI (mapping)
- **Implementation**: Connects template methods to UI using artifacts
- **Tests**: Use template interface only (device-independent)

### Example Flow: Reboot Device

**1. Template Definition (Once):**
```python
# devices/acs_template/gui_component.py
class AcsGuiTemplate(BaseGuiComponent):
    def reboot_device(self):
        """Standard interface: Reboot selected device."""
        raise NotImplementedError("Implement in device-specific class")
```

**2. UI Discovery (Per Device):**
```bash
python ui_discovery.py --url http://genieacs:3000 → ui_map.json
python selector_generator.py → selectors.yaml
```

**3. Generated Artifacts:**
```yaml
# selectors.yaml
device_list_page:
  buttons:
    reboot:
      by: css
      selector: .btn-reboot
```

**4. Device Implementation:**
```python
# devices/genieacs/genieacs_gui.py
class GenieAcsGui(AcsGuiTemplate):
    def __init__(self, device, **kwargs):
        super().__init__(device,
            selectors_file="./devices/genieacs/selectors.yaml",
            **kwargs)
    
    def reboot_device(self):
        """Implements template using artifacts."""
        self.click_element("button", "reboot", page="device_list")
        self.click_element("button", "confirm", context="modal")
```

**5. Test Usage:**
```python
# steps/device_steps.py
@when("user reboots the device")
def reboot_device(bf_context):
    acs = bf_context.devices.genieacs
    acs.gui.reboot_device()  # Uses standard interface
```

### Benefits of This Pattern

**For Test Authors:**
- Write once, works for all ACS implementations
- Tests are readable (business logic, not UI details)
- No changes needed when UI changes (just regenerate artifacts)

**For Maintainers:**
- Standard interface enforces consistency
- Artifacts are auto-generated (tools do the work)
- Easy to add new ACS types (implement template)

**For Automation:**
- UI changes detected early (run discovery in CI/CD)
- Artifacts updated automatically (generate in pipeline)
- Test suite stays synchronized with UI

## Workflow Architecture

```
┌─────────────────────┐
│   Web Application   │  Your app under test
└──────────┬──────────┘
           │
           ↓ Automated Discovery
┌─────────────────────┐
│  Boardfarm Tools    │  ui_discovery.py
│  (Graph Generation) │  selector_generator.py
│                     │  navigation_generator.py
└──────────┬──────────┘
           │
           ↓ Generates
┌─────────────────────┐
│   Test Artifacts    │  selectors.yaml (element locators)
│                     │  navigation.yaml (page paths)
└──────────┬──────────┘
           │
           ↓ Used by
┌─────────────────────┐
│  Device Classes     │  genieacs_gui.py (implements template)
│  (Template Pattern) │  Uses artifacts to fulfill interface
└──────────┬──────────┘
           │
           ↓ Used by
┌─────────────────────┐
│  Your Step Defs     │  steps/gui_steps.py
│  Your Feature Files │  features/use_case.feature
│  (Standard Interface)│  Use template methods only
└─────────────────────┘
```

## Workflow for Test Authors

### Step 1: Discover UI Structure (Once Per Sprint/Release)

Run the discovery tool against your application:

```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

python ../boardfarm/boardfarm3/lib/gui/ui_discovery.py \
  --url http://your-app:3000 \
  --username admin \
  --password admin \
  --discover-interactions \
  --skip-pattern-duplicates \
  --output ./tests/ui_helpers/ui_map.json
```

**What this does:**
- Logs into your application
- Crawls all pages using breadth-first search
- Discovers buttons, inputs, links, tables
- Tests safe button interactions (finds modals/dialogs)
- Builds a graph representation
- Skips duplicate pages (e.g., 1000 product pages → samples 3)

**Output:** `ui_map.json` - Graph with all pages and elements

**When to run:**
- Weekly (recommended)
- When UI structure changes
- Before starting new feature development

### Step 2: Generate Test Artifacts

Generate the YAML files that step definitions will use:

```bash
# Generate selectors
python ../boardfarm/boardfarm3/lib/gui/selector_generator.py \
  --input ./tests/ui_helpers/ui_map.json \
  --output ./tests/ui_helpers/selectors.yaml

# Generate navigation paths
python ../boardfarm/boardfarm3/lib/gui/navigation_generator.py \
  --input ./tests/ui_helpers/ui_map.json \
  --output ./tests/ui_helpers/navigation.yaml \
  --mode common
```

**What this does:**
- **selectors.yaml**: Organizes all element locators by page
- **navigation.yaml**: Generates optimal paths between pages

**Output:**
```
tests/ui_helpers/
├── ui_map.json          # Graph (usually not committed)
├── selectors.yaml       # Commit this
└── navigation.yaml      # Commit this
```

### Step 3a: Define Template (Once per Device Type)

Create a template that defines the standard interface:

```python
# devices/acs_template/gui_component.py
from boardfarm3.lib.gui import BaseGuiComponent

class AcsGuiTemplate(BaseGuiComponent):
    """Standard GUI interface for ACS devices.
    
    This template defines the stable test interface that all ACS
    implementations must provide. Similar to CpeTemplate for CPE devices.
    """
    
    # Navigation methods
    def navigate_to_device_list(self):
        """Navigate to the device list page."""
        raise NotImplementedError("Subclass must implement")
    
    def navigate_to_admin_settings(self):
        """Navigate to admin settings page."""
        raise NotImplementedError("Subclass must implement")
    
    # Device management methods
    def search_device(self, device_id: str):
        """Search for a device by ID or serial number."""
        raise NotImplementedError("Subclass must implement")
    
    def select_device(self, device_id: str):
        """Select a device from the list."""
        raise NotImplementedError("Subclass must implement")
    
    def reboot_device(self):
        """Reboot the selected/current device."""
        raise NotImplementedError("Subclass must implement")
    
    def delete_device(self):
        """Delete the selected/current device."""
        raise NotImplementedError("Subclass must implement")
    
    # Configuration methods
    def get_device_parameter(self, parameter_path: str) -> str:
        """Get a device parameter value from the UI."""
        raise NotImplementedError("Subclass must implement")
    
    def set_device_parameter(self, parameter_path: str, value: str):
        """Set a device parameter value via the UI."""
        raise NotImplementedError("Subclass must implement")
```

### Step 3b: Implement Device-Specific Class

Map the template to actual UI using generated artifacts:

```python
# devices/genieacs/genieacs_gui.py
from devices.acs_template.gui_component import AcsGuiTemplate

class GenieAcsGui(AcsGuiTemplate):
    """GenieACS-specific implementation of standard ACS GUI interface.
    
    This class fulfills the template contract using GenieACS-specific
    selectors and navigation paths (auto-generated by tools).
    """
    
    def __init__(self, device, **kwargs):
        super().__init__(
            device,
            base_url="http://genieacs:3000",
            selectors_file="./devices/genieacs/selectors.yaml",
            navigation_file="./devices/genieacs/navigation.yaml",
            **kwargs
        )
    
    # Implement template methods using artifacts
    def navigate_to_device_list(self):
        """Navigate to device list (uses navigation.yaml)."""
        self.navigate_to_page("device_list")
    
    def navigate_to_admin_settings(self):
        """Navigate to admin settings (uses navigation.yaml)."""
        self.navigate_path("Path_overview_to_admin_settings")
    
    def search_device(self, device_id: str):
        """Search for device (uses selectors.yaml)."""
        self.enter_text("search", device_id, page="device_list")
        self.press_key("ENTER")
    
    def select_device(self, device_id: str):
        """Select device from list."""
        # Click on device row
        xpath = f"//tr[contains(.,'{device_id}')]"
        element = self.driver.find_element("xpath", xpath)
        element.click()
    
    def reboot_device(self):
        """Reboot device (uses selectors.yaml)."""
        self.click_element("button", "reboot", page="device_list")
        # Handle confirmation modal
        self.click_element("button", "confirm", context="modal")
    
    def delete_device(self):
        """Delete device (uses selectors.yaml)."""
        self.click_element("button", "delete", page="device_list")
        self.click_element("button", "confirm", context="modal")
    
    def get_device_parameter(self, parameter_path: str) -> str:
        """Get parameter value from UI."""
        # Implementation specific to GenieACS parameter display
        xpath = f"//tr[td[text()='{parameter_path}']]/td[2]"
        element = self.driver.find_element("xpath", xpath)
        return element.text
    
    def set_device_parameter(self, parameter_path: str, value: str):
        """Set parameter value via UI."""
        # Implementation specific to GenieACS parameter editing
        self.click_element("button", "edit_parameter", page="device_details")
        self.enter_text("parameter_path", parameter_path, context="modal")
        self.enter_text("parameter_value", value, context="modal")
        self.click_element("button", "save", context="modal")
```

### Step 3c: Assemble Device Class (Compositional Pattern)

```python
# devices/genieacs/genieacs_device.py
from .genieacs_gui import GenieAcsGui
from .genieacs_nbi import GenieAcsNbi

class GenieAcsDevice:
    """GenieACS device with compositional components.
    
    Components:
    - .gui: Web UI interface (inherits from AcsGuiTemplate)
    - .nbi: Northbound API interface (REST)
    """
    
    def __init__(self, **kwargs):
        # Initialize components
        self.gui = GenieAcsGui(self, **kwargs)
        self.nbi = GenieAcsNbi(self, **kwargs)
    
    # Device-level operations can coordinate components
    def factory_reset_device_via_gui(self, device_id: str):
        """Example: Multi-step operation using GUI."""
        self.gui.navigate_to_device_list()
        self.gui.search_device(device_id)
        self.gui.select_device(device_id)
        self.gui.click_element("button", "factory_reset")
```

### Step 4: Write BDD Feature Files

Write scenarios that reference pages and elements by name:

```gherkin
# features/device_management.feature
Feature: Device Management
  As an ISP operator
  I want to manage customer devices through the web UI
  So that I can perform remote operations

  Scenario: Reboot a device
    Given user is logged into GenieACS
    And user is on the "device_list" page
    When user searches for device "SN123456"
    And user clicks the "reboot" button
    Then the device should reboot successfully
```

### Step 5: Implement Step Definitions

Use the generated artifacts in your step definitions:

```python
# steps/device_management_steps.py
from pytest_bdd import given, when, then, parsers

@given("user is logged into GenieACS")
def login_to_genieacs(bf_context):
    device = bf_context.devices.genieacs
    device.gui.login("admin", "admin")

@given(parsers.parse('user is on the "{page_name}" page'))
def navigate_to_page(bf_context, page_name):
    device = bf_context.devices.genieacs
    # Uses navigation.yaml to find optimal path
    device.gui.navigate_to_page(page_name)

@when(parsers.parse('user searches for device "{device_id}"'))
def search_device(bf_context, device_id):
    device = bf_context.devices.genieacs
    # Uses selectors.yaml to find the search input
    device.gui.enter_text("search_input", device_id)

@when(parsers.parse('user clicks the "{button_name}" button'))
def click_button(bf_context, button_name):
    device = bf_context.devices.genieacs
    # Uses selectors.yaml to find the button
    device.gui.click_element("button", button_name)
```

## Generated Artifacts Explained

### selectors.yaml

Organizes element locators by page:

```yaml
device_list_page:
  buttons:
    reboot:
      by: css
      selector: .primary
    delete:
      by: css
      selector: .critical
  inputs:
    search:
      by: id
      selector: device-filter
  links:
    device_details:
      by: css
      selector: a[href*='devices']
```

**How to use in step definitions:**

```python
# Option 1: Direct element access
device.gui.click_element("button", "reboot", page="device_list_page")

# Option 2: Using helper methods
device.gui.enter_text("search", "SN123456", page="device_list_page")

# Option 3: Find element for custom operations
element = device.gui.find_element("button", "reboot", page="device_list_page")
element.click()
```

### navigation.yaml

Defines multi-step paths between pages:

```yaml
Path_overview_to_admin_presets:
  description: Navigate from home to admin presets
  from: '#!/overview'
  to: '#!/admin/presets'
  steps:
  - action: click
    element: Admin
    locator:
      by: css
      value: a
  - action: click
    element: Presets
    locator:
      by: css
      value: a
```

**How to use in step definitions:**

```python
# Option 1: Use named path
device.gui.navigate_path("Path_overview_to_admin_presets")

# Option 2: Navigate to page (finds optimal path automatically)
device.gui.navigate_to_page("admin_presets")

# Option 3: Manual navigation with validation
device.gui.ensure_on_page("overview")
device.gui.navigate_path("Path_overview_to_admin_presets")
device.gui.verify_on_page("admin_presets")
```

## Common Patterns

### Pattern 1: Page Navigation

```gherkin
Given user is on the "admin_settings" page
```

```python
@given(parsers.parse('user is on the "{page_name}" page'))
def navigate_to_page(bf_context, page_name):
    device = bf_context.devices.genieacs
    current_url = device.gui.driver.current_url
    
    if page_name not in current_url:
        # Uses navigation.yaml to find optimal path
        device.gui.navigate_to_page(page_name)
```

### Pattern 2: Form Filling

```gherkin
When user fills the login form:
  | username | admin |
  | password | admin |
```

```python
@when("user fills the login form:", target_fixture="form_data")
def fill_login_form(bf_context, datatable):
    device = bf_context.devices.genieacs
    
    for row in datatable:
        field_name = row["field"]
        value = row["value"]
        # Uses selectors.yaml
        device.gui.enter_text(field_name, value, page="login_page")
```

### Pattern 3: Button Interaction

```gherkin
When user clicks the "save" button
```

```python
@when(parsers.parse('user clicks the "{button_name}" button'))
def click_button(bf_context, button_name):
    device = bf_context.devices.genieacs
    device.gui.click_element("button", button_name)
```

### Pattern 4: Modal Interaction

```gherkin
When user opens the "add_device" modal
And user fills the device form with:
  | device_id | DEV123 |
And user clicks "save" in the modal
```

```python
@when(parsers.parse('user opens the "{modal_name}" modal'))
def open_modal(bf_context, modal_name):
    device = bf_context.devices.genieacs
    # Finds the button that opens this modal
    device.gui.open_modal(modal_name)

@when(parsers.parse('user clicks "{button_name}" in the modal'))
def click_modal_button(bf_context, button_name):
    device = bf_context.devices.genieacs
    device.gui.click_element("button", button_name, context="modal")
```

### Pattern 5: Verification

```gherkin
Then user should see the "success_message" element
And the "device_status" should display "Online"
```

```python
@then(parsers.parse('user should see the "{element_name}" element'))
def verify_element_visible(bf_context, element_name):
    device = bf_context.devices.genieacs
    assert device.gui.is_element_visible(element_name), \
        f"Element '{element_name}' not visible"

@then(parsers.parse('the "{element_name}" should display "{expected_text}"'))
def verify_element_text(bf_context, element_name, expected_text):
    device = bf_context.devices.genieacs
    actual_text = device.gui.get_element_text(element_name)
    assert actual_text == expected_text, \
        f"Expected '{expected_text}', got '{actual_text}'"
```

## Maintenance Workflow

### When UI Changes

**Option 1: Manual Update (Test Suite Owned)**

1. Run ui_discovery.py
2. Regenerate selectors.yaml and navigation.yaml
3. Review changes (git diff)
4. Update step definitions if element names changed
5. Commit updated YAML files

**Option 2: Automated Update (CI/CD Integration) ⭐ Recommended**

Configure the product's CI/CD to:
1. Run ui_discovery.py on every UI change
2. Generate new YAML files
3. Create PR against test suite repository
4. Test suite reviews and merges

Benefits:
- Early warning of UI changes
- Automatic artifact updates
- Faster feedback loop

### Handling Element Changes

If an element's selector changes:

```yaml
# Old selectors.yaml
device_list_page:
  buttons:
    reboot:
      by: id
      selector: reboot-btn

# New selectors.yaml (after UI change)
device_list_page:
  buttons:
    reboot:
      by: css
      selector: .btn-reboot
```

**Your step definitions don't change!**

```python
# Still works - uses updated selector from YAML
device.gui.click_element("button", "reboot")
```

## Best Practices

### 1. Use Semantic Names

✅ **Good:**
```gherkin
Given user is on the "device_list" page
When user clicks the "add_device" button
```

❌ **Bad:**
```gherkin
Given user navigates to "http://app/#!/devices"
When user clicks element with CSS selector ".btn-primary"
```

### 2. Keep Artifacts in Version Control

```
tests/ui_helpers/
├── selectors.yaml      # ✅ Commit
├── navigation.yaml     # ✅ Commit
└── ui_map.json         # ❌ Don't commit (regenerate)
```

### 3. Regenerate Regularly

- Weekly during active development
- Before each sprint
- When UI changes are made
- Before major releases

### 4. Customize Generated Names

The generator creates names automatically, but you can edit them:

```yaml
# Generated (automatic)
device_list_page:
  buttons:
    button_1:  # Generic name
      by: css
      selector: .btn-primary

# Customized (better)
device_list_page:
  buttons:
    add_device:  # Descriptive name
      by: css
      selector: .btn-primary
```

### 5. One Source of Truth Per Environment

```
tests/ui_helpers/
├── dev/
│   ├── selectors.yaml
│   └── navigation.yaml
├── staging/
│   ├── selectors.yaml
│   └── navigation.yaml
└── production/
    ├── selectors.yaml
    └── navigation.yaml
```

## Troubleshooting

### Problem: Element Not Found

**Error:** `NoSuchElementException: Unable to locate element: {"by":"css","selector":".btn-reboot"}`

**Solutions:**
1. Regenerate selectors.yaml (UI may have changed)
2. Check if you're on the correct page
3. Add explicit wait if element loads dynamically

```python
# Add wait for dynamic elements
device.gui.wait_for_element("button", "reboot", timeout=10)
device.gui.click_element("button", "reboot")
```

### Problem: Navigation Path Not Found

**Error:** `ValueError: No navigation path from X to Y`

**Solutions:**
1. Regenerate navigation.yaml
2. Check if pages are connected (run discovery with `--discover-interactions`)
3. Use specific path if common paths don't include it

```python
# Try specific navigation
device.gui.navigate_path("Path_overview_to_admin_presets")
```

### Problem: Stale Element Reference

**Error:** `StaleElementReferenceException`

**Solutions:**
Already handled by ui_discovery.py, but if you encounter it:

```python
# Retry element interaction
from selenium.common.exceptions import StaleElementReferenceException

for attempt in range(3):
    try:
        device.gui.click_element("button", "save")
        break
    except StaleElementReferenceException:
        if attempt < 2:
            time.sleep(0.5)
            continue
        raise
```

## Advanced Usage

### Custom Page Objects

For complex pages, create custom page objects:

```python
# pages/device_list_page.py
class DeviceListPage:
    def __init__(self, gui):
        self.gui = gui
    
    def search_device(self, device_id):
        """Search for a device by ID."""
        self.gui.ensure_on_page("device_list")
        self.gui.enter_text("search", device_id)
        self.gui.press_key("ENTER")
    
    def select_device(self, device_id):
        """Select a device from the list."""
        # Custom logic using selectors.yaml
        xpath = f"//tr[contains(.,'{device_id}')]//input[@type='checkbox']"
        element = self.gui.driver.find_element("xpath", xpath)
        element.click()
    
    def perform_bulk_action(self, action_name):
        """Perform bulk action on selected devices."""
        self.gui.click_element("button", action_name)

# Use in step definitions
@when(parsers.parse('user searches for device "{device_id}"'))
def search_device(bf_context, device_id):
    device = bf_context.devices.genieacs
    page = DeviceListPage(device.gui)
    page.search_device(device_id)
```

### Conditional Navigation

Handle authentication-required pages:

```python
@given("user is on the admin page")
def navigate_to_admin(bf_context):
    device = bf_context.devices.genieacs
    
    # Check if already logged in
    if not device.gui.is_logged_in():
        device.gui.login("admin", "admin")
    
    # Navigate to admin
    device.gui.navigate_to_page("admin")
```

### Dynamic Element Handling

For elements that change based on state:

```python
@when("user toggles the device power")
def toggle_device_power(bf_context):
    device = bf_context.devices.genieacs
    
    # Check current state
    if device.gui.get_element_text("power_status") == "ON":
        device.gui.click_element("button", "power_off")
    else:
        device.gui.click_element("button", "power_on")
```

## Integration with Use Case Development

### Use Case → Feature File → Step Definitions

**1. Use Case (Requirements Document)**
```markdown
# UC-123: Reboot Device

## Success Guarantee
- Device is rebooted
- Reboot is logged in system

## Minimal Guarantee
- System state is unchanged if reboot fails

## Main Success Scenario
1. Operator navigates to device list
2. Operator searches for target device
3. Operator selects device
4. Operator initiates reboot
5. System confirms reboot
6. Device reboots successfully
```

**2. Feature File (BDD Scenario)**
```gherkin
Feature: Device Reboot (UC-123)
  
  Scenario: Successful device reboot
    Given user is logged into GenieACS
    And user is on the "device_list" page
    When user searches for device "SN123456"
    And user selects the device
    And user clicks the "reboot" button
    And user confirms the reboot
    Then the device should reboot successfully
    And the reboot should be logged
```

**3. Step Definitions (Implementation)**
```python
# Uses generated selectors.yaml and navigation.yaml
@given("user is logged into GenieACS")
def login(bf_context):
    device = bf_context.devices.genieacs
    device.gui.login("admin", "admin")

@given('user is on the "device_list" page')
def navigate_to_device_list(bf_context):
    device = bf_context.devices.genieacs
    device.gui.navigate_to_page("device_list")

@when('user searches for device "{device_id}"')
def search_device(bf_context, device_id):
    device = bf_context.devices.genieacs
    device.gui.enter_text("search", device_id)

@when("user selects the device")
def select_device(bf_context):
    device = bf_context.devices.genieacs
    # Assuming first result
    device.gui.click_element("link", "device_details")

@when('user clicks the "reboot" button')
def click_reboot(bf_context):
    device = bf_context.devices.genieacs
    device.gui.click_element("button", "reboot")

@when("user confirms the reboot")
def confirm_reboot(bf_context):
    device = bf_context.devices.genieacs
    # Handle modal confirmation
    device.gui.click_element("button", "confirm", context="modal")

@then("the device should reboot successfully")
def verify_reboot(bf_context):
    device = bf_context.devices.genieacs
    # Verify success message
    assert device.gui.is_element_visible("success_message")
```

## Summary

### The Boardfarm Standardization Strategy

The UI testing framework embodies Boardfarm's core principle: **stable, standardized test interfaces**.

**Just like M2M APIs:**
```python
# CPE devices - same interface, different implementations
cpe.reboot()  # Works for PrplOS, OpenWrt, etc.

# ACS GUI - same interface, different implementations  
acs.gui.reboot_device()  # Works for GenieACS, AxirosACS, etc.
```

**The Complete Pattern:**

1. **Template** - Defines stable interface (what operations exist)
2. **Tools** - Discover UI and generate mapping artifacts (automated)
3. **Artifacts** - Map interface to actual UI (selectors + navigation)
4. **Implementation** - Fulfills template using artifacts
5. **Tests** - Use standard interface only (device-independent)

**Key Benefits:**

1. **Automated Discovery**: No manual element hunting
2. **Generated Artifacts**: selectors.yaml + navigation.yaml (auto-generated)
3. **Standard Interface**: Same API for all ACS types
4. **Maintainable Tests**: Change YAML, not test code
5. **Device Independence**: Tests work across implementations
6. **Graph Algorithms**: Optimal path finding
7. **BDD Integration**: Clean, readable scenarios

**For Test Authors:**
- Define template interface once per device type
- Run discovery weekly to generate/update artifacts
- Implement device class using template + artifacts
- Write tests using standard interface only
- Focus on business logic, not UI implementation details

**The Framework Provides:**
- Template pattern (like CPE devices)
- Automated UI discovery and artifact generation
- Graph-based navigation path finding
- Separation of test interface from UI implementation

**For detailed tool usage, see:**
- [UI Discovery Tool](../boardfarm/boardfarm3/lib/gui/README_UI_DISCOVERY.md)
- [Selector Generator](../boardfarm/boardfarm3/lib/gui/README_SELECTOR_GENERATOR.md)
- [Navigation Generator](../boardfarm/boardfarm3/lib/gui/README_navigation_generator.md)
- [Framework Overview](../boardfarm/boardfarm3/lib/gui/README.md)

