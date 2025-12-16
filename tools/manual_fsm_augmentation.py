#!/usr/bin/env python3
"""
Manual FSM Graph Augmentation Tool

Interactive tool for recording UI workflows through manual user actions.
The user performs actions in the browser, and the tool captures states on command.

Features:
- Workflow-agnostic: Record ANY workflow you manually perform
- Interactive: Press Enter to capture current state
- Optional input graph: Start from scratch or augment existing
- ARIA-based state capture with element extraction

Usage:
    # Start fresh (no input graph)
    python manual_fsm_augmentation.py --output fsm_graph.json
    
    # Augment existing graph
    python manual_fsm_augmentation.py --input fsm_graph.json --output fsm_graph_augmented.json
    
    # With custom URL
    python manual_fsm_augmentation.py --url http://localhost:3000 --output fsm_graph.json
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import argparse

from playwright.async_api import async_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ManualFSMAugmenter:
    """Interactive tool for recording UI workflows through manual actions."""
    
    def __init__(
        self,
        base_url: str,
        headless: bool = False,
    ):
        self.base_url = base_url
        self.headless = headless
        self.browser: Browser | None = None
        self.page: Page | None = None
        
        self.discovered_states: List[Dict[str, Any]] = []
        self.discovered_transitions: List[Dict[str, Any]] = []
        self.state_counter = 1
        self.transition_counter = 1
        self.last_state_id: Optional[str] = None
        
    async def start_browser(self):
        """Start Playwright browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.firefox.launch(headless=self.headless)
        context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await context.new_page()
        
        # Navigate to base URL
        await self.page.goto(self.base_url)
        
        logger.info("Browser started and navigated to %s", self.base_url)
        logger.info("You can now manually interact with the page")
        
    async def stop_browser(self):
        """Stop browser."""
        if self.browser:
            await self.browser.close()
            # Small delay to allow Playwright subprocess cleanup
            await asyncio.sleep(0.1)
            logger.info("Browser closed")
    
    async def get_user_command(self) -> str:
        """
        Get user command asynchronously without blocking the event loop.
        Returns: user input string
        """
        loop = asyncio.get_event_loop()
        try:
            user_input = await loop.run_in_executor(
                None,  # Use default executor
                input,
                "Command (s=snapshot, q=quit): "
            )
            return user_input.strip().lower()
        except (EOFError, KeyboardInterrupt):
            return 'q'
    
    async def capture_state_snapshot(self, state_id: Optional[str] = None, state_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture current page state with ARIA snapshot.
        
        Args:
            state_id: Unique identifier (auto-generated if None)
            state_type: Type classification (auto-detected if None)
            
        Returns:
            State node dictionary
        """
        # Auto-generate state ID if not provided
        if state_id is None:
            state_id = f"V_STATE_{self.state_counter:03d}"
            self.state_counter += 1
        
        logger.info("Capturing state: %s", state_id)
        
        # Get ARIA snapshot
        aria_snapshot = await self.page.locator('body').aria_snapshot()
        
        # Get page metadata
        url = self.page.url
        title = await self.page.title()
        
        # Extract actionable elements
        buttons = []
        button_locators = await self.page.locator('button').all()
        for button in button_locators:
            try:
                if await button.is_visible():
                    text = await button.inner_text()
                    if text.strip():
                        buttons.append({
                            "role": "button",
                            "name": text.strip(),
                            "locator_strategy": f"getByRole('button', {{ name: '{text.strip()}' }})"
                        })
            except Exception:
                # Skip buttons that cause issues
                pass
        
        links = []
        link_locators = await self.page.locator('a[href]').all()
        for link in link_locators:
            try:
                if await link.is_visible():
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    if text.strip():
                        links.append({
                            "role": "link",
                            "name": text.strip(),
                            "href": href,
                            "locator_strategy": f"getByRole('link', {{ name: '{text.strip()}' }})"
                        })
            except Exception:
                # Skip links that cause issues
                pass
        
        inputs = []
        input_locators = await self.page.locator('input, textarea, select').all()
        for input_el in input_locators:
            try:
                if await input_el.is_visible():
                    input_type = await input_el.get_attribute('type') or 'text'
                    placeholder = await input_el.get_attribute('placeholder') or ''
                    name = await input_el.get_attribute('name') or ''
                    inputs.append({
                        "role": "textbox" if input_type in ('text', 'email', 'password') else input_type,
                        "name": placeholder or name,
                        "locator_strategy": f"getByRole('textbox')" if not name else f"getByRole('textbox', {{ name: '{name}' }})"
                    })
            except Exception:
                # Skip inputs that cause issues
                pass
        
        # Auto-detect state type if not provided
        if state_type is None:
            if len(inputs) > 2:
                state_type = "form"
            elif "overlay" in aria_snapshot.lower() or "modal" in aria_snapshot.lower():
                state_type = "overlay"
            elif "device" in url.lower() and "/" in url.split("#")[-1]:
                state_type = "detail"
            elif len(buttons) + len(links) > 10:
                state_type = "list"
            else:
                state_type = "interactive"
        
        # Create state node
        state_node = {
            "id": state_id,
            "node_type": "state",
            "state_type": state_type,
            "discovered_manually": True,
            "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
            "fingerprint": {
                "url": url,
                "title": title,
                "aria_snapshot": aria_snapshot,
                "actionable_elements": {
                    "buttons": buttons,
                    "links": links,
                    "inputs": inputs,
                    "total_count": len(buttons) + len(links) + len(inputs)
                }
            },
            "verification_logic": {
                "url_pattern": url.split('?')[0].split('#')[-1] if '#' in url else url.split('?')[0],
                "title_contains": title,
            }
        }
        
        logger.info("  - Type: %s", state_type)
        logger.info("  - URL: %s", url)
        logger.info("  - Elements: %d buttons, %d links, %d inputs",
                   len(buttons), len(links), len(inputs))
        
        return state_node
    
    async def prompt_for_action_details(self) -> Dict[str, Any]:
        """
        Prompt user for details about the action they just performed.
        
        Returns:
            Dictionary with action metadata
        """
        print("\n" + "="*70)
        print("⚠️  DESCRIBE THE ACTION YOU JUST PERFORMED")
        print("="*70)
        print("What did you do in the BROWSER to reach this state?")
        print()
        print("Examples:")
        print("  • clicked the Devices link")
        print("  • filled search field and pressed Enter")
        print("  • pressed the Reboot button")
        print("  • waited for popup to disappear")
        print()
        print("(Press Enter alone to skip and use generic description)")
        print("-"*70)
        
        # Use asyncio executor to get user description without blocking
        loop = asyncio.get_event_loop()
        try:
            description = await loop.run_in_executor(
                None,
                input,
                "Your action → "
            )
            description = description.strip()
        except (EOFError, KeyboardInterrupt):
            description = ""
        
        action_data = {
            "action_type": "custom",
            "description": description if description else "User performed manual action",
            "trigger_locators": {},
            "action_data": {}
        }
        
        # Try to infer action type from description
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['click', 'clicked', 'press', 'pressed']):
            if 'button' in desc_lower:
                action_data["action_type"] = "click_button"
            elif 'link' in desc_lower:
                action_data["action_type"] = "click_link"
            else:
                action_data["action_type"] = "click"
        elif any(word in desc_lower for word in ['fill', 'filled', 'enter', 'entered', 'type', 'typed']):
            action_data["action_type"] = "fill_and_submit"
        elif any(word in desc_lower for word in ['select', 'selected', 'choose', 'chose']):
            action_data["action_type"] = "select"
        elif any(word in desc_lower for word in ['wait', 'waited']):
            action_data["action_type"] = "wait"
        elif any(word in desc_lower for word in ['navigate', 'navigated', 'go to', 'went to']):
            action_data["action_type"] = "navigate"
        
        print("="*70)
        return action_data
    
    async def create_transition(self, from_state_id: str, to_state_id: str, action_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a transition between two states.
        
        Args:
            from_state_id: Source state ID
            to_state_id: Target state ID
            action_metadata: Metadata about the action (from prompt_for_action_details)
            
        Returns:
            Transition edge dictionary
        """
        transition_id = f"T_{from_state_id}_TO_{to_state_id}"
        if len(transition_id) > 50:
            # Use counter-based ID if too long
            transition_id = f"T_TRANSITION_{self.transition_counter:03d}"
            self.transition_counter += 1
        
        transition = {
            "id": transition_id,
            "edge_type": "transition",
            "source": from_state_id,
            "target": to_state_id,
            "action_type": action_metadata.get("action_type", "manual"),
            "description": action_metadata.get("description", f"Transition from {from_state_id} to {to_state_id}"),
            "trigger_locators": action_metadata.get("trigger_locators", {}),
            "action_data": action_metadata.get("action_data", {}),
            "discovered_manually": True,
            "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return transition
    
    async def interactive_recording_loop(self):
        """Main interactive loop for recording workflows."""
        # Print instructions
        print("\n" + "="*70)
        print("INTERACTIVE RECORDING MODE")
        print("="*70)
        print("The browser is open. You can interact with it normally.")
        print("Commands (type in this TERMINAL, not the browser):")
        print()
        print("  's' + [Enter]     - Capture/Snapshot current browser state")
        print("  'q' + [Enter]     - Quit recording and save")
        print("="*70)
        print()
        print("TIP: Use Enter freely in the browser (forms, etc.).")
        print("     Only type 's' in THIS terminal to capture states.")
        print("="*70)
        print()
        
        logger.info("\nBrowser is ready. Perform your workflow manually.")
        logger.info("Type 's' in the TERMINAL after each significant state change.")
        logger.info("Type 'q' in the TERMINAL when done.\n")
        
        try:
            while True:
                # Get user command
                command = await self.get_user_command()
                
                if command in ('q', 'quit', 'exit'):
                    logger.info("User requested exit")
                    break
                    
                elif command in ('s', 'snap', 'snapshot', 'capture', 'c'):
                    # Capture state
                    print("\nCapturing current state...")
                    
                    # Auto-generate state ID
                    state_id = None
                    
                    # Capture state
                    state = await self.capture_state_snapshot(state_id)
                    self.discovered_states.append(state)
                    
                    logger.info("State captured: %s", state['id'])
                    logger.info("Total states captured: %d", len(self.discovered_states))
                    
                    # Create transition if there was a previous state
                    if self.last_state_id is not None:
                        # Prompt for action details
                        action_metadata = await self.prompt_for_action_details()
                        
                        transition = await self.create_transition(
                            self.last_state_id,
                            state['id'],
                            action_metadata
                        )
                        self.discovered_transitions.append(transition)
                        logger.info("Transition created: %s → %s",
                                   self.last_state_id, state['id'])
                        logger.info("  Action: %s", action_metadata.get('description', 'N/A'))
                    
                    # Update last state
                    self.last_state_id = state['id']
                    
                    print("\nReady. Perform next action in browser, then type 's' here.\n")
                    
                elif command == '':
                    # Empty input - show help
                    print("  → Type 's' to capture state, 'q' to quit")
                    
                else:
                    print(f"  → Unknown command: '{command}'. Use 's' or 'q'")
                
        except KeyboardInterrupt:
            logger.info("\nRecording interrupted by user")
        
        logger.info("\nRecording complete!")
        logger.info("Captured %d states and %d transitions",
                   len(self.discovered_states),
                   len(self.discovered_transitions))
    
    async def record_interactive_workflow(self):
        """Start interactive recording session."""
        await self.start_browser()
        
        try:
            await self.interactive_recording_loop()
        finally:
            await self.stop_browser()
    
    def compute_state_fingerprint(self, state: Dict[str, Any]) -> str:
        """
        Compute a fingerprint hash for a state based on structural properties.
        
        Uses: URL pattern, state type, element roles/names (ignoring data values)
        
        Args:
            state: State node dictionary
            
        Returns:
            Fingerprint string for duplicate detection
        """
        import hashlib
        
        fingerprint = state.get('fingerprint', {})
        
        # Extract URL pattern (strip query params with dynamic data)
        url = fingerprint.get('url', '')
        if '?' in url:
            url_base = url.split('?')[0]
        else:
            url_base = url
        # Remove hash fragment base
        if '#!' in url_base:
            url_base = url_base.split('#!')[-1]
        
        # Get element structure (roles and names, not counts which can vary with data)
        elements = fingerprint.get('actionable_elements', {})
        
        # Create structural signature
        button_signatures = []
        for btn in elements.get('buttons', []):
            # Skip dynamic data like "Log out" vs specific names
            button_signatures.append(btn.get('role', ''))
        
        link_signatures = []
        for link in elements.get('links', []):
            role = link.get('role', '')
            name = link.get('name', '')
            # Skip numeric/data values in names
            if not name or name.isdigit() or '%' in name:
                link_signatures.append(f"{role}")
            else:
                link_signatures.append(f"{role}:{name}")
        
        input_signatures = []
        for inp in elements.get('inputs', []):
            input_signatures.append(inp.get('role', ''))
        
        # Combine into fingerprint
        fp_data = {
            'url_base': url_base,
            'state_type': state.get('state_type', ''),
            'button_count': len(button_signatures),
            'link_structure': sorted([ls for ls in link_signatures if not ls.endswith(':')]),  # Non-data links
            'input_count': len(input_signatures),
        }
        
        # Create hash
        fp_str = json.dumps(fp_data, sort_keys=True)
        return hashlib.md5(fp_str.encode()).hexdigest()
    
    def merge_with_existing_graph(
        self,
        existing_graph_path: Path,
        output_path: Path
    ):
        """
        Merge discovered states/transitions with existing FSM graph.
        Uses fingerprint-based duplicate detection.
        
        Args:
            existing_graph_path: Path to existing fsm_graph.json
            output_path: Path to save augmented graph
        """
        logger.info("\n" + "="*60)
        logger.info("MERGING WITH EXISTING GRAPH")
        logger.info("="*60)
        
        # Load existing graph
        with existing_graph_path.open('r') as f:
            graph = json.load(f)
        
        logger.info("Existing graph: %d states, %d transitions",
                   len(graph.get('nodes', [])),
                   len(graph.get('edges', [])))
        
        # Build fingerprint map for existing states
        existing_fingerprints = {}  # fingerprint -> state_id
        for node in graph.get('nodes', []):
            fp = self.compute_state_fingerprint(node)
            existing_fingerprints[fp] = node['id']
        
        logger.info("Computed %d fingerprints from existing states", len(existing_fingerprints))
        
        # Map manually recorded state IDs to existing IDs if they match
        state_id_mapping = {}  # manual_id -> existing_id or manual_id
        new_nodes = []
        duplicate_count = 0
        
        for manual_state in self.discovered_states:
            manual_fp = self.compute_state_fingerprint(manual_state)
            manual_id = manual_state['id']
            
            if manual_fp in existing_fingerprints:
                # Duplicate! Use existing state ID
                existing_id = existing_fingerprints[manual_fp]
                state_id_mapping[manual_id] = existing_id
                duplicate_count += 1
                logger.info("  Duplicate detected: %s matches existing %s", manual_id, existing_id)
            else:
                # Genuinely new state
                state_id_mapping[manual_id] = manual_id
                new_nodes.append(manual_state)
                # Add to fingerprints to detect duplicates within manual recording
                existing_fingerprints[manual_fp] = manual_id
        
        graph['nodes'].extend(new_nodes)
        logger.info("Added %d new states", len(new_nodes))
        logger.info("Skipped %d duplicate states", duplicate_count)
        
        # Remap transitions to use existing state IDs where duplicates were found
        # Also collect existing edge IDs
        existing_edge_ids = set()
        for edge in graph.get('edges', []):
            edge_id = edge.get('id') or edge.get('transition_id')
            if edge_id:
                existing_edge_ids.add(edge_id)
        
        # Build set of existing transitions (source -> target pairs)
        existing_transitions = set()
        for edge in graph.get('edges', []):
            source = edge.get('source')
            target = edge.get('target')
            if source and target:
                existing_transitions.add((source, target))
        
        new_edges = []
        remapped_count = 0
        duplicate_edge_count = 0
        
        for edge in self.discovered_transitions:
            # Remap source and target IDs
            original_source = edge['source']
            original_target = edge['target']
            
            remapped_source = state_id_mapping.get(original_source, original_source)
            remapped_target = state_id_mapping.get(original_target, original_target)
            
            # Check if this transition already exists
            if (remapped_source, remapped_target) in existing_transitions:
                duplicate_edge_count += 1
                logger.info("  Duplicate transition: %s → %s already exists", remapped_source, remapped_target)
                continue
            
            # Update edge with remapped IDs
            edge['source'] = remapped_source
            edge['target'] = remapped_target
            
            # Update edge ID if needed
            if original_source != remapped_source or original_target != remapped_target:
                edge['id'] = f"T_{remapped_source}_TO_{remapped_target}"
                remapped_count += 1
            
            # Check if this specific edge ID already exists
            if edge['id'] in existing_edge_ids:
                # Generate unique ID
                counter = 1
                while f"{edge['id']}_{counter}" in existing_edge_ids:
                    counter += 1
                edge['id'] = f"{edge['id']}_{counter}"
            
            new_edges.append(edge)
            existing_transitions.add((remapped_source, remapped_target))
            existing_edge_ids.add(edge['id'])
        
        graph['edges'].extend(new_edges)
        logger.info("Added %d new transitions", len(new_edges))
        logger.info("Remapped %d transitions to existing states", remapped_count)
        logger.info("Skipped %d duplicate transitions", duplicate_edge_count)
        
        # Update statistics
        if 'statistics' not in graph:
            graph['statistics'] = {}
        
        graph['statistics'].update({
            'state_count': len(graph['nodes']),
            'transition_count': len(graph['edges']),
            'manually_augmented': True,
            'augmentation_timestamp': datetime.now(timezone.utc).isoformat(),
            'new_states_added': len(new_nodes),
            'new_transitions_added': len(new_edges),
            'duplicate_states_skipped': duplicate_count,
            'duplicate_transitions_skipped': duplicate_edge_count,
            'states_captured_manually': len(self.discovered_states),
            'transitions_captured_manually': len(self.discovered_transitions)
        })
        
        # Save augmented graph
        with output_path.open('w') as f:
            json.dump(graph, f, indent=2)
        
        logger.info("Augmented graph saved to: %s", output_path)
        logger.info("Total: %d states, %d transitions",
                   len(graph['nodes']),
                   len(graph['edges']))
        
        # Print summary
        logger.info("\n" + "-"*60)
        logger.info("DEDUPLICATION SUMMARY")
        logger.info("-"*60)
        logger.info("Manually captured: %d states, %d transitions",
                   len(self.discovered_states), len(self.discovered_transitions))
        logger.info("Duplicates found: %d states, %d transitions",
                   duplicate_count, duplicate_edge_count)
        logger.info("Actually added: %d states, %d transitions",
                   len(new_nodes), len(new_edges))
        
        if new_nodes:
            logger.info("\nNew states added:")
            for node in new_nodes:
                logger.info("  - %s (%s) - %s",
                           node['id'],
                           node['state_type'],
                           node['fingerprint'].get('url', '')[:60])
        
        if new_edges:
            logger.info("\nNew transitions added:")
            for edge in new_edges:
                logger.info("  - %s: %s → %s",
                           edge['id'], edge['source'], edge['target'])


async def main():
    parser = argparse.ArgumentParser(
        description="Manual FSM Graph Augmentation Tool - Interactive Workflow Recorder",
        epilog="""
Examples:
  # Start fresh recording
  python manual_fsm_augmentation.py --output fsm_graph.json
  
  # Augment existing graph
  python manual_fsm_augmentation.py --input fsm_graph.json --output fsm_graph_augmented.json
  
  # Custom URL
  python manual_fsm_augmentation.py --url http://localhost:3000 --output fsm_graph.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--url",
        default="http://localhost:3000",
        help="Base URL to start browser at (default: http://localhost:3000)"
    )
    parser.add_argument(
        "--input",
        help="Path to existing fsm_graph.json (optional - can start from scratch)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save the recorded/augmented fsm_graph.json"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (not recommended for manual recording)"
    )
    
    args = parser.parse_args()
    
    # Warn if headless mode is used
    if args.headless:
        logger.warning("Headless mode is not recommended for interactive recording!")
        logger.warning("You won't see the browser. Consider removing --headless flag.")
    
    # Create augmenter
    augmenter = ManualFSMAugmenter(
        base_url=args.url,
        headless=args.headless,
    )
    
    # Record workflows interactively
    await augmenter.record_interactive_workflow()
    
    # Check if we captured anything
    if not augmenter.discovered_states:
        logger.warning("No states captured. Exiting without saving.")
        return
    
    # Merge with existing graph if provided
    if args.input:
        augmenter.merge_with_existing_graph(
            existing_graph_path=Path(args.input),
            output_path=Path(args.output)
        )
    else:
        # Create new graph from scratch
        logger.info("\nCreating new FSM graph from scratch")
        graph = {
            "base_url": args.url,
            "graph_type": "fsm_mbt",
            "discovery_method": "manual_interactive_recording",
            "nodes": augmenter.discovered_states,
            "edges": augmenter.discovered_transitions,
            "statistics": {
                "state_count": len(augmenter.discovered_states),
                "transition_count": len(augmenter.discovered_transitions),
                "manually_recorded": True,
                "recording_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
        
        output_path = Path(args.output)
        with output_path.open('w') as f:
            json.dump(graph, f, indent=2)
        
        logger.info("New FSM graph saved to: %s", output_path)
    
    logger.info("\n" + "="*70)
    logger.info("RECORDING COMPLETE!")
    logger.info("="*70)
    logger.info("Captured:")
    logger.info("  - %d states", len(augmenter.discovered_states))
    logger.info("  - %d transitions", len(augmenter.discovered_transitions))
    logger.info("\nSaved to: %s", args.output)
    logger.info("\nNext steps:")
    logger.info("1. Review the graph: cat %s | jq '.statistics'", args.output)
    logger.info("2. Update GenieAcsGUI.STATE_REGISTRY with new state IDs")
    logger.info("3. Refactor test steps to use FSM transitions")
    logger.info("="*70)


if __name__ == "__main__":
    # Suppress harmless Playwright subprocess cleanup exceptions that occur on exit
    # This is a known issue where Playwright's subprocess cleanup tries to use 
    # the event loop after it's been closed by asyncio.run()
    import io
    
    asyncio.run(main())
    
    # Temporarily redirect stderr to suppress cleanup exception messages
    old_stderr = sys.stderr
    try:
        sys.stderr = io.StringIO()
        # Brief sleep to allow Python's cleanup to complete
        import time
        time.sleep(0.1)
    finally:
        sys.stderr = old_stderr

