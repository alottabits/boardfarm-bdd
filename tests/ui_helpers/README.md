# UI Discovery Wrapper

This directory contains a convenience wrapper script for the UI discovery tool.

## Prerequisites

Make sure to activate the virtual environment before running the script:

```bash
# From the boardfarm-bdd directory
source .venv-3.12/bin/activate
```

## Quick Start

```bash
# From the boardfarm-bdd directory (with venv activated)
cd tests/ui_helpers

# Run UI discovery (basic usage)
python discover_ui.py --url http://127.0.0.1:3000 --username admin --password admin

# Run with all recommended options
python discover_ui.py \
  --url http://127.0.0.1:3000 \
  --username admin \
  --password admin \
  --discover-interactions \
  --skip-pattern-duplicates \
  --pattern-sample-size 3 \
  --output genieacs_ui_map.json
```

## What This Script Does

The `discover_ui.py` script is a thin wrapper that imports and calls the `main()` function from `boardfarm3.lib.gui.ui_discovery`.

**Prerequisites:**
- Boardfarm must be installed in your active Python environment
- If using editable install: `pip install -e /path/to/boardfarm`
- Required dependencies: selenium, networkx

This allows you to use the UI discovery functionality locally with a simple command, without navigating to the boardfarm directory.

## Available Options

All command-line options from `ui_discovery.py` are supported:

- `--url` - Base URL of the application to crawl (required)
- `--output` - Output file for UI map (default: ui_map.json)
- `--username` - Login username (optional)
- `--password` - Login password (optional)
- `--login-url` - Custom login URL (optional)
- `--headless` - Run browser in headless mode (default: True)
- `--no-headless` - Run browser with GUI
- `--no-login` - Skip login step
- `--disable-pattern-detection` - Disable URL pattern detection
- `--pattern-min-count` - Minimum URLs required to form a pattern (default: 3)
- `--skip-pattern-duplicates` - Skip URLs matching detected patterns after sampling
- `--pattern-sample-size` - Number of pattern instances to crawl before skipping (default: 3)
- `--discover-interactions` - Discover modals and dialogs by clicking buttons
- `--safe-buttons` - Comma-separated list of safe button text patterns
- `--interaction-timeout` - Seconds to wait for modals to appear after clicking (default: 2)

## Example Workflows

### Basic crawl without login
```bash
python discover_ui.py --url http://example.com --no-login --output example_ui.json
```

### Full discovery with interaction testing
```bash
python discover_ui.py \
  --url http://127.0.0.1:3000 \
  --username admin \
  --password admin \
  --discover-interactions \
  --skip-pattern-duplicates \
  --output complete_ui_map.json
```

### Debug mode (visible browser)
```bash
python discover_ui.py \
  --url http://127.0.0.1:3000 \
  --username admin \
  --password admin \
  --no-headless
```

## Output

The script generates a JSON file containing:
- NetworkX graph representation of the UI
- Page nodes (URLs, titles, types)
- Element nodes (buttons, inputs, selects) with **rich functional metadata**
- Modal and form nodes (if `--discover-interactions` is enabled)
- Navigation edges between pages (including query parameters)
- Graph statistics and discovery metrics

### Enhanced Metadata (Phase 5)

The discovery tool now captures rich functional metadata for semantic element search:

**For Buttons:**
- `text`, `title`, `aria-label` - User-visible descriptions
- `data-action`, `data-target` - Functional attributes
- `onclick` - JavaScript handler hints
- `id`, `class` - Developer identifiers

**For Inputs:**
- `name`, `placeholder`, `aria-label` - Field descriptions
- `type` - Input purpose (text, email, search, etc.)
- Custom `data-*` attributes

This metadata enables **self-healing tests** that can find elements by function even when names/IDs change.

## Configuration: Optional GUI Testing

### Overview

GUI testing is **completely optional**. By default, devices use only the machine to maching API's / NBI (Northbound Interface) for fast API-based testing. GUI testing is enabled by adding configuration to your device config.

### Enabling GUI Testing for a Device

**1. Generate UI artifacts** (one-time per ACS vendor):

```bash
# From boardfarm-bdd directory with venv activated
cd tests/ui_helpers

# Discover UI structure
python discover_ui.py \
  --url http://127.0.0.1:7557 \
  --username admin \
  --password admin \
  --discover-interactions \
  --skip-pattern-duplicates \
  --output ../../bf_config/gui_artifacts/genieacs/ui_map.json

# Generate selectors
cd ../../
python -m boardfarm3.lib.gui.selector_generator \
  --input bf_config/gui_artifacts/genieacs/ui_map.json \
  --output bf_config/gui_artifacts/genieacs/selectors.yaml

# Generate navigation paths
python -m boardfarm3.lib.gui.navigation_generator \
  --input bf_config/gui_artifacts/genieacs/ui_map.json \
  --output bf_config/gui_artifacts/genieacs/navigation.yaml
```

**2. Update device config** in `bf_config/boardfarm_config_example.json`:

```json
{
    "prplos-docker-1": {
        "devices": [
            {
                "name": "genieacs",
                "type": "bf_acs",
                "ipaddr": "localhost",
                "http_port": 7557,
                "http_username": "admin",
                "http_password": "admin",
                "port": 4503,
                
                "gui_selector_file": "bf_config/gui_artifacts/genieacs/selectors.yaml",
                "gui_navigation_file": "bf_config/gui_artifacts/genieacs/navigation.yaml",
                "gui_headless": true,
                "gui_default_timeout": 30
            }
        ]
    }
}
```

**Important: Path Resolution**
- File paths are relative to the **current working directory** (where you run pytest)
- **Not** relative to the config file's location
- When running from `boardfarm-bdd/`, paths should start with `bf_config/`

**3. GUI automatically initializes** when device boots.

### Configuration Options in case the GUI is intended to be used

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `gui_selector_file` | Yes (for GUI) | - | Path to generated selectors.yaml (relative to working directory) |
| `gui_navigation_file` | Yes (for GUI) | - | Path to generated navigation.yaml (relative to working directory) |
| `gui_base_url` | No | Derived from `ipaddr:http_port` | Base URL for GUI |
| `gui_headless` | No | `true` | Run browser in headless mode |
| `gui_default_timeout` | No | `20` | Element wait timeout in seconds |

**Path Resolution Context:**
- Paths resolve relative to where you **run pytest** (the current working directory)
- Typically: `cd ~/projects/req-tst/boardfarm-bdd && pytest ...`
- Example path: `bf_config/gui_artifacts/genieacs/selectors.yaml`

### Without GUI Testing

Simply **omit** the GUI config fields - the device works perfectly with just NBI:

```json
{
    "name": "genieacs",
    "type": "bf_acs",
    "ipaddr": "localhost",
    "http_port": 7557,
    "http_username": "admin",
    "http_password": "admin"
}
```

### Using GUI in Step Definitions

**Check availability first:**

```python
from boardfarm3.exceptions import BoardfarmException

@given("the ACS GUI is available")
def step_acs_gui_available(bf_context):
    """Ensure ACS GUI is ready for testing."""
    acs = bf_context.device_manager.get_device_by_name("genieacs")
    
    # Skip if GUI not configured
    if not acs.gui.is_gui_configured():
        pytest.skip("GUI testing not configured for this device")
    
    # Initialize if needed
    if not acs.gui.is_initialized():
        acs.gui.initialize()
    
    # Verify login
    assert acs.gui.is_logged_in() or acs.gui.login()


@when("I reboot device {cpe_id} via ACS GUI")
def step_reboot_via_gui(bf_context, cpe_id):
    """Reboot device using ACS GUI."""
    acs = bf_context.device_manager.get_device_by_name("genieacs")
    success = acs.gui.reboot_device_via_gui(cpe_id)
    assert success, f"Failed to reboot {cpe_id} via GUI"
```

**Conditional usage (GUI preferred, NBI fallback):**

```python
@when("I reboot device {cpe_id}")
def step_reboot_device(bf_context, cpe_id):
    """Reboot device using best available interface."""
    acs = bf_context.device_manager.get_device_by_name("genieacs")
    
    # Use GUI if initialized, otherwise NBI
    if acs.gui.is_initialized():
        success = acs.gui.reboot_device_via_gui(cpe_id)
    else:
        success = acs.nbi.reboot_device(cpe_id)
    
    assert success
```

### Recommended Directory Structure

```
boardfarm-bdd/                           # ← Run pytest from here (working directory)
  bf_config/
    boardfarm_config_example.json        # Config file
    gui_artifacts/
      genieacs/
        selectors.yaml                   # Element locators
        navigation.yaml                  # Navigation paths
        ui_map.json                      # Source (for regeneration)
      axiros/
        selectors.yaml
        navigation.yaml
        ui_map.json
```

**How Path Resolution Works:**
1. You run: `cd boardfarm-bdd && pytest ...`
2. Working directory: `boardfarm-bdd/`
3. Config path: `bf_config/gui_artifacts/genieacs/selectors.yaml`
4. Resolves to: `boardfarm-bdd/bf_config/gui_artifacts/genieacs/selectors.yaml` ✅

### Benefits of Optional GUI

✅ **Fast by Default** - NBI-only tests run quickly  
✅ **No Breaking Changes** - Existing tests continue to work  
✅ **Progressive Enhancement** - Add GUI testing incrementally  
✅ **Environment Flexibility** - Enable GUI per testbed/environment  
✅ **Clear Errors** - Helpful messages when GUI unavailable  
✅ **CI/CD Friendly** - Easy to enable/disable per pipeline  

### Migration Checklist

- [ ] Run `discover_ui.py` to generate `ui_map.json`
- [ ] Run `selector_generator.py` to create `selectors.yaml`
- [ ] Run `navigation_generator.py` to create `navigation.yaml`
- [ ] Add `gui_selector_file` to device config
- [ ] Add `gui_navigation_file` to device config
- [ ] (Optional) Set `gui_headless: true` for CI/CD
- [ ] Test with `acs.gui.is_gui_configured()` in step definitions
- [ ] Create GUI-specific scenarios or enhance existing ones

## Template Pattern: Task-Oriented Methods

The GUI templates (`ACSGUI`) use **task-oriented methods** that describe business operations, not UI navigation. This follows the same pattern as `ACSNBI`:

**✅ Recommended:**
```python
acs.gui.reboot_device_via_gui(cpe_id)      # Task: what to do
acs.gui.get_device_status(cpe_id)          # Task: what to get
```

**❌ Not Recommended:**
```python
acs.gui.navigate_to_device_list()          # Navigation: how to do it
acs.gui.click_reboot_button()              # UI action: too low-level
```

**Why Task-Oriented?**
- Vendor-neutral - works for any ACS implementation
- Test clarity - states intent, not navigation steps
- Self-healing - implementations use semantic search
- Consistent - matches proven NBI pattern

**Implementation:**
Device-specific implementations (e.g., `GenieAcsGUI`) use the generated artifacts and semantic element search to fulfill the task-oriented interface, hiding all navigation and UI-structure details.

For complete details, see: `boardfarm/boardfarm3/lib/gui/README.md` (section: "Task-Oriented Template Pattern")

## See Also

- **Framework Overview:** `boardfarm/boardfarm3/lib/gui/README.md` - Complete architecture and task-oriented pattern
- **UI Discovery:** `boardfarm/boardfarm3/lib/gui/README_UI_DISCOVERY.md` - Discovery tool documentation
- **Graph Architecture:** `boardfarm/boardfarm3/lib/gui/NETWORKX_GRAPH_ARCHITECTURE.md` - NetworkX graph details
- **Semantic Search:** `boardfarm/boardfarm3/lib/gui/SEMANTIC_SEARCH_OVERVIEW.md` - Self-healing test capability
- **Template Definition:** `boardfarm/boardfarm3/templates/acs/acs_gui.py` - ACSGUI with 18 task-oriented methods
