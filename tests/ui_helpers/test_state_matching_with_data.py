#!/usr/bin/env python3
"""Test state matching with real data changes.

This validates that StateComparer correctly identifies the same page
even when the data content changes (e.g., device count, status values).

Scenario: Dashboard with 0 devices vs Dashboard with 1+ devices
Expected: Should match as same state (semantic structure identical)
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


async def test_data_change_matching():
    """Test matching with data content changes."""
    
    print("=" * 70)
    print("Testing State Matching with Real Data Changes")
    print("Scenario: Dashboard with different device counts/status")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Login
            print("\n1. Logging in to GenieACS...")
            await page.goto('http://127.0.0.1:3000')
            await page.wait_for_load_state('networkidle')
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin')
            await page.click('button:has-text("Login")')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            # Capture dashboard fingerprint (current state with CPE connected)
            print("\n2. Capturing dashboard fingerprint (CURRENT state with CPE)...")
            fp_current = await StateFingerprinter.create_fingerprint(page)
            
            # Extract key info
            a11y_current = fp_current.get('accessibility_tree', {})
            actions_current = fp_current.get('actionable_elements', {})
            
            print(f"   Current State:")
            print(f"   - URL: {fp_current.get('url_pattern')}")
            print(f"   - Title: {fp_current.get('title')}")
            print(f"   - Landmarks: {a11y_current.get('landmark_roles', [])}")
            print(f"   - Interactive count: {a11y_current.get('interactive_count', 0)}")
            print(f"   - Actions: {actions_current.get('total_count', 0)}")
            print(f"   - Buttons: {len(actions_current.get('buttons', []))}")
            print(f"   - Links: {len(actions_current.get('links', []))}")
            
            # Show sample link names
            links_current = actions_current.get('links', [])
            print(f"\n   Sample links (first 5):")
            for link in links_current[:5]:
                print(f"     - {link.get('name')}")
            
            # Capture raw ARIA snapshot for inspection
            print("\n3. Capturing raw ARIA snapshot for inspection...")
            locator = page.locator('body')
            yaml_current = await locator.aria_snapshot()
            
            print("\n   ARIA Snapshot (first 30 lines):")
            for i, line in enumerate(yaml_current.split('\n')[:30], 1):
                print(f"   {i:2}. {line}")
            
            # Load baseline fingerprint (from Phase 1/2 testing)
            print("\n4. Loading baseline fingerprint (from previous testing)...")
            try:
                with open('fp_dashboard_1.json', 'r') as f:
                    fp_baseline = json.load(f)
                
                a11y_baseline = fp_baseline.get('accessibility_tree', {})
                actions_baseline = fp_baseline.get('actionable_elements', {})
                
                print(f"   Baseline State:")
                print(f"   - URL: {fp_baseline.get('url_pattern')}")
                print(f"   - Title: {fp_baseline.get('title')}")
                print(f"   - Landmarks: {a11y_baseline.get('landmark_roles', [])}")
                print(f"   - Interactive count: {a11y_baseline.get('interactive_count', 0)}")
                print(f"   - Actions: {actions_baseline.get('total_count', 0)}")
                print(f"   - Buttons: {len(actions_baseline.get('buttons', []))}")
                print(f"   - Links: {len(actions_baseline.get('links', []))}")
                
                links_baseline = actions_baseline.get('links', [])
                print(f"\n   Baseline links (first 5):")
                for link in links_baseline[:5]:
                    print(f"     - {link.get('name')}")
                
            except FileNotFoundError:
                print("   ⚠️  Baseline not found, will only analyze current state")
                fp_baseline = None
            
            # Compare if we have baseline
            if fp_baseline:
                print("\n5. Calculating similarity between baseline and current...")
                
                similarity = StateComparer.calculate_similarity(fp_baseline, fp_current)
                
                print("\n" + "=" * 70)
                print("SIMILARITY ANALYSIS")
                print("=" * 70)
                print(f"\n   Overall Similarity: {similarity * 100:.1f}%")
                
                # Detailed breakdown
                semantic_score = StateComparer._compare_a11y_trees(
                    fp_baseline.get('accessibility_tree'),
                    fp_current.get('accessibility_tree')
                )
                print(f"   - Semantic (A11y Tree): {semantic_score * 100:.1f}%")
                
                functional_score = StateComparer._compare_actionable_elements(
                    fp_baseline.get('actionable_elements'),
                    fp_current.get('actionable_elements')
                )
                print(f"   - Functional (Actions): {functional_score * 100:.1f}%")
                
                structural_score = StateComparer._compare_url_patterns(
                    fp_baseline.get('url_pattern', ''),
                    fp_current.get('url_pattern', '')
                )
                print(f"   - Structural (URL): {structural_score * 100:.1f}%")
                
                content_score = StateComparer._compare_content(
                    fp_baseline.get('title', ''),
                    fp_current.get('title', ''),
                    fp_baseline.get('main_heading', ''),
                    fp_current.get('main_heading', '')
                )
                print(f"   - Content (Title): {content_score * 100:.1f}%")
                
                # Detailed comparison of changes
                print("\n   CHANGES DETECTED:")
                
                # Compare landmarks
                landmarks_base = set(a11y_baseline.get('landmark_roles', []))
                landmarks_curr = set(a11y_current.get('landmark_roles', []))
                if landmarks_base != landmarks_curr:
                    print(f"   - Landmarks: {landmarks_base} → {landmarks_curr}")
                else:
                    print(f"   - Landmarks: ✓ Same ({landmarks_base})")
                
                # Compare interactive counts
                count_base = a11y_baseline.get('interactive_count', 0)
                count_curr = a11y_current.get('interactive_count', 0)
                if count_base != count_curr:
                    diff = count_curr - count_base
                    variance = abs(diff) / max(count_base, 1) * 100
                    print(f"   - Interactive count: {count_base} → {count_curr} ({diff:+d}, {variance:.1f}% variance)")
                else:
                    print(f"   - Interactive count: ✓ Same ({count_base})")
                
                # Compare action counts
                total_base = actions_baseline.get('total_count', 0)
                total_curr = actions_current.get('total_count', 0)
                if total_base != total_curr:
                    diff = total_curr - total_base
                    variance = abs(diff) / max(total_base, 1) * 100
                    print(f"   - Action count: {total_base} → {total_curr} ({diff:+d}, {variance:.1f}% variance)")
                else:
                    print(f"   - Action count: ✓ Same ({total_base})")
                
                # Compare link names
                names_base = set(link.get('name', '') for link in links_baseline)
                names_curr = set(link.get('name', '') for link in links_current)
                
                if names_base != names_curr:
                    added = names_curr - names_base
                    removed = names_base - names_curr
                    if added:
                        print(f"   - Links added: {added}")
                    if removed:
                        print(f"   - Links removed: {removed}")
                    common = names_base & names_curr
                    print(f"   - Links in common: {len(common)}/{max(len(names_base), len(names_curr))}")
                else:
                    print(f"   - Link names: ✓ Same ({len(names_base)} links)")
                
                # Test with find_matching_state
                print("\n6. Testing find_matching_state() method...")
                state_baseline = UIState(
                    state_id="V_OVERVIEW_PAGE",
                    state_type="dashboard",
                    fingerprint=fp_baseline,
                    verification_logic={},
                    element_descriptors=[]
                )
                
                matched_state, match_score = StateComparer.find_matching_state(
                    fp_current,
                    [state_baseline],
                    threshold=0.80
                )
                
                if matched_state:
                    print(f"   ✅ Match found: {matched_state.state_id} ({match_score * 100:.1f}%)")
                else:
                    print(f"   ❌ No match found (score: {match_score * 100:.1f}%)")
                
                # Validation
                print("\n" + "=" * 70)
                print("VALIDATION RESULTS")
                print("=" * 70)
                
                success = True
                
                # Check 1: Should still match (>= 80%)
                if similarity >= 0.80:
                    print(f"✅ States match despite data changes (>= 80%): {similarity * 100:.1f}%")
                else:
                    print(f"⚠️  States did not match: {similarity * 100:.1f}%")
                    print(f"   This may be expected if data changes are significant.")
                    if similarity >= 0.70:
                        print(f"   Score is close to threshold (70-80% = weak match)")
                    success = False
                
                # Check 2: Semantic should be high (landmarks shouldn't change)
                if semantic_score >= 0.90:
                    print(f"✅ Semantic structure stable (>= 90%): {semantic_score * 100:.1f}%")
                elif semantic_score >= 0.80:
                    print(f"⚠️  Semantic structure mostly stable (80-90%): {semantic_score * 100:.1f}%")
                else:
                    print(f"❌ Semantic structure changed significantly: {semantic_score * 100:.1f}%")
                    success = False
                
                # Check 3: URL should be identical
                if structural_score >= 0.95:
                    print(f"✅ URL pattern identical: {structural_score * 100:.1f}%")
                else:
                    print(f"⚠️  URL pattern differs: {structural_score * 100:.1f}%")
                
                # Check 4: find_matching_state should work
                if matched_state:
                    print(f"✅ find_matching_state() correctly identified match")
                else:
                    if similarity >= 0.70:
                        print(f"⚠️  find_matching_state() didn't match (close: {similarity * 100:.1f}%)")
                        print(f"   May need to adjust threshold or weights")
                    else:
                        print(f"ℹ️  No match found, states may be genuinely different")
                
                print("\n" + "=" * 70)
                if success:
                    print("🎉 STATE MATCHING: RESILIENT TO DATA CHANGES!")
                    print(f"   Same page recognized despite content differences.")
                else:
                    print("⚠️  STATE MATCHING: NEEDS REVIEW")
                    print(f"   Data changes may have affected matching.")
                    print(f"   Review breakdown above to see what changed.")
                print("=" * 70)
            
            # Save current fingerprint
            print("\n7. Saving current fingerprint for future comparison...")
            with open('fp_dashboard_with_cpe.json', 'w') as f:
                json.dump(fp_current, f, indent=2)
            print("   - Saved: fp_dashboard_with_cpe.json")
            
            # Save raw ARIA snapshot
            with open('aria_snapshot_with_cpe.yaml', 'w') as f:
                f.write(yaml_current)
            print("   - Saved: aria_snapshot_with_cpe.yaml")
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_data_change_matching())

