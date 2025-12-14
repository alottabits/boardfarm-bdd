# FSM-Based GUI Testing - Implementation Guide

**Last Updated**: December 14, 2025  
**Status**: Ready for Implementation

---

## Overview

This guide documents the implementation of a comprehensive FSM (Finite State Machine) based GUI testing framework for boardfarm using Playwright and the StateExplorer packages.

### Architectural Principle: Separation of Concerns

**FsmGuiComponent provides primitives and data, pytest handles reporting:**

| Layer | Responsibility |
|-------|---------------|
| **FsmGuiComponent** | State management, navigation, element finding, screenshot comparison - **returns data** |
| **GenieAcsGUI** | Business goal methods using FSM primitives - **returns results** |
| **Step Definitions** | Test logic, assertions - **uses primitives** |
| **pytest** | Test execution, reporting, HTML/XML generation - **captures everything** |

The FSM component **never generates reports**. It returns data that tests assert against. pytest captures test results and generates reports with `--html=report.html`.

### Three Testing Modes

This architecture supports **three distinct testing strategies**, all driven by a single source of truth (`fsm_graph.json`):

1. **Functional Testing** - Business goal verification (e.g., "Can I reboot a device via GUI?")
2. **Navigation/Structure Testing** - Graph-based exploration and resilience validation
3. **Visual Regression Testing** - Pixel-perfect screenshot comparison

### Key Components

1. **Generic FSM Components** (~1,200 lines)
   - `FsmGuiComponent` - FSM navigation engine with support for all three testing modes
   - `PlaywrightSyncAdapter` - Browser automation wrapper

2. **Device Integration** (~800 lines)
   - `GenieAcsGUI` - Task-oriented test API with state mappings

3. **Dependencies**
   - `model-resilience-core` - State fingerprinting and matching
   - `aria-state-mapper` - Playwright integration for element location
   - `playwright` - Browser automation

4. **Artifacts**
   - `fsm_graph.json` - FSM state graph from aria-discover tool

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Layer                                │
│  BDD Step Definitions  │  Navigation Tests  │  Visual Tests  │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│              Device Layer (GenieAcsGUI)                      │
│                                                               │
│  • Business goal methods (Mode 1: Functional)                │
│  • STATE_REGISTRY (friendly names → FSM IDs)                 │
│  • Direct FSM access (Mode 2 & 3)                            │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│           Generic Layer (FsmGuiComponent)                    │
│                                                               │
│  • State management & verification                           │
│  • Navigation & pathfinding (BFS)                            │
│  • Element finding (role-based)                              │
│  • Graph structure analysis                                  │
│  • Screenshot capture & comparison                           │
│  • Coverage metrics & reporting                              │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│          StateExplorer Packages                              │
│                                                               │
│  • StateComparer: Fingerprint matching                       │
│  • ElementLocator: Role-based element finding                │
│  • PlaywrightFingerprinter: State capture                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. FsmGuiComponent (Generic Core)

**File**: `boardfarm/boardfarm3/lib/gui/fsm_gui_component.py`  
**Purpose**: Generic FSM-based navigation, structure analysis, and visual regression  
**Size**: ~1,200 lines

#### Responsibilities
- Load and parse `fsm_graph.json` into `UIState` objects
- Track current state with history
- Verify states using multi-dimensional fingerprint matching
- Find elements using role-based locators
- Navigate between states using BFS pathfinding
- **Analyze graph structure for navigation testing**
- **Capture and compare screenshots for visual regression**
- **Generate comprehensive test reports**

#### Key Features
- **Generic**: Works with any FSM graph, not GenieACS-specific
- **Reuses StateExplorer**: Delegates to proven packages
- **Multi-mode**: Supports functional, structural, and visual testing
- **FSM IDs only**: Uses raw state IDs (e.g., `V_LOGIN_FORM_EMPTY`)

#### API

##### Core FSM Primitives

```python
class FsmGuiComponent:
    """Generic FSM GUI component for comprehensive testing."""
    
    def __init__(
        self,
        driver: PlaywrightSyncAdapter,
        fsm_graph_file: Path,
        default_timeout: int = 30,
        match_threshold: float = 0.80,
        screenshot_dir: Path = None
    ):
        """Initialize with FSM graph and driver."""
        pass
    
    # ------------------------------------------------------------------------
    # State Management
    # ------------------------------------------------------------------------
    
    def verify_state(self, state_id: str, timeout: int = 5) -> bool:
        """Verify current UI matches expected state using fingerprint matching."""
        pass
    
    def detect_current_state(self, update_state: bool = True) -> str | None:
        """Detect current state by comparing fingerprints."""
        pass
    
    def get_state(self) -> str | None:
        """Get currently tracked state ID."""
        pass
    
    def set_state(self, state_id: str, via_action: str = None):
        """Manually set current state (with history tracking)."""
        pass
    
    def get_state_history(self) -> list[dict]:
        """Get state transition history for this session."""
        pass
    
    # ------------------------------------------------------------------------
    # Element Finding (Functional Testing)
    # ------------------------------------------------------------------------
    
    def find_element(
        self,
        state_id: str,
        role: str,
        name: str = None,
        timeout: int = None
    ):
        """Find element in current state using role-based locators."""
        pass
    
    def find_all_elements(self, state_id: str, role: str = None) -> list:
        """Find all elements in state (optionally filtered by role)."""
        pass
```

##### Mode 1: Functional Testing Support

```python
    # ------------------------------------------------------------------------
    # Navigation & Transitions
    # ------------------------------------------------------------------------
    
    def navigate_to_state(
        self,
        target_state_id: str,
        max_steps: int = 10,
        record_path: bool = False
    ) -> bool | dict:
        """Navigate from current state to target state using BFS.
        
        Args:
            target_state_id: Destination state
            max_steps: Maximum navigation steps
            record_path: If True, returns dict with path details
            
        Returns:
            bool: True if successful (record_path=False)
            dict: Navigation details (record_path=True)
        """
        pass
    
    def execute_transition(self, transition: StateTransition) -> bool:
        """Execute a specific state transition."""
        pass
    
    def get_available_transitions(
        self,
        from_state_id: str = None
    ) -> list[StateTransition]:
        """Get all available transitions from a state."""
        pass
```

##### Mode 2: Navigation/Structure Testing Support

```python
    # ------------------------------------------------------------------------
    # Graph Structure Analysis
    # ------------------------------------------------------------------------
    
    def get_graph_structure(self) -> dict:
        """Export FSM graph structure for graph-based testing.
        
        Returns:
            {
                'states': [list of state IDs],
                'transitions': [list of transition dicts],
                'adjacency_matrix': [[...]], 
                'state_metadata': {...}
            }
        """
        pass
    
    def export_graphml(self, output_path: Path):
        """Export FSM graph as GraphML for GraphWalker/yEd."""
        pass
    
    def export_dot(self, output_path: Path):
        """Export FSM graph as DOT for Graphviz visualization."""
        pass
    
    def validate_graph_connectivity(self) -> dict:
        """Validate graph structure (dead ends, unreachable states).
        
        Returns:
            {
                'is_connected': bool,
                'unreachable_states': [list],
                'dead_end_states': [list],
                'strongly_connected_components': [[...]],
            }
        """
        pass
    
    def execute_random_walk(
        self,
        num_steps: int,
        start_state: str = None,
        coverage_target: float = None
    ) -> dict:
        """Execute random walk for exploration testing.
        
        Returns:
            {
                'path': [states visited],
                'transitions_executed': [transitions],
                'coverage': float,
                'errors': [failures]
            }
        """
        pass
    
    def execute_path_from_graphwalker(
        self,
        path: list[str]
    ) -> dict:
        """Execute a path generated by GraphWalker.
        
        Returns:
            {
                'success': bool,
                'completed_steps': int,
                'failed_at': str | None,
                'error': str | None
            }
        """
        pass
    
    def calculate_path_coverage(self) -> dict:
        """Calculate coverage metrics for current session.
        
        Returns:
            {
                'states_visited': int,
                'total_states': int,
                'state_coverage': float,
                'transitions_executed': int,
                'total_transitions': int,
                'transition_coverage': float,
                'unvisited_states': [list],
                'unexecuted_transitions': [list]
            }
        """
        pass
```

##### Mode 3: Visual Regression Testing Support

```python
    # ------------------------------------------------------------------------
    # Screenshot Capture & Comparison
    # ------------------------------------------------------------------------
    
    def capture_state_screenshot(
        self,
        state_id: str,
        reference: bool = False
    ) -> Path:
        """Capture screenshot of current state.
        
        Args:
            state_id: State identifier
            reference: If True, save as reference image
            
        Returns:
            Path to saved screenshot
        """
        pass
    
    def compare_screenshot_with_reference(
        self,
        state_id: str,
        threshold: float = 0.95,
        comparison_method: str = 'auto',
        mask_selectors: list[str] = None
    ) -> dict:
        """Compare current screenshot with reference using fuzzy matching.
        
        Primary method: Playwright's built-in comparison (handles anti-aliasing, 
        font rendering differences, supports masking dynamic regions).
        
        Secondary method: SSIM (Structural Similarity) for layout-focused comparison.
        
        Args:
            state_id: State identifier
            threshold: Similarity threshold (0.0-1.0, default 0.95 = 95% similar)
            comparison_method: 'auto', 'playwright', or 'ssim'
            mask_selectors: CSS selectors for regions to ignore (timestamps, counters)
        
        Returns:
            {
                'match': bool,
                'similarity': float,
                'method': str,  # 'playwright' or 'ssim'
                'diff_image_path': Path | None,
                'error': str | None
            }
        """
        pass
    
    def capture_all_states_screenshots(
        self,
        reference: bool = False,
        max_time: int = 300
    ) -> dict:
        """Navigate and capture all state screenshots.
        
        Returns:
            {
                'captured': [state IDs],
                'failed': [state IDs],
                'screenshots': {state_id: path},
                'coverage': float
            }
        """
        pass
    
    def validate_all_states_visually(
        self,
        threshold: float = 0.99
    ) -> dict:
        """Navigate and compare all states with references.
        
        Returns:
            {
                'passed': [state IDs],
                'failed': [state IDs],
                'results': {state_id: comparison},
                'overall_pass': bool
            }
        """
        pass
```

##### Graph Metadata (Data Providers)

```python
    # ------------------------------------------------------------------------
    # Metadata Access (for test assertions)
    # ------------------------------------------------------------------------
    
    def get_state_metadata(self, state_id: str) -> dict:
        """Get complete metadata for a state from FSM graph.
        
        Returns state data for test validation and debugging.
        """
        pass
    
    def get_transition_metadata(
        self,
        from_state: str,
        to_state: str
    ) -> StateTransition | None:
        """Get transition metadata between two states.
        
        Returns transition data for test validation.
        """
        pass
```

#### Internal Structure

```python
class FsmGuiComponent:
    # FSM graph data (from fsm_graph.json)
    _states: dict[str, UIState]              # FSM ID → UIState object
    _transitions: list[StateTransition]       # All transitions
    _transition_map: dict[str, list]          # From state → transitions
    
    # State tracking
    _current_state: str | None                # Current FSM state ID
    _state_history: list[dict]                # Navigation history
    
    # StateExplorer components
    _comparer: StateComparer                  # From model-resilience-core
    _element_locator: ElementLocator          # From aria-state-mapper
    
    # Visual testing
    _screenshot_dir: Path                     # Screenshot storage
    _reference_dir: Path                      # Reference images
    
    # Coverage tracking
    _visited_states: set[str]                 # States visited this session
    _executed_transitions: set[str]           # Transitions executed
    
    # Configuration
    _driver: PlaywrightSyncAdapter
    _default_timeout: int
    _match_threshold: float
```

---

### 2. PlaywrightSyncAdapter

**File**: `boardfarm/boardfarm3/lib/gui/playwright_sync_adapter.py`  
**Purpose**: Synchronous wrapper for Playwright with StateExplorer integration  
**Size**: ~200 lines

#### Responsibilities
- Launch and manage Playwright browser (sync API)
- Provide page navigation methods
- Integrate AriaSnapshotCapture for state fingerprinting
- Provide screenshot capabilities for visual testing
- Provide utility methods

#### API

```python
class PlaywrightSyncAdapter:
    """Synchronous Playwright driver wrapper."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize adapter."""
        pass
    
    def start(self):
        """Launch browser and create page."""
        pass
    
    def close(self):
        """Close browser."""
        pass
    
    def goto(self, url: str):
        """Navigate to URL."""
        pass
    
    @property
    def page(self):
        """Get Playwright Page object."""
        pass
    
    @property
    def url(self) -> str:
        """Get current URL."""
        pass
    
    def capture_fingerprint(self) -> dict:
        """Capture current page fingerprint using AriaSnapshotCapture."""
        pass
    
    def capture_aria_snapshot(self) -> dict:
        """Capture ARIA accessibility snapshot."""
        pass
    
    def take_screenshot(self, path: str, full_page: bool = True):
        """Take screenshot and save to file."""
        pass
```

---

### 3. GenieAcsGUI (Device Interface)

**File**: `boardfarm/boardfarm3/devices/genie_acs.py`  
**Purpose**: GenieACS-specific GUI interface with task-oriented API  
**Size**: ~800 lines (including state registry)

#### Responsibilities
- Provide task-oriented methods for functional testing (Mode 1)
- Map friendly names to FSM state IDs
- Encapsulate GenieACS-specific UI logic
- Provide direct FSM access for structural and visual testing (Modes 2 & 3)
- Hide FSM complexity from test authors

#### State Registry

```python
class GenieAcsGUI(ACSGUI):
    """GenieACS GUI interface with FSM support."""
    
    # GenieACS-specific state mappings
    STATE_REGISTRY = {
        'login_page': 'V_LOGIN_FORM_EMPTY',
        'home_page': 'V_OVERVIEW_PAGE',
        'device_list_page': 'V_DEVICES',
        'device_details_page': 'V_DEVICE_DETAILS',
        'faults_page': 'V_FAULTS',
        'admin_page': 'V_ADMIN_PRESETS',
    }
```

#### API Structure

```python
class GenieAcsGUI(ACSGUI):
    """GenieACS GUI interface."""
    
    def initialize(self, driver=None):
        """Initialize GUI component with FSM engine."""
        pass
    
    # ========================================================================
    # MODE 1: FUNCTIONAL TESTING - High-Level Business Goals
    # ========================================================================
    
    # Authentication
    def login(self, username: str = None, password: str = None) -> bool:
        """Login to GenieACS GUI."""
        pass
    
    def logout(self) -> bool:
        """Logout from GenieACS GUI."""
        pass
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        pass
    
    # Device operations
    def reboot_device_via_gui(self, cpe_id: str) -> bool:
        """Reboot device using GUI."""
        pass
    
    def get_device_status(self, cpe_id: str) -> dict:
        """Get device status information."""
        pass
    
    def verify_device_online(self, cpe_id: str, timeout: int = 60) -> bool:
        """Verify device is online."""
        pass
    
    # ... additional business goal methods
    
    # ========================================================================
    # MODE 2 & 3: DIRECT FSM ACCESS
    # ========================================================================
    
    @property
    def fsm(self) -> FsmGuiComponent:
        """Direct access to FSM component for navigation/visual testing.
        
        Use this for:
        - Graph-based navigation testing (Mode 2)
        - Visual regression testing (Mode 3)
        """
        return self._fsm_component
    
    # ========================================================================
    # MODE 3: VISUAL REGRESSION HELPERS
    # ========================================================================
    
    def capture_reference_screenshots(self) -> dict:
        """Capture reference screenshots of all GenieACS states.
        
        GenieACS-specific: ensures login first, handles session.
        """
        pass
    
    def validate_ui_against_references(self, threshold: float = 0.99) -> dict:
        """Validate all states against reference screenshots."""
        pass
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    def _get_fsm_state_id(self, friendly_name: str) -> str:
        """Convert friendly name to FSM state ID."""
        return self.STATE_REGISTRY.get(friendly_name, friendly_name)
```

---

## Configuration

### Boardfarm Config

**File**: `bf_config/boardfarm_config_example.json`

```json
{
  "name": "genieacs",
  "type": "bf_acs",
  "connection_type": "local_cmd",
  "ipaddr": "127.0.0.1",
  "gui_port": 3000,
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

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `gui_fsm_graph_file` | Path to fsm_graph.json artifact | Required |
| `gui_headless` | Run browser in headless mode | `true` |
| `gui_default_timeout` | Default timeout in seconds | `30` |
| `gui_state_match_threshold` | State matching threshold (0.0-1.0) | `0.80` |
| `gui_screenshot_dir` | Screenshot storage directory | `"bf_config/gui_artifacts/{device}/screenshots"` |
| `gui_visual_threshold` | Visual similarity threshold (0.0-1.0) | `0.95` |
| `gui_visual_comparison_method` | Visual comparison method | `"auto"` |
| `gui_visual_mask_selectors` | CSS selectors to mask (dynamic regions) | `[]` |
| `gui_port` | GUI web server port | `3000` |
| `http_username` | Login username | `"admin"` |
| `http_password` | Login password | `"admin"` |

---

## Dependencies

### Python Packages

Add to `boardfarm/pyproject.toml`:

```toml
[project.dependencies]
playwright = ">=1.40.0"        # Browser automation + built-in visual comparison
scikit-image = ">=0.22.0"      # SSIM for structural similarity comparison
numpy = ">=1.24.0"             # Array operations for image processing
pillow = ">=10.0.0"            # Image loading and manipulation
networkx = ">=3.0"             # Graph analysis for navigation testing

# StateExplorer packages (local development)
model-resilience-core = { path = "../StateExplorer/packages/model-resilience-core", develop = true }
aria-state-mapper = { path = "../StateExplorer/packages/aria-state-mapper", develop = true }
```

### Installation

```bash
cd ~/projects/req-tst/boardfarm

# Install StateExplorer packages (editable mode)
pip install -e ../StateExplorer/packages/model-resilience-core
pip install -e ../StateExplorer/packages/aria-state-mapper

# Install Playwright and visual comparison dependencies
pip install playwright scikit-image numpy pillow networkx
playwright install chromium

# Verify installation
python -c "
from model_resilience_core.models import UIState
from model_resilience_core.matching import StateComparer
from aria_state_mapper.playwright_integration import ElementLocator
from playwright.sync_api import sync_playwright
from skimage.metrics import structural_similarity
import numpy as np
from PIL import Image
print('✅ All dependencies installed')
"
```

---

## Implementation Plan

### Phase 1: Generic Components (Week 1)

#### Tasks

**1. Install Dependencies**
- [ ] Install model-resilience-core (editable)
- [ ] Install aria-state-mapper (editable)
- [ ] Install Playwright, Pillow, NetworkX
- [ ] Verify imports work

**2. Create FsmGuiComponent - Core** (~400 lines)
- [ ] Graph loading: Parse `fsm_graph.json` into `UIState` objects
- [ ] State tracking: `set_state()`, `get_state()`, history
- [ ] Verification: `verify_state()` using `StateComparer`
- [ ] Element finding: `find_element()` using `ElementLocator`
- [ ] Navigation: BFS pathfinding algorithm
- [ ] Transition execution: Click, submit, navigate actions
- [ ] State detection: `detect_current_state()` using fuzzy matching

**3. Create FsmGuiComponent - Structure Testing** (~400 lines)
- [ ] Graph structure export: `get_graph_structure()`
- [ ] Graph validation: `validate_graph_connectivity()`
- [ ] Random walk: `execute_random_walk()`
- [ ] GraphWalker integration: `execute_path_from_graphwalker()`
- [ ] Coverage metrics: `calculate_path_coverage()`
- [ ] Export formats: `export_graphml()`, `export_dot()`

**4. Create FsmGuiComponent - Visual Testing** (~400 lines)
- [ ] Screenshot capture: `capture_state_screenshot()`
- [ ] Screenshot comparison with Playwright (primary): `_compare_playwright()`
- [ ] Screenshot comparison with SSIM (secondary): `_compare_ssim()`
- [ ] Intelligent method selection: `compare_screenshot_with_reference()`
- [ ] Batch capture: `capture_all_states_screenshots()`
- [ ] Batch validation: `validate_all_states_visually()`

**5. Create PlaywrightSyncAdapter** (~200 lines)
- [ ] Browser initialization (sync_playwright)
- [ ] Page navigation methods
- [ ] AriaSnapshotCapture integration
- [ ] Fingerprint capture delegation
- [ ] Screenshot utilities

**6. Unit Testing**
- [ ] Test graph loading and parsing
- [ ] Test state tracking and history
- [ ] Test BFS pathfinding algorithm
- [ ] Test coverage calculation
- [ ] Test screenshot comparison
- [ ] Mock StateExplorer components
- [ ] Target: 90%+ coverage

**Deliverables**:
- `boardfarm3/lib/gui/fsm_gui_component.py` (~1,200 lines)
- `boardfarm3/lib/gui/playwright_sync_adapter.py` (~200 lines)
- Unit tests in `boardfarm/unittests/lib/gui/`

---

### Phase 2: Device Integration (Week 2)

#### Tasks

**1. Add STATE_REGISTRY to GenieAcsGUI**
- [ ] Define state mappings (friendly → FSM IDs)
- [ ] Implement `_get_fsm_state_id()` helper
- [ ] Implement `_get_friendly_name()` helper

**2. Update Initialization**
- [ ] Remove Selenium imports
- [ ] Create PlaywrightSyncAdapter in `initialize()`
- [ ] Create FsmGuiComponent with FSM graph path
- [ ] Handle configuration errors gracefully

**3. Implement Mode 1: Business Goal Methods**
- [ ] Rewrite `login()` using FSM component
- [ ] Rewrite `logout()` using FSM component
- [ ] Rewrite `is_logged_in()` using state detection
- [ ] Rewrite `reboot_device_via_gui()`
- [ ] Rewrite `get_device_status()`
- [ ] Rewrite `verify_device_online()`

**4. Add Mode 2 & 3: Direct FSM Access**
- [ ] Add `fsm` property for direct access
- [ ] Implement `capture_reference_screenshots()`
- [ ] Implement `validate_ui_against_references()`

**5. Remove Legacy Code**
- [ ] Delete all Selenium references
- [ ] Delete POM-related helpers
- [ ] Clean up imports

**Deliverables**:
- Updated `genie_acs.py` with FSM support
- Integration test: login/logout flow
- All task-oriented methods working

---

### Phase 3: Testing Examples (Week 3)

#### Mode 1: Functional Testing

```python
# tests/features/device_management.feature
@when("the operator reboots the device via the ACS GUI")
def step_reboot_device(acs, bf_context):
    """Functional test: Business goal verification."""
    success = acs.gui.reboot_device_via_gui(bf_context.cpe_id)
    assert success, "Failed to reboot device"

@then("the device should be online in the ACS GUI")
def step_verify_online(acs, bf_context):
    """Functional test: Verify outcome."""
    is_online = acs.gui.verify_device_online(bf_context.cpe_id, timeout=120)
    assert is_online, "Device did not come online"
```

#### Mode 2: Navigation/Structure Testing

```python
# tests/test_gui_navigation_structure.py

def test_graph_structure_validation(acs):
    """Verify FSM graph has no structural issues."""
    acs.gui.initialize()
    acs.gui.login()
    
    validation = acs.gui.fsm.validate_graph_connectivity()
    
    assert validation['is_connected'], "Graph not fully connected"
    assert len(validation['unreachable_states']) == 0, \
        f"Unreachable states: {validation['unreachable_states']}"
    assert len(validation['dead_end_states']) == 0, \
        f"Dead end states: {validation['dead_end_states']}"

def test_random_navigation_resilience(acs):
    """Test UI resilience with random walk.
    
    Run with: pytest --html=report.html --self-contained-html
    """
    acs.gui.initialize()
    acs.gui.login()
    
    result = acs.gui.fsm.execute_random_walk(
        num_steps=50,
        coverage_target=0.80
    )
    
    # Component provides data, test makes assertions
    assert len(result['errors']) == 0, \
        f"Errors during random walk: {result['errors']}"
    assert result['coverage'] >= 0.70, \
        f"Low coverage: {result['coverage']}"
    
    # pytest automatically captures and reports these results

def test_state_coverage_completeness(acs):
    """Verify all documented states are reachable."""
    acs.gui.initialize()
    acs.gui.login()
    
    graph = acs.gui.fsm.get_graph_structure()
    
    # Try to reach each state
    for state_id in graph['states']:
        success = acs.gui.fsm.navigate_to_state(state_id, max_steps=10)
        assert success, f"Could not reach state: {state_id}"
    
    # Verify complete coverage
    coverage = acs.gui.fsm.calculate_path_coverage()
    assert coverage['state_coverage'] == 1.0, \
        f"Not all states reachable: {coverage['unvisited_states']}"
```

#### Mode 3: Visual Regression Testing

```python
# tests/test_gui_visual_regression.py

def test_capture_reference_screenshots(acs):
    """Capture reference screenshots for all states (run once)."""
    acs.gui.initialize()
    acs.gui.login()
    
    result = acs.gui.capture_reference_screenshots()
    
    assert len(result['failed']) == 0, \
        f"Failed to capture: {result['failed']}"
    assert result['coverage'] >= 0.95, \
        f"Low coverage: {result['coverage']}"

def test_visual_regression_validation(acs):
    """Compare current UI against reference screenshots using Playwright.
    
    Run with: pytest --html=report.html --self-contained-html
    Diff images saved to: bf_config/gui_artifacts/genieacs/screenshots/
    """
    acs.gui.initialize()
    acs.gui.login()
    
    # Use Playwright's built-in comparison (default)
    result = acs.gui.validate_ui_against_references(
        threshold=0.95,  # 95% similarity
        comparison_method='playwright'
    )
    
    # Component provides data and saves diff images automatically
    # pytest captures the assertion and includes it in HTML report
    assert result['overall_pass'], \
        f"Visual regression failures: {result['failed']}\n" \
        f"See diff images in screenshot directory"

def test_login_page_visual_stability(acs):
    """Verify specific state hasn't changed visually with dynamic region masking."""
    acs.gui.initialize()
    
    driver = acs.gui._driver
    driver.goto(f"{acs.gui._gui_base_url}/#!/login")
    
    login_state = acs.gui._get_fsm_state_id('login_page')
    
    # Compare with Playwright, masking dynamic regions
    comparison = acs.gui.fsm.compare_screenshot_with_reference(
        login_state,
        threshold=0.95,
        comparison_method='playwright',
        mask_selectors=['.timestamp', '.version-info']  # Ignore dynamic content
    )
    
    assert comparison['match'], \
        f"Login page changed! Similarity: {comparison['similarity']:.2%}"

def test_form_layout_stability_ssim(acs):
    """Verify form layout using SSIM (structure-focused)."""
    acs.gui.initialize()
    acs.gui.login()
    
    # Navigate to device details (has forms)
    device_state = acs.gui._get_fsm_state_id('device_details_page')
    acs.gui.fsm.navigate_to_state(device_state)
    
    # Use SSIM for layout verification (more tolerant of color variations)
    comparison = acs.gui.fsm.compare_screenshot_with_reference(
        device_state,
        threshold=0.95,
        comparison_method='ssim'  # Structure-focused
    )
    
    assert comparison['match'], \
        f"Layout changed! SSIM: {comparison['similarity']:.2%}"

def test_visual_regression_auto_method(acs):
    """Test with automatic method selection based on state type.
    
    Component automatically selects best comparison method per state type.
    """
    acs.gui.initialize()
    acs.gui.login()
    
    # Auto-select best comparison method per state
    result = acs.gui.validate_ui_against_references(
        threshold=0.95,
        comparison_method='auto'  # Intelligent selection
    )
    
    # Log details for debugging (pytest captures stdout)
    if not result['overall_pass']:
        print("\nVisual regression details:")
        for state_id, details in result['results'].items():
            status = "✓" if details['match'] else "✗"
            print(f"{status} {state_id}: {details['method']} - {details['similarity']:.2%}")
    
    # pytest captures this assertion and includes in report
    assert result['overall_pass'], f"Visual failures: {result['failed']}"
```

---

### Visual Comparison Implementation Details

#### Playwright Method (Primary - Recommended)

**Advantages**:
- Built-in to Playwright (no extra dependencies beyond basic install)
- Handles anti-aliasing and font rendering differences
- Can mask dynamic regions (timestamps, live counters)
- Generates diff images automatically
- Battle-tested by thousands of projects

**Implementation**:

```python
def _compare_playwright(
    self,
    state_id: str,
    threshold: float = 0.95,
    mask_selectors: list[str] = None
) -> dict:
    """Compare using Playwright's built-in visual comparison.
    
    This method handles anti-aliasing, font rendering, and dynamic content.
    """
    from playwright.sync_api import expect
    
    reference_path = self._reference_dir / f"{state_id}.png"
    
    if not reference_path.exists():
        return {
            'match': False,
            'similarity': 0.0,
            'method': 'playwright',
            'error': 'Reference image not found'
        }
    
    try:
        # Build mask list from selectors
        masks = []
        if mask_selectors:
            for selector in mask_selectors:
                try:
                    masks.append(self._driver.page.locator(selector))
                except Exception:
                    pass  # Selector not found, skip
        
        # Playwright's visual comparison
        expect(self._driver.page).to_have_screenshot(
            str(reference_path),
            threshold=1.0 - threshold,  # Playwright uses inverse (0 = strict)
            max_diff_pixels=int((1.0 - threshold) * 1920 * 1080),  # Rough estimate
            mask=masks if masks else None
        )
        
        return {
            'match': True,
            'similarity': 1.0,
            'method': 'playwright',
            'error': None
        }
        
    except AssertionError as e:
        # Comparison failed - diff image auto-generated by Playwright
        error_msg = str(e)
        
        # Try to extract similarity from error message
        similarity = 0.0
        # Playwright error format: "Screenshot comparison failed: ..."
        
        return {
            'match': False,
            'similarity': similarity,
            'method': 'playwright',
            'error': error_msg,
            'diff_image_path': self._screenshot_dir / f"{state_id}-diff.png"
        }
```

#### SSIM Method (Secondary - Layout-Focused)

**Advantages**:
- Focuses on **structure** (layout, element positioning)
- More tolerant of color variations and font changes
- Industry standard for image quality comparison
- Good for detecting layout shifts

**Use Cases**:
- Form layouts where structure matters more than exact appearance
- Complex pages with color themes
- Responsive layouts

**Implementation**:

```python
def _compare_ssim(
    self,
    state_id: str,
    threshold: float = 0.95
) -> dict:
    """Compare using SSIM (Structural Similarity Index).
    
    Focuses on layout structure rather than pixel-perfect matching.
    """
    from PIL import Image
    from skimage.metrics import structural_similarity as ssim
    import numpy as np
    
    # Capture current screenshot
    current_path = self.capture_state_screenshot(state_id, reference=False)
    reference_path = self._reference_dir / f"{state_id}.png"
    
    if not reference_path.exists():
        return {
            'match': False,
            'similarity': 0.0,
            'method': 'ssim',
            'error': 'Reference image not found'
        }
    
    try:
        # Load images
        current_img = Image.open(current_path).convert('RGB')
        reference_img = Image.open(reference_path).convert('RGB')
        
        # Ensure same size (resize if needed)
        if current_img.size != reference_img.size:
            _LOGGER.warning(
                "Image size mismatch for %s: %s vs %s, resizing",
                state_id, current_img.size, reference_img.size
            )
            current_img = current_img.resize(reference_img.size)
        
        # Convert to numpy arrays
        current_array = np.array(current_img)
        reference_array = np.array(reference_img)
        
        # Calculate SSIM (multichannel for RGB)
        similarity, diff_image = ssim(
            reference_array,
            current_array,
            multichannel=True,
            channel_axis=2,
            full=True
        )
        
        match = similarity >= threshold
        
        # Save diff image if mismatch
        diff_path = None
        if not match:
            diff_path = self._screenshot_dir / f"{state_id}_ssim_diff.png"
            # Normalize diff image to 0-255 range
            diff_normalized = ((1.0 - diff_image) * 255).astype(np.uint8)
            Image.fromarray(diff_normalized).save(diff_path)
            
            _LOGGER.warning(
                "SSIM comparison failed for %s: %.2f%% (threshold: %.2f%%)",
                state_id, similarity * 100, threshold * 100
            )
        
        return {
            'match': match,
            'similarity': similarity,
            'method': 'ssim',
            'error': None,
            'diff_image_path': diff_path
        }
        
    except Exception as e:
        return {
            'match': False,
            'similarity': 0.0,
            'method': 'ssim',
            'error': str(e)
        }
```

#### Intelligent Method Selection

```python
def compare_screenshot_with_reference(
    self,
    state_id: str,
    threshold: float = 0.95,
    comparison_method: str = 'auto',
    mask_selectors: list[str] = None
) -> dict:
    """Compare with automatic method selection.
    
    Args:
        state_id: State to compare
        threshold: Similarity threshold (0.0-1.0)
        comparison_method: 'auto', 'playwright', or 'ssim'
        mask_selectors: CSS selectors for regions to ignore (Playwright only)
    """
    # Auto-select best method based on state type
    if comparison_method == 'auto':
        state = self._states.get(state_id)
        
        if state and state.state_type == 'form':
            # Forms: Use SSIM (layout-focused)
            method = 'ssim'
            _LOGGER.debug("Auto-selected SSIM for form state: %s", state_id)
        elif state and 'login' in state_id.lower():
            # Login pages: Use Playwright (may have dynamic content)
            method = 'playwright'
            _LOGGER.debug("Auto-selected Playwright for login state: %s", state_id)
        else:
            # Default: Use Playwright (balanced)
            method = 'playwright'
            _LOGGER.debug("Auto-selected Playwright (default) for: %s", state_id)
    else:
        method = comparison_method
    
    # Execute comparison
    if method == 'playwright':
        return self._compare_playwright(state_id, threshold, mask_selectors)
    elif method == 'ssim':
        return self._compare_ssim(state_id, threshold)
    else:
        raise ValueError(f"Unknown comparison method: {method}")
```

---

### Phase 4: Configuration & Artifacts (Week 3)

#### Tasks

**1. Update Boardfarm Config**
- [ ] Add `gui_fsm_graph_file` parameter
- [ ] Add `gui_screenshot_dir` parameter
- [ ] Add `gui_visual_threshold` parameter
- [ ] Add `gui_visual_comparison_method` parameter
- [ ] Remove old POM parameters

**2. Organize FSM Artifacts**
- [ ] Create `bf_config/gui_artifacts/genieacs/` directory structure:
  ```
  bf_config/
    gui_artifacts/
      genieacs/
        fsm_graph.json          # FSM state graph
        screenshots/            # Test screenshots
          references/           # Reference images for visual regression
  ```
- [ ] Copy `fsm_graph.json` to artifacts directory
- [ ] Update config to point to correct paths

**3. Update Dependencies**
- [ ] Add model-resilience-core to pyproject.toml
- [ ] Add aria-state-mapper to pyproject.toml
- [ ] Add playwright, pillow, networkx to pyproject.toml
- [ ] Document installation steps

**Deliverables**:
- Updated `boardfarm_config_example.json`
- FSM graph in proper location
- Updated `pyproject.toml`

---

### Phase 5: Documentation & Examples (Week 4)

#### Tasks

**1. Update Documentation**
- [ ] Update `boardfarm3/lib/gui/README.md`
- [ ] Update `boardfarm3/devices/README.md`
- [ ] Create mode-specific usage guides
- [ ] Create troubleshooting guide

**2. Create Example Tests**
- [ ] Functional test examples (Mode 1)
- [ ] Navigation test examples (Mode 2)
- [ ] Visual regression test examples (Mode 3)
- [ ] GraphWalker integration example

**3. Create Helper Scripts**
- [ ] Script to regenerate FSM graph
- [ ] Script to capture reference screenshots
- [ ] Script to run visual regression suite
- [ ] Script to generate coverage reports

**Deliverables**:
- Complete documentation
- Example test suite
- Helper scripts

---

## Success Metrics

### Code Quality
- Generic components: 90%+ test coverage
- Device integration: 85%+ test coverage
- Zero linter errors
- Type hints throughout

### Performance
- State detection: ≥95% accuracy (fingerprint matching)
- Navigation: ≥98% success rate (BFS pathfinding)
- Visual comparison: 
  - Playwright: <1 second per screenshot
  - SSIM: <2 seconds per screenshot
  - Batch (10 states): <15 seconds
- Test execution: Similar to or faster than Selenium

### Maintainability
- FSM graph regeneration: <5 minutes
- State registry updates: <5 minutes
- Adding new device: <1 day
- Reference screenshot update: <10 minutes

### Testing Capabilities
- **Mode 1**: All business goals testable via GUI
- **Mode 2**: 100% state coverage achievable
- **Mode 3**: Fuzzy visual validation with intelligent comparison
  - Playwright: Handles anti-aliasing, font rendering, dynamic content masking
  - SSIM: Structure-focused, layout verification, color-tolerant
  - Auto-selection: Best method per state type

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Generic Components | FsmGuiComponent (all modes), PlaywrightSyncAdapter |
| 2 | Device Integration | Updated GenieAcsGUI with STATE_REGISTRY |
| 3 | Testing Examples | Mode 1, 2, 3 test suites, configuration |
| 4 | Documentation | Complete docs, examples, helper scripts |

**Total Duration**: 4 weeks

---

## Troubleshooting

### FSM Graph Regeneration

If UI changes and state detection fails:

```bash
cd ~/projects/req-tst/StateExplorer
source .venv/bin/activate

# Regenerate FSM graph
aria-discover --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output ~/projects/req-tst/boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json
```

### State Registry Updates

If new states are needed, update `GenieAcsGUI.STATE_REGISTRY`:

```python
STATE_REGISTRY = {
    'login_page': 'V_LOGIN_FORM_EMPTY',
    'new_page': 'V_NEW_STATE_ID',  # ← Add new mapping
}
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('boardfarm3.lib.gui').setLevel(logging.DEBUG)
```

### Visual Regression Issues

If visual comparisons fail unexpectedly:

**1. Check browser window size (must be consistent)**

```python
# Ensure consistent viewport
self._driver.page.set_viewport_size({"width": 1920, "height": 1080})
```

**2. Verify reference images exist**

```bash
ls -lh bf_config/gui_artifacts/genieacs/screenshots/references/
```

**3. Use appropriate comparison method**

- **Playwright** (default): Good for general UI, handles anti-aliasing
- **SSIM**: Better for layouts/forms, tolerates color variations

```python
# Try SSIM if Playwright is too strict
comparison = fsm.compare_screenshot_with_reference(
    state_id,
    threshold=0.95,
    comparison_method='ssim'
)
```

**4. Mask dynamic regions**

```python
# Ignore timestamps, counters, live data
comparison = fsm.compare_screenshot_with_reference(
    state_id,
    threshold=0.95,
    mask_selectors=[
        '.timestamp',
        '.live-counter',
        '[data-dynamic="true"]'
    ]
)
```

**5. Adjust threshold for acceptable differences**

- `0.99` = Very strict (99% similar)
- `0.95` = Recommended (95% similar)
- `0.90` = Lenient (90% similar)

```python
# More lenient for dynamic pages
comparison = fsm.compare_screenshot_with_reference(
    state_id,
    threshold=0.90  # Allow 10% difference
)
```

**6. Review diff images**

```python
# Diff images saved automatically on mismatch
if not comparison['match']:
    print(f"See diff: {comparison['diff_image_path']}")
    # Playwright: state_id-diff.png
    # SSIM: state_id_ssim_diff.png
```

**7. Debug similarity scores**

```python
# Enable debug logging to see scores
import logging
logging.getLogger('boardfarm3.lib.gui').setLevel(logging.DEBUG)

# Compare and check score
comparison = fsm.compare_screenshot_with_reference(state_id)
print(f"Similarity: {comparison['similarity']:.4f} (threshold: 0.95)")
print(f"Method: {comparison['method']}")
```

**8. Common false positives**

- **Animations**: Wait for animations to complete before capture
- **Fonts**: Ensure same fonts installed (or use SSIM)
- **Browser differences**: Use same browser/version for references
- **Timestamps/dates**: Always mask with `mask_selectors`
- **Random content**: Mask or regenerate references

---

## Additional Resources

### StateExplorer Documentation
- `StateExplorer/docs/architecture/FINGERPRINTING_STRATEGY.md`
- `StateExplorer/docs/architecture/FSM_VS_POM.md`
- `StateExplorer/docs/guides/GETTING_STARTED.md`

### Related Files
- `FSM_API_REFERENCE.md` - Quick API reference
- `FSM_QUICK_START.md` - Getting started guide
- `fsm_graph.json` - FSM state graph artifact

### External Tools
- **GraphWalker**: Model-based testing tool (https://graphwalker.github.io/)
- **yEd**: Graph visualization tool (https://www.yworks.com/products/yed)
- **Graphviz**: Graph rendering (https://graphviz.org/)

---

**Last Updated**: December 14, 2025  
**Version**: 2.0 - Three-Mode Comprehensive Testing Architecture
