# FSM GUI Testing - Quick Start Guide

**Last Updated**: December 14, 2025

---

## Overview

This guide will help you quickly set up and start implementing FSM-based GUI testing for boardfarm with support for **three testing modes**:

1. **Functional Testing** - Verify business goals (e.g., "Can I reboot a device?")
2. **Navigation Testing** - Validate graph structure and UI resilience
3. **Visual Regression** - Pixel-perfect screenshot comparison

---

## Prerequisites

- Python 3.12+ with virtual environment
- Access to GenieACS running at http://localhost:3000
- StateExplorer monorepo at `~/projects/req-tst/StateExplorer`
- Boardfarm repository at `~/projects/req-tst/boardfarm`

---

## Step 1: Install Dependencies

```bash
# Activate boardfarm environment
cd ~/projects/req-tst/boardfarm
source .venv-3.12/bin/activate

# Install StateExplorer packages (editable mode)
pip install -e ../StateExplorer/packages/model-resilience-core
pip install -e ../StateExplorer/packages/aria-state-mapper

# Install Playwright and visual comparison dependencies
pip install playwright scikit-image numpy pillow networkx
playwright install chromium

# Verify installation
python3 << 'EOF'
from model_resilience_core.models import UIState
from model_resilience_core.matching import StateComparer
from aria_state_mapper.playwright_integration import ElementLocator
from playwright.sync_api import sync_playwright
from PIL import Image
from skimage.metrics import structural_similarity
import numpy as np
import networkx as nx
print("✅ All dependencies installed successfully!")
EOF
```

---

## Step 2: Verify FSM Graph

Check that you have the FSM graph artifact:

```bash
ls -lh ~/projects/req-tst/boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json
```

If missing, regenerate it:

```bash
cd ~/projects/req-tst/StateExplorer
source .venv/bin/activate

aria-discover --url http://localhost:3000 \
  --username admin \
  --password admin \
  --max-states 100 \
  --output ~/projects/req-tst/boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json
```

---

## Step 3: Implement FsmGuiComponent

**File**: `boardfarm/boardfarm3/lib/gui/fsm_gui_component.py`

### Minimal Implementation (Core Features)

```python
"""FSM-based GUI component for comprehensive testing."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque

from model_resilience_core.models import UIState, StateTransition
from model_resilience_core.matching import StateComparer
from aria_state_mapper.playwright_integration import ElementLocator

_LOGGER = logging.getLogger(__name__)


class FsmGuiComponent:
    """Generic FSM GUI component supporting functional, structural, and visual testing."""
    
    def __init__(
        self,
        driver,
        fsm_graph_file: Path,
        default_timeout: int = 30,
        match_threshold: float = 0.80,
        screenshot_dir: Path = None
    ):
        """Initialize FSM component.
        
        Args:
            driver: PlaywrightSyncAdapter instance
            fsm_graph_file: Path to fsm_graph.json
            default_timeout: Default timeout in seconds
            match_threshold: State matching threshold (0.0-1.0)
            screenshot_dir: Directory for screenshots (None = ./screenshots)
        """
        self._driver = driver
        self._default_timeout = default_timeout
        self._match_threshold = match_threshold
        self._screenshot_dir = screenshot_dir or Path("screenshots")
        self._reference_dir = self._screenshot_dir / "references"
        
        # Create directories
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._reference_dir.mkdir(parents=True, exist_ok=True)
        
        # FSM graph data
        self._states: Dict[str, UIState] = {}
        self._transitions: List[StateTransition] = []
        self._transition_map: Dict[str, List[StateTransition]] = {}
        
        # State tracking
        self._current_state: Optional[str] = None
        self._state_history: List[dict] = []
        
        # Coverage tracking
        self._visited_states: set = set()
        self._executed_transitions: set = set()
        
        # Load FSM graph
        self._load_fsm_graph(fsm_graph_file)
        
        # StateExplorer components
        self._comparer = StateComparer(match_threshold=match_threshold)
        self._element_locator = ElementLocator(driver.page)
        
        _LOGGER.info(
            "FsmGuiComponent initialized: %d states, %d transitions",
            len(self._states),
            len(self._transitions)
        )
    
    # ========================================================================
    # CORE PRIMITIVES
    # ========================================================================
    
    def _load_fsm_graph(self, graph_file: Path):
        """Load FSM graph from JSON file."""
        with open(graph_file, 'r') as f:
            data = json.load(f)
        
        # Parse states (handle both 'states' and 'nodes' formats)
        states_data = data.get('states', data.get('nodes', []))
        for state_data in states_data:
            # Handle node_type vs state format
            if 'node_type' in state_data and state_data['node_type'] == 'state':
                state = UIState.from_dict(state_data)
                self._states[state.id] = state
        
        # Parse transitions (handle both 'transitions' and 'edges' formats)
        trans_data = data.get('transitions', data.get('edges', []))
        for trans_dict in trans_data:
            trans = StateTransition.from_dict(trans_dict)
            self._transitions.append(trans)
            
            # Build transition map
            if trans.from_state_id not in self._transition_map:
                self._transition_map[trans.from_state_id] = []
            self._transition_map[trans.from_state_id].append(trans)
    
    def verify_state(self, state_id: str, timeout: int = 5) -> bool:
        """Verify current UI matches expected state."""
        if state_id not in self._states:
            _LOGGER.error("State '%s' not found in FSM graph", state_id)
            return False
        
        expected_state = self._states[state_id]
        current_fp = self._driver.capture_fingerprint()
        
        similarity = self._comparer.calculate_similarity(
            current_fp,
            expected_state.fingerprint
        )
        
        matches = similarity >= self._match_threshold
        
        if matches:
            self.set_state(state_id, via_action='verify')
            self._visited_states.add(state_id)
            _LOGGER.info("State verified: %s (similarity: %.2f)", state_id, similarity)
        else:
            _LOGGER.warning("State mismatch: expected %s, similarity: %.2f", state_id, similarity)
        
        return matches
    
    def find_element(
        self,
        state_id: str,
        role: str,
        name: str = None,
        timeout: int = None
    ):
        """Find element in current state."""
        if state_id not in self._states:
            raise KeyError(f"State '{state_id}' not in FSM graph")
        
        state = self._states[state_id]
        
        return self._element_locator.find_by_role(
            role=role,
            name=name,
            state_descriptors=state.element_descriptors,
            timeout=(timeout or self._default_timeout) * 1000
        )
    
    def get_state(self) -> Optional[str]:
        """Get currently tracked state ID."""
        return self._current_state
    
    def set_state(self, state_id: str, via_action: str = None):
        """Manually set current state."""
        self._current_state = state_id
        self._visited_states.add(state_id)
        self._state_history.append({
            'state_id': state_id,
            'via_action': via_action,
            'timestamp': None
        })
    
    def get_state_history(self) -> List[dict]:
        """Get state transition history."""
        return self._state_history.copy()
    
    # ========================================================================
    # MODE 1: FUNCTIONAL TESTING
    # ========================================================================
    
    def navigate_to_state(
        self,
        target_state_id: str,
        max_steps: int = 10,
        record_path: bool = False
    ):
        """Navigate from current state to target state using BFS."""
        if target_state_id not in self._states:
            _LOGGER.error("Target state '%s' not found", target_state_id)
            return False if not record_path else {'success': False, 'error': 'State not found'}
        
        # Detect current state if unknown
        if not self._current_state:
            self.detect_current_state()
        
        if not self._current_state:
            error = "Cannot navigate: current state unknown"
            _LOGGER.error(error)
            return False if not record_path else {'success': False, 'error': error}
        
        # Already there?
        if self._current_state == target_state_id:
            _LOGGER.info("Already in target state: %s", target_state_id)
            return True if not record_path else {'success': True, 'path': []}
        
        # Find path using BFS
        path = self._find_state_path(self._current_state, target_state_id, max_steps)
        
        if not path:
            error = f"No path found: {self._current_state} -> {target_state_id}"
            _LOGGER.error(error)
            return False if not record_path else {'success': False, 'error': error}
        
        # Execute path
        _LOGGER.info("Executing path: %d steps", len(path))
        for transition in path:
            if not self._execute_transition(transition):
                error = f"Transition failed: {transition.from_state_id} -> {transition.to_state_id}"
                return False if not record_path else {'success': False, 'error': error, 'path': path}
        
        # Verify final state
        success = self.verify_state(target_state_id, timeout=10)
        
        if record_path:
            return {'success': success, 'path': path, 'steps': len(path)}
        return success
    
    def _find_state_path(
        self,
        from_state_id: str,
        to_state_id: str,
        max_steps: int
    ) -> Optional[List[StateTransition]]:
        """Find shortest path using BFS."""
        queue = deque([(from_state_id, [])])
        visited = {from_state_id}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) >= max_steps:
                continue
            
            for transition in self._transition_map.get(current, []):
                next_state = transition.to_state_id
                
                if next_state == to_state_id:
                    return path + [transition]
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [transition]))
        
        return None
    
    def _execute_transition(self, transition: StateTransition) -> bool:
        """Execute a single state transition."""
        _LOGGER.info(
            "Executing: %s -> %s (%s)",
            transition.from_state_id,
            transition.to_state_id,
            transition.action_type
        )
        
        try:
            if transition.action_type == 'click':
                element = self.find_element(
                    transition.from_state_id,
                    transition.element_role,
                    transition.element_name
                )
                element.click()
            elif transition.action_type == 'navigate':
                self._driver.goto(transition.target_url)
            elif transition.action_type == 'submit':
                element = self.find_element(
                    transition.from_state_id,
                    transition.element_role,
                    transition.element_name
                )
                element.click()
            
            # Track execution
            trans_id = f"{transition.from_state_id}->{transition.to_state_id}"
            self._executed_transitions.add(trans_id)
            
            # Update state
            self.set_state(transition.to_state_id, via_action=transition.action_type)
            return True
            
        except Exception as e:
            _LOGGER.error("Transition failed: %s", e)
            return False
    
    def detect_current_state(self, update_state: bool = True) -> Optional[str]:
        """Detect current state by comparing fingerprints."""
        current_fp = self._driver.capture_fingerprint()
        
        best_match = None
        best_similarity = 0.0
        
        for state_id, state in self._states.items():
            similarity = self._comparer.calculate_similarity(
                current_fp,
                state.fingerprint
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = state_id
        
        if best_match and best_similarity >= self._match_threshold:
            if update_state:
                self.set_state(best_match, via_action='detect')
            _LOGGER.info("State detected: %s (similarity: %.2f)", best_match, best_similarity)
            return best_match
        
        _LOGGER.warning("No matching state found (best: %.2f)", best_similarity)
        return None
    
    # ========================================================================
    # MODE 2: NAVIGATION/STRUCTURE TESTING
    # ========================================================================
    
    def get_graph_structure(self) -> dict:
        """Export FSM graph structure for analysis."""
        return {
            'states': list(self._states.keys()),
            'transitions': [
                {
                    'from': t.from_state_id,
                    'to': t.to_state_id,
                    'action': t.action_type
                }
                for t in self._transitions
            ],
            'state_count': len(self._states),
            'transition_count': len(self._transitions)
        }
    
    def calculate_path_coverage(self) -> dict:
        """Calculate coverage metrics for current session."""
        total_states = len(self._states)
        visited_count = len(self._visited_states)
        
        total_transitions = len(self._transitions)
        executed_count = len(self._executed_transitions)
        
        unvisited_states = set(self._states.keys()) - self._visited_states
        
        return {
            'states_visited': visited_count,
            'total_states': total_states,
            'state_coverage': visited_count / total_states if total_states > 0 else 0.0,
            'transitions_executed': executed_count,
            'total_transitions': total_transitions,
            'transition_coverage': executed_count / total_transitions if total_transitions > 0 else 0.0,
            'unvisited_states': list(unvisited_states),
        }
    
    # ========================================================================
    # MODE 3: VISUAL REGRESSION TESTING
    # ========================================================================
    
    def capture_state_screenshot(
        self,
        state_id: str,
        reference: bool = False
    ) -> Path:
        """Capture screenshot of current state."""
        dir_path = self._reference_dir if reference else self._screenshot_dir
        filename = f"{state_id}.png"
        filepath = dir_path / filename
        
        self._driver.take_screenshot(str(filepath), full_page=True)
        _LOGGER.info("Screenshot saved: %s", filepath)
        
        return filepath
    
    def compare_screenshot_with_reference(
        self,
        state_id: str,
        threshold: float = 0.95,
        comparison_method: str = 'auto',
        mask_selectors: list[str] = None
    ) -> dict:
        """Compare with Playwright (primary) or SSIM (secondary).
        
        Args:
            state_id: State to compare
            threshold: Similarity threshold (0.0-1.0)
            comparison_method: 'auto', 'playwright', or 'ssim'
            mask_selectors: CSS selectors to ignore (Playwright only)
        """
        # Auto-select method based on state type
        if comparison_method == 'auto':
            state = self._states.get(state_id)
            method = 'ssim' if state and state.state_type == 'form' else 'playwright'
        else:
            method = comparison_method
        
        if method == 'playwright':
            return self._compare_playwright(state_id, threshold, mask_selectors)
        elif method == 'ssim':
            return self._compare_ssim(state_id, threshold)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _compare_playwright(self, state_id: str, threshold: float, mask_selectors: list = None) -> dict:
        """Compare using Playwright's built-in comparison."""
        from playwright.sync_api import expect
        
        reference_path = self._reference_dir / f"{state_id}.png"
        
        if not reference_path.exists():
            return {'match': False, 'similarity': 0.0, 'method': 'playwright', 'error': 'No reference'}
        
        try:
            # Build mask list
            masks = []
            if mask_selectors:
                for selector in mask_selectors:
                    try:
                        masks.append(self._driver.page.locator(selector))
                    except:
                        pass
            
            # Playwright comparison
            expect(self._driver.page).to_have_screenshot(
                str(reference_path),
                threshold=1.0 - threshold,  # Playwright uses inverse
                mask=masks if masks else None
            )
            
            return {'match': True, 'similarity': 1.0, 'method': 'playwright'}
        except AssertionError as e:
            return {'match': False, 'similarity': 0.0, 'method': 'playwright', 'error': str(e)}
    
    def _compare_ssim(self, state_id: str, threshold: float) -> dict:
        """Compare using SSIM (structure-focused)."""
        from PIL import Image
        from skimage.metrics import structural_similarity as ssim
        import numpy as np
        
        current_path = self.capture_state_screenshot(state_id, reference=False)
        reference_path = self._reference_dir / f"{state_id}.png"
        
        if not reference_path.exists():
            return {'match': False, 'similarity': 0.0, 'method': 'ssim', 'error': 'No reference'}
        
        # Load and prepare images
        current_img = Image.open(current_path).convert('RGB')
        reference_img = Image.open(reference_path).convert('RGB')
        
        if current_img.size != reference_img.size:
            current_img = current_img.resize(reference_img.size)
        
        # Calculate SSIM
        current_array = np.array(current_img)
        reference_array = np.array(reference_img)
        
        similarity, diff_image = ssim(
            reference_array, current_array,
            multichannel=True, channel_axis=2, full=True
        )
        
        match = similarity >= threshold
        
        # Save diff if mismatch
        if not match:
            diff_path = self._screenshot_dir / f"{state_id}_ssim_diff.png"
            diff_normalized = ((1.0 - diff_image) * 255).astype(np.uint8)
            Image.fromarray(diff_normalized).save(diff_path)
        
        return {
            'match': match,
            'similarity': similarity,
            'method': 'ssim',
            'diff_image_path': diff_path if not match else None
        }
```

---

## Step 4: Implement PlaywrightSyncAdapter

**File**: `boardfarm/boardfarm3/lib/gui/playwright_sync_adapter.py`

```python
"""Synchronous Playwright driver wrapper."""

import logging
from playwright.sync_api import sync_playwright, Page
from aria_state_mapper.playwright_integration import AriaSnapshotCapture

_LOGGER = logging.getLogger(__name__)


class PlaywrightSyncAdapter:
    """Synchronous Playwright driver wrapper."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize adapter.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
        """
        self._headless = headless
        self._timeout = timeout
        self._playwright = None
        self._browser = None
        self._page: Page = None
        self._snapshot_capture = None
    
    def start(self):
        """Launch browser and create page."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self._timeout)
        
        # Initialize AriaSnapshotCapture
        self._snapshot_capture = AriaSnapshotCapture(self._page)
        
        _LOGGER.info("Playwright browser started (headless=%s)", self._headless)
    
    def close(self):
        """Close browser."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        _LOGGER.info("Playwright browser closed")
    
    def goto(self, url: str):
        """Navigate to URL."""
        self._page.goto(url)
        _LOGGER.debug("Navigated to: %s", url)
    
    @property
    def page(self) -> Page:
        """Get Playwright Page object."""
        return self._page
    
    @property
    def url(self) -> str:
        """Get current URL."""
        return self._page.url
    
    def capture_fingerprint(self) -> dict:
        """Capture current page fingerprint using AriaSnapshotCapture."""
        return self._snapshot_capture.capture()
    
    def capture_aria_snapshot(self) -> dict:
        """Capture ARIA accessibility snapshot."""
        return self._snapshot_capture.capture_aria_tree()
    
    def take_screenshot(self, path: str, full_page: bool = True):
        """Take screenshot and save to file."""
        self._page.screenshot(path=path, full_page=full_page)
        _LOGGER.debug("Screenshot saved: %s", path)
```

---

## Step 5: Update GenieAcsGUI

**File**: `boardfarm/boardfarm3/devices/genie_acs.py`

Add STATE_REGISTRY and update initialization:

```python
from pathlib import Path
from boardfarm3.lib.gui.fsm_gui_component import FsmGuiComponent
from boardfarm3.lib.gui.playwright_sync_adapter import PlaywrightSyncAdapter


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
    
    def initialize(self, driver=None):
        """Initialize GUI component."""
        if driver is None:
            driver = PlaywrightSyncAdapter(
                headless=self.config.get("gui_headless", True),
                timeout=self.config.get("gui_default_timeout", 30) * 1000
            )
            driver.start()
        
        self._driver = driver
        
        # Initialize FSM component
        self._fsm_component = FsmGuiComponent(
            driver=self._driver,
            fsm_graph_file=Path(self.config['gui_fsm_graph_file']),
            default_timeout=self.config.get("gui_default_timeout", 30),
            match_threshold=self.config.get("gui_state_match_threshold", 0.80),
            screenshot_dir=Path(self.config.get("gui_screenshot_dir", "screenshots"))
        )
        
        self._gui_base_url = f"http://{self.config['ipaddr']}:{self.config.get('gui_port', 3000)}"
    
    @property
    def fsm(self) -> FsmGuiComponent:
        """Direct access to FSM component for navigation/visual testing."""
        return self._fsm_component
    
    def _get_fsm_state_id(self, friendly_name: str) -> str:
        """Convert friendly name to FSM state ID."""
        return self.STATE_REGISTRY.get(friendly_name, friendly_name)
    
    # MODE 1: Business goal methods
    def login(self, username: str = None, password: str = None) -> bool:
        """Login to GenieACS (functional business goal)."""
        username = username or self.config.get("http_username", "admin")
        password = password or self.config.get("http_password", "admin")
        
        try:
            # Navigate to login page
            login_url = f"{self._gui_base_url}/#!/login"
            self._driver.goto(login_url)
            
            # Get FSM state ID
            login_state_id = self._get_fsm_state_id('login_page')
            
            # Verify on login page
            if not self._fsm_component.verify_state(login_state_id, timeout=5):
                return False
            
            # Fill credentials (using Playwright directly for now)
            username_input = self._driver.page.get_by_role('textbox').first
            username_input.fill(username)
            
            password_input = self._driver.page.get_by_role('textbox').nth(1)
            password_input.fill(password)
            
            # Click login
            login_button = self._fsm_component.find_element(
                state_id=login_state_id,
                role='button',
                name='Login'
            )
            login_button.click()
            
            # Verify home page
            import time
            time.sleep(1)
            home_state_id = self._get_fsm_state_id('home_page')
            return self._fsm_component.verify_state(home_state_id, timeout=10)
            
        except Exception as e:
            _LOGGER.error("Login failed: %s", e)
            return False
    
    # MODE 3: Visual regression helpers
    def capture_reference_screenshots(self) -> dict:
        """Capture reference screenshots of all GenieACS states."""
        if not self.is_logged_in():
            self.login()
        
        return self._fsm_component.capture_all_states_screenshots(
            reference=True,
            max_time=600
        )
    
    def validate_ui_against_references(self, threshold: float = 0.99) -> dict:
        """Validate all states against reference screenshots."""
        if not self.is_logged_in():
            self.login()
        
        return self._fsm_component.validate_all_states_visually(threshold)
```

---

## Step 6: Update Configuration

**File**: `boardfarm-bdd/bf_config/boardfarm_config_example.json`

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
  "gui_visual_mask_selectors": [".timestamp", ".version-info"],
  "http_username": "admin",
  "http_password": "admin"
}
```

---

## Step 7: Test Each Mode

### Mode 1: Functional Test

```python
# tests/step_defs/acs_gui_steps.py
@when("the operator reboots the device via the ACS GUI")
def step_reboot_device(acs, bf_context):
    """Functional test: Can I reboot via UI?"""
    success = acs.gui.reboot_device_via_gui(bf_context.cpe_id)
    assert success, "Failed to reboot device"
```

### Mode 2: Navigation Test

```python
# tests/test_gui_navigation.py
def test_graph_structure(acs):
    """Validate FSM graph structure."""
    acs.gui.initialize()
    acs.gui.login()
    
    # Get graph structure
    graph = acs.gui.fsm.get_graph_structure()
    
    # Verify we have states and transitions
    assert graph['state_count'] > 0, "No states in graph"
    assert graph['transition_count'] > 0, "No transitions in graph"
    
    # Calculate coverage
    coverage = acs.gui.fsm.calculate_path_coverage()
    print(f"State coverage: {coverage['state_coverage']:.1%}")
```

### Mode 3: Visual Test

```bash
# Capture references (run once)
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

python3 << 'EOF'
from boardfarm3.devices.genie_acs import GenieACS
from argparse import Namespace

# Initialize device
config = {...}  # Your config
acs = GenieACS(config, Namespace())
acs.gui.initialize()
acs.gui.login()

# Capture references
result = acs.gui.capture_reference_screenshots()
print(f"Captured {len(result['captured'])} screenshots")
EOF

# Run visual regression
pytest tests/test_gui_visual.py -v
```

---

## Next Steps

1. ✅ Complete FsmGuiComponent implementation
2. ✅ Complete PlaywrightSyncAdapter implementation
3. ✅ Update GenieAcsGUI methods
4. ⏭️ Implement all three testing modes
5. ⏭️ Run integration tests
6. ⏭️ Generate coverage reports

See [`FSM_IMPLEMENTATION_GUIDE.md`](./FSM_IMPLEMENTATION_GUIDE.md) for complete implementation plan.

---

## Troubleshooting

### Import Errors

```bash
# Verify StateExplorer packages installed
pip list | grep model-resilience-core
pip list | grep aria-state-mapper
```

### FSM Graph Not Found

```bash
# Check path
ls -lh ~/projects/req-tst/boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json

# Regenerate if needed
cd ~/projects/req-tst/StateExplorer
aria-discover --url http://localhost:3000 \
  --username admin --password admin \
  --output ../boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json
```

### State Detection Fails

```python
# Enable debug logging
import logging
logging.getLogger('boardfarm3.lib.gui').setLevel(logging.DEBUG)

# Check similarity scores
component.detect_current_state()  # Check logs for similarity values
```

### Visual Comparison Issues

```bash
# Check if references exist
ls -lh bf_config/gui_artifacts/genieacs/screenshots/references/

# Verify dependencies
python3 -c "from skimage.metrics import structural_similarity; print('✅ SSIM available')"
```

```python
# Ensure consistent viewport
driver.page.set_viewport_size({"width": 1920, "height": 1080})

# Try different comparison methods
comparison = fsm.compare_screenshot_with_reference(
    state_id,
    threshold=0.95,
    comparison_method='ssim'  # Try SSIM if Playwright too strict
)

# Mask dynamic regions
comparison = fsm.compare_screenshot_with_reference(
    state_id,
    threshold=0.95,
    mask_selectors=['.timestamp', '.live-counter']
)

# Check similarity score
print(f"Similarity: {comparison['similarity']:.2%}")
print(f"Method: {comparison['method']}")

# Review diff image
if not comparison['match']:
    print(f"See diff: {comparison['diff_image_path']}")
```

---

## Resources

- **Implementation Guide**: [`FSM_IMPLEMENTATION_GUIDE.md`](./FSM_IMPLEMENTATION_GUIDE.md)
- **API Reference**: [`FSM_API_REFERENCE.md`](./FSM_API_REFERENCE.md)
- **StateExplorer Docs**: `~/projects/req-tst/StateExplorer/docs/`

---

**Last Updated**: December 14, 2025  
**Version**: 2.0 - Three-Mode Testing Architecture  
**Status**: Ready for Implementation
