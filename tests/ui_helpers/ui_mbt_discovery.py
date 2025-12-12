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
from enum import Enum
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


class ActionType(str, Enum):
    CLICK = "click"
    FILL_FORM = "fill_form"
    NAVIGATE = "navigate"


@dataclass
class StateTransition:
    """Represents an action that transitions between states.
    
    In FSM/MBT terminology, this is an 'Edge' - the executable action
    that moves the system from one verifiable state to another.
    """
    transition_id: str
    from_state: str
    to_state: str
    action_type: ActionType | str  # "click", "fill_form", "navigate"
    trigger_locators: dict[str, Any] = field(default_factory=dict)
    action_data: Optional[dict[str, Any]] = None
    success_rate: float = 1.0  # Track reliability


class StateFingerprinter:
    """Creates robust fingerprints using Accessibility Tree as primary source.
    
    The accessibility tree provides semantic, stable state identification
    that is resilient to CSS and DOM changes. This approach prioritizes:
    1. Semantic identity (ARIA roles, landmarks, states) - 60%
    2. Functional identity (actionable elements) - 25%
    3. Structural identity (URL pattern) - 10%
    4. Content identity (title, headings) - 4%
    5. Style identity (DOM hash - optional) - 1%
    """
    
    @staticmethod
    async def create_fingerprint(page: Page) -> dict[str, Any]:
        """Generate accessibility-tree-based state fingerprint.
        
        This replaces DOM scraping with semantic capture from the browser's
        accessibility tree, providing maximum resilience to UI changes.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Dictionary with accessibility-first fingerprint dimensions
        """
        # Capture the accessibility tree (PRIMARY SOURCE)
        # Use Playwright's native ariaSnapshot() API
        a11y_tree = await StateFingerprinter._capture_a11y_tree_via_aria_snapshot(page)
        
        if not a11y_tree:
            logger.warning("Accessibility tree capture returned None, falling back to basic fingerprint")
            # Fallback to minimal fingerprint
            return {
                "url_pattern": StateFingerprinter._extract_url_pattern(page.url),
                "title": await page.title(),
                "accessibility_tree": None,
                "actionable_elements": {"buttons": [], "links": [], "inputs": [], "total_count": 0},
            }
        
        # Extract structured fingerprint from a11y tree
        return {
            # PRIMARY IDENTITY (60% weight) - Semantic
            "accessibility_tree": StateFingerprinter._extract_a11y_fingerprint(a11y_tree),
            
            # FUNCTIONAL IDENTITY (25% weight) - Actionable elements
            "actionable_elements": StateFingerprinter._extract_actionable_elements(a11y_tree),
            
            # STRUCTURAL IDENTITY (10% weight)
            "url_pattern": StateFingerprinter._extract_url_pattern(page.url),
            "route_params": StateFingerprinter._extract_route_params(page.url),
            
            # CONTENT IDENTITY (4% weight)
            "title": await page.title(),
            "main_heading": await StateFingerprinter._get_main_heading(page),
            
            # STYLE IDENTITY (1% weight - OPTIONAL, only for edge cases)
            # "dom_structure_hash": await StateFingerprinter._get_dom_hash(page),
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
    def _extract_route_params(url: str) -> dict[str, str]:
        """Extract route parameters from URL (query and fragment params).
        
        Args:
            url: Full URL
            
        Returns:
            Dictionary of parameters
        """
        parsed = urlparse(url)
        params = {}
        
        # Extract query parameters
        if parsed.query:
            from urllib.parse import parse_qs
            query_params = parse_qs(parsed.query)
            # Flatten single-value lists
            params.update({k: v[0] if len(v) == 1 else v for k, v in query_params.items()})
        
        # For SPAs, check fragment for additional params
        if parsed.fragment and '?' in parsed.fragment:
            fragment_query = parsed.fragment.split('?', 1)[1]
            from urllib.parse import parse_qs
            frag_params = parse_qs(fragment_query)
            params.update({k: v[0] if len(v) == 1 else v for k, v in frag_params.items()})
        
        return params
    
    @staticmethod
    async def _capture_a11y_tree_via_aria_snapshot(page: Page) -> dict:
        """Capture accessibility tree using Playwright's native ariaSnapshot() API.
        
        This uses Playwright's built-in ARIA snapshot feature which provides
        a YAML representation of the accessible elements. This is the official,
        supported method for capturing accessibility state.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Accessibility tree dictionary parsed from ARIA snapshot YAML
        """
        try:
            # Use native ariaSnapshot() API - returns YAML string
            locator = page.locator('body')
            yaml_snapshot = await locator.aria_snapshot()
            
            # Parse YAML to extract structured data
            tree = StateFingerprinter._parse_aria_snapshot_yaml(yaml_snapshot)
            return tree
        except Exception as e:
            logger.warning(f"Error capturing ARIA snapshot: {e}")
            return None
    
    @staticmethod
    def _parse_aria_snapshot_yaml(yaml_str: str) -> dict:
        """Parse ARIA snapshot YAML into structured tree.
        
        ARIA snapshot format (actual example):
            - navigation:
              - list:
                - listitem:
                  - link "Overview":
                    - /url: "#!/overview"
            - heading "Dashboard" [level=2]
            - button "Submit"
        
        Args:
            yaml_str: YAML string from ariaSnapshot()
            
        Returns:
            Parsed tree structure with role/name/children
        """
        import re
        
        lines = yaml_str.strip().split('\n')
        root = {'role': 'root', 'name': '', 'children': []}
        stack = [(-2, root)]  # (indent_level, node)
        
        for line in lines:
            # Calculate indent level (each indent is 2 spaces)
            indent = (len(line) - len(line.lstrip()))
            content = line.strip()
            
            if not content or content.startswith('#'):
                continue
            
            # Skip URL lines (they're metadata, not nodes)
            if content.startswith('- /url:') or content.startswith('/url:'):
                # Extract URL and add to parent node
                url_match = re.search(r'/url:\s*"([^"]+)"', content)
                if url_match and stack:
                    parent = stack[-1][1]
                    parent['value'] = url_match.group(1)
                continue
            
            # Remove leading '- '
            if content.startswith('- '):
                content = content[2:]
            
            # Skip if it's just a key: value pair (not a role)
            if not content or content.startswith('/'):
                continue
            
            # Parse node: role "name" [attributes]
            node = {'children': []}
            
            # Check for attributes in brackets
            attr_match = re.search(r'\[([^\]]+)\]$', content)
            if attr_match:
                attrs_str = attr_match.group(1)
                content = content[:attr_match.start()].strip()
                
                # Parse attributes (level=1, pressed=true, etc.)
                for attr_pair in attrs_str.split(','):
                    if '=' in attr_pair:
                        key, val = attr_pair.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        
                        # Convert to appropriate type
                        if val.lower() == 'true':
                            node[key] = True
                        elif val.lower() == 'false':
                            node[key] = False
                        elif val.isdigit():
                            node[key] = int(val)
                        else:
                            node[key] = val
            
            # Check if ends with colon (container node)
            is_container = content.endswith(':')
            if is_container:
                content = content[:-1].strip()
            
            # Parse role and name
            # Format: role "name" or just role or text: "content"
            
            # Handle text: "content" specially
            if content.startswith('text:'):
                text_match = re.search(r'text:\s*"?([^"]*)"?', content)
                if text_match:
                    node['role'] = 'text'
                    node['name'] = text_match.group(1)
                else:
                    node['role'] = 'text'
                    node['name'] = content[5:].strip()
            else:
                # Try to match: role "name"
                name_match = re.search(r'^(\S+)\s+"([^"]+)"$', content)
                if name_match:
                    node['role'] = name_match.group(1)
                    node['name'] = name_match.group(2)
                else:
                    # Just role, no name
                    node['role'] = content if content else 'generic'
                    node['name'] = ''
            
            # Pop stack to correct parent level
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            
            # Add to parent
            if stack:
                parent = stack[-1][1]
                if 'children' not in parent:
                    parent['children'] = []
                parent['children'].append(node)
            
            # Push current node onto stack (it might have children)
            stack.append((indent, node))
        
        return root
    
    @staticmethod
    async def _get_main_heading(page: Page) -> str:
        """Get the main heading (h1) from the page.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Text content of first h1 element, or empty string
        """
        try:
            h1 = page.locator('h1').first
            if await h1.count() > 0:
                return await h1.text_content() or ""
        except Exception:
            pass
        return ""
    
    @staticmethod
    def _extract_a11y_fingerprint(tree: dict) -> dict:
        """Extract stable semantic fingerprint from accessibility tree.
        
        Args:
            tree: Accessibility tree from page.accessibility.snapshot()
            
        Returns:
            Dictionary with semantic fingerprint components
        """
        return {
            "structure_hash": StateFingerprinter._hash_tree_structure(tree),
            "landmark_roles": StateFingerprinter._extract_landmarks(tree),
            "interactive_count": StateFingerprinter._count_interactive(tree),
            "heading_hierarchy": StateFingerprinter._extract_headings(tree),
            "key_landmarks": StateFingerprinter._extract_key_landmarks(tree),
            "aria_states": StateFingerprinter._extract_aria_states(tree),
        }
    
    @staticmethod
    def _extract_actionable_elements(tree: dict) -> dict:
        """Extract all interactive elements from accessibility tree.
        
        This REPLACES ui_map.json seeding! The a11y tree provides both
        state identity AND the list of available actions.
        
        Args:
            tree: Accessibility tree
            
        Returns:
            Dictionary with categorized actionable elements
        """
        buttons = []
        links = []
        inputs = []
        
        def traverse(node: dict):
            role = node.get("role", "")
            name = node.get("name", "")
            value = node.get("value")
            
            if role == "button":
                buttons.append({
                    "role": role,
                    "name": name,
                    "aria_states": StateFingerprinter._get_node_aria_states(node),
                    "locator_strategy": f"getByRole('button', {{ name: '{name}' }})"
                })
            elif role == "link":
                links.append({
                    "role": role,
                    "name": name,
                    "href": value,
                    "aria_states": StateFingerprinter._get_node_aria_states(node),
                    "locator_strategy": f"getByRole('link', {{ name: '{name}' }})"
                })
            elif role in ["textbox", "combobox", "searchbox", "spinbutton"]:
                inputs.append({
                    "role": role,
                    "name": name,
                    "aria_states": StateFingerprinter._get_node_aria_states(node),
                    "locator_strategy": f"getByLabel('{name}')" if name else f"getByRole('{role}')"
                })
            
            # Recurse to children
            for child in node.get("children", []):
                traverse(child)
        
        traverse(tree)
        
        return {
            "buttons": buttons,
            "links": links,
            "inputs": inputs,
            "total_count": len(buttons) + len(links) + len(inputs),
        }
    
    @staticmethod
    def _hash_tree_structure(tree: dict) -> str:
        """Create hash of accessibility tree topology (roles + hierarchy).
        
        This is MORE stable than DOM hash because it captures semantic structure.
        Text is truncated to avoid hash changes from content updates.
        
        Args:
            tree: Accessibility tree
            
        Returns:
            8-character hash of tree structure
        """
        def extract_structure(node: dict) -> dict:
            return {
                "role": node.get("role"),
                "name": node.get("name", "")[:20],  # Truncate to avoid text changes
                "children": [extract_structure(child) for child in node.get("children", [])]
            }
        
        structure = extract_structure(tree)
        structure_str = json.dumps(structure, sort_keys=True)
        return hashlib.md5(structure_str.encode()).hexdigest()[:8]
    
    @staticmethod
    def _extract_landmarks(tree: dict) -> list[str]:
        """Extract ARIA landmark roles (most stable identifiers).
        
        Args:
            tree: Accessibility tree
            
        Returns:
            List of landmark role names
        """
        landmarks = []
        landmark_roles = {"navigation", "main", "complementary", "contentinfo", 
                         "banner", "search", "form", "region"}
        
        def traverse(node: dict):
            role = node.get("role", "")
            if role in landmark_roles:
                landmarks.append(role)
            for child in node.get("children", []):
                traverse(child)
        
        traverse(tree)
        return landmarks
    
    @staticmethod
    def _count_interactive(tree: dict) -> int:
        """Count total interactive elements.
        
        Args:
            tree: Accessibility tree
            
        Returns:
            Count of interactive elements
        """
        interactive_roles = {"button", "link", "textbox", "combobox", 
                            "checkbox", "radio", "searchbox", "spinbutton"}
        count = 0
        
        def traverse(node: dict):
            nonlocal count
            if node.get("role") in interactive_roles:
                count += 1
            for child in node.get("children", []):
                traverse(child)
        
        traverse(tree)
        return count
    
    @staticmethod
    def _extract_headings(tree: dict) -> list[str]:
        """Extract heading hierarchy (h1-h6).
        
        Args:
            tree: Accessibility tree
            
        Returns:
            List of headings with levels (e.g., ["h1: Dashboard", "h2: Overview"])
        """
        headings = []
        
        def traverse(node: dict):
            role = node.get("role", "")
            if role == "heading":
                level = node.get("level", 0)
                name = node.get("name", "")
                if name:  # Only include non-empty headings
                    headings.append(f"h{level}: {name}")
            for child in node.get("children", []):
                traverse(child)
        
        traverse(tree)
        return headings
    
    @staticmethod
    def _extract_key_landmarks(tree: dict) -> dict:
        """Extract stable anchor landmarks for contextual navigation.
        
        Args:
            tree: Accessibility tree
            
        Returns:
            Dictionary of key landmarks with their paths
        """
        landmarks = {}
        
        def traverse(node: dict, path: list[str]):
            role = node.get("role", "")
            name = node.get("name", "")
            
            # Record navigation landmarks (most stable)
            if role == "navigation" and name:
                landmarks[f"nav_{len(landmarks)}"] = {
                    "role": role,
                    "name": name,
                    "path": " > ".join(path + [role])
                }
            
            # Record main content area
            if role == "main":
                landmarks["main_content"] = {
                    "role": role,
                    "name": name,
                    "path": " > ".join(path + [role])
                }
            
            # Record search landmarks
            if role == "search":
                landmarks["search"] = {
                    "role": role,
                    "name": name,
                    "path": " > ".join(path + [role])
                }
            
            for child in node.get("children", []):
                traverse(child, path + [role])
        
        traverse(tree, [])
        return landmarks
    
    @staticmethod
    def _extract_aria_states(tree: dict) -> dict:
        """Extract ARIA state attributes from the tree.
        
        ARIA states capture dynamic functional conditions:
        - aria-expanded: Collapsible menus/accordions
        - aria-selected: Tabs/options
        - aria-checked: Checkboxes/radios
        - aria-disabled: Disabled elements
        - aria-current: Current page/step
        - aria-pressed: Toggle buttons
        
        Args:
            tree: Accessibility tree
            
        Returns:
            Dictionary summarizing ARIA states in the tree
        """
        states_summary = {
            "expanded_elements": [],
            "selected_elements": [],
            "checked_elements": [],
            "disabled_count": 0,
            "current_indicators": [],
        }
        
        def traverse(node: dict, path: list[str]):
            role = node.get("role", "")
            name = node.get("name", "")
            
            # Check for various ARIA states
            if node.get("expanded") is not None:
                states_summary["expanded_elements"].append({
                    "role": role,
                    "name": name,
                    "expanded": node.get("expanded"),
                    "path": " > ".join(path + [role]) if path else role
                })
            
            if node.get("selected") is not None:
                states_summary["selected_elements"].append({
                    "role": role,
                    "name": name,
                    "selected": node.get("selected")
                })
            
            if node.get("checked") is not None:
                states_summary["checked_elements"].append({
                    "role": role,
                    "name": name,
                    "checked": node.get("checked")
                })
            
            if node.get("disabled"):
                states_summary["disabled_count"] += 1
            
            # aria-current indicates current page/step
            if node.get("current"):
                states_summary["current_indicators"].append({
                    "role": role,
                    "name": name,
                    "current": node.get("current")
                })
            
            for child in node.get("children", []):
                traverse(child, path + [role])
        
        traverse(tree, [])
        return states_summary
    
    @staticmethod
    def _get_node_aria_states(node: dict) -> dict:
        """Extract ARIA state attributes from a single node.
        
        Args:
            node: Single node from accessibility tree
            
        Returns:
            Dictionary of ARIA states for this node
        """
        return {
            "expanded": node.get("expanded"),
            "selected": node.get("selected"),
            "checked": node.get("checked"),
            "disabled": node.get("disabled"),
            "pressed": node.get("pressed"),
            "current": node.get("current"),
        }
    
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


class StateComparer:
    """Compares UI states using weighted similarity scoring.
    
    Implements fuzzy matching based on accessibility tree properties
    to identify same states even after UI changes (CSS, DOM restructure).
    
    Weighting Hierarchy (from Architecting UI Test Resilience):
    1. Semantic identity (60%): Accessibility tree (landmarks, roles, structure)
    2. Functional identity (25%): Actionable elements (buttons, links, inputs)
    3. Structural identity (10%): URL pattern
    4. Content identity (4%): Title, headings
    5. Style identity (1%): DOM hash (optional, rarely used)
    """
    
    # Similarity thresholds
    MATCH_THRESHOLD = 0.80  # 80% similarity = same state
    STRONG_MATCH = 0.90     # 90%+ = very confident match
    WEAK_MATCH = 0.70       # 70-80% = possible match (needs review)
    
    @staticmethod
    def calculate_similarity(fp1: dict[str, Any], fp2: dict[str, Any]) -> float:
        """Calculate weighted similarity between two state fingerprints.
        
        Args:
            fp1: First state fingerprint (with accessibility tree)
            fp2: Second state fingerprint (with accessibility tree)
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        scores = {}
        
        # 1. Semantic identity (60%): Accessibility tree
        scores['semantic'] = StateComparer._compare_a11y_trees(
            fp1.get('accessibility_tree'),
            fp2.get('accessibility_tree')
        )
        
        # 2. Functional identity (25%): Actionable elements
        scores['functional'] = StateComparer._compare_actionable_elements(
            fp1.get('actionable_elements'),
            fp2.get('actionable_elements')
        )
        
        # 3. Structural identity (10%): URL pattern
        scores['structural'] = StateComparer._compare_url_patterns(
            fp1.get('url_pattern', ''),
            fp2.get('url_pattern', '')
        )
        
        # 4. Content identity (4%): Title and headings
        scores['content'] = StateComparer._compare_content(
            fp1.get('title', ''),
            fp2.get('title', ''),
            fp1.get('main_heading', ''),
            fp2.get('main_heading', '')
        )
        
        # 5. Style identity (1%): Optional, not used by default
        # scores['style'] = ...
        
        # Calculate weighted average
        weighted_score = (
            scores['semantic'] * 0.60 +
            scores['functional'] * 0.25 +
            scores['structural'] * 0.10 +
            scores['content'] * 0.04
            # + scores['style'] * 0.01  # Optional
        )
        
        logger.debug(
            "Similarity scores: semantic=%.2f, functional=%.2f, "
            "structural=%.2f, content=%.2f, weighted=%.2f",
            scores['semantic'], scores['functional'],
            scores['structural'], scores['content'], weighted_score
        )
        
        return weighted_score
    
    @staticmethod
    def _compare_a11y_trees(tree1: dict | None, tree2: dict | None) -> float:
        """Compare accessibility trees for semantic similarity.
        
        Compares:
        - Landmark roles (navigation, main, etc.)
        - Interactive element count
        - Heading hierarchy
        - Key landmarks
        - ARIA states
        
        Args:
            tree1: First accessibility tree
            tree2: Second accessibility tree
            
        Returns:
            Similarity score 0.0-1.0
        """
        if not tree1 or not tree2:
            return 0.0
        
        scores = []
        
        # Compare landmark roles (most stable) - 40% of semantic score
        landmarks1 = set(tree1.get('landmark_roles', []))
        landmarks2 = set(tree2.get('landmark_roles', []))
        if landmarks1 or landmarks2:
            landmark_score = len(landmarks1 & landmarks2) / max(len(landmarks1 | landmarks2), 1)
            scores.append((landmark_score, 0.40))
        
        # Compare interactive count (approximate) - 20% of semantic score
        count1 = tree1.get('interactive_count', 0)
        count2 = tree2.get('interactive_count', 0)
        if count1 or count2:
            # Allow 20% variance (e.g., 8 vs 10 elements)
            max_count = max(count1, count2)
            diff = abs(count1 - count2)
            count_score = max(0.0, 1.0 - (diff / max(max_count * 0.2, 1)))
            scores.append((count_score, 0.20))
        
        # Compare heading hierarchy - 20% of semantic score
        headings1 = tree1.get('heading_hierarchy', [])
        headings2 = tree2.get('heading_hierarchy', [])
        if headings1 or headings2:
            # Exact match on headings (they're stable content)
            heading_score = 1.0 if headings1 == headings2 else 0.5
            scores.append((heading_score, 0.20))
        
        # Compare key landmarks - 10% of semantic score
        key_landmarks1 = set(tree1.get('key_landmarks', {}).keys())
        key_landmarks2 = set(tree2.get('key_landmarks', {}).keys())
        if key_landmarks1 or key_landmarks2:
            key_landmark_score = len(key_landmarks1 & key_landmarks2) / max(len(key_landmarks1 | key_landmarks2), 1)
            scores.append((key_landmark_score, 0.10))
        
        # Compare ARIA states - 10% of semantic score
        aria_score = StateComparer._compare_aria_states(
            tree1.get('aria_states'),
            tree2.get('aria_states')
        )
        scores.append((aria_score, 0.10))
        
        # Calculate weighted average
        if not scores:
            return 0.5  # Neutral if no data
        
        total_weight = sum(weight for _, weight in scores)
        weighted_sum = sum(score * weight for score, weight in scores)
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def _compare_aria_states(states1: dict | None, states2: dict | None) -> float:
        """Compare ARIA state attributes.
        
        Compares expanded/selected/checked/disabled states to detect
        same page in different dynamic conditions.
        
        Args:
            states1: First ARIA states dict
            states2: Second ARIA states dict
            
        Returns:
            Similarity score 0.0-1.0
        """
        if not states1 or not states2:
            return 1.0  # If no states, assume same (no dynamic state)
        
        scores = []
        
        # Compare expanded elements count
        exp1_count = len(states1.get('expanded_elements', []))
        exp2_count = len(states2.get('expanded_elements', []))
        if exp1_count or exp2_count:
            max_exp = max(exp1_count, exp2_count)
            exp_score = 1.0 - (abs(exp1_count - exp2_count) / max(max_exp, 1))
            scores.append(exp_score)
        
        # Compare selected elements count
        sel1_count = len(states1.get('selected_elements', []))
        sel2_count = len(states2.get('selected_elements', []))
        if sel1_count or sel2_count:
            max_sel = max(sel1_count, sel2_count)
            sel_score = 1.0 - (abs(sel1_count - sel2_count) / max(max_sel, 1))
            scores.append(sel_score)
        
        # Compare disabled count
        dis1 = states1.get('disabled_count', 0)
        dis2 = states2.get('disabled_count', 0)
        if dis1 or dis2:
            max_dis = max(dis1, dis2)
            dis_score = 1.0 - (abs(dis1 - dis2) / max(max_dis, 1))
            scores.append(dis_score)
        
        return sum(scores) / len(scores) if scores else 1.0
    
    @staticmethod
    def _compare_actionable_elements(
        actions1: dict | None,
        actions2: dict | None
    ) -> float:
        """Compare actionable elements (buttons, links, inputs).
        
        Uses fuzzy matching on role + name to handle text changes.
        
        Args:
            actions1: First actionable elements dict
            actions2: Second actionable elements dict
            
        Returns:
            Similarity score 0.0-1.0
        """
        if not actions1 or not actions2:
            return 0.0
        
        scores = []
        
        # Compare button count and names
        buttons1 = actions1.get('buttons', [])
        buttons2 = actions2.get('buttons', [])
        if buttons1 or buttons2:
            button_score = StateComparer._compare_element_lists(buttons1, buttons2)
            scores.append((button_score, 0.40))  # Buttons are important
        
        # Compare link count and names
        links1 = actions1.get('links', [])
        links2 = actions2.get('links', [])
        if links1 or links2:
            link_score = StateComparer._compare_element_lists(links1, links2)
            scores.append((link_score, 0.40))  # Links are important
        
        # Compare input count
        inputs1 = actions1.get('inputs', [])
        inputs2 = actions2.get('inputs', [])
        if inputs1 or inputs2:
            input_score = StateComparer._compare_element_lists(inputs1, inputs2)
            scores.append((input_score, 0.20))
        
        # Calculate weighted average
        if not scores:
            return 0.5
        
        total_weight = sum(weight for _, weight in scores)
        weighted_sum = sum(score * weight for score, weight in scores)
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def _compare_element_lists(list1: list, list2: list) -> float:
        """Compare two lists of elements by role and name.
        
        Uses fuzzy string matching for names to handle minor text changes.
        
        Args:
            list1: First element list
            list2: Second element list
            
        Returns:
            Similarity score 0.0-1.0
        """
        if not list1 and not list2:
            return 1.0
        if not list1 or not list2:
            return 0.0
        
        # Extract names from elements
        names1 = [elem.get('name', '') for elem in list1]
        names2 = [elem.get('name', '') for elem in list2]
        
        # Count exact matches
        set1 = set(names1)
        set2 = set(names2)
        exact_matches = len(set1 & set2)
        
        # Calculate Jaccard similarity
        union_size = len(set1 | set2)
        if union_size == 0:
            return 1.0  # Both empty
        
        return exact_matches / union_size
    
    @staticmethod
    def _compare_url_patterns(url1: str, url2: str) -> float:
        """Compare URL patterns.
        
        Args:
            url1: First URL pattern
            url2: Second URL pattern
            
        Returns:
            Similarity score 0.0-1.0
        """
        if not url1 and not url2:
            return 1.0
        if not url1 or not url2:
            return 0.0
        
        # Exact match
        if url1 == url2:
            return 1.0
        
        # Partial match (e.g., "admin/config" vs "admin/users" = 50%)
        parts1 = url1.split('/')
        parts2 = url2.split('/')
        
        # Match as many parts as possible
        matches = sum(1 for p1, p2 in zip(parts1, parts2) if p1 == p2)
        max_parts = max(len(parts1), len(parts2))
        
        return matches / max_parts if max_parts > 0 else 0.0
    
    @staticmethod
    def _compare_content(
        title1: str,
        title2: str,
        heading1: str,
        heading2: str
    ) -> float:
        """Compare content (title and main heading).
        
        Args:
            title1: First page title
            title2: Second page title
            heading1: First main heading
            heading2: Second main heading
            
        Returns:
            Similarity score 0.0-1.0
        """
        scores = []
        
        # Compare titles (70% of content score)
        if title1 or title2:
            title_score = 1.0 if title1 == title2 else 0.0
            scores.append((title_score, 0.70))
        
        # Compare headings (30% of content score)
        if heading1 or heading2:
            heading_score = 1.0 if heading1 == heading2 else 0.0
            scores.append((heading_score, 0.30))
        
        if not scores:
            return 1.0
        
        total_weight = sum(weight for _, weight in scores)
        weighted_sum = sum(score * weight for score, weight in scores)
        return weighted_sum / total_weight if total_weight > 0 else 1.0
    
    @staticmethod
    def find_matching_state(
        candidate_fingerprint: dict[str, Any],
        existing_states: list[UIState],
        threshold: float = 0.80
    ) -> tuple[UIState | None, float]:
        """Find the best matching state from existing states.
        
        Args:
            candidate_fingerprint: Fingerprint to match
            existing_states: List of existing UIState objects
            threshold: Minimum similarity score to consider a match
            
        Returns:
            Tuple of (matched_state, similarity_score) or (None, 0.0)
        """
        best_match = None
        best_score = 0.0
        
        for state in existing_states:
            score = StateComparer.calculate_similarity(
                candidate_fingerprint,
                state.fingerprint
            )
            
            if score >= threshold and score > best_score:
                best_match = state
                best_score = score
        
        if best_match:
            logger.info(
                "Found matching state: %s (similarity: %.2f%%)",
                best_match.state_id, best_score * 100
            )
        
        return best_match, best_score


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
        title = fingerprint.get("title", "").lower()
        
        # Extract from accessibility tree
        a11y_tree = fingerprint.get("accessibility_tree", {})
        landmarks = a11y_tree.get("landmark_roles", []) if a11y_tree else []
        
        # Extract from actionable elements
        actionable = fingerprint.get("actionable_elements", {})
        buttons = actionable.get("buttons", [])
        links = actionable.get("links", [])
        
        # Check for logout button as indicator of logged-in state
        has_logout = any(
            btn.get("name", "").lower() in ["log out", "logout", "sign out"]
            for btn in buttons
        ) or any(
            link.get("name", "").lower() in ["log out", "logout", "sign out"]
            for link in links
        )
        
        # Check for login button (indicates we're on login page, not logged in)
        has_login_button = any(
            btn.get("name", "").lower() in ["login", "log in", "sign in"]
            for btn in buttons
        )
        
        # Check for form role (login forms)
        has_form = "form" in landmarks
        
        # Check for data table
        has_table = any(btn.get("role") == "table" for btn in buttons)
        
        # Priority 1: Error states
        # Check for alert role or error indicators in URL/title
        has_actual_error = ("alert" in landmarks or 
                           "error" in url_pattern.lower() or 
                           "error" in title)
        if has_actual_error:
            # If it has form and login button, it's a login page (even with error banner)
            if has_form and has_login_button:
                # This is a login page, not an error page
                logger.debug("Login form detected with error banner, treating as login page")
                pass  # Fall through to login form handling
            elif "login" in url_pattern.lower() or "login" in title:
                return "error", "V_LOGIN_FORM_ERROR"
            else:
                state_id = f"V_ERROR_{StateClassifier._normalize_name(url_pattern)}"
                return "error", state_id
        
        # Priority 2: Modal states (dialog role)
        if "dialog" in [btn.get("role") for btn in buttons]:
            state_id = f"V_MODAL_{StateClassifier._normalize_name(url_pattern)}"
            return "modal", state_id
        
        # Priority 3: Loading states
        # Check for aria-busy or loading text
        is_loading = any(
            btn.get("aria_states", {}).get("disabled") and "load" in btn.get("name", "").lower()
            for btn in buttons
        )
        if is_loading or "loading" in url_pattern.lower():
            state_id = f"V_LOADING_{StateClassifier._normalize_name(url_pattern)}"
            return "loading", state_id
        
        # Priority 4: Logged-in states (check BEFORE login form)
        # If we have logout button and navigation landmark, we're logged in
        if has_logout and "navigation" in landmarks:
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
            elif "list" in url_pattern or has_table:
                 state_type = "list"
            else:
                state_type = "page"
                
            return state_type, state_id
        
        # Priority 5: Login form states (empty/ready)
        # Check if we're on a login page (has form and login button, no logout)
        if (has_form or "login" in url_pattern or "login" in title) and has_login_button:
            # Only classify as login form if we DON'T have logout button
            if not has_logout:
                return "form", "V_LOGIN_FORM_EMPTY"
        
        # Priority 6: Dashboard/main application states
        if "main" in landmarks and ("dashboard" in url_pattern or "dashboard" in title or "overview" in url_pattern):
            return "dashboard", "V_DASHBOARD_LOADED"
        
        if "navigation" in landmarks and has_table:
            # Likely a list/management page
            state_id = f"V_LIST_{StateClassifier._normalize_name(url_pattern)}"
            return "list", state_id
        
        # Priority 7: Success states (status role)
        if "status" in landmarks:
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



class UIMapLoader:
    """Loader for ui_map.json generated by the discovery tool."""
    
    @staticmethod
    def load_map(path: str) -> dict[str, Any]:
        """Load and parse ui_map.json.
        
        Args:
            path: Path to ui_map.json file
            
        Returns:
            Dictionary containing the map data
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            logger.info("Loaded UI map from %s: %d pages, %d elements", 
                       path, 
                       data.get("statistics", {}).get("page_count", 0),
                       data.get("statistics", {}).get("element_count", 0))
            return data
        except Exception as e:
            logger.error("Error loading UI map from %s: %s", path, e)
            return {}

    @staticmethod
    def extract_states(map_data: dict[str, Any]) -> list[UIState]:
        """Convert map pages into initial UIStates.
        
        Args:
            map_data: Loaded map data
            
        Returns:
            List of UIState objects
        """
        states = []
        graph = map_data.get("graph", {})
        nodes = graph.get("nodes", [])
        
        # Index elements by page URL for efficient lookup
        elements_by_page = {}
        nodes_by_id = {node.get("id"): node for node in nodes}
        
        # Build page -> elements map from edges
        edges = graph.get("edges", [])
        for edge in edges:
            if edge.get("edge_type") == "ON_PAGE":
                elem_id = edge.get("source")
                page_url = edge.get("target")
                
                elem_node = nodes_by_id.get(elem_id)
                if elem_node:
                    if page_url not in elements_by_page:
                        elements_by_page[page_url] = []
                    elements_by_page[page_url].append(elem_node)

        # Create states from pages
        for node in nodes:
            if node.get("node_type") == "Page":
                url = node.get("id")
                
                # Create rudimentary fingerprint from static data
                fingerprint = {
                    "url_pattern": StateFingerprinter._extract_url_pattern(url),
                    "title": node.get("title", ""),
                    "key_elements": []
                }
                
                # Add known elements to fingerprint/state
                if url in elements_by_page:
                    for elem in elements_by_page[url]:
                        # Convert map element to descriptor format
                        descriptor = {
                            "element_type": elem.get("element_type"),
                            "locators": {
                                "css": elem.get("locator_value"),
                                "text": elem.get("text") or "",
                                "test_id": elem.get("button_id") or elem.get("name") # Approximation
                            },
                            "metadata": {
                                "friendly_name": elem.get("friendly_name")
                            }
                        }
                        fingerprint["key_elements"].append(descriptor)
                
                # Classify
                state_type, state_id = StateClassifier.classify_state(fingerprint)
                
                state = UIState(
                    state_id=state_id,
                    state_type=state_type,
                    fingerprint=fingerprint,
                    verification_logic={"url_pattern": fingerprint["url_pattern"]}, # Basic verification
                    element_descriptors=fingerprint["key_elements"]
                )
                states.append(state)
                
        return states


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
        max_states: int = 100,
        safe_button_patterns: str = "New,Add,Edit,View,Show,Cancel,Close,Search,Filter,Create,Upload,Refresh,Submit,Save,Update,Confirm,OK,Yes",
        use_dfs: bool = True,
    ):
        """Initialize the state machine discovery tool.
        
        Args:
            base_url: Base URL of the application
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
            max_states: Maximum number of states to discover (safety limit, default: 100)
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
        
        # Track transition signatures to avoid duplicates
        self.transition_signatures: set[tuple[str, str, str]] = set()  # (from_state, action_type, to_state)
        
        # Store credentials for re-login if needed
        self.username: str | None = None
        self.password: str | None = None
        
        # Map-seeded data
        self.known_states: dict[str, UIState] = {}
        self.known_transitions: list[StateTransition] = []

    def seed_from_map(self, map_path: str):
        """Seed the FSM with states and transitions from ui_map.json.
        
        Args:
            map_path: Path to ui_map.json file
        """
        map_data = UIMapLoader.load_map(map_path)
        if not map_data:
            return
            
        seeded_states = UIMapLoader.extract_states(map_data)
        logger.info("Seeding FSM with %d states from map", len(seeded_states))
        
        for state in seeded_states:
            self.known_states[state.state_id] = state
            # Also add to active states, treating them as "discovered" but unverified
            # We add them to states dict so we know about them, but we might verify them later
            if state.state_id not in self.states:
                self.states[state.state_id] = state

        
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
        """Discover and classify the current UI state with fuzzy matching.
        
        Uses StateComparer to find matching states before creating new ones.
        This enables resilience to CSS changes, DOM restructuring, and minor
        UI updates by recognizing "same state" based on semantic similarity.
        
        Args:
            page: Playwright Page object
            
        Returns:
            UIState object (existing match or newly created)
        """
        # Wait for state to stabilize (e.g. loading spinners to disappear)
        await self._wait_for_stable_state(page)

        # Create fingerprint
        fingerprint = await StateFingerprinter.create_fingerprint(page)
        
        # PHASE 2: Try to find matching existing state (fuzzy matching)
        existing_states = list(self.states.values())
        matched_state, similarity = StateComparer.find_matching_state(
            fingerprint,
            existing_states,
            threshold=StateComparer.MATCH_THRESHOLD  # 80% threshold
        )
        
        if matched_state:
            # Found a match! Reuse existing state
            logger.info(
                "Matched existing state: %s (%.1f%% similar)",
                matched_state.state_id, similarity * 100
            )
            
            # Update element descriptors if new fingerprint has more/different elements
            # (UI might have changed slightly but still same state)
            actionable = fingerprint.get("actionable_elements", {})
            new_descriptors = (
                actionable.get("buttons", []) + 
                actionable.get("links", []) + 
                actionable.get("inputs", [])
            )
            
            # Merge descriptors (keep union of old + new)
            existing_names = {d.get('name') for d in matched_state.element_descriptors}
            for desc in new_descriptors:
                if desc.get('name') not in existing_names:
                    matched_state.element_descriptors.append(desc)
                    logger.debug(
                        "Added new element to matched state: %s",
                        desc.get('name')
                    )
            
            return matched_state
        
        # No match found - create new state
        state_type, state_id = StateClassifier.classify_state(fingerprint)
        
        # Create verification logic
        verification = self._create_verification_logic(fingerprint)
        
        # Extract actionable elements for state transitions
        actionable = fingerprint.get("actionable_elements", {})
        element_descriptors = (
            actionable.get("buttons", []) + 
            actionable.get("links", []) + 
            actionable.get("inputs", [])
        )
        
        state = UIState(
            state_id=state_id,
            state_type=state_type,
            fingerprint=fingerprint,
            verification_logic=verification,
            element_descriptors=element_descriptors
        )
        
        # Log discovery with a11y info
        a11y_tree = fingerprint.get("accessibility_tree", {})
        landmarks = a11y_tree.get("landmark_roles", []) if a11y_tree else []
        logger.info(
            "Created NEW state: %s (landmarks: %s, actions: %d)", 
            state_id, landmarks, actionable.get("total_count", 0)
        )
        
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
            fingerprint: State fingerprint (accessibility tree-based)
            
        Returns:
            Dictionary of verification checks
        """
        a11y_tree = fingerprint.get("accessibility_tree", {})
        
        return {
            "url_pattern": fingerprint.get("url_pattern", ""),
            "required_landmarks": a11y_tree.get("landmark_roles", []) if a11y_tree else [],
            "min_interactive_count": a11y_tree.get("interactive_count", 0) if a11y_tree else 0,
            "structure_hash": a11y_tree.get("structure_hash") if a11y_tree else None,
            "title": fingerprint.get("title", ""),
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
            
            # Skip ephemeral/non-explorable states (error, form, loading)
            if state.state_type in ["error", "form", "loading"]:
                logger.info("Skipping exploration of ephemeral %s state: %s",
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
                # Find all safe links, buttons, and forms
                forms = await self._identify_forms(page)
                safe_links = await self._find_safe_links(page)
                safe_buttons = await self._find_safe_buttons(page)
                
                logger.info("%sFound %d forms, %d links, %d buttons to explore",
                           indent, len(forms), len(safe_links[:10]), len(safe_buttons[:5]))

                # Explore forms depth-first (Priority)
                for form_info in forms:
                    try:
                        logger.debug("%sExecuting form fill", indent)
                        new_state_id = await self._execute_form_fill(page, state, form_info, navigate_back=False)
                        
                        if new_state_id and new_state_id != state_id:
                            # Recursively explore!
                            await explore_state_recursive(new_state_id, depth + 1)
                            
                            # Navigate back using browser back (preserves SPA state better than goto)
                            logger.debug("%sReturning to %s after form fill in %s",
                                       indent, state_id, new_state_id)
                            try:
                                await page.go_back()
                                await page.wait_for_load_state('networkidle', timeout=3000)
                                await asyncio.sleep(0.5)  # Extra wait for SPA to stabilize
                            except Exception as e:
                                logger.debug("%sError navigating back: %s, trying goto as fallback", indent, e)
                                # Fallback to goto if back fails
                                target_pattern = state.fingerprint.get("url_pattern", "")
                                if target_pattern and target_pattern != "root":
                                    await page.goto(f"{self.base_url}/#{target_pattern}")
                                    await page.wait_for_load_state('networkidle', timeout=3000)
                    
                    except Exception as e:
                        logger.debug("%sError with form: %s", indent, e)
                
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
                            
                            # After exploring the new state, navigate back using browser back
                            logger.debug("%sReturning to %s after exploring %s",
                                       indent, state_id, new_state_id)
                            try:
                                await page.go_back()
                                await page.wait_for_load_state('networkidle', timeout=3000)
                                await asyncio.sleep(0.5)  # Extra wait for SPA to stabilize
                            except Exception as e:
                                logger.debug("%sError navigating back: %s, trying goto as fallback", indent, e)
                                # Fallback to goto if back fails
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
                            
                            # Navigate back using browser back (preserves SPA state)
                            logger.debug("%sReturning to %s after exploring %s",
                                       indent, state_id, new_state_id)
                            try:
                                await page.go_back()
                                await page.wait_for_load_state('networkidle', timeout=3000)
                                await asyncio.sleep(0.5)  # Extra wait for SPA to stabilize
                            except Exception as e:
                                logger.debug("%sError navigating back: %s, trying goto as fallback", indent, e)
                                # Fallback to goto if back fails
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
            
            # Skip ephemeral/non-explorable states
            current_state = self.states.get(current_state_id)
            if current_state and current_state.state_type in ["error", "form", "loading"]:
                logger.info("Skipping exploration of ephemeral %s state: %s",
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
            
            # Skip exploring ephemeral/non-explorable states (they won't have useful navigation or can't be navigated to)
            current_state = self.states.get(current_state_id)
            if current_state and current_state.state_type in ["error", "form", "loading"]:
                logger.info("Skipping exploration of ephemeral %s state: %s", 
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
        
        # Strategy 1: Fill and submit forms (High Priority)
        forms = await self._identify_forms(page)
        logger.debug("Found %d forms to try", len(forms))
        
        for form_info in forms:
            try:
                # Execute form fill
                # For BFS, we always navigate back to source to continue discovery
                new_state_id = await self._execute_form_fill(page, state, form_info, navigate_back=True)
                if new_state_id and new_state_id != state.state_id:
                    new_states.append(new_state_id)
            except Exception as e:
                logger.debug("Error executing form fill: %s", e)

        # Strategy 2: Click safe navigation links (most common transition)
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
    
    async def _identify_forms(self, page: Page) -> list[dict[str, Any]]:
        """Identify forms that can be filled and submitted.
        
        This looks for logical groupings of inputs and submit buttons,
        supporting the Compound Action model.
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of form descriptors
        """
        forms = []
        try:
            # 1. Standard <form> elements
            form_elements = await page.locator("form:visible").all()
            
            for form in form_elements:
                try:
                    # Check if it has actionable elements
                    inputs = await form.locator("input:not([type='hidden']), select, textarea").all()
                    buttons = await form.locator("button, input[type='submit']").all()
                    
                    if not inputs and not buttons:
                        continue
                        
                    # Create descriptor
                    descriptor = {
                        "type": "standard_form",
                        "locator": await self._get_unique_selector(form),
                        "inputs": [await self._get_element_descriptor(i) for i in inputs],
                        "buttons": [await self._get_element_descriptor(b) for b in buttons if await b.is_visible()]
                    }
                    forms.append(descriptor)
                    
                except Exception as e:
                    logger.debug("Error processing form element: %s", e)
                    continue

            # 2. Implicit forms (e.g. login div) could be detected here if needed
            # For now, we rely on standard <form> tags or implicit containers if we defined them
            
        except Exception as e:
            logger.debug("Error identifying forms: %s", e)
            
        return forms

    async def _execute_form_fill(
        self,
        page: Page,
        from_state: UIState,
        form_info: dict[str, Any],
        navigate_back: bool = True
    ) -> str | None:
        """Execute a form fill compound action.
        
        Args:
            page: Playwright Page object
            from_state: State before action
            form_info: Form descriptor
            navigate_back: whether to return to source state
            
        Returns:
            New state ID or None
        """
        initial_url = page.url
        try:
            # Simple strategy: Fill text inputs with "test", check checkboxes
            inputs = form_info.get("inputs", [])
            submit_buttons = form_info.get("buttons", [])
            
            if not submit_buttons:
                logger.debug("No submit button found for form")
                return None
                
            # Use the first button as submit (heuristic)
            # In V2 we might want to try ALL buttons
            submit_btn_desc = submit_buttons[0]
            
            # Fill inputs
            filled_data = {}
            for inp in inputs:
                loc_dict = inp.get("locators", {})
                element_type = inp.get("element_type", "input")
                
                # Locate element
                try:
                    loc = await self._locate_element_from_descriptor(page, inp)
                    if not loc: continue
                    
                    if element_type == "input":
                        input_type = loc_dict.get("input_type", "text")
                        name = loc_dict.get("name", "unknown")
                        
                        if input_type in ["text", "email", "password", "search"]:
                            val = "test_value"
                            if input_type == "email": val = "test@example.com"
                            if input_type == "password": val = "password123"
                            
                            await loc.fill(val)
                            filled_data[name] = val
                            
                    elif element_type == "select":
                        # Try to select first option (TODO)
                        pass
                        
                except Exception as e:
                    logger.debug("Error filling input: %s", e)

            # Submit
            loc_btn = await self._locate_element_from_descriptor(page, submit_btn_desc)
            if loc_btn:
                await loc_btn.click()
                
                # Wait for potential navigation
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)
                except PlaywrightTimeoutError:
                    await asyncio.sleep(1.0)
                
                # Discover new state
                new_state = await self._discover_current_state(page)
                
                # If changed state, record transition
                if new_state.state_id != from_state.state_id:
                     if new_state.state_id not in self.states:
                        self.states[new_state.state_id] = new_state
                     
                     # Check if this transition already exists (avoid duplicates)
                     transition_sig = (from_state.state_id, "fill_form", new_state.state_id)
                     if transition_sig not in self.transition_signatures:
                         transition = StateTransition(
                            transition_id=f"T_{from_state.state_id}_TO_{new_state.state_id}_FORM",
                            from_state=from_state.state_id,
                            to_state=new_state.state_id,
                            action_type=ActionType.FILL_FORM,
                            trigger_locators=submit_btn_desc, # Attribution to the submit button
                            action_data=filled_data
                         )
                         self.transitions.append(transition)
                         self.transition_signatures.add(transition_sig)
                         logger.info("Form transition: %s -> %s", from_state.state_id, new_state.state_id)
                     else:
                         logger.debug("Form transition %s -> %s already recorded, skipping duplicate",
                                    from_state.state_id, new_state.state_id)
                     
                     # Navigate back
                     if navigate_back and page.url != initial_url:
                        try:
                            # Use browser back to preserve SPA state
                            await page.go_back()
                            await page.wait_for_load_state('networkidle', timeout=3000)
                            await asyncio.sleep(0.3)  # Brief wait for SPA to stabilize
                        except Exception as e:
                            logger.debug("Browser back failed: %s, using goto as fallback", e)
                            await page.goto(initial_url)
                            await page.wait_for_load_state('networkidle')
                     
                     return new_state.state_id

        except Exception as e:
            logger.debug("Error executing form fill: %s", e)
            if navigate_back and page.url != initial_url:
                await page.goto(initial_url)

        return None
    
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
                link_text = link_info.get("locators", {}).get("text", "unknown")
                logger.debug("Failed to locate link: %s (descriptor: %s)", link_text, link_info.get("locators"))
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
            
            # Check if this transition already exists (avoid duplicates)
            transition_sig = (from_state.state_id, "navigate", new_state.state_id)
            if transition_sig in self.transition_signatures:
                logger.debug("Transition %s -> %s already recorded, skipping duplicate", 
                           from_state.state_id, new_state.state_id)
            else:
                # Record transition
                transition = StateTransition(
                    transition_id=f"T_{from_state.state_id}_TO_{new_state.state_id}_NAV",
                    from_state=from_state.state_id,
                    to_state=new_state.state_id,
                    action_type="navigate",
                    trigger_locators=link_info,
                )
                self.transitions.append(transition)
                self.transition_signatures.add(transition_sig)
                
                logger.info("Navigation transition: %s -> %s (via '%s')", 
                           from_state.state_id, new_state.state_id, link_text)
            
            # Navigate back to source state so we can click other links
            # This is essential for discovering multiple transitions from one state
            if navigate_back and page.url != initial_url:
                logger.debug("Navigating back to %s to discover more transitions", from_state.state_id)
                try:
                    # Use browser back to preserve SPA state
                    await page.go_back()
                    await page.wait_for_load_state('networkidle', timeout=3000)
                    await asyncio.sleep(0.3)  # Brief wait for SPA to stabilize
                except Exception as e:
                    logger.debug("Browser back failed: %s, using goto as fallback", e)
                    await page.goto(initial_url)
                    await page.wait_for_load_state('networkidle')
            
            return new_state.state_id
            
        except Exception as e:
            link_text = link_info.get("locators", {}).get("text", "unknown")
            logger.debug("Error in link click execution for '%s': %s (type: %s)", 
                        link_text, str(e), type(e).__name__)
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
                button_text = button_info.get("locators", {}).get("text", "unknown")
                logger.debug("Failed to locate button: %s (descriptor: %s)", button_text, button_info.get("locators"))
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
            
            # Check if this transition already exists (avoid duplicates)
            transition_sig = (from_state.state_id, "click", new_state.state_id)
            if transition_sig in self.transition_signatures:
                logger.debug("Transition %s -> %s already recorded, skipping duplicate", 
                           from_state.state_id, new_state.state_id)
            else:
                # Record transition
                transition = StateTransition(
                    transition_id=f"T_{from_state.state_id}_TO_{new_state.state_id}_CLICK",
                    from_state=from_state.state_id,
                    to_state=new_state.state_id,
                    action_type="click",
                    trigger_locators=button_info,
                )
                self.transitions.append(transition)
                self.transition_signatures.add(transition_sig)
                
                logger.info("Button transition: %s -> %s", from_state.state_id, new_state.state_id)
            
            # Navigate back to source state
            if navigate_back and page.url != initial_url:
                logger.debug("Navigating back to %s to discover more transitions", from_state.state_id)
                try:
                    # Use browser back to preserve SPA state
                    await page.go_back()
                    await page.wait_for_load_state('networkidle', timeout=3000)
                    await asyncio.sleep(0.3)  # Brief wait for SPA to stabilize
                except Exception as e:
                    logger.debug("Browser back failed: %s, using goto as fallback", e)
                    await page.goto(initial_url)
                    await page.wait_for_load_state('networkidle')
            
            return new_state.state_id
            
        except Exception as e:
            button_text = button_info.get("locators", {}).get("text", "unknown")
            logger.debug("Error in button click execution for '%s': %s (type: %s)", 
                        button_text, str(e), type(e).__name__)
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
        default=100,
        help="Maximum number of states to discover (default: 100)",
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
    parser.add_argument(
        "--seed-map",
        help="Path to ui_map.json to seed the FSM with known states",
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
    
    # Seed from map if provided
    if args.seed_map:
        tool.seed_from_map(args.seed_map)


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

