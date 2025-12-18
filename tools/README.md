# Manual FSM Recording Tool

Interactive tool for recording UI workflows through manual browser interactions, with intelligent deduplication.

## Purpose

Automated UI discovery captures 60-70% of UI states (page-level navigation). This **interactive recording tool** captures the remaining 20-30% by letting YOU manually perform actions while the tool records states:

- Dropdown menus and filter selections
- Modal overlays and confirmation dialogs  
- Multi-step compound actions
- Dynamic UI elements that appear on interaction
- Pop-ups and their appearance/disappearance
- **ANY workflow you can manually perform**

## Key Features

### 🎯 Workflow-Agnostic Design
- No hardcoded workflows - YOU decide what to record
- No CPE IDs, usernames, or credentials needed
- Start fresh or augment existing graphs
- Works with any web application

### 🧬 Intelligent Deduplication
- **Fingerprint-based matching** - Structural comparison, not just ID matching
- Detects duplicate states using URL pattern + element structure
- Automatically remaps transitions to existing states
- Prevents graph pollution
- Idempotent - safe to re-record same workflows

### 🎨 Rich State Capture
- **ARIA snapshots** - Accessibility tree for robust element identification
- **Actionable elements** - Buttons, links, inputs with role-based locators
- **State types** - form, detail, overlay, interactive, dashboard
- **URL patterns** - Normalized for matching

### 🔄 Smart Transitions
- **Action metadata** - What you did to reach each state
- **Action types** - click, fill_and_submit, select, navigate, wait
- **Element locators** - ARIA role-based (resilient to CSS changes)
- **Automatic type inference** - From your action descriptions

### 💻 Clean User Experience
- **Interactive 's' key** - Capture states without interfering with browser
- **Clear prompts** - Visual cues, examples, immediate feedback
- **Race-free input** - Pure asyncio, no threading issues
- **Clean output** - No exception noise

## Quick Start

### Prerequisites

```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
```

### Basic Usage

```bash
# Start fresh recording
python tools/manual_fsm_augmentation.py \
  --url http://localhost:3000 \
  --output bf_config/gui_artifacts/genieacs/fsm_graph.json

# Augment existing graph (recommended)
python tools/manual_fsm_augmentation.py \
  --url http://localhost:3000 \
  --input bf_config/gui_artifacts/genieacs/fsm_graph.json \
  --output bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json
```

### Interactive Session

```
INTERACTIVE RECORDING MODE
======================================================================
The browser is open. You can interact with it normally.
Commands (type in this TERMINAL, not the browser):

  's' + [Enter]     - Capture/Snapshot current browser state
  'q' + [Enter]     - Quit recording and save
======================================================================

Command (s=snapshot, q=quit): s

Capturing current state...
State captured: V_STATE_002
Total states captured: 2

======================================================================
⚠️  DESCRIBE THE ACTION YOU JUST PERFORMED
======================================================================
What did you do in the BROWSER to reach this state?

Examples:
  • clicked the Devices link
  • filled search field and pressed Enter
  • pressed the Reboot button
  • waited for popup to disappear

(Press Enter alone to skip and use generic description)
----------------------------------------------------------------------
Your action → clicked the Devices link
======================================================================
Transition created: V_STATE_001 → V_STATE_002
  Action: clicked the Devices link

Ready. Perform next action in browser, then type 's' here.

Command (s=snapshot, q=quit):
```

## What Gets Captured

### States (Nodes)
Each state snapshot includes:
- **URL** and **title**
- **ARIA snapshot** (accessibility tree)
- **Actionable elements** (buttons, links, inputs)
- **Element locators** (role-based, resilient: `getByRole('button', { name: 'Login' })`)
- **State type** (form, detail, overlay, interactive)
- **Discovery metadata** (timestamp, manually recorded flag)

### Transitions (Edges)
Each transition between states includes:
- **Action type** (click, fill_and_submit, select, navigate, wait, custom)
- **Description** (human-readable: "clicked the Devices link")
- **Element locators** (how to find the element for automation)
- **Action data** (form fields, dropdown options, URLs)

Example:
```json
{
  "id": "T_V_STATE_001_TO_V_STATE_002",
  "edge_type": "transition",
  "source": "V_STATE_001",
  "target": "V_STATE_002",
  "action_type": "click_link",
  "description": "clicked the Devices link",
  "trigger_locators": {},
  "action_data": {}
}
```

## Intelligent Deduplication

When merging with an existing graph, the tool uses **fingerprint-based duplicate detection**:

### How It Works

1. **Computes structural fingerprint** for each state:
   - URL pattern (stripped of dynamic query params)
   - State type
   - Element structure (button/link/input counts)
   - Non-data link names (ignores numeric values)

2. **Compares manually recorded states** against existing states

3. **Detects duplicates** and maps to existing state IDs

4. **Remaps transitions** to use existing states where appropriate

5. **Only adds genuinely new states**

### Example Output

```
MERGING WITH EXISTING GRAPH
============================================================
Existing graph: 10 states, 58 transitions
Computed 10 fingerprints from existing states
  Duplicate detected: V_STATE_001 matches existing V_OVERVIEW_PAGE
  Duplicate detected: V_STATE_002 matches existing V_DEVICES
Added 11 new states
Skipped 2 duplicate states

DEDUPLICATION SUMMARY
------------------------------------------------------------
Manually captured: 13 states, 12 transitions
Duplicates found: 2 states, 1 transitions
Actually added: 11 states, 11 transitions
```

### Benefits

- ✅ **Clean graph** - No duplicate states
- ✅ **Start anywhere** - Can begin recording from any existing state
- ✅ **Idempotent** - Safe to re-record the same workflow multiple times
- ✅ **Correct connections** - Transitions automatically link to existing states

## Recording Strategy

### Best Practices

1. **Plan your workflow** - Decide what to record before starting
2. **Significant states only** - Don't capture every hover/animation
3. **After actions** - Type 's' AFTER each action completes and page settles
4. **Describe accurately** - Provide correct button/link names for automation
5. **Capture overlays** - Type 's' when overlays/dropdowns appear AND after they disappear
6. **Be patient** - Wait for page loads, then type 's'
7. **Use browser normally** - Press Enter in forms as usual (doesn't trigger capture)

### When to Capture States

**DO capture**:
- After clicking a button/link (once page loads)
- When a dropdown menu opens
- When an overlay/modal appears
- After submitting a form (once result page loads)
- When a pop-up appears
- When a pop-up disappears (leaving underlying page)

**DON'T capture**:
- During animations
- While page is loading
- On hover (unless it reveals persistent UI elements)
- Temporary tooltips

### Action Description Tips

When prompted for action details, provide clear descriptions:

**Good examples**:
- "clicked the Devices link"
- "selected 'Serial number:' from the dropdown"
- "entered CPE serial number and pressed Enter"
- "pressed the Reboot button"
- "waited for popup to disappear"

**Avoid**:
- Generic: "clicked something"
- Vague: "did stuff"
- Technical: "executed JavaScript click event on element #btn_1"

The tool will infer action types from your description:
- "clicked" → `click` or `click_button` or `click_link`
- "filled", "entered" → `fill_and_submit`
- "selected" → `select`
- "waited" → `wait`

## Command Reference

### Arguments

```
--url URL                Base URL to navigate to (default: http://localhost:3000)
--input PATH             Path to existing fsm_graph.json (optional)
--output PATH            Path to save the recorded/augmented graph (required)
--headless               Run browser in headless mode (not recommended)
```

### Interactive Commands

During recording session:

| Command | Action |
|---------|--------|
| `s` | Capture current browser state |
| `q` | Quit recording and save all captured data |
| `Enter` (at action prompt) | Skip action description (uses generic) |

## Output Format

The tool generates/augments an FSM graph JSON file:

```json
{
  "base_url": "http://localhost:3000",
  "graph_type": "fsm_mbt",
  "discovery_method": "playwright_state_machine_dfs",
  "nodes": [
    {
      "id": "V_STATE_001",
      "node_type": "state",
      "state_type": "interactive",
      "discovered_manually": true,
      "fingerprint": {
        "url": "http://localhost:3000/#!/overview",
        "aria_snapshot": "- navigation:\n  - link \"Overview\"\n  ...",
        "actionable_elements": {
          "buttons": [...],
          "links": [...],
          "inputs": [...],
          "total_count": 8
        }
      },
      "verification_logic": {
        "url_pattern": "overview",
        "title_contains": "Overview"
      }
    }
  ],
  "edges": [
    {
      "id": "T_V_STATE_001_TO_V_STATE_002",
      "source": "V_STATE_001",
      "target": "V_STATE_002",
      "action_type": "click_link",
      "description": "clicked the Devices link"
    }
  ],
  "statistics": {
    "state_count": 21,
    "transition_count": 69,
    "manually_augmented": true,
    "new_states_added": 11,
    "duplicate_states_skipped": 2
  }
}
```

## Use Cases

### 1. Capture Dropdown Interactions

**Scenario**: Search filter has dropdown menu for field selection

**Steps**:
1. Navigate to search page → Type 's'
2. Click in filter field → Type 's' (dropdown appears)
3. Select "Serial number:" → Type 's' (dropdown closes)
4. Enter serial number → Type 's' (results shown)

**Result**: 4 states capturing dropdown lifecycle

### 2. Record Overlay Workflows

**Scenario**: Reboot button shows confirmation overlay

**Steps**:
1. Navigate to device details → Type 's'
2. Click "Reboot" button → Type 's' (overlay appears)
3. Click "Commit" button → Type 's' (overlay shows pending)
4. Wait for overlay to close → Type 's' (back to device details)

**Result**: 4 states capturing overlay lifecycle

### 3. Multi-Step Forms

**Scenario**: Form with dynamic fields based on selections

**Steps**:
1. Initial form state → Type 's'
2. Select option from dropdown → Type 's' (new fields appear)
3. Fill new fields → Type 's'
4. Submit form → Type 's' (result page)

**Result**: 4 states capturing form evolution

## Troubleshooting

### Issue: Action descriptions interpreted as commands

**Symptom**: You see `→ Unknown command: 'clicked on Devices' tab'. Use 's' or 'q'`

**Cause**: This was a threading race condition (fixed in current version)

**Solution**: Update to latest version of the tool. The issue is resolved through pure asyncio implementation.

### Issue: Duplicate states added to graph

**Symptom**: Graph size grows by exact number of states captured (no deduplication)

**Cause**: Using old version without fingerprint-based deduplication

**Solution**: 
- Tool now uses **fingerprint-based deduplication** (not just ID matching)
- Check merge output for "Duplicate detected" messages
- Verify statistics show `duplicate_states_skipped` count

### Issue: Browser doesn't open

**Symptom**: Script runs but no browser appears

**Cause**: Playwright not installed or wrong Python environment

**Solution**:
```bash
source .venv-3.12/bin/activate
pip install playwright
python -m playwright install firefox
```

### Issue: States not captured correctly

**Symptom**: States missing elements or ARIA snapshot incomplete

**Solution**:
- Wait for page to fully load before typing 's'
- Ensure page has settled (no animations)
- Check browser console for JavaScript errors
- Try increasing wait time (future enhancement)

### Issue: Can't distinguish similar states

**Symptom**: Tool thinks two different states are duplicates

**Cause**: States have same URL and similar element structure

**Solution**: This is expected for states that differ only in data (e.g., different device counts). For structural differences (e.g., dropdown open vs closed), the tool should detect them. If not, file an issue with examples.

## Technical Details

### Architecture

- **Pure asyncio** - No threading, no race conditions
- **Non-blocking input** - Uses `loop.run_in_executor()` for stdin
- **Playwright** - Firefox browser automation
- **ARIA snapshots** - Accessibility tree capture
- **Fingerprint algorithm** - MD5 hash of structural properties

### Fingerprint Computation

States are compared using:
```python
fingerprint = {
    'url_base': normalized_url,
    'state_type': 'form' | 'detail' | 'interactive' | ...,
    'button_count': len(buttons),
    'link_structure': [non-data link names],
    'input_count': len(inputs)
}
hash = md5(json.dumps(fingerprint, sort_keys=True))
```

### Merge Algorithm

1. Build fingerprint map of existing states
2. For each manually recorded state:
   - Compute fingerprint
   - Check against existing fingerprints
   - If match: map to existing ID (don't add)
   - If new: add to graph
3. Remap transitions to use mapped IDs
4. Skip transitions that already exist

## Dependencies

Required packages (already in `.venv-3.12`):
- `playwright>=1.40.0`
- Python 3.10+

## Files

- **`manual_fsm_augmentation.py`** - Interactive recording tool (756 lines)
- **`README.md`** - This documentation

## Next Steps After Recording

1. **Review the augmented graph**:
   ```bash
   cat bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json | jq '.statistics'
   ```

2. **Update STATE_REGISTRY**:
   ```python
   # In genie_acs.py
   STATE_REGISTRY = {
       "login": "V_LOGIN_FORM_EMPTY",
       "overview": "V_OVERVIEW_PAGE",
       "devices": "V_DEVICES",
       "devices_dropdown_open": "V_STATE_003",  # New!
       "device_details": "V_STATE_006",         # New!
       # ...
   }
   ```

3. **Refactor test steps** to use FSM transitions instead of direct Playwright locators

4. **Test resilience** - Make minor UI changes and verify tests still pass

## Complete Workflow Guide

For the **full end-to-end workflow** (Fresh Discovery → Manual Recording → Incremental Discovery), see:

📖 **[Complete Workflow Guide](../../StateExplorer/COMPLETE_WORKFLOW_GUIDE.md)**

This comprehensive guide includes:
- All three stages with detailed steps
- Verification commands
- Troubleshooting
- Next steps and integration

## Support

For issues, questions, or contributions:
- Check troubleshooting section above
- Review captured JSON for state/transition details
- Consult FSM implementation guide in `../docs/`
- See complete workflow guide (link above)

## License

BSD-3-Clause (see LICENSE file in project root)
