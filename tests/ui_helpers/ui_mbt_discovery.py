"""UI Discovery Tool using FSM/MBT (Model-Based Testing) approach with Playwright.

This tool discovers UI states (not just pages) and transitions (actions)
to build a behavior-centric graph model for resilient test automation.

Key Concepts:
- Nodes represent VERIFIABLE STATES (not just pages)
- Edges represent ACTIONS/TRANSITIONS (not just navigation links)
- Focus on behavior and flow, not structure

This is an experimental alternative to the POM-based ui_discovery.py,
designed to test whether a state-machine representation provides superior
resilience for UI test automation.

References:
- GraphWalker Model-Based Testing concepts
- Playwright resilient locator strategies
- Finite State Machine (FSM) testing patterns
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Page, Locator, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.DEBUG,  # ENABLE DEBUG LOGGING
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class UIState:
    """Represents a verifiable UI state.
    
    In FSM/MBT terminology, this is a 'Vertex' - an assertion/verification point.
    It's not just a page, but a specific condition the UI is in.
    
    Examples:
        - V_LOGIN_FORM_EMPTY: Login page ready for input
        - V_LOGIN_FORM_ERROR: Login page showing validation errors
        - V_DASHBOARD_LOADED: Main dashboard after successful login
    """
    state_id: str  # Unique identifier (e.g., "V_LOGIN_FORM_EMPTY")
    state_type: str  # e.g., "form", "dashboard", "error", "modal"
    fingerprint: dict[str, Any] = field(default_factory=dict)
    verification_logic: dict[str, Any] = field(default_factory=dict)
    element_descriptors: list[dict[str, Any]] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)
    
    def __hash__(self):
        return hash(self.state_id)


@dataclass
class StateTransition:
    """Represents an action that transitions between states.
    
    In FSM/MBT terminology, this is an 'Edge' - the executable action
    that moves the system from one verifiable state to another.
    """
    transition_id: str
    from_state: str
    to_state: str
    action_type: str  # "click", "fill", "submit", "navigate"
    trigger_locators: dict[str, Any] = field(default_factory=dict)
    action_data: Optional[dict[str, Any]] = None
    success_rate: float = 1.0  # Track reliability


class StateFingerprinter:
    """Creates robust fingerprints for UI states.
    
    A fingerprint is a collection of stable attributes that uniquely
    identify a state, even if minor UI changes occur.
    """
    
    @staticmethod
    async def create_fingerprint(page: Page) -> dict[str, Any]:
        """Generate a multi-faceted state fingerprint.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Dictionary with multiple fingerprint dimensions
        """
        return {
            "url_pattern": StateFingerprinter._extract_url_pattern(page.url),
            "dom_structure_hash": await StateFingerprinter._get_dom_hash(page),
            "visible_components": await StateFingerprinter._get_visible_components(page),
            "page_state": await StateFingerprinter._get_page_state(page),
            "key_elements": await StateFingerprinter._get_key_elements(page),
            "title": await page.title(),
        }
    
    @staticmethod
    def _extract_url_pattern(url: str) -> str:
        """Extract stable URL pattern (removing volatile IDs but keeping structure).
        
        Args:
            url: Full URL
            
        Returns:
            Normalized URL pattern (e.g. "admin/config" or "devices/edit")
        """
        parsed = urlparse(url)
        # For SPAs, fragment is often the "path"
        path = parsed.fragment if parsed.fragment else parsed.path
        
        # NOTE: We do NOT strip query params blindly anymore, as they might define state (tabs)
        # But for GenieACS, the "path" is usually in the fragment BEFORE the query (?)
        # structure: #/admin/config
        
        # Handle "hash-bang" or clean paths
        if path.startswith('!'):
            path = path[1:]
        
        # Clean up
        path = path.strip('/')
        
        # Remove known pattern of specific IDs (digits or UUIDs) at the END of path
        # intended to collapse /devices/123 -> /devices
        # But we want to keep /admin/config -> /admin/config
        
        parts = path.split('/')
        normalized_parts = []
        
        for part in parts:
            # Simple heuristic: if it looks like an ID, replace with placeholder or skip
            # But for now, we leave it, trusting the caller to handle it or 
            # refined logic to spot pure IDs. 
            # In GenieACS, paths are usually semantic tokens (admin, config, users).
            # IDs usually appear in edit pages.
            normalized_parts.append(part)
            
        path = '/'.join(normalized_parts)

        # If path is empty, check root
        if not path:
             return 'root'
        
        return path
    
    @staticmethod
    async def _get_dom_hash(page: Page) -> str:
        """Create hash of significant DOM structure.
        
        This hash should be stable across cosmetic changes but different
        for structural changes that indicate a different state.
        
        Args:
            page: Playwright Page object
            
        Returns:
            8-character hash of DOM structure
        """
        try:
            structure = await page.evaluate("""
                () => {
                    const significant = Array.from(document.querySelectorAll(
                        '[role], [data-testid], form, [aria-label], h1, h2, h3, button, input[type="text"], input[type="password"]'
                    ));
                    return significant.map(el => ({
                        tag: el.tagName,
                        role: el.getAttribute('role'),
                        testid: el.getAttribute('data-testid'),
                        ariaLabel: el.getAttribute('aria-label'),
                        visible: el.offsetParent !== null,
                        text: el.textContent ? el.textContent.substring(0, 50) : ''
                    })).filter(x => x.visible);
                }
            """)
            structure_str = json.dumps(structure, sort_keys=True)
            return hashlib.md5(structure_str.encode()).hexdigest()[:8]
        except Exception as e:
            logger.debug("Error creating DOM hash: %s", e)
            return "unknown"
    
    @staticmethod
    async def _get_visible_components(page: Page) -> list[str]:
        """Identify major visible components that define the state.
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of component names present and visible
        """
        components = []
        
        # Check for common component types using multiple strategies
        checks = {
            "login_form": [
                'form[name*="login"]',
                '[data-testid*="login"]',
                'form:has(input[type="password"])',
            ],
            "error_banner": [
                '[role="alert"]',
                '.error',
                '.alert-danger',
                '[class*="error"]',
            ],
            "success_message": [
                '[role="status"]',
                '.success',
                '.alert-success',
            ],
            "modal_dialog": [
                '[role="dialog"]',
                '.modal.show',
                '.modal[style*="display: block"]',
            ],
            "dashboard": [
                '[data-testid*="dashboard"]',
                'main[role="main"]',
                '[class*="dashboard"]',
            ],
            "loading_indicator": [
                '[aria-busy="true"]',
                '.loading',
                '.spinner',
            ],
            "navigation_menu": [
                'nav',
                '[role="navigation"]',
                '.navbar',
            ],
            "data_table": [
                'table',
                '[role="table"]',
                '[role="grid"]',
            ],
            "tabs_container": [
                '.tabs',
                '[role="tablist"]',
                'ul.tabs',
            ]
        }
        
        for comp_name, selectors in checks.items():
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0:
                        is_visible = await locator.is_visible(timeout=100)
                        if is_visible:
                            components.append(comp_name)
                            break  # Found this component, move to next
                except Exception:
                    continue
        
        return components
    
    @staticmethod
    async def _get_page_state(page: Page) -> dict[str, bool]:
        """Get page loading/ready state indicators.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Dictionary of state indicators
        """
        try:
            has_errors = await page.locator('[role="alert"]').count() > 0
            is_loading = await page.locator('[aria-busy="true"]').count() > 0
            
            return {
                "ready": True,  # If we can query, page is ready
                "has_errors": has_errors,
                "is_loading": is_loading,
            }
        except Exception:
            return {
                "ready": False,
                "has_errors": False,
                "is_loading": True,
            }
    
    @staticmethod
    async def _get_key_elements(page: Page) -> list[dict[str, Any]]:
        """Extract key interactive elements with resilient locators.
        
        This follows the Playwright locator priority hierarchy:
        1. data-testid (explicit contract)
        2. role + name (functional identity)
        3. label/placeholder (semantic)
        4. text (visible content)
        5. relative position
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of element descriptor dictionaries
        """
        elements = []
        
        try:
            # Get all visible buttons
            buttons = await page.locator('button:visible').all()
            for btn in buttons[:20]:  # Limit to prevent overwhelming
                try:
                    element = await StateFingerprinter._create_element_descriptor(btn, "button")
                    if element:
                        elements.append(element)
                except Exception as e:
                    logger.debug("Error extracting button: %s", e)
                    continue
            
            # Get all visible inputs
            inputs = await page.locator('input:visible').all()
            for inp in inputs[:20]:
                try:
                    element = await StateFingerprinter._create_element_descriptor(inp, "input")
                    if element:
                        elements.append(element)
                except Exception as e:
                    logger.debug("Error extracting input: %s", e)
                    continue
            
            # Get all visible links
            links = await page.locator('a[href]:visible').all()
            for link in links[:30]: # Increased from 20 to capture tabs
                try:
                    element = await StateFingerprinter._create_element_descriptor(link, "link")
                    if element:
                        elements.append(element)
                except Exception as e:
                    logger.debug("Error extracting link: %s", e)
                    continue
        
        except Exception as e:
            logger.warning("Error extracting key elements: %s", e)
        
        return elements
    
    @staticmethod
    async def _create_element_descriptor(locator: Locator, elem_type: str) -> Optional[dict[str, Any]]:
        """Create resilient multi-strategy locator descriptor.
        
        Args:
            locator: Playwright Locator object
            elem_type: Element type ("button", "input", "link", etc.)
            
        Returns:
            Element descriptor with prioritized locators, or None
        """
        try:
            descriptor = {
                "element_type": elem_type,
                "locators": {},  # Priority-ordered locators
                "metadata": {}
            }
            
            # Priority 1: data-testid (most stable)
            test_id = await locator.get_attribute('data-testid')
            if test_id:
                descriptor["locators"]["test_id"] = test_id
                descriptor["metadata"]["test_id"] = test_id
            
            # Priority 2: Role + accessible name
            role = await locator.get_attribute('role')
            aria_label = await locator.get_attribute('aria-label')
            if role:
                descriptor["locators"]["role"] = role
            if aria_label:
                descriptor["locators"]["aria_label"] = aria_label
            
            # Priority 3: Semantic attributes
            if elem_type == "input":
                input_type = await locator.get_attribute('type')
                placeholder = await locator.get_attribute('placeholder')
                name = await locator.get_attribute('name')
                if input_type:
                    descriptor["locators"]["input_type"] = input_type
                if placeholder:
                    descriptor["locators"]["placeholder"] = placeholder
                if name:
                    descriptor["locators"]["name"] = name
            
            # Priority 4: Text content
            text = await locator.text_content()
            if text and text.strip():
                descriptor["locators"]["text"] = text.strip()[:100]  # Limit length
            
            # Priority 5: title attribute
            title = await locator.get_attribute('title')
            if title:
                descriptor["locators"]["title"] = title
            
            # Link-specific: href
            if elem_type == "link":
                href = await locator.get_attribute('href')
                if href:
                    descriptor["locators"]["href"] = href
            
            # Store tag name for reference
            tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")
            descriptor["metadata"]["tag"] = tag_name
            
            # Only return if we have at least one locator strategy
            return descriptor if descriptor["locators"] else None
            
        except Exception as e:
            logger.debug("Error creating element descriptor: %s", e)
            return None


class StateClassifier:
    """Classifies UI states based on fingerprint.
    
    This is application-specific logic that can be overridden for different UIs.
    """
    
    @staticmethod
    def classify_state(fingerprint: dict[str, Any]) -> tuple[str, str]:
        """Classify state and generate unique state_id.
        
        Args:
            fingerprint: State fingerprint dictionary
            
        Returns:
            Tuple of (state_type, state_id)
            
        Examples:
            - ("form", "V_LOGIN_FORM_EMPTY")
            - ("error", "V_LOGIN_FORM_ERROR")
            - ("dashboard", "V_DASHBOARD_LOADED")
        """
        url_pattern = fingerprint.get("url_pattern", "")
        components = fingerprint.get("visible_components", [])
        page_state = fingerprint.get("page_state", {})
        title = fingerprint.get("title", "").lower()
        key_elements = fingerprint.get("key_elements", [])
        
        # Check for logout button as indicator of logged-in state
        has_logout = any(
            elem.get("locators", {}).get("text", "").lower() in ["log out", "logout", "sign out"]
            for elem in key_elements
        )
        
        # Check for login button (indicates we're on login page, not logged in)
        has_login_button = any(
            elem.get("locators", {}).get("text", "").lower() in ["login", "log in", "sign in"]
            and elem.get("element_type") == "button"
            for elem in key_elements
        )
        
        # Priority 1: Error states (but NOT if it's just the login form)
        # Only treat as error if we have actual error state indicators
        has_actual_error = page_state.get("has_errors") or "error_banner" in components
        if has_actual_error:
            # If it has a login form AND login button, it's a login page (even with error banner)
            # The error banner might be from a previous failed attempt or just a message
            if "login_form" in components and has_login_button:
                # This is a login page, not an error page
                logger.debug("Login form detected with error banner, treating as login page")
                pass  # Fall through to login form handling
            elif "login" in url_pattern.lower() or "login" in title:
                return "error", "V_LOGIN_FORM_ERROR"
            else:
                state_id = f"V_ERROR_{StateClassifier._normalize_name(url_pattern)}"
                return "error", state_id
        
        # Priority 2: Modal states
        if "modal_dialog" in components:
            state_id = f"V_MODAL_{StateClassifier._normalize_name(url_pattern)}"
            return "modal", state_id
        
        # Priority 3: Loading states
        if page_state.get("is_loading") or "loading_indicator" in components:
            state_id = f"V_LOADING_{StateClassifier._normalize_name(url_pattern)}"
            return "loading", state_id
        
        # Priority 4: Logged-in states (check BEFORE login form)
        # If we have logout button and navigation menu, we're logged in
        if has_logout and "navigation_menu" in components:
            # DYNAMIC CLASSIFICATION: Use the URL pattern to define the state
            # This allows discovery of ANY sub-page (admin/config, admin/users)
            # without hardcoding.
            
            # Special case for root/dashboard
            if "overview" in url_pattern or "overview" in title:
                return "dashboard", "V_OVERVIEW_PAGE"
            
            # For everything else, derive ID from normalized URL
            # e.g. "admin/config" -> "V_ADMIN_CONFIG"
            # e.g. "devices" -> "V_DEVICES"
            state_id = f"V_{StateClassifier._normalize_name(url_pattern)}"
            
            # Determine type (heuristic)
            if "admin" in url_pattern:
                state_type = "admin"
            elif "list" in url_pattern or "table" in components:
                 state_type = "list"
            else:
                state_type = "page"
                
            return state_type, state_id
        
        # Priority 5: Login form states (empty/ready)
        # Check if we're on a login page (has form and login button, no logout)
        if ("login_form" in components or "login" in url_pattern or "login" in title) and has_login_button:
            # Only classify as login form if we DON'T have logout button
            if not has_logout:
                return "form", "V_LOGIN_FORM_EMPTY"
        
        # Priority 6: Dashboard/main application states
        if "dashboard" in components or "dashboard" in title:
            return "dashboard", "V_DASHBOARD_LOADED"
        
        if "navigation_menu" in components and "data_table" in components:
            # Likely a list/management page
            state_id = f"V_LIST_{StateClassifier._normalize_name(url_pattern)}"
            return "list", state_id
        
        # Priority 7: Success states
        if "success_message" in components:
            state_id = f"V_SUCCESS_{StateClassifier._normalize_name(url_pattern)}"
            return "success", state_id
        
        # Default: use URL pattern
        state_type = "page"
        state_id = f"V_{StateClassifier._normalize_name(url_pattern)}"
        
        return state_type, state_id
    
    @staticmethod
    def _normalize_name(text: str) -> str:
        """Normalize text for use in state IDs.
        
        Args:
            text: Text to normalize
            
        Returns:
            Uppercase, underscored identifier
        """
        normalized = text.replace('/', '_').replace('#', '').replace('!', '')
        normalized = normalized.replace('-', '_').replace('.', '_')
        normalized = normalized.strip('_').upper()
        return normalized if normalized else "UNKNOWN"


class UIStateMachineDiscovery:
    """Main discovery tool using FSM/MBT approach with Playwright.
    
    This tool builds a Finite State Machine representation of the UI by:
    1. Discovering verifiable states (vertices)
    2. Recording transitions between states (edges)
    3. Capturing resilient locators for each actionable element
    """
    
    def __init__(
        self,
        base_url: str,
        headless: bool = True,
        timeout: int = 10000,
        max_states: int = 50,
        safe_button_patterns: str = "New,Add,Edit,View,Show,Cancel,Close,Search,Filter,Create,Upload,Refresh,Submit,Save,Update,Confirm,OK,Yes",
        use_dfs: bool = True,
    ):
        """Initialize the state machine discovery tool.
        
        Args:
            base_url: Base URL of the application
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
            max_states: Maximum number of states to discover (safety limit)
            safe_button_patterns: Comma-separated button text patterns safe to click
            use_dfs: Use Depth-First Search (recommended) vs Breadth-First Search
        """
        self.base_url = base_url.rstrip('/')
        self.headless = headless
        self.timeout = timeout
        self.max_states = max_states
        self.safe_button_patterns = [p.strip().lower() for p in safe_button_patterns.split(',')]
        self.use_dfs = use_dfs
        
        self.states: dict[str, UIState] = {}
        self.transitions: list[StateTransition] = []
        self.visited_states: set[str] = set()
        self.state_queue: deque[str] = deque()  # For BFS mode
        
        # Store credentials for re-login if needed
        self.username: str | None = None
        self.password: str | None = None
        
    async def discover(
        self,
        username: str | None = None,
        password: str | None = None,
        discover_login_flow: bool = True,
    ) -> dict[str, Any]:
        """Main discovery flow.
        
        Args:
            username: Login username (optional)
            password: Login password (optional)
            discover_login_flow: Whether to discover login states
            
        Returns:
            Dictionary with FSM graph data
        """
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=self.headless)
            page = await browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                exploration_method = "DFS (Depth-First)" if self.use_dfs else "BFS (Breadth-First)"
                logger.info("Starting FSM/MBT discovery for %s using %s", 
                           self.base_url, exploration_method)
                
                # Store credentials for potential re-login
                self.username = username
                self.password = password
                
                # Navigate to base URL
                await page.goto(self.base_url)
                await page.wait_for_load_state('networkidle')
                
                # Discover initial state (likely login page)
                initial_state = await self._discover_current_state(page)
                self.states[initial_state.state_id] = initial_state
                
                logger.info("Initial state: %s (%s)", initial_state.state_id, initial_state.state_type)
                
                # If login required, perform login
                if username and password and discover_login_flow:
                    await self._discover_login_flow(page, username, password)
                
                # After login (or if no login), discover the current state
                # This is our starting point for exploration
                current_state = await self._discover_current_state(page)
                if current_state.state_id not in self.states:
                    self.states[current_state.state_id] = current_state
                
                # Start BFS from current state (post-login or initial)
                logger.info("Starting exploration from: %s (%s)", 
                           current_state.state_id, current_state.state_type)
                self.state_queue.append(current_state.state_id)
                
                # Choose exploration strategy
                if self.use_dfs:
                    # DFS: Explore each branch completely before moving to next
                    await self._explore_states_dfs(page)
                else:
                    # BFS: Explore level by level
                    await self._explore_states_simple_bfs(page)
                
                # Export to graph
                graph_data = self._export_to_graph()
                
                logger.info("Discovery complete: %d states, %d transitions", 
                           len(self.states), len(self.transitions))
                
                return graph_data
                
            finally:
                await browser.close()
    
    async def _discover_current_state(self, page: Page) -> UIState:
        """Discover and classify the current UI state.
        
        Args:
            page: Playwright Page object
            
        Returns:
            UIState object representing current state
        """
        # Wait for state to stabilize (e.g. loading spinners to disappear)
        await self._wait_for_stable_state(page)

        # Create fingerprint
        fingerprint = await StateFingerprinter.create_fingerprint(page)
        
        # Classify state
        state_type, state_id = StateClassifier.classify_state(fingerprint)
        
        # Create verification logic
        verification = self._create_verification_logic(fingerprint)
        
        state = UIState(
            state_id=state_id,
            state_type=state_type,
            fingerprint=fingerprint,
            verification_logic=verification,
            element_descriptors=fingerprint.get("key_elements", [])
        )
        
        logger.debug("Discovered state: %s (components: %s)", 
                    state_id, fingerprint.get("visible_components"))
        
        return state

    async def _wait_for_stable_state(self, page: Page, timeout: int = 2000) -> None:
        """Wait for the UI to stabilize (loading indicators to clear).

        Args:
            page: Playwright Page object
            timeout: Max time to wait for stability in ms
        """
        start_time = time.time()
        check_interval = 0.2
        
        # Already waited for networkidle in navigation, but give a small buffer for UI rendering
        await asyncio.sleep(0.2)

        while (time.time() - start_time) * 1000 < timeout:
            try:
                # Check directly for loading indicators without full fingerprinting
                page_state = await StateFingerprinter._get_page_state(page)
                
                # Also check component presence if needed
                # But _get_page_state covers aria-busy and generic loading classes
                
                if not page_state["is_loading"]:
                    # Stable!
                    return
                
                logger.debug("Waiting for state to stabilize (loading detected)...")
                await asyncio.sleep(check_interval)
            except Exception:
                # If check fails, assume stable enough or error will be caught later
                return
        
        logger.debug("State verification timed out waiting for stability, proceeding anyway")
    
    def _create_verification_logic(self, fingerprint: dict[str, Any]) -> dict[str, Any]:
        """Create assertions to verify this state.
        
        Args:
            fingerprint: State fingerprint
            
        Returns:
            Dictionary of verification checks
        """
        return {
            "url_pattern": fingerprint["url_pattern"],
            "required_components": fingerprint["visible_components"],
            "dom_hash": fingerprint["dom_structure_hash"],
            "page_ready": fingerprint["page_state"]["ready"],
            "no_loading": not fingerprint["page_state"]["is_loading"],
        }
    
    async def _navigate_to_state(
        self, 
        page: Page, 
        target_state_id: str,
        _visited_in_recursion: set[str] | None = None
    ) -> bool:
        """Navigate to a specific state.
        
        Strategy:
        1. Check if already in target state
        2. Find a transition that leads to target state
        3. Execute that transition
        4. Verify arrival
        
        Args:
            page: Playwright Page object
            target_state_id: State ID to navigate to
            _visited_in_recursion: Internal recursion tracking
            
        Returns:
            True if navigation successful, False otherwise
        """
        # Initialize recursion tracking
        if _visited_in_recursion is None:
            _visited_in_recursion = set()
        
        # Prevent infinite recursion
        if target_state_id in _visited_in_recursion:
            logger.warning("Circular navigation detected for %s", target_state_id)
            return False
        _visited_in_recursion.add(target_state_id)
        
        # Check if already in target state
        try:
            current_state = await self._discover_current_state(page)
            if current_state.state_id == target_state_id:
                logger.debug("Already in target state %s", target_state_id)
                return True
        except Exception as e:
            logger.error("Error checking current state: %s", e)
            return False
        
        # Find a transition to the target state
        transition_to_target = None
        for transition in self.transitions:
            if transition.to_state == target_state_id:
                transition_to_target = transition
                break
        
        if not transition_to_target:
            logger.warning("No known transition to state %s", target_state_id)
            return False
        
        # Check if we're in the source state of this transition
        if current_state.state_id != transition_to_target.from_state:
            # Need to navigate to source state first (recursive)
            logger.debug("Need to navigate to %s before going to %s", 
                        transition_to_target.from_state, target_state_id)
            if not await self._navigate_to_state(
                page, 
                transition_to_target.from_state,
                _visited_in_recursion
            ):
                return False
        
        # Execute the transition
        try:
            success = await self._execute_transition(page, transition_to_target)
            
            if success:
                logger.debug("Successfully navigated to %s", target_state_id)
                return True
            else:
                logger.warning("Failed to execute transition to %s", target_state_id)
                return False
        except Exception as e:
            logger.error("Error executing transition to %s: %s", target_state_id, e)
            return False
    
    async def _execute_transition(self, page: Page, transition: StateTransition) -> bool:
        """Execute a known transition.
        
        Args:
            page: Playwright Page object
            transition: StateTransition to execute
            
        Returns:
            True if successful, False otherwise
        """
        try:
            trigger_locators = transition.trigger_locators
            action_type = transition.action_type
            
            if action_type == "submit_login":
                # Special case: re-execute login with stored credentials
                if not self.username or not self.password:
                    logger.debug("No credentials available for login")
                    return False
                
                try:
                    # Find and fill login form
                    username_field = page.get_by_label("Username", exact=False).or_(
                        page.get_by_placeholder("Username")
                    ).or_(page.locator('input[name="username"]')).first
                    
                    password_field = page.get_by_label("Password", exact=False).or_(
                        page.get_by_placeholder("Password")  
                    ).or_(page.locator('input[type="password"]')).first
                    
                    submit_button = page.get_by_role("button", name="Login").or_(
                        page.get_by_role("button", name="Submit")
                    ).or_(page.locator('button[type="submit"]')).first
                    
                    await username_field.fill(self.username)
                    await password_field.fill(self.password)
                    await submit_button.click()
                    
                    await page.wait_for_load_state('networkidle', timeout=self.timeout)
                    
                    # Verify we reached the target state
                    new_state = await self._discover_current_state(page)
                    return new_state.state_id == transition.to_state
                    
                except Exception as e:
                    logger.debug("Error re-executing login: %s", e)
                    return False
            
            elif action_type == "navigate":
                # For navigation links, try URL-based navigation first (faster for SPAs)
                href = trigger_locators.get("locators", {}).get("href")
                
                if href:
                    # Direct URL navigation for SPAs
                    try:
                        target_url = href if href.startswith('http') else self.base_url + '/' + href.lstrip('/')
                        await page.goto(target_url)
                        await page.wait_for_load_state('networkidle', timeout=3000)
                        
                        # Verify we reached the target state
                        new_state = await self._discover_current_state(page)
                        if new_state.state_id == transition.to_state:
                            return True
                    except Exception as e:
                        logger.debug("URL navigation failed: %s, trying click", e)
                
                # Fallback: locate and click the trigger element
                element = await self._locate_element_from_descriptor(page, trigger_locators)
                
                if not element:
                    logger.debug("Could not locate trigger element for transition")
                    return False
                
                await element.click()
                
                # Wait for navigation
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)
                except PlaywrightTimeoutError:
                    await asyncio.sleep(0.5)
                
                # Verify we reached the target state
                new_state = await self._discover_current_state(page)
                return new_state.state_id == transition.to_state
            
            elif action_type == "click":
                # Locate and click the trigger element
                element = await self._locate_element_from_descriptor(page, trigger_locators)
                
                if not element:
                    logger.debug("Could not locate trigger element for transition")
                    return False
                
                await element.click()
                
                # Wait for potential state change
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)
                except PlaywrightTimeoutError:
                    await asyncio.sleep(0.5)
                
                # Verify we reached the target state
                new_state = await self._discover_current_state(page)
                return new_state.state_id == transition.to_state
            
            else:
                logger.warning("Unknown action type: %s", action_type)
                return False
                
        except Exception as e:
            logger.debug("Error executing transition: %s", e)
            return False
    
    async def _discover_login_flow(self, page: Page, username: str, password: str) -> None:
        """Discover login flow states and transitions WITH intermediate states.
        
        This method captures the COMPLETE login cycle with all intermediate states:
        1. Empty login form state (V_LOGIN_FORM_EMPTY)
        2. Username filled state (V_LOGIN_FORM_USERNAME_FILLED)
        3. Both credentials filled state (V_LOGIN_FORM_READY)
        4. Post-submit result state (V_OVERVIEW_PAGE or V_LOGIN_FORM_ERROR)
        
        This granular approach aligns with FSM/MBT philosophy of capturing
        all verifiable states in the user journey.
        
        Args:
            page: Playwright Page object
            username: Username to use
            password: Password to use
        """
        logger.info("Discovering granular login flow with intermediate states...")
        
        try:
            # Find login elements using resilient locators
            username_field = page.get_by_label("Username", exact=False).or_(
                page.get_by_placeholder("Username")
            ).or_(page.locator('input[name="username"]')).first
            
            password_field = page.get_by_label("Password", exact=False).or_(
                page.get_by_placeholder("Password")  
            ).or_(page.locator('input[type="password"]')).first
            
            submit_button = page.get_by_role("button", name="Login").or_(
                page.get_by_role("button", name="Submit")
            ).or_(page.locator('button[type="submit"]')).first
            
            # Capture element descriptors for transitions
            username_field_desc = await self._get_element_descriptor(username_field)
            password_field_desc = await self._get_element_descriptor(password_field)
            submit_button_desc = await self._get_element_descriptor(submit_button)
            
            # ==========================================
            # STATE 1: Empty/Initial login form
            # ==========================================
            state1_empty = await self._discover_current_state(page)
            if state1_empty.state_id not in self.states:
                self.states[state1_empty.state_id] = state1_empty
            logger.info("State 1 - Empty form: %s", state1_empty.state_id)
            
            # ==========================================
            # TRANSITION 1: Fill username field
            # ==========================================
            await username_field.fill(username)
            await asyncio.sleep(0.3)  # Let UI update
            
            # STATE 2: Username filled, password empty
            state2_username = await self._discover_current_state(page)
            if state2_username.state_id not in self.states:
                self.states[state2_username.state_id] = state2_username
            
            # Record transition 1
            if state2_username.state_id != state1_empty.state_id:
                transition1 = StateTransition(
                    transition_id=f"T_{state1_empty.state_id}_TO_{state2_username.state_id}_FILL_USERNAME",
                    from_state=state1_empty.state_id,
                    to_state=state2_username.state_id,
                    action_type="fill",
                    trigger_locators=username_field_desc,
                    action_data={"field": "username", "value": "***"}
                )
                self.transitions.append(transition1)
                logger.info("Transition 1: %s -> %s (username filled)", 
                           state1_empty.state_id, state2_username.state_id)
            else:
                logger.debug("Username fill didn't change state, continuing...")
                state2_username = state1_empty  # Use same state
            
            # ==========================================
            # TRANSITION 2: Fill password field
            # ==========================================
            await password_field.fill(password)
            await asyncio.sleep(0.3)  # Let UI update
            
            # STATE 3: Both username and password filled (ready to submit)
            state3_ready = await self._discover_current_state(page)
            if state3_ready.state_id not in self.states:
                self.states[state3_ready.state_id] = state3_ready
            
            # Record transition 2
            if state3_ready.state_id != state2_username.state_id:
                transition2 = StateTransition(
                    transition_id=f"T_{state2_username.state_id}_TO_{state3_ready.state_id}_FILL_PASSWORD",
                    from_state=state2_username.state_id,
                    to_state=state3_ready.state_id,
                    action_type="fill",
                    trigger_locators=password_field_desc,
                    action_data={"field": "password", "value": "***"}
                )
                self.transitions.append(transition2)
                logger.info("Transition 2: %s -> %s (password filled)", 
                           state2_username.state_id, state3_ready.state_id)
            else:
                logger.debug("Password fill didn't change state, continuing...")
                state3_ready = state2_username  # Use same state
            
            # ==========================================
            # TRANSITION 3: Click submit button
            # ==========================================
            await submit_button.click()
            
            # Wait for navigation/state change
            try:
                await page.wait_for_load_state('networkidle', timeout=self.timeout)
            except PlaywrightTimeoutError:
                logger.warning("Networkidle timeout after login, continuing...")
                await asyncio.sleep(1)
            
            # Additional wait for SPA to update
            await asyncio.sleep(0.5)
            
            # Log current URL for debugging
            current_url = page.url
            logger.debug("After login submit, current URL: %s", current_url)
            
            # STATE 4: After login (success -> overview, or failure -> error)
            state4_result = await self._discover_current_state(page)
            if state4_result.state_id not in self.states:
                self.states[state4_result.state_id] = state4_result
            
            # Record transition 3
            transition3 = StateTransition(
                transition_id=f"T_{state3_ready.state_id}_TO_{state4_result.state_id}_SUBMIT",
                from_state=state3_ready.state_id,
                to_state=state4_result.state_id,
                action_type="submit",
                trigger_locators=submit_button_desc,
                action_data={"requires_credentials": True}
            )
            self.transitions.append(transition3)
            
            logger.info("Transition 3: %s -> %s (login submitted)", 
                       state3_ready.state_id, state4_result.state_id)
            logger.info("Login flow complete: 4 states, 3 transitions discovered")
            
        except Exception as e:
            logger.error("Error discovering granular login flow: %s", e)
            raise
    
    async def _get_element_descriptor(self, locator: Locator) -> dict[str, Any]:
        """Extract resilient locator strategies for element.
        
        Args:
            locator: Playwright Locator object
            
        Returns:
            Element descriptor with multiple locator strategies
        """
        try:
            # Get element type
            tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")
            elem_type = "button" if tag_name == "button" else "input" if tag_name == "input" else "link"
            
            descriptor = await StateFingerprinter._create_element_descriptor(locator, elem_type)
            return descriptor if descriptor else {}
        except Exception as e:
            logger.debug("Error getting element descriptor: %s", e)
            return {}
    
    async def _explore_states_dfs(self, page: Page):
        """Depth-First Search exploration - explore deeply before broadly.
        
        This is much more natural for UI exploration:
        1. Click a link
        2. Immediately explore that new state (recursive)
        3. When done, come back and try the next link
        4. This way we're always on the page we want to explore!
        
        Args:
            page: Playwright Page object
        """
        logger.info("Starting DFS (depth-first) state exploration...")
        
        # Track which states we've explored
        explored_states: set[str] = set()
        
        async def explore_state_recursive(state_id: str, depth: int = 0):
            """Recursively explore a state and all states reachable from it."""
            # Check limits
            if depth > 10:  # Prevent too deep recursion
                logger.warning("Max depth reached at %s", state_id)
                return
            
            if len(explored_states) >= self.max_states:
                logger.warning("Max states limit reached")
                return
            
            if state_id in explored_states:
                return
            
            # Get the state
            state = self.states.get(state_id)
            if not state:
                logger.warning("State %s not found in states dict", state_id)
                return
            
            # Skip error/login states
            if state.state_type in ["error", "form"]:
                logger.info("Skipping exploration of %s state: %s",
                           state.state_type, state_id)
                explored_states.add(state_id)
                return
            
            indent = "  " * depth
            logger.info("%sExploring state [depth %d]: %s (%d/%d)",
                       indent, depth, state_id, len(explored_states), self.max_states)
            
            # Mark as explored
            explored_states.add(state_id)
            
            # Verify we're in this state (or can navigate to it)
            try:
                actual_state = await self._discover_current_state(page)
                
                if actual_state.state_id != state_id:
                    logger.debug("%sNot in expected state %s, currently in %s",
                                indent, state_id, actual_state.state_id)
                    
                    # Try to navigate
                    target_pattern = state.fingerprint.get("url_pattern", "")
                    if target_pattern and target_pattern != "root":
                        target_url = f"{self.base_url}/#{target_pattern}"
                        logger.debug("%sNavigating to %s", indent, target_url)
                        await page.goto(target_url)
                        await page.wait_for_load_state('networkidle', timeout=3000)
                        
                        # Verify again
                        actual_state = await self._discover_current_state(page)
                        if actual_state.state_id != state_id:
                            logger.warning("%sCan't navigate to %s, skipping", indent, state_id)
                            return
            
            except Exception as e:
                logger.error("%sError navigating to state: %s", indent, e)
                return
            
            # Discover transitions from this state
            try:
                # Find all safe links and buttons
                safe_links = await self._find_safe_links(page)
                safe_buttons = await self._find_safe_buttons(page)
                
                logger.info("%sFound %d links and %d buttons to explore",
                           indent, len(safe_links[:10]), len(safe_buttons[:5]))
                
                # Explore each link depth-first
                for link_info in safe_links[:10]:
                    try:
                        link_text = link_info.get("locators", {}).get("text", "unknown")
                        logger.debug("%sClicking link: %s", indent, link_text)
                        
                        # Click and discover new state (DON'T navigate back)
                        new_state_id = await self._execute_link_click(page, state, link_info, navigate_back=False)
                        
                        if new_state_id and new_state_id != state_id:
                            # Recursively explore the new state immediately!
                            await explore_state_recursive(new_state_id, depth + 1)
                            
                            # After exploring the new state, navigate back to continue
                            logger.debug("%sReturning to %s after exploring %s",
                                       indent, state_id, new_state_id)
                            target_pattern = state.fingerprint.get("url_pattern", "")
                            if target_pattern and target_pattern != "root":
                                await page.goto(f"{self.base_url}/#{target_pattern}")
                                await page.wait_for_load_state('networkidle', timeout=3000)
                    
                    except Exception as e:
                        logger.debug("%sError with link: %s", indent, e)
                
                # Explore buttons depth-first
                for button_info in safe_buttons[:5]:
                    try:
                        button_text = button_info.get("locators", {}).get("text", "unknown")
                        logger.debug("%sClicking button: %s", indent, button_text)
                        
                        new_state_id = await self._execute_button_click(page, state, button_info, navigate_back=False)
                        
                        if new_state_id and new_state_id != state_id:
                            # Recursively explore!
                            await explore_state_recursive(new_state_id, depth + 1)
                            
                            # Navigate back
                            logger.debug("%sReturning to %s after exploring %s",
                                       indent, state_id, new_state_id)
                            target_pattern = state.fingerprint.get("url_pattern", "")
                            if target_pattern and target_pattern != "root":
                                await page.goto(f"{self.base_url}/#{target_pattern}")
                                await page.wait_for_load_state('networkidle', timeout=3000)
                    
                    except Exception as e:
                        logger.debug("%sError with button: %s", indent, e)
            
            except Exception as e:
                logger.error("%sError discovering transitions: %s", indent, e)
        
        # Start DFS from the initial state in the queue
        if self.state_queue:
            initial_state_id = self.state_queue.popleft()
            await explore_state_recursive(initial_state_id, depth=0)
        
        logger.info("DFS exploration complete: %d states explored", len(explored_states))
        self.visited_states = explored_states
    
    async def _explore_states_simple_bfs(self, page: Page):
        """Simple BFS exploration without complex state navigation.
        
        Like the original ui_discovery.py, we:
        1. Start from current page (post-login)
        2. Discover elements and links on current page
        3. Click links to discover new states
        4. Don't navigate back - just explore forward
        
        Args:
            page: Playwright Page object
        """
        logger.info("Starting simple BFS state exploration...")
        
        # Track which states we've explored (not just visited)
        explored_states: set[str] = set()
        
        while self.state_queue and len(explored_states) < self.max_states:
            current_state_id = self.state_queue.popleft()
            
            if current_state_id in explored_states:
                continue
            
            # Skip error/login states
            current_state = self.states.get(current_state_id)
            if current_state and current_state.state_type in ["error", "form"]:
                logger.info("Skipping exploration of %s state: %s",
                           current_state.state_type, current_state_id)
                explored_states.add(current_state_id)
                continue
            
            logger.info("Exploring state: %s (%d/%d)",
                       current_state_id, len(explored_states), self.max_states)
            
            # We're already in SOME state, verify which one
            try:
                actual_state = await self._discover_current_state(page)
                
                # If we're not in the expected state, navigate by URL if possible
                if actual_state.state_id != current_state_id:
                    logger.debug("Not in expected state %s, currently in %s",
                                current_state_id, actual_state.state_id)
                    
                    # Try to get the URL pattern and navigate directly
                    target_pattern = current_state.fingerprint.get("url_pattern", "")
                    if target_pattern and target_pattern != "root":
                        target_url = f"{self.base_url}/#{target_pattern}"
                        logger.debug("Navigating directly to %s", target_url)
                        await page.goto(target_url)
                        await page.wait_for_load_state('networkidle', timeout=3000)
                        
                        # Verify again
                        actual_state = await self._discover_current_state(page)
                        if actual_state.state_id != current_state_id:
                            # Can't navigate to target state
                            # Check if actual state has already been explored
                            if actual_state.state_id in explored_states:
                                logger.warning("Can't navigate to %s, and current state %s already explored. Skipping.",
                                             current_state_id, actual_state.state_id)
                                explored_states.add(current_state_id)  # Mark target as explored too
                                continue
                            else:
                                logger.warning("Can't navigate to %s, will explore current state %s instead",
                                             current_state_id, actual_state.state_id)
                                # Switch to exploring the actual state
                                current_state_id = actual_state.state_id
                                current_state = actual_state
                                if current_state_id not in self.states:
                                    self.states[current_state_id] = actual_state
            
            except Exception as e:
                logger.error("Error verifying/navigating to state: %s", e)
                explored_states.add(current_state_id)
                continue
            
            # Mark as explored
            explored_states.add(current_state_id)
            
            # Discover transitions from this state (will click links and discover new states)
            try:
                new_states = await self._discover_transitions_from_state(page, current_state)
                
                logger.info("Found %d new states from %s", len(new_states), current_state_id)
                
                # Add new states to queue (if not already explored or queued)
                # Convert queue to list for membership testing
                queue_list = list(self.state_queue)
                added_count = 0
                for new_state_id in new_states:
                    if new_state_id not in explored_states and new_state_id not in queue_list:
                        self.state_queue.append(new_state_id)
                        queue_list.append(new_state_id)  # Update our copy too
                        added_count += 1
                        logger.info("Added %s to exploration queue (queue size: %d)", 
                                   new_state_id, len(self.state_queue))
                    else:
                        logger.debug("Skipping %s (already explored or in queue)", new_state_id)
                
                logger.info("Added %d states to queue, queue now has %d states", 
                           added_count, len(self.state_queue))
            
            except Exception as e:
                logger.error("Error discovering transitions: %s", e)
        
        logger.info("Exploration complete: %d states explored", len(explored_states))
        self.visited_states = explored_states
    
    async def _explore_states_bfs(self, page: Page):
        """BFS exploration of reachable states via actions.
        
        For each discovered state, find actionable elements (buttons, links),
        execute safe actions, discover resulting states, and record transitions.
        
        Args:
            page: Playwright Page object
        """
        logger.info("Starting BFS state exploration...")
        
        max_iterations = self.max_states * 2  # Safety limit on iterations
        iteration_count = 0
        
        while self.state_queue and len(self.visited_states) < self.max_states:
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.error("Exceeded max iterations (%d), stopping to prevent infinite loop", max_iterations)
                break
            
            current_state_id = self.state_queue.popleft()
            
            if current_state_id in self.visited_states:
                continue
            
            # Skip exploring error or login states (they won't have useful navigation)
            current_state = self.states.get(current_state_id)
            if current_state and current_state.state_type in ["error", "form"]:
                logger.info("Skipping exploration of %s state: %s", 
                           current_state.state_type, current_state_id)
                self.visited_states.add(current_state_id)
                continue
            
            logger.info("Exploring state: %s (%d/%d)", 
                       current_state_id, len(self.visited_states), self.max_states)
            
            # Navigate to this state (current_state already retrieved above)
            try:
                nav_success = await asyncio.wait_for(
                    self._navigate_to_state(page, current_state_id),
                    timeout=30.0  # 30 second timeout per navigation
                )
            except asyncio.TimeoutError:
                logger.error("Navigation to %s timed out after 30s", current_state_id)
                self.visited_states.add(current_state_id)
                continue
            except Exception as e:
                logger.error("Error navigating to %s: %s", current_state_id, e)
                self.visited_states.add(current_state_id)
                continue
            
            if not nav_success:
                logger.warning("Failed to navigate to state %s, skipping exploration", current_state_id)
                self.visited_states.add(current_state_id)  # Mark as visited to avoid retry
                continue
            
            # Verify we're in the expected state
            try:
                actual_state = await self._discover_current_state(page)
                if actual_state.state_id != current_state_id:
                    logger.warning("Navigation mismatch: expected %s, got %s", 
                                 current_state_id, actual_state.state_id)
                    # Continue anyway - maybe the state changed slightly
            except Exception as e:
                logger.error("Error verifying state: %s", e)
                self.visited_states.add(current_state_id)
                continue
            
            # Mark as visited
            self.visited_states.add(current_state_id)
            
            # Find and execute safe actions from this state
            try:
                new_states = await asyncio.wait_for(
                    self._discover_transitions_from_state(page, current_state),
                    timeout=60.0  # 60 second timeout per state exploration
                )
            except asyncio.TimeoutError:
                logger.error("State exploration for %s timed out after 60s", current_state_id)
                new_states = []
            except Exception as e:
                logger.error("Error discovering transitions from %s: %s", current_state_id, e)
                new_states = []
            
            # Add new states to queue
            for new_state_id in new_states:
                if new_state_id not in self.visited_states and new_state_id not in self.state_queue:
                    self.state_queue.append(new_state_id)
            
            logger.debug("Found %d new states from %s", len(new_states), current_state_id)
        
        if len(self.visited_states) >= self.max_states:
            logger.warning("Reached max_states limit (%d)", self.max_states)
    
    async def _discover_transitions_from_state(
        self, 
        page: Page, 
        state: UIState
    ) -> list[str]:
        """Discover possible transitions from a given state.
        
        Args:
            page: Playwright Page object
            state: Current UIState
            
        Returns:
            List of new state IDs discovered (that haven't been explored yet)
        """
        new_states = []
        
        # Strategy 1: Click safe navigation links (most common transition)
        safe_links = await self._find_safe_links(page)
        logger.debug("Found %d safe navigation links to try", len(safe_links))
        
        for i, link_info in enumerate(safe_links[:10]):  # Try up to 10 links
            try:
                # Don't navigate back on the last link - stay there to explore it next
                is_last = (i == len(safe_links[:10]) - 1) and len(safe_links[:10]) > 0
                new_state_id = await self._execute_link_click(page, state, link_info, navigate_back=not is_last)
                # Add any state that was discovered (even if already in self.states)
                # The caller will check if it needs to be explored
                if new_state_id and new_state_id != state.state_id:
                    new_states.append(new_state_id)
                    logger.debug("Link click produced state: %s", new_state_id)
            except Exception as e:
                logger.debug("Error executing link click: %s", e)
        
        # Strategy 2: Click safe buttons
        safe_buttons = await self._find_safe_buttons(page)
        logger.debug("Found %d safe buttons to try", len(safe_buttons))
        
        for i, button_info in enumerate(safe_buttons[:5]):  # Limit to first 5 buttons
            try:
                # Don't navigate back on the last button - stay there to explore it next
                is_last = (i == len(safe_buttons[:5]) - 1) and len(safe_buttons[:5]) > 0
                new_state_id = await self._execute_button_click(page, state, button_info, navigate_back=not is_last)
                # Add any state that was discovered (even if already in self.states)
                if new_state_id and new_state_id != state.state_id:
                    new_states.append(new_state_id)
                    logger.debug("Button click produced state: %s", new_state_id)
            except Exception as e:
                logger.debug("Error executing button click: %s", e)
        
        return new_states
    
    async def _find_safe_links(self, page: Page) -> list[dict[str, Any]]:
        """Find navigation links that are safe to click.
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of safe link descriptors
        """
        safe_links = []
        seen_hashes = set()  # To avoid duplicates
        
        # Safe navigation patterns (menu items, not data links)
        safe_nav_patterns = [
            "overview", "dashboard", "devices", "faults", "admin",
            "config", "presets", "provisions", "files", "tasks",
            "users", "permissions", "virtualparameters"
        ]
        
        try:
            # 1. Standard Navigation Links
            nav_locators = [
                page.locator('nav a'),  # removed :visible to see if that's the blocker
                page.locator('[role="navigation"] a'),
                page.locator('.wrapper .sidebar a'), # Less specific sidebar selector
                page.locator('header a')
            ]

            # 2. Tab Links
            tab_locators = [
                page.locator('.tabs a'),
                page.locator('ul.tabs a'),
                page.locator('[role="tablist"] a'),
                page.locator('[role="tab"]')
            ]
            
            all_locators = nav_locators + tab_locators
            
            # Iterate through all locator strategies
            candidates = []
            for loc in all_locators:
                try:
                    count = await loc.count()
                    logger.debug("Locator found %d candidates", count)
                    for i in range(count):
                        candidates.append(loc.nth(i))
                except Exception as e:
                    logger.debug("Error counting locator: %s", e)
                    continue
            
            logger.debug("Total candidates found: %d", len(candidates))
            
            # Process candidates (limit to unique ones)
            for link in candidates:
                try:
                    # Deduplication check
                    if len(safe_links) >= 30:
                        break

                    text = await link.text_content()
                    text_lower = text.strip().lower() if text else ""
                    href = await link.get_attribute('href')
                    
                    logger.debug("Checking link: text='%s', href='%s'", text_lower, href)
                    
                    # Dedupe based on href + text
                    link_hash = f"{href}|{text_lower}"
                    if link_hash in seen_hashes:
                        logger.debug("Skipping duplicate")
                        continue
                    seen_hashes.add(link_hash)

                    # Skip external links
                    if href and href.startswith('http') and self.base_url not in href:
                         logger.debug("Skipping external link")
                         continue
                    
                    # TRUST TABS AND NAV: If it's in a known nav/tab container, it's likely safe
                    # regardless of text pattern, unless it looks destructive.
                    
                    # Check if matches safe navigation patterns
                    is_known_safe_term = any(pattern in text_lower or (href and pattern in href.lower()) 
                                 for pattern in safe_nav_patterns)
                    
                    # Heuristic: If it's in a tab/nav container and DOESN'T look like "delete" or "remove"
                    is_likely_safe_nav = True
                    unsafe_terms = ["delete", "remove", "destroy", "drop"]
                    if any(term in text_lower for term in unsafe_terms):
                        is_likely_safe_nav = False
                        
                    if is_known_safe_term or is_likely_safe_nav:
                        logger.debug("Link accepted as safe")
                        descriptor = await self._get_element_descriptor(link)
                        if descriptor:
                            safe_links.append(descriptor)
                    else:
                        logger.debug("Link rejected as unsafe")
                
                except Exception as e:
                    logger.debug("Error processing link candidate: %s", e)
                    continue
        
        except Exception as e:
            logger.debug("Error finding safe links: %s", e)
        
        return safe_links
    
    async def _find_safe_buttons(self, page: Page) -> list[dict[str, Any]]:
        """Find buttons that are safe to click.
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of safe button descriptors
        """
        safe_buttons = []
        
        try:
            # BROADENED SCOPE: Include role="button" elements
            all_buttons = await page.locator('button:visible, [role="button"]:visible').all()
            
            for button in all_buttons[:20]:  # Limit scan
                try:
                    text = await button.text_content()
                    text_lower = text.strip().lower() if text else ""
                    
                    # Check if matches safe patterns
                    is_safe = any(pattern in text_lower for pattern in self.safe_button_patterns)
                    
                    if is_safe:
                        descriptor = await self._get_element_descriptor(button)
                        if descriptor:
                            safe_buttons.append(descriptor)
                
                except Exception:
                    continue
        
        except Exception as e:
            logger.debug("Error finding safe buttons: %s", e)
        
        return safe_buttons
    
    async def _execute_link_click(
        self,
        page: Page,
        from_state: UIState,
        link_info: dict[str, Any],
        navigate_back: bool = True
    ) -> str | None:
        """Execute a link click and discover resulting state.
        
        Args:
            page: Playwright Page object
            from_state: State before clicking
            link_info: Link element descriptor
            navigate_back: Whether to navigate back after discovering new state
            
        Returns:
            New state ID, or None if no state change
        """
        initial_url = page.url
        
        try:
            # Try to locate link using descriptor
            link = await self._locate_element_from_descriptor(page, link_info)
            
            if not link:
                return None
            
            # Get link text for logging
            link_text = link_info.get("locators", {}).get("text", "unknown")
            
            # Click link
            await link.click()
            
            # Wait for navigation
            try:
                await page.wait_for_load_state('networkidle', timeout=3000)
            except PlaywrightTimeoutError:
                await asyncio.sleep(0.5)
            
            # Discover new state
            new_state = await self._discover_current_state(page)
            
            # Check if actually changed state
            if new_state.state_id == from_state.state_id:
                logger.debug("Link click didn't change state: %s", link_text)
                # Navigate back anyway
                if navigate_back and page.url != initial_url:
                    await page.goto(initial_url)
                    await page.wait_for_load_state('networkidle')
                return None
            
            # Add new state
            if new_state.state_id not in self.states:
                self.states[new_state.state_id] = new_state
            
            # Record transition
            transition = StateTransition(
                transition_id=f"T_{from_state.state_id}_TO_{new_state.state_id}_NAV",
                from_state=from_state.state_id,
                to_state=new_state.state_id,
                action_type="navigate",
                trigger_locators=link_info,
            )
            self.transitions.append(transition)
            
            logger.info("Navigation transition: %s -> %s (via '%s')", 
                       from_state.state_id, new_state.state_id, link_text)
            
            # Navigate back to source state so we can click other links
            # This is essential for discovering multiple transitions from one state
            if navigate_back and page.url != initial_url:
                logger.debug("Navigating back to %s to discover more transitions", from_state.state_id)
                await page.goto(initial_url)
                await page.wait_for_load_state('networkidle')
            
            return new_state.state_id
            
        except Exception as e:
            logger.debug("Error in link click execution: %s", e)
            # Try to navigate back on error
            if navigate_back:
                try:
                    if page.url != initial_url:
                        await page.goto(initial_url)
                        await page.wait_for_load_state('networkidle')
                except Exception:
                    pass
            return None
    
    async def _execute_button_click(
        self,
        page: Page,
        from_state: UIState,
        button_info: dict[str, Any],
        navigate_back: bool = True
    ) -> str | None:
        """Execute a button click and discover resulting state.
        
        Args:
            page: Playwright Page object
            from_state: State before clicking
            button_info: Button element descriptor
            navigate_back: Whether to navigate back after discovering new state
            
        Returns:
            New state ID, or None if no state change
        """
        initial_url = page.url
        
        try:
            # Try to locate button using descriptor
            button = await self._locate_element_from_descriptor(page, button_info)
            
            if not button:
                return None
            
            # Click button
            await button.click()
            
            # Wait for potential state change
            try:
                await page.wait_for_load_state('networkidle', timeout=2000)
            except PlaywrightTimeoutError:
                await asyncio.sleep(0.5)
            
            # Discover new state
            new_state = await self._discover_current_state(page)
            
            # Check if actually changed state
            if new_state.state_id == from_state.state_id:
                logger.debug("Button click didn't change state")
                if navigate_back and page.url != initial_url:
                    await page.goto(initial_url)
                    await page.wait_for_load_state('networkidle')
                return None
            
            # Add new state
            if new_state.state_id not in self.states:
                self.states[new_state.state_id] = new_state
            
            # Record transition
            transition = StateTransition(
                transition_id=f"T_{from_state.state_id}_TO_{new_state.state_id}_CLICK",
                from_state=from_state.state_id,
                to_state=new_state.state_id,
                action_type="click",
                trigger_locators=button_info,
            )
            self.transitions.append(transition)
            
            logger.info("Button transition: %s -> %s", from_state.state_id, new_state.state_id)
            
            # Navigate back to source state
            if navigate_back and page.url != initial_url:
                logger.debug("Navigating back to %s to discover more transitions", from_state.state_id)
                await page.goto(initial_url)
                await page.wait_for_load_state('networkidle')
            
            return new_state.state_id
            
        except Exception as e:
            logger.debug("Error in button click execution: %s", e)
            if navigate_back:
                try:
                    if page.url != initial_url:
                        await page.goto(initial_url)
                        await page.wait_for_load_state('networkidle')
                except Exception:
                    pass
            return None
    
    async def _locate_element_from_descriptor(
        self,
        page: Page,
        descriptor: dict[str, Any]
    ) -> Locator | None:
        """Locate element using resilient descriptor.
        
        Args:
            page: Playwright Page object
            descriptor: Element descriptor with locator strategies
            
        Returns:
            Locator object, or None if not found
        """
        locators = descriptor.get("locators", {})
        element_type = descriptor.get("element_type", "")
        
        # Try locators in priority order
        # Priority 1: test_id
        if "test_id" in locators:
            try:
                loc = page.get_by_test_id(locators["test_id"])
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        
        # Priority 2: role + aria_label
        if "role" in locators:
            try:
                if "aria_label" in locators:
                    loc = page.get_by_role(locators["role"], name=locators["aria_label"])
                else:
                    loc = page.get_by_role(locators["role"])
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        
        # Priority 3: text (with element type context)
        if "text" in locators:
            try:
                text = locators["text"]
                if element_type == "link":
                    # For links, combine text with href if available
                    loc = page.locator(f'a:has-text("{text}")').first
                    if await loc.count() > 0:
                        return loc
                else:
                    loc = page.get_by_text(text, exact=False)
                    if await loc.count() > 0:
                        return loc.first
            except Exception:
                pass
        
        # Priority 4: href (for links)
        if "href" in locators and element_type == "link":
            try:
                href = locators["href"]
                loc = page.locator(f'a[href="{href}"]')
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        
        # Priority 5: placeholder (for inputs)
        if "placeholder" in locators:
            try:
                loc = page.get_by_placeholder(locators["placeholder"])
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        
        # Priority 6: name attribute (for inputs)
        if "name" in locators and element_type in ["input", "select"]:
            try:
                name = locators["name"]
                loc = page.locator(f'{element_type}[name="{name}"]')
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        
        return None
    
    def _export_to_graph(self) -> dict[str, Any]:
        """Export FSM to graph format compatible with analysis tools.
        
        Returns:
            Dictionary containing nodes, edges, and metadata
        """
        nodes = []
        edges = []
        
        # Export states as nodes
        for state_id, state in self.states.items():
            nodes.append({
                "id": state_id,
                "node_type": "state",
                "state_type": state.state_type,
                "fingerprint": state.fingerprint,
                "verification_logic": state.verification_logic,
                "element_descriptors": state.element_descriptors,
                "discovered_at": state.discovered_at,
            })
        
        # Export transitions as edges
        for transition in self.transitions:
            edges.append({
                "source": transition.from_state,
                "target": transition.to_state,
                "edge_type": "transition",
                "transition_id": transition.transition_id,
                "action_type": transition.action_type,
                "trigger_locators": transition.trigger_locators,
                "action_data": transition.action_data,
                "success_rate": transition.success_rate,
            })
        
        return {
            "base_url": self.base_url,
            "graph_type": "fsm_mbt",
            "discovery_method": "playwright_state_machine_dfs" if self.use_dfs else "playwright_state_machine_bfs",
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "state_count": len(self.states),
                "transition_count": len(self.transitions),
                "visited_states": len(self.visited_states),
                "state_types": self._get_state_type_distribution(),
            }
        }
    
    def _get_state_type_distribution(self) -> dict[str, int]:
        """Get distribution of state types.
        
        Returns:
            Dictionary mapping state_type to count
        """
        distribution: dict[str, int] = {}
        for state in self.states.values():
            distribution[state.state_type] = distribution.get(state.state_type, 0) + 1
        return distribution


def main():
    """Command-line interface for FSM/MBT UI discovery tool."""
    parser = argparse.ArgumentParser(
        description="Discover UI states and transitions using FSM/MBT approach with Playwright"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of the application to crawl",
    )
    parser.add_argument(
        "--output",
        default="ui_state_machine.json",
        help="Output file for FSM graph (default: ui_state_machine.json)",
    )
    parser.add_argument(
        "--username",
        help="Login username (optional)",
    )
    parser.add_argument(
        "--password",
        help="Login password (optional)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser with GUI",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10000,
        help="Default timeout in milliseconds (default: 10000)",
    )
    parser.add_argument(
        "--max-states",
        type=int,
        default=50,
        help="Maximum number of states to discover (default: 50)",
    )
    parser.add_argument(
        "--safe-buttons",
        default="New,Add,Edit,View,Show,Cancel,Close,Search,Filter",
        help="Comma-separated button text patterns safe to click",
    )
    parser.add_argument(
        "--skip-login-discovery",
        action="store_true",
        help="Skip discovering login flow states",
    )
    parser.add_argument(
        "--use-bfs",
        action="store_true",
        help="Use Breadth-First Search instead of Depth-First Search (default: DFS)",
    )

    args = parser.parse_args()

    # Create discovery tool
    tool = UIStateMachineDiscovery(
        base_url=args.url,
        headless=args.headless,
        timeout=args.timeout,
        max_states=args.max_states,
        safe_button_patterns=args.safe_buttons,
        use_dfs=not args.use_bfs,  # Default to DFS
    )

    # Run discovery
    logger.info("Starting FSM/MBT discovery for %s", args.url)
    graph_data = asyncio.run(tool.discover(
        username=args.username,
        password=args.password,
        discover_login_flow=not args.skip_login_discovery,
    ))

    # Save to file
    output_path = Path(args.output)
    with output_path.open("w") as f:
        json.dump(graph_data, f, indent=2)

    logger.info("FSM graph saved to %s", output_path)
    
    # Log statistics
    stats = graph_data.get("statistics", {})
    logger.info("Discovery complete:")
    logger.info("  - States discovered: %d", stats.get("state_count", 0))
    logger.info("  - Transitions found: %d", stats.get("transition_count", 0))
    logger.info("  - States explored: %d", stats.get("visited_states", 0))
    logger.info("  - State type distribution:")
    for state_type, count in stats.get("state_types", {}).items():
        logger.info("      %s: %d", state_type, count)


if __name__ == "__main__":
    main()

