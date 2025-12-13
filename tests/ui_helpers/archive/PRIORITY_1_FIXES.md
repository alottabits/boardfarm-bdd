# Priority 1 Fixes - FSM Discovery Tool

**Date**: December 11, 2025  
**Status**: ✅ IMPLEMENTED

---

## Problem Statement

Initial run showed shallow exploration (only 6/32 states explored) due to:
1. Ephemeral loading states causing navigation failures
2. Duplicate transitions being recorded multiple times
3. Conservative max_states limit (50)
4. Insufficient debugging information for failures

---

## Fixes Implemented

### 1. ✅ Transition Deduplication

**Problem**: Same transitions recorded multiple times (e.g., V_OVERVIEW_PAGE -> V_ADMIN_PRESETS recorded 4+ times from different source states).

**Solution**: Added `transition_signatures` set to track `(from_state, action_type, to_state)` tuples.

**Implementation**:
- Added `self.transition_signatures: set[tuple[str, str, str]]` to `__init__` (line ~708)
- Check before recording transitions in:
  - `_execute_link_click()`: Check signature before appending (line ~2043)
  - `_execute_button_click()`: Check signature before appending (line ~2138)
  - `_execute_form_fill()`: Check signature before appending (line ~1959)

**Expected Impact**: Reduces redundant explorations, cleaner transition graph.

---

### 2. ✅ Skip Ephemeral Loading States

**Problem**: `V_LOADING_DEVICES` state appears briefly when clicking "Devices" link, then auto-transitions to `V_DEVICES`. Navigation attempts fail because state is transient.

**Solution**: Skip exploration of states with `state_type == "loading"` (also skip "error" and "form" states).

**Implementation**:
- DFS exploration: Skip check at line ~1293
- BFS exploration (_explore_states_bfs): Skip check at line ~1444
- BFS exploration (_explore_states_simple_bfs): Skip check at line ~1555

**Code**:
```python
if state.state_type in ["error", "form", "loading"]:
    logger.info("Skipping exploration of ephemeral %s state: %s", ...)
    explored_states.add(state_id)
    return
```

**Expected Impact**: Eliminates navigation failures, allows exploration to proceed to stable states.

---

### 3. ✅ Increase max_states from 50 to 100

**Problem**: Conservative limit of 50 states prevented full exploration (32 states seeded from ui_map.json).

**Solution**: Doubled limit to 100 states.

**Implementation**:
- `__init__` default parameter: Changed from 50 to 100 (line ~682)
- CLI `--max-states` default: Changed from 50 to 100 (line ~2341)

**Expected Impact**: Allows exploration of more states without hitting limit.

---

### 4. ✅ Improved Debugging Logs

**Problem**: Many link/button clicks failed silently (logs showed "Clicking link: X" but no follow-up indicating success or failure).

**Solution**: Added detailed logging for element location failures and execution errors.

**Implementation**:
- `_execute_link_click()`: 
  - Log when link can't be located with descriptor details (line ~2008)
  - Log exception with link text and exception type (line ~2074)
- `_execute_button_click()`:
  - Log when button can't be located with descriptor details (line ~2106)
  - Log exception with button text and exception type (line ~2167)

**Code Examples**:
```python
if not link:
    logger.debug("Failed to locate link: %s (descriptor: %s)", link_text, link_info.get("locators"))
    return None

except Exception as e:
    logger.debug("Error in link click execution for '%s': %s (type: %s)", 
                link_text, str(e), type(e).__name__)
```

**Expected Impact**: Better visibility into why explorations fail, easier debugging.

---

## Expected Results

### Before Fixes
```
States discovered: 32 (31 seeded + 1 new)
States explored: 6
Transitions found: 18
Issues:
  - Can't navigate to V_LOADING_DEVICES
  - Many duplicate transitions
  - Hit max_states early
  - Silent failures
```

### After Fixes (Expected)
```
States discovered: 35-40
States explored: 20-30
Transitions found: 30-50 (unique only)
Improvements:
  ✅ Loading states skipped (no navigation errors)
  ✅ No duplicate transitions
  ✅ More headroom (max 100 states)
  ✅ Clear failure logs
```

---

## Testing Instructions

### Re-run Discovery

```bash
cd /home/rjvisser/projects/req-tst/boardfarm-bdd/tests/ui_helpers

# Stage 1: POM (unchanged, for comparison)
python discover_ui.py \
  --url http://127.0.0.1:3000 \
  --username admin --password admin \
  --output ui_map.json

# Stage 2: FSM with fixes
python ui_mbt_discovery.py \
  --url http://127.0.0.1:3000 \
  --username admin --password admin \
  --seed-map ui_map.json \
  --output fsm_graph_fixed.json \
  --max-states 100
```

### Compare Outputs

```bash
# Check statistics
jq '.statistics' fsm_graph_fixed.json

# Expected improvements:
# - state_count: 35-40 (up from 32)
# - transition_count: 30-50 (up from 18, unique only)
# - visited_states: 20-30 (up from 6)
```

### Analyze Logs

Look for:
- ✅ "Skipping exploration of ephemeral loading state: V_LOADING_DEVICES"
- ✅ "Transition X -> Y already recorded, skipping duplicate"
- ✅ "Failed to locate link: ... (descriptor: ...)" for debugging
- ✅ More states at depth 2-3 explored

---

## Files Modified

1. `ui_mbt_discovery.py` (11 changes):
   - Line ~708: Added `transition_signatures` set
   - Line ~682: Increased default max_states to 100
   - Line ~1293: Skip loading states in DFS
   - Line ~1444: Skip loading states in BFS
   - Line ~1555: Skip loading states in simple BFS
   - Line ~2043: Link click deduplication check
   - Line ~2138: Button click deduplication check
   - Line ~1959: Form fill deduplication check
   - Line ~2008: Link location failure logging
   - Line ~2074: Link execution error logging
   - Line ~2106: Button location failure logging
   - Line ~2167: Button execution error logging
   - Line ~2341: CLI max_states default to 100

---

## Next Steps

1. **Run Discovery**: Execute with fixes and compare results
2. **Analyze Coverage**: Check if more states/transitions discovered
3. **Proceed to Phase 8**: If coverage improved significantly (20+ explored states, 30+ transitions), proceed to resilience evaluation
4. **Optional Further Fixes**: If still shallow:
   - Increase exploration depth limit for DFS
   - Add retry logic for failed element location
   - Implement form detection improvements

---

**Status**: ✅ Ready for Testing
