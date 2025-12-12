#!/usr/bin/env python3
"""Test script to validate Phase 2: State Matching with fuzzy comparison.

This validates that StateComparer can correctly identify same states
even after UI changes (CSS, DOM restructure, minor text changes).
"""

import asyncio
import json
import sys
from playwright.async_api import async_playwright

# Add parent directory to path for imports
sys.path.insert(0, '/home/rjvisser/projects/req-tst/boardfarm-bdd')

from tests.ui_helpers.ui_mbt_discovery import (
    StateFingerprinter,
    StateComparer,
    UIState
)


async def test_state_matching():
    """Test state matching on the same page captured twice."""
    
    print("=" * 70)
    print("Testing Phase 2: State Matching with Weighted Similarity")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Login first
            print("\n1. Logging in to GenieACS...")
            await page.goto('http://127.0.0.1:3000')
            await page.wait_for_load_state('networkidle')
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin')
            await page.click('button:has-text("Login")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            # Capture dashboard fingerprint #1
            print("\n2. Capturing dashboard fingerprint (first capture)...")
            fp1 = await StateFingerprinter.create_fingerprint(page)
            print(f"   - URL: {fp1.get('url_pattern')}")
            print(f"   - Actions: {fp1.get('actionable_elements', {}).get('total_count', 0)}")
            
            # Navigate away and back (same state, potentially different rendering)
            print("\n3. Navigating to Admin page...")
            await page.click('a:has-text("Admin")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(0.5)
            
            print("\n4. Navigating back to dashboard...")
            await page.click('a:has-text("Overview")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            # Capture dashboard fingerprint #2
            print("\n5. Capturing dashboard fingerprint (second capture)...")
            fp2 = await StateFingerprinter.create_fingerprint(page)
            print(f"   - URL: {fp2.get('url_pattern')}")
            print(f"   - Actions: {fp2.get('actionable_elements', {}).get('total_count', 0)}")
            
            # Test similarity calculation
            print("\n6. Calculating similarity between two captures...")
            similarity = StateComparer.calculate_similarity(fp1, fp2)
            
            print("\n" + "=" * 70)
            print("SIMILARITY ANALYSIS")
            print("=" * 70)
            print(f"\n   Overall Similarity: {similarity * 100:.1f}%")
            
            # Detailed comparison
            a11y_score = StateComparer._compare_a11y_trees(
                fp1.get('accessibility_tree'),
                fp2.get('accessibility_tree')
            )
            print(f"   - Semantic (A11y Tree): {a11y_score * 100:.1f}%")
            
            functional_score = StateComparer._compare_actionable_elements(
                fp1.get('actionable_elements'),
                fp2.get('actionable_elements')
            )
            print(f"   - Functional (Actions): {functional_score * 100:.1f}%")
            
            structural_score = StateComparer._compare_url_patterns(
                fp1.get('url_pattern', ''),
                fp2.get('url_pattern', '')
            )
            print(f"   - Structural (URL): {structural_score * 100:.1f}%")
            
            content_score = StateComparer._compare_content(
                fp1.get('title', ''),
                fp2.get('title', ''),
                fp1.get('main_heading', ''),
                fp2.get('main_heading', '')
            )
            print(f"   - Content (Title): {content_score * 100:.1f}%")
            
            # Test with existing state object
            print("\n7. Testing find_matching_state() method...")
            state1 = UIState(
                state_id="V_OVERVIEW_PAGE",
                state_type="dashboard",
                fingerprint=fp1,
                verification_logic={},
                element_descriptors=[]
            )
            
            matched_state, match_score = StateComparer.find_matching_state(
                fp2,
                [state1],
                threshold=0.80
            )
            
            if matched_state:
                print(f"   ✅ Match found: {matched_state.state_id} ({match_score * 100:.1f}%)")
            else:
                print(f"   ❌ No match found (score: {match_score * 100:.1f}%)")
            
            # Test with different pages
            print("\n8. Testing similarity between DIFFERENT pages (Admin vs Dashboard)...")
            await page.click('a:has-text("Admin")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(0.5)
            
            fp_admin = await StateFingerprinter.create_fingerprint(page)
            diff_similarity = StateComparer.calculate_similarity(fp1, fp_admin)
            
            print(f"   Dashboard vs Admin similarity: {diff_similarity * 100:.1f}%")
            
            # Validation
            print("\n" + "=" * 70)
            print("VALIDATION RESULTS")
            print("=" * 70)
            
            success = True
            
            # Check 1: Same page should match >= 80%
            if similarity >= 0.80:
                print(f"✅ Same page captures match (>= 80%): {similarity * 100:.1f}%")
            else:
                print(f"❌ Same page should match >= 80%, got {similarity * 100:.1f}%")
                success = False
            
            # Check 2: Ideally >= 90% for exact same state
            if similarity >= 0.90:
                print(f"✅ Strong match (>= 90%): {similarity * 100:.1f}%")
            else:
                print(f"⚠️  Match is good but not strong (<90%): {similarity * 100:.1f}%")
            
            # Check 3: find_matching_state should find the match
            if matched_state:
                print(f"✅ find_matching_state() correctly identified match")
            else:
                print(f"❌ find_matching_state() failed to find match")
                success = False
            
            # Check 4: Different pages should NOT match
            if diff_similarity < 0.80:
                print(f"✅ Different pages correctly NOT matched (<80%): {diff_similarity * 100:.1f}%")
            else:
                print(f"❌ Different pages should not match (>= 80%): {diff_similarity * 100:.1f}%")
                success = False
            
            # Save fingerprints for inspection
            print("\n9. Saving fingerprints for inspection...")
            with open('fp_dashboard_1.json', 'w') as f:
                json.dump(fp1, f, indent=2)
            with open('fp_dashboard_2.json', 'w') as f:
                json.dump(fp2, f, indent=2)
            with open('fp_admin.json', 'w') as f:
                json.dump(fp_admin, f, indent=2)
            print("   - Saved: fp_dashboard_1.json, fp_dashboard_2.json, fp_admin.json")
            
            print("\n" + "=" * 70)
            if success:
                print("🎉 PHASE 2 IMPLEMENTATION: SUCCESS!")
                print("   State matching working correctly.")
            else:
                print("⚠️  PHASE 2 IMPLEMENTATION: NEEDS ATTENTION")
                print("   Some matching criteria need adjustment.")
            print("=" * 70)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_state_matching())

