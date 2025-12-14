# FSM GUI Testing - API Quick Reference

**Purpose**: Quick reference for FSM-based GUI testing with three testing modes

**Last Updated**: December 14, 2025

---

## Three Testing Modes

| Mode | API Level | Primary Methods |
|------|-----------|-----------------|
| **1. Functional** | Device (GenieAcsGUI) | `login()`, `reboot_device_via_gui()`, `get_device_status()` |
| **2. Navigation** | FSM (FsmGuiComponent) | `validate_graph_connectivity()`, `execute_random_walk()`, `calculate_path_coverage()` |
| **3. Visual** | FSM (FsmGuiComponent) | `capture_state_screenshot()`, `compare_screenshot_with_reference()`, `validate_all_states_visually()` |

---

## Architecture Layers

```
Test Layer (BDD/Pytest)
    ↓
Device Layer (GenieAcsGUI) - Business goals, friendly names
    ↓
Generic Layer (FsmGuiComponent) - FSM engine, navigation, analysis, screenshots
    ↓
StateExplorer - Fingerprinting, matching, element location
```

---

## MODE 1: Functional Testing API

### Device Layer (GenieAcsGUI)

#### Authentication

```python
# Login to GUI
success = acs.gui.login(username="admin", password="admin")

# Check login status
is_logged_in = acs.gui.is_logged_in()

# Logout
success = acs.gui.logout()
```

#### Device Operations

```python
# Reboot device via GUI
success = acs.gui.reboot_device_via_gui(cpe_id="123-456-789")

# Get device status
status = acs.gui.get_device_status(cpe_id="123-456-789")
# Returns: {'online': True, 'last_inform': '2025-12-14T10:30:00Z'}

# Verify device online
is_online = acs.gui.verify_device_online(cpe_id="123-456-789", timeout=120)

# Get last inform time
timestamp = acs.gui.get_last_inform_time(cpe_id="123-456-789")
```

#### Navigation

```python
# Search for device
found = acs.gui.search_device(cpe_id="123-456-789")

# Navigate to device details
success = acs.gui.navigate_to_device_details(cpe_id="123-456-789")
```

#### BDD Step Definition Pattern

```python
@when("the operator reboots the device via the ACS GUI")
def step_reboot_device(acs, bf_context):
    """Business goal: Reboot device."""
    success = acs.gui.reboot_device_via_gui(bf_context.cpe_id)
    assert success, "Failed to reboot device"

@then("the device should be online in the ACS GUI")
def step_verify_online(acs, bf_context):
    """Verify outcome: Device online."""
    is_online = acs.gui.verify_device_online(bf_context.cpe_id, timeout=120)
    assert is_online, "Device did not come online"
```

---

## MODE 2: Navigation/Structure Testing API

### FSM Component Access

```python
# Access FSM component directly
fsm = acs.gui.fsm

# Or from device class
fsm = acs.gui._fsm_component
```

### Graph Structure

```python
# Get graph structure
graph = fsm.get_graph_structure()
# Returns:
# {
#     'states': ['V_LOGIN', 'V_HOME', 'V_DEVICES', ...],
#     'transitions': [{'from': 'V_LOGIN', 'to': 'V_HOME', 'action': 'click'}, ...],
#     'state_count': 10,
#     'transition_count': 58
# }

# Export for GraphWalker
fsm.export_graphml(Path("genieacs.graphml"))

# Export for Graphviz
fsm.export_dot(Path("genieacs.dot"))
```

### Graph Validation

```python
# Validate connectivity
validation = fsm.validate_graph_connectivity()
# Returns:
# {
#     'is_connected': True,
#     'unreachable_states': [],
#     'dead_end_states': [],
#     'strongly_connected_components': [[...]]
# }

assert validation['is_connected'], "Graph not fully connected"
assert len(validation['unreachable_states']) == 0, \
    f"Unreachable states: {validation['unreachable_states']}"
assert len(validation['dead_end_states']) == 0, \
    f"Dead end states: {validation['dead_end_states']}"
```

### Random Walk Testing

```python
# Execute random walk
result = fsm.execute_random_walk(
    num_steps=50,          # Number of transitions
    start_state=None,      # Uses current state
    coverage_target=0.80   # Stop at 80% coverage
)
# Returns:
# {
#     'path': ['V_HOME', 'V_DEVICES', 'V_DEVICE_DETAILS', ...],
#     'transitions_executed': [<StateTransition>, ...],
#     'coverage': 0.85,
#     'errors': []
# }

# Check for errors
assert len(result['errors']) == 0, f"Errors: {result['errors']}"
assert result['coverage'] >= 0.70, f"Low coverage: {result['coverage']}"
```

### Coverage Metrics

```python
# Calculate coverage
coverage = fsm.calculate_path_coverage()
# Returns:
# {
#     'states_visited': 8,
#     'total_states': 10,
#     'state_coverage': 0.80,
#     'transitions_executed': 45,
#     'total_transitions': 58,
#     'transition_coverage': 0.78,
#     'unvisited_states': ['V_ADMIN_CONFIG', 'V_PERMISSIONS']
# }

print(f"State coverage: {coverage['state_coverage']:.1%}")
print(f"Transition coverage: {coverage['transition_coverage']:.1%}")
print(f"Unvisited: {coverage['unvisited_states']}")
```

### GraphWalker Integration

```python
# Execute path from GraphWalker
path = ['V_OVERVIEW_PAGE', 'V_DEVICES', 'V_DEVICE_DETAILS', 'V_FAULTS']

result = fsm.execute_path_from_graphwalker(path)
# Returns:
# {
#     'success': True,
#     'completed_steps': 3,
#     'failed_at': None,
#     'error': None
# }

assert result['success'], f"Path failed at {result['failed_at']}: {result['error']}"
```

### Navigation Test Pattern

```python
def test_graph_structure_validation(acs):
    """Validate FSM graph has no structural issues."""
    acs.gui.initialize()
    acs.gui.login()
    
    validation = acs.gui.fsm.validate_graph_connectivity()
    
    assert validation['is_connected'], "Graph not connected"
    assert len(validation['unreachable_states']) == 0
    assert len(validation['dead_end_states']) == 0

def test_random_navigation_resilience(acs):
    """Test UI resilience with random walk.
    
    Component provides data, test makes assertions.
    Run with: pytest --html=report.html
    """
    acs.gui.initialize()
    acs.gui.login()
    
    result = acs.gui.fsm.execute_random_walk(
        num_steps=50,
        coverage_target=0.80
    )
    
    # Component returns data, test asserts
    assert len(result['errors']) == 0, f"Errors: {result['errors']}"
    assert result['coverage'] >= 0.70, f"Coverage: {result['coverage']:.1%}"
    
    # pytest automatically captures and reports these results

def test_complete_state_coverage(acs):
    """Verify all states are reachable."""
    acs.gui.initialize()
    acs.gui.login()
    
    fsm = acs.gui.fsm
    graph = fsm.get_graph_structure()
    
    # Try to reach each state
    for state_id in graph['states']:
        success = fsm.navigate_to_state(state_id, max_steps=10)
        assert success, f"Could not reach state: {state_id}"
    
    # Verify 100% coverage
    coverage = fsm.calculate_path_coverage()
    assert coverage['state_coverage'] == 1.0
```

---

## MODE 3: Visual Regression Testing API

### Screenshot Capture

```python
# Capture single state screenshot
path = fsm.capture_state_screenshot(
    state_id='V_LOGIN_FORM_EMPTY',
    reference=False  # False = test screenshot, True = reference
)
# Returns: Path to screenshot file

# Capture reference screenshot
ref_path = fsm.capture_state_screenshot(
    state_id='V_LOGIN_FORM_EMPTY',
    reference=True
)
```

### Screenshot Comparison

```python
# Compare with reference
comparison = fsm.compare_screenshot_with_reference(
    state_id='V_LOGIN_FORM_EMPTY',
    threshold=0.99  # 99% similarity required
)
# Returns:
# {
#     'match': True,
#     'similarity': 0.9987,
#     'diff_image_path': None  # Path to diff image if mismatch
# }

assert comparison['match'], \
    f"Visual mismatch! Similarity: {comparison['similarity']:.2%}"
```

### Batch Operations

```python
# Capture all state screenshots
result = fsm.capture_all_states_screenshots(
    reference=True,   # Save as references
    max_time=300      # 5 minute timeout
)
# Returns:
# {
#     'captured': ['V_LOGIN', 'V_HOME', 'V_DEVICES', ...],
#     'failed': [],
#     'screenshots': {'V_LOGIN': Path(...), 'V_HOME': Path(...), ...},
#     'coverage': 1.0
# }

print(f"Captured {len(result['captured'])} screenshots")
print(f"Failed: {result['failed']}")

# Validate all states visually
validation = fsm.validate_all_states_visually(threshold=0.99)
# Returns:
# {
#     'passed': ['V_LOGIN', 'V_HOME', 'V_DEVICES'],
#     'failed': ['V_ADMIN_CONFIG'],
#     'results': {
#         'V_LOGIN': {'match': True, 'similarity': 0.999},
#         'V_ADMIN_CONFIG': {'match': False, 'similarity': 0.892}
#     },
#     'overall_pass': False
# }

assert validation['overall_pass'], \
    f"Visual regression failures: {validation['failed']}"
```

### Device-Level Helpers

```python
# Capture references (handles login automatically)
result = acs.gui.capture_reference_screenshots()

# Validate against references (handles login automatically)
validation = acs.gui.validate_ui_against_references(threshold=0.99)

if not validation['overall_pass']:
    # Component saves diff images automatically
    # Print details for debugging (pytest captures stdout)
    print(f"\nFailed states: {validation['failed']}")
    for state_id in validation['failed']:
        details = validation['results'][state_id]
        print(f"  {state_id}: {details['similarity']:.2%} similarity")
    print(f"\nSee diff images in screenshot directory")
```

### Visual Test Pattern

```python
def test_capture_reference_screenshots(acs):
    """Capture reference screenshots for all states (run once)."""
    acs.gui.initialize()
    acs.gui.login()
    
    result = acs.gui.capture_reference_screenshots()
    
    assert len(result['failed']) == 0, \
        f"Failed to capture: {result['failed']}"
    assert result['coverage'] >= 0.95, \
        f"Low coverage: {result['coverage']}"
    
    print(f"✅ Captured {len(result['captured'])} reference screenshots")

def test_visual_regression_validation(acs):
    """Compare current UI against reference screenshots.
    
    Diff images automatically saved to screenshot directory.
    Run with: pytest --html=report.html
    """
    acs.gui.initialize()
    acs.gui.login()
    
    result = acs.gui.validate_ui_against_references(threshold=0.95)
    
    # Component provides data and saves diff images
    # pytest captures assertion and includes in HTML report
    assert result['overall_pass'], \
        f"Visual regression failures: {result['failed']}\n" \
        f"See diff images in screenshot directory"
    
    print(f"✅ All {len(result['passed'])} states passed visual validation")

def test_specific_state_visual_stability(acs):
    """Verify specific state hasn't changed visually."""
    acs.gui.initialize()
    
    # Navigate to login page
    driver = acs.gui._driver
    driver.goto(f"{acs.gui._gui_base_url}/#!/login")
    
    # Compare with reference
    login_state = acs.gui._get_fsm_state_id('login_page')
    comparison = acs.gui.fsm.compare_screenshot_with_reference(
        login_state,
        threshold=0.99
    )
    
    assert comparison['match'], \
        f"Login page changed! Similarity: {comparison['similarity']:.2%}"
```

---

## Core FSM Primitives

### State Management

```python
# Verify current state
matches = fsm.verify_state('V_LOGIN_FORM_EMPTY', timeout=5)

# Detect current state automatically
detected = fsm.detect_current_state(update_state=True)
# Returns: 'V_OVERVIEW_PAGE' or None

# Get current state
current = fsm.get_state()

# Set state manually
fsm.set_state('V_HOME', via_action='navigate')

# Get state history
history = fsm.get_state_history()
# Returns: [
#     {'state_id': 'V_LOGIN', 'via_action': 'navigate', 'timestamp': None},
#     {'state_id': 'V_HOME', 'via_action': 'login', 'timestamp': None}
# ]
```

### Navigation

```python
# Navigate to target state (BFS pathfinding)
success = fsm.navigate_to_state(
    target_state_id='V_DEVICE_DETAILS',
    max_steps=10,
    record_path=False
)

# With path recording
result = fsm.navigate_to_state(
    target_state_id='V_DEVICE_DETAILS',
    max_steps=10,
    record_path=True
)
# Returns: {
#     'success': True,
#     'path': [<StateTransition>, ...],
#     'steps': 3
# }

# Get available transitions from current state
transitions = fsm.get_available_transitions()
# Or from specific state
transitions = fsm.get_available_transitions(from_state_id='V_HOME')
```

### Element Finding

```python
# Find element by role and name
button = fsm.find_element(
    state_id='V_LOGIN_FORM_EMPTY',
    role='button',
    name='Login'
)
button.click()

# Find input fields
username_input = fsm.find_element(
    state_id='V_LOGIN_FORM_EMPTY',
    role='textbox',
    name='Username'
)
username_input.fill('admin')

# Find links
devices_link = fsm.find_element(
    state_id='V_OVERVIEW_PAGE',
    role='link',
    name='Devices'
)
devices_link.click()

# Find all elements of a type
all_buttons = fsm.find_all_elements(
    state_id='V_DEVICE_DETAILS',
    role='button'
)
```

---

## State Registry (Device-Specific)

### Friendly Name Mapping

```python
class GenieAcsGUI(ACSGUI):
    STATE_REGISTRY = {
        'login_page': 'V_LOGIN_FORM_EMPTY',
        'home_page': 'V_OVERVIEW_PAGE',
        'device_list_page': 'V_DEVICES',
        'device_details_page': 'V_DEVICE_DETAILS',
        'faults_page': 'V_FAULTS',
        'admin_page': 'V_ADMIN_PRESETS',
    }
    
    def _get_fsm_state_id(self, friendly_name: str) -> str:
        """Convert friendly name to FSM state ID."""
        return self.STATE_REGISTRY.get(friendly_name, friendly_name)
```

### Usage Pattern

```python
# In business goal methods - use friendly names
def login(self, username, password):
    login_state = self._get_fsm_state_id('login_page')
    # ... use login_state with FSM

# In tests - use friendly names
@when("the operator is on the home page")
def step_on_home(acs):
    home_state = acs.gui._get_fsm_state_id('home_page')
    acs.gui.fsm.verify_state(home_state)
```

---

## Configuration

### Boardfarm Device Config

```json
{
  "name": "genieacs",
  "type": "bf_acs",
  "gui_fsm_graph_file": "bf_config/gui_artifacts/genieacs/fsm_graph.json",
  "gui_headless": true,
  "gui_default_timeout": 30,
  "gui_state_match_threshold": 0.80,
  "gui_screenshot_dir": "bf_config/gui_artifacts/genieacs/screenshots",
  "gui_visual_threshold": 0.95,
  "gui_visual_comparison_method": "auto",
  "gui_visual_mask_selectors": [".timestamp", ".version-info", "[data-live]"],
  "http_username": "admin",
  "http_password": "admin"
}
```

### Configuration Access

```python
# In GenieAcsGUI __init__
# Note: screenshot_dir should be configured in device config, but falls back to 
# fsm_graph_file parent directory if not specified
fsm_graph_path = Path(self.config['gui_fsm_graph_file'])
default_screenshot_dir = fsm_graph_path.parent / "screenshots"

self._fsm_component = FsmGuiComponent(
    driver=self._driver,
    fsm_graph_file=fsm_graph_path,
    default_timeout=self.config.get("gui_default_timeout", 30),
    match_threshold=self.config.get("gui_state_match_threshold", 0.80),
    screenshot_dir=Path(self.config.get("gui_screenshot_dir", str(default_screenshot_dir)))
)
```

---

## Test Reporting

### pytest Handles All Reporting

The FSM component **provides data**, pytest **generates reports**.

```bash
# Run tests with HTML report generation
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

pytest tests/test_gui_navigation.py \
  --html=report.html \
  --self-contained-html \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  -v
```

### What the Component Provides

The FSM component returns **data for assertions**:

```python
# Component returns data
coverage = fsm.calculate_path_coverage()
validation = fsm.validate_graph_connectivity()
result = fsm.execute_random_walk(50)

# Test makes assertions (pytest captures these)
assert coverage['state_coverage'] >= 0.70
assert len(validation['unreachable_states']) == 0
assert len(result['errors']) == 0
```

### What pytest Provides

- **HTML reports**: `--html=report.html`
- **JUnit XML**: `--junit-xml=results.xml`
- **Coverage reports**: `--cov` (with pytest-cov)
- **Stdout capture**: print() statements captured in test output
- **Failure details**: Stack traces, assertion details
- **Screenshots**: Diff images automatically included if in test directory

### Accessing Test Artifacts

```python
# Component saves artifacts to configured directory
# bf_config/gui_artifacts/genieacs/screenshots/

# Diff images automatically saved on visual failures
# - state_id-diff.png (Playwright)
# - state_id_ssim_diff.png (SSIM)

# Reference images
# - bf_config/gui_artifacts/genieacs/screenshots/references/state_id.png
```

---

## Common Patterns

### Pattern 1: Functional Test with Verification

```python
@when("the operator performs action X")
def step_action_x(acs, bf_context):
    # Business goal method
    success = acs.gui.perform_action_x(bf_context.param)
    assert success, "Action X failed"

@then("the system should show result Y")
def step_verify_y(acs):
    # Verify outcome
    result = acs.gui.get_result_y()
    assert result == expected, f"Got {result}, expected {expected}"
```

### Pattern 2: Navigation Validation

```python
def test_ui_navigation_resilience(acs):
    """Validate UI can be navigated successfully."""
    acs.gui.initialize()
    acs.gui.login()
    
    # Validate structure
    validation = acs.gui.fsm.validate_graph_connectivity()
    assert validation['is_connected']
    
    # Test random navigation
    result = acs.gui.fsm.execute_random_walk(num_steps=30)
    assert len(result['errors']) == 0
    
    # Check coverage
    coverage = acs.gui.fsm.calculate_path_coverage()
    assert coverage['state_coverage'] >= 0.70
```

### Pattern 3: Visual Regression Suite

```python
@pytest.fixture(scope="session")
def reference_screenshots(acs):
    """Capture reference screenshots once per session."""
    acs.gui.initialize()
    acs.gui.login()
    return acs.gui.capture_reference_screenshots()

def test_visual_regression(acs, reference_screenshots):
    """Run visual regression against references."""
    acs.gui.initialize()
    acs.gui.login()
    
    validation = acs.gui.validate_ui_against_references(threshold=0.99)
    
    # Component provides data and saves diff images
    # pytest captures failure and includes in HTML report
    if not validation['overall_pass']:
        pytest.fail(
            f"Visual failures: {validation['failed']}\n"
            f"See diff images in screenshot directory"
        )
```

---

## Troubleshooting

### Debug Logging

```python
import logging

# Enable FSM component debug logging
logging.getLogger('boardfarm3.lib.gui').setLevel(logging.DEBUG)

# Check state detection scores
fsm.detect_current_state()  # Watch logs for similarity scores
```

### State Detection Issues

```python
# Get current fingerprint
current_fp = fsm._driver.capture_fingerprint()

# Compare manually against all states
for state_id, state in fsm._states.items():
    similarity = fsm._comparer.calculate_similarity(
        current_fp,
        state.fingerprint
    )
    print(f"{state_id}: {similarity:.3f}")
```

### Visual Comparison Issues

```python
# Check reference exists
ref_path = fsm._reference_dir / f"{state_id}.png"
print(f"Reference exists: {ref_path.exists()}")

# Capture with debug
fsm.capture_state_screenshot(state_id, reference=False)

# Compare with lower threshold
comparison = fsm.compare_screenshot_with_reference(state_id, threshold=0.95)
print(f"Similarity: {comparison['similarity']:.4f}")

# Check diff image
if not comparison['match']:
    print(f"See diff: {comparison['diff_image_path']}")
```

---

## Performance Tips

### State Detection
- First verification after navigation: ~200ms
- Subsequent verifications: ~100ms
- Detection across all states: ~1-2 seconds

### Navigation
- Average transition execution: ~500ms
- BFS pathfinding: <50ms for 10-state graph
- 10-step navigation: ~5-7 seconds

### Visual Comparison
- Single screenshot capture: ~500ms
- Single comparison: ~1-2 seconds
- Full suite (10 states): ~20-30 seconds

---

**Last Updated**: December 14, 2025  
**Version**: 2.0 - Three-Mode Testing Architecture  
**See Also**: 
- [`FSM_IMPLEMENTATION_GUIDE.md`](./FSM_IMPLEMENTATION_GUIDE.md) - Complete implementation guide
- [`FSM_QUICK_START.md`](./FSM_QUICK_START.md) - Getting started
- [`README.md`](./README.md) - Overview
