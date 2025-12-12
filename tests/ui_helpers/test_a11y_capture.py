#!/usr/bin/env python3
"""Test script to verify accessibility tree capture works correctly.

This script tests Phase 1 implementation of the Accessibility Tree Strategy.
"""

import asyncio
import json
import sys
from playwright.async_api import async_playwright

# Add parent directory to path for imports
sys.path.insert(0, '/home/rjvisser/projects/req-tst/boardfarm-bdd')

from tests.ui_helpers.ui_mbt_discovery import StateFingerprinter


async def test_a11y_capture():
    """Test accessibility tree capture on GenieACS login and dashboard."""
    
    print("=" * 70)
    print("Testing Accessibility Tree State Fingerprinting")
    print("=" * 70)
    
    async with async_playwright() as p:
        # Launch browser
        print("\n1. Launching Firefox browser...")
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Test 1: Login page
            print("\n2. Navigating to login page...")
            await page.goto('http://127.0.0.1:3000')
            await page.wait_for_load_state('networkidle')
            
            print("\n3. Capturing login page fingerprint...")
            fingerprint_login = await StateFingerprinter.create_fingerprint(page)
            
            print("\n   Login Page Fingerprint:")
            print(f"   - URL Pattern: {fingerprint_login.get('url_pattern')}")
            print(f"   - Title: {fingerprint_login.get('title')}")
            
            a11y_tree = fingerprint_login.get('accessibility_tree', {})
            if a11y_tree:
                print(f"   - Landmark Roles: {a11y_tree.get('landmark_roles')}")
                print(f"   - Interactive Count: {a11y_tree.get('interactive_count')}")
                print(f"   - Headings: {a11y_tree.get('heading_hierarchy')}")
                
                aria_states = a11y_tree.get('aria_states', {})
                print(f"   - Expanded Elements: {len(aria_states.get('expanded_elements', []))}")
                print(f"   - Selected Elements: {len(aria_states.get('selected_elements', []))}")
            
            actionable = fingerprint_login.get('actionable_elements', {})
            print(f"   - Buttons: {len(actionable.get('buttons', []))}")
            print(f"   - Links: {len(actionable.get('links', []))}")
            print(f"   - Inputs: {len(actionable.get('inputs', []))}")
            print(f"   - Total Actions: {actionable.get('total_count', 0)}")
            
            # Test 2: Dashboard page
            print("\n4. Logging in...")
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin')
            await page.click('button:has-text("Login")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)  # Wait for SPA to stabilize
            
            print("\n5. Capturing dashboard fingerprint...")
            fingerprint_dashboard = await StateFingerprinter.create_fingerprint(page)
            
            print("\n   Dashboard Fingerprint:")
            print(f"   - URL Pattern: {fingerprint_dashboard.get('url_pattern')}")
            print(f"   - Title: {fingerprint_dashboard.get('title')}")
            
            a11y_tree_dash = fingerprint_dashboard.get('accessibility_tree', {})
            if a11y_tree_dash:
                print(f"   - Landmark Roles: {a11y_tree_dash.get('landmark_roles')}")
                print(f"   - Interactive Count: {a11y_tree_dash.get('interactive_count')}")
                print(f"   - Headings: {a11y_tree_dash.get('heading_hierarchy')}")
                
                key_landmarks = a11y_tree_dash.get('key_landmarks', {})
                print(f"   - Key Landmarks: {list(key_landmarks.keys())}")
                
                aria_states_dash = a11y_tree_dash.get('aria_states', {})
                print(f"   - Expanded Elements: {len(aria_states_dash.get('expanded_elements', []))}")
                if aria_states_dash.get('expanded_elements'):
                    print("     Expanded elements:")
                    for elem in aria_states_dash.get('expanded_elements', [])[:3]:
                        print(f"       - {elem.get('role')}: {elem.get('name')} (expanded={elem.get('expanded')})")
            
            actionable_dash = fingerprint_dashboard.get('actionable_elements', {})
            print(f"   - Buttons: {len(actionable_dash.get('buttons', []))}")
            print(f"   - Links: {len(actionable_dash.get('links', []))}")
            print(f"   - Inputs: {len(actionable_dash.get('inputs', []))}")
            print(f"   - Total Actions: {actionable_dash.get('total_count', 0)}")
            
            # Show sample links
            links = actionable_dash.get('links', [])
            if links:
                print("\n   Sample Links (first 5):")
                for link in links[:5]:
                    print(f"     - {link.get('name')} (href: {link.get('href')})")
            
            # Test 3: Navigate to admin page
            print("\n6. Navigating to Admin page...")
            await page.click('a:has-text("Admin")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(0.5)
            
            print("\n7. Capturing admin page fingerprint...")
            fingerprint_admin = await StateFingerprinter.create_fingerprint(page)
            
            print("\n   Admin Page Fingerprint:")
            print(f"   - URL Pattern: {fingerprint_admin.get('url_pattern')}")
            
            a11y_tree_admin = fingerprint_admin.get('accessibility_tree', {})
            if a11y_tree_admin:
                aria_states_admin = a11y_tree_admin.get('aria_states', {})
                expanded_elements = aria_states_admin.get('expanded_elements', [])
                print(f"   - Expanded Elements: {len(expanded_elements)}")
                if expanded_elements:
                    print("     Expanded elements (showing admin menu state):")
                    for elem in expanded_elements:
                        if 'admin' in elem.get('name', '').lower():
                            print(f"       - {elem.get('role')}: {elem.get('name')} (expanded={elem.get('expanded')})")
            
            actionable_admin = fingerprint_admin.get('actionable_elements', {})
            print(f"   - Total Actions: {actionable_admin.get('total_count', 0)}")
            
            # Save full fingerprints for inspection
            print("\n8. Saving full fingerprints to JSON files...")
            with open('fingerprint_login.json', 'w') as f:
                json.dump(fingerprint_login, f, indent=2)
            print("   - Saved: fingerprint_login.json")
            
            with open('fingerprint_dashboard.json', 'w') as f:
                json.dump(fingerprint_dashboard, f, indent=2)
            print("   - Saved: fingerprint_dashboard.json")
            
            with open('fingerprint_admin.json', 'w') as f:
                json.dump(fingerprint_admin, f, indent=2)
            print("   - Saved: fingerprint_admin.json")
            
            # Validation
            print("\n" + "=" * 70)
            print("VALIDATION RESULTS")
            print("=" * 70)
            
            success = True
            
            # Check 1: All fingerprints have accessibility_tree
            if fingerprint_login.get('accessibility_tree') and \
               fingerprint_dashboard.get('accessibility_tree') and \
               fingerprint_admin.get('accessibility_tree'):
                print("✅ All states have accessibility_tree property")
            else:
                print("❌ Some states missing accessibility_tree")
                success = False
            
            # Check 2: All have actionable_elements
            if fingerprint_login.get('actionable_elements') and \
               fingerprint_dashboard.get('actionable_elements') and \
               fingerprint_admin.get('actionable_elements'):
                print("✅ All states have actionable_elements property")
            else:
                print("❌ Some states missing actionable_elements")
                success = False
            
            # Check 3: Dashboard has more actions than login
            if actionable_dash.get('total_count', 0) > actionable.get('total_count', 0):
                print(f"✅ Dashboard has more actions than login ({actionable_dash.get('total_count')} > {actionable.get('total_count')})")
            else:
                print("❌ Dashboard should have more actions than login")
                success = False
            
            # Check 4: Admin page has ARIA states (expanded menu)
            if a11y_tree_admin and aria_states_admin.get('expanded_elements'):
                print(f"✅ Admin page captures ARIA expanded states ({len(aria_states_admin.get('expanded_elements'))} elements)")
            else:
                print("⚠️  Admin page has no expanded elements (may be OK if menu not expanded)")
            
            # Check 5: No NULL properties
            null_count = 0
            for name, fp in [("login", fingerprint_login), ("dashboard", fingerprint_dashboard), ("admin", fingerprint_admin)]:
                a11y = fp.get('accessibility_tree', {})
                if a11y:
                    if a11y.get('landmark_roles') is None:
                        print(f"❌ {name}: landmark_roles is NULL")
                        null_count += 1
                    if a11y.get('aria_states') is None:
                        print(f"❌ {name}: aria_states is NULL")
                        null_count += 1
            
            if null_count == 0:
                print("✅ No NULL properties in accessibility trees")
            else:
                print(f"❌ Found {null_count} NULL properties")
                success = False
            
            print("\n" + "=" * 70)
            if success:
                print("🎉 PHASE 1 IMPLEMENTATION: SUCCESS!")
                print("   All accessibility tree features working correctly.")
            else:
                print("⚠️  PHASE 1 IMPLEMENTATION: NEEDS ATTENTION")
                print("   Some features need adjustment.")
            print("=" * 70)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_a11y_capture())

