# Practical Example: Using the Scalable UI Testing Approach

This document provides a complete, working example of how to use the scalable UI testing approach with YAML-based selectors.

## File Structure

```
boardfarm-bdd/
├── tests/
│   ├── conftest.py                    # Add UI fixtures here
│   ├── ui_helpers/
│   │   ├── __init__.py
│   │   ├── acs_ui_helpers.py          # ✅ Created
│   │   └── acs_ui_selectors.yaml      # ✅ Created
│   └── step_defs/
│       └── reboot_ui_steps.py         # Example below
```

## Step 1: Add UI Fixtures to conftest.py

Add these fixtures to your existing `boardfarm-bdd/tests/conftest.py`:

```python
import pytest
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy
from pathlib import Path
import sys

# Add ui_helpers to Python path
sys.path.insert(0, str(Path(__file__).parent / "ui_helpers"))


@pytest.fixture(scope="session")
def acs_ui_driver(acs):
    """Provide WebDriver for ACS UI automation.
    
    This fixture creates a WebDriver instance for the ACS and provides
    connection information. The driver is shared across the test session.
    """
    gui_helper = GuiHelperNoProxy(default_delay=20, headless=True)
    driver = gui_helper.get_web_driver()
    
    # Build base URL from ACS config
    base_url = f"http://{acs.config.get('ipaddr')}:{acs.config.get('http_port')}"
    
    ui_info = {
        "driver": driver,
        "base_url": base_url,
        "username": acs.config.get("http_username", "admin"),
        "password": acs.config.get("http_password", "admin"),
    }
    
    yield ui_info
    
    # Cleanup
    driver.quit()


@pytest.fixture
def acs_ui_helpers(acs_ui_driver, acs):
    """Provide ACS UI helper functions.
    
    This fixture creates an ACSUIHelpers instance with the WebDriver
    and loads the appropriate selector configuration.
    """
    from acs_ui_helpers import ACSUIHelpers
    
    # Get ACS version from config (or use "default")
    acs_version = acs.config.get("ui_version", "default")
    
    return ACSUIHelpers(acs_ui_driver, acs_version)
```

## Step 2: Create Step Definitions Using UI Helpers

Create `boardfarm-bdd/tests/step_defs/reboot_ui_steps.py`:

```python
"""Step definitions for UI-based reboot scenarios."""

from pytest_bdd import given, when, then, scenario


@scenario('../features/Remote CPE Reboot UI.feature', 
          'UC-12347-UI: Successful Remote Reboot via UI')
def test_reboot_via_ui():
    """Test reboot via GenieACS UI."""
    pass


@when("the operator initiates a reboot task via the ACS UI for the CPE")
def operator_initiates_reboot_ui(acs, cpe, acs_ui_helpers, bf_context):
    """Operator clicks Reboot button in GenieACS UI.
    
    This step uses the acs_ui_helpers fixture to interact with the UI.
    No UI code in the device class - all UI logic is in the helper.
    """
    # Get CPE ID
    cpe_id = f"{cpe.config['oui']}-{cpe.config['product_class']}-{cpe.config['serial']}"
    
    # Use UI helpers (not device class methods!)
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device(cpe_id)
    acs_ui_helpers.click_reboot_button()
    
    bf_context.reboot_command_key = "reboot_ui_test"


# For comparison: NBI version (uses device class)
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

## Step 3: Create Feature File

Create `boardfarm-bdd/tests/features/Remote CPE Reboot UI.feature`:

```gherkin
Feature: Remote CPE Reboot via UI
  As an operator of a network,
  I want to remotely reboot a CPE device via the ACS UI
  So that I can verify the UI workflow works correctly.

  Background:
    Given a CPE is online and fully provisioned
    And the user has set the CPE GUI password to "p@ssw0rd123!"

  Scenario: UC-12347-UI: Successful Remote Reboot via UI
    When the operator initiates a reboot task via the ACS UI for the CPE
    Then the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    And the CPE resumes normal operation, continuing periodic communication with the ACS
    And the CPE's configuration and operational state are preserved after reboot
    And use case succeeds and all success guarantees are met
```

## Step 4: Update Inventory Configuration

Add UI version to your inventory file `boardfarm-bdd/bf_config/inventory.yaml`:

```yaml
acs:
  name: "genieacs"
  type: "genie_acs"
  ipaddr: "192.168.1.100"
  http_port: 3000
  http_username: "admin"
  http_password: "admin"
  ui_version: "default"  # or "1.2.8", "1.3.0", etc.
```

## Step 5: Run Tests

```bash
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Run UI-based test
pytest tests/features/Remote\ CPE\ Reboot\ UI.feature::UC-12347-UI

# Run NBI-based test (for comparison)
pytest tests/features/Remote\ CPE\ Reboot.feature::UC-12347-Main
```

## Updating Selectors When UI Changes

### Scenario: GenieACS UI Changes

Let's say GenieACS updates and the Reboot button selector changes:

**Old UI:**
```html
<button title="Reboot">Reboot</button>
```

**New UI:**
```html
<button data-action="reboot" class="btn-reboot">Reboot</button>
```

### Solution: Update YAML Only

```bash
# Edit the selector config
vim boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml
```

Change:
```yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"  # Old
```

To:
```yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[data-action='reboot']"  # New
```

**No code changes needed!** The `acs_ui_helpers.py` code remains unchanged.

## Supporting Multiple GenieACS Versions

### Create Version-Specific Selector Files

```bash
# Copy default config
cp boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml \
   boardfarm-bdd/tests/ui_helpers/acs_ui_selectors_v1.2.8.yaml

# Create config for new version
cp boardfarm-bdd/tests/ui_helpers/acs_ui_selectors.yaml \
   boardfarm-bdd/tests/ui_helpers/acs_ui_selectors_v1.3.0.yaml

# Edit new version config
vim boardfarm-bdd/tests/ui_helpers/acs_ui_selectors_v1.3.0.yaml
```

Update version-specific selectors:

```yaml
# acs_ui_selectors_v1.3.0.yaml
version: "1.3.0"
last_updated: "2025-11-24"

device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[data-action='reboot']"  # New selector for v1.3
```

### Configure Which Version to Use

In your inventory:

```yaml
# For testbed with GenieACS 1.2.8
acs:
  ui_version: "1.2.8"

# For testbed with GenieACS 1.3.0
acs:
  ui_version: "1.3.0"
```

The `ACSUIHelpers` class automatically loads the correct selector file!

## Automated Selector Discovery

Use the discovery tool to generate selector configs:

```bash
# Discover UI and generate selector config
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json ui_discovery.json \
  --headless

# Generate YAML from discovery (you'll need to create this tool)
python tools/generate_selector_config.py \
  --input ui_discovery.json \
  --output tests/ui_helpers/acs_ui_selectors_v1.3.0.yaml
```

## Benefits Demonstrated

### ✅ Minimal Maintenance
- UI changes? Update YAML, not Python code
- No framework changes needed
- Quick updates (minutes, not hours)

### ✅ Maximum Portability
- Support multiple GenieACS versions
- Version-specific configs
- Easy testbed switching

### ✅ Clean Separation
- Framework (boardfarm) has no UI code
- Test layer handles all UI specifics
- Clear responsibilities

### ✅ Easy Testing
```python
# Test UI helpers independently
def test_login(acs_ui_helpers):
    acs_ui_helpers.login()
    assert acs_ui_helpers._logged_in

def test_navigate(acs_ui_helpers):
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device("ABC-CPE-123")
    assert "/devices/ABC-CPE-123" in acs_ui_helpers.driver.current_url
```

## Comparison: Old vs New Approach

### ❌ Old Approach (High Maintenance)

```python
# In boardfarm device class - BAD!
class GenieACS:
    def Reboot_UI(self, cpe_id):
        # UI code in framework - hard to maintain
        btn = driver.find_element(By.CSS_SELECTOR, "button[title='Reboot']")
        btn.click()
```

**Problems:**
- UI selector in framework code
- Requires framework update for UI changes
- Can't support multiple versions easily

### ✅ New Approach (Low Maintenance)

```python
# In test layer - GOOD!
@when("operator initiates reboot via UI")
def step(acs_ui_helpers, cpe):
    acs_ui_helpers.click_reboot_button()
```

```yaml
# In YAML config - EASY TO UPDATE!
device_details:
  reboot_button:
    selector: "button[title='Reboot']"
```

**Benefits:**
- Selector in config file
- Update YAML, not code
- Version-specific configs supported

## Summary

This approach gives you:

1. **Minimal maintenance** - Update YAML configs, not Python code
2. **Maximum portability** - Support multiple GenieACS versions
3. **Clean architecture** - Framework stays stable, tests stay flexible
4. **Easy updates** - Discovery tool can generate configs

The boardfarm device class remains focused on stable NBI methods, while the test layer handles all UI variability through easily-updatable YAML configuration files.
