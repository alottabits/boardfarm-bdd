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
