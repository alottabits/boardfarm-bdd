# Manual FSM Recording Tool

This directory contains tools for recording UI workflows through interactive manual actions.

## Purpose

Automated UI discovery captures 60-70% of UI states (page-level navigation). This **interactive recording tool** captures the remaining 20-30% by letting YOU manually perform actions while the tool records states:

- Dropdown menus and filter selections
- Modal overlays and confirmation dialogs
- Multi-step compound actions
- Dynamic UI elements that appear on interaction
- **ANY workflow you can manually perform**

## Key Design Philosophy

🎯 **Workflow-Agnostic**: The tool doesn't prescribe specific workflows. YOU decide what to record by performing actions in the browser.

✅ **Interactive**: Type 's' in terminal to capture states (won't interfere with browser Enter key)  
✅ **Flexible**: Start fresh or augment existing graphs  
✅ **No hardcoding**: No CPE IDs, usernames, or specific workflows required  
✅ **ARIA-based**: Captures accessibility tree snapshots automatically  

## When to Use

Use manual recording when:
1. Automated discovery misses critical interaction states
2. You need to capture dropdown/overlay states
3. Test code has direct Playwright locators (technical debt)
4. UI changes require re-recording specific workflows
5. You want to explore and document a new UI workflow

## What Gets Captured

### States (Nodes)
For each state snapshot, the tool captures:
- **URL** and **title**
- **ARIA snapshot** (accessibility tree)
- **Actionable elements** (buttons, links, inputs)
- **Element locators** (role-based, resilient)
- **State type** (form, list, detail, overlay, interactive)

### Transitions (Edges)
For each transition between states, the tool captures:
- **Action type** (click, fill_and_submit, select, navigate, custom)
- **Target element** (button name, link text, form description)
- **Element locators** (how to find the element for automation)
- **Action data** (form fields, dropdown options, URLs)
- **Description** (human-readable action summary)

**Example Transition**:
```json
{
  "id": "T_LOGIN_TO_OVERVIEW",
  "source": "V_STATE_001",
  "target": "V_STATE_002",
  "action_type": "fill_and_submit",
  "description": "Fill and submit login form",
  "trigger_locators": {},
  "action_data": {
    "fields": "username, password",
    "submit_method": "button or Enter key"
  }
}
```

## Tool: `manual_fsm_augmentation.py`

### How It Works

1. **Browser opens** at your specified URL (visible mode)
2. **You manually navigate** - login, click buttons, fill forms, etc.
3. **Type 's' in terminal** after each significant state change (won't interfere with form submissions!)
4. **Tool captures** current page state (ARIA snapshot, elements, URL)
5. **Tool prompts** for action details (what you just did to reach this state)
6. **Type 'q' in terminal** when done - tool saves all recorded states/transitions

### Usage

```bash
# Activate virtual environment
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

# Start fresh recording
python tools/manual_fsm_augmentation.py \
  --url http://localhost:3000 \
  --output bf_config/gui_artifacts/genieacs/fsm_graph.json

# Augment existing graph
python tools/manual_fsm_augmentation.py \
  --url http://localhost:3000 \
  --input bf_config/gui_artifacts/genieacs/fsm_graph.json \
  --output bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json

# Or use the wrapper script
./tools/augment_fsm.sh           # Augment existing
./tools/augment_fsm.sh --fresh   # Start from scratch
```

### Interactive Recording Session

Here's what a typical session looks like:

```bash
$ ./tools/augment_fsm.sh

==========================================
Manual FSM Recording (Interactive)
==========================================
Mode:        Augmentation
URL:         http://localhost:3000
Input:       bf_config/gui_artifacts/genieacs/fsm_graph.json
Output:      bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json
==========================================

The browser will open at http://localhost:3000
You will manually perform actions in the browser.
After each significant action, type 's' in the TERMINAL to capture the state.
Type 'q' in the TERMINAL when you're done recording.

Ready to start? (y/n) y

Starting interactive recording session...

Browser started and navigated to http://localhost:3000
You can now manually interact with the page

============================================================
INTERACTIVE RECORDING MODE
============================================================
The browser is open. You can interact with it normally.
Commands (type in this TERMINAL, not the browser):

  's' + [Enter]     - Capture/Snapshot current browser state
  'q' + [Enter]     - Quit recording and save
============================================================

TIP: Use Enter freely in the browser (forms, etc.).
     Only type 's' in THIS terminal to capture states.
============================================================

Command (s=snapshot, q=quit): 

# You perform in BROWSER: Fill username, password, press Enter to login
# Then type 's' in TERMINAL

s
Capturing current state...
Capturing state: V_STATE_001
  - Type: form
  - URL: http://localhost:3000/#/login
  - Elements: 1 buttons, 1 links, 2 inputs
State captured: V_STATE_001
Total states captured: 1

Ready. Perform next action in browser, then type 's' here.

Command (s=snapshot, q=quit): 

# You in BROWSER: Navigate to devices page (click "Devices" link)
# Then type 's' in THIS TERMINAL

s
Capturing current state...
Capturing state: V_STATE_002
  - Type: list
  - URL: http://localhost:3000/#/devices
  - Elements: 5 buttons, 12 links, 1 inputs
State captured: V_STATE_002

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
Your action → clicked the Devices link    ← TYPE YOUR DESCRIPTION HERE
======================================================================
Transition created: V_STATE_001 → V_STATE_002
  Action: clicked the Devices link
Total states captured: 2

Ready. Perform next action in browser, then type 's' here.

Command (s=snapshot, q=quit):    ← NOW you can type 's' again

# ... continue until done ...

Command (s=snapshot, q=quit): q

Recording complete!
Captured 5 states and 4 transitions
```

### Recording Strategy

1. **Plan your workflow** - Decide what to record before starting
2. **Significant states only** - Don't capture every hover/animation
3. **After actions** - Type 's' AFTER each action completes and page settles
4. **Describe actions accurately** - Provide correct button/link names for automation
5. **Capture overlays** - Type 's' when overlays/dropdowns appear
6. **Be patient** - Wait for page loads, then type 's' to capture
7. **Use browser normally** - Press Enter in forms as usual (doesn't trigger capture)

### Smart Deduplication

When merging with an existing graph, the tool uses **fingerprint-based duplicate detection**:

**What happens:**
- Computes a structural fingerprint for each state (URL pattern + element structure)
- Compares manually recorded states against existing states
- If match found, skips the duplicate and remaps transitions to existing state ID
- Only adds genuinely new states

**Example output:**
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

**Benefits:**
- ✅ Clean graph with no duplicates
- ✅ Can start recording from any existing state
- ✅ Idempotent - safe to re-record the same workflow
- ✅ Transitions correctly linked to existing states

See [FINGERPRINT_DEDUPLICATION.md](./FINGERPRINT_DEDUPLICATION.md) for technical details.

### Action Detail Tips

When prompted for action details:
- **Button/Link names**: Use exact text from the UI (case-sensitive)
- **Form fields**: List all fields filled (e.g., "username, password, email")
- **Dropdown options**: Specify exact option text selected
- **Skip if unsure**: Press Enter to create generic transition (can edit JSON later)
- **Be specific**: Good locators = more reliable automation

**Good examples**:
- Button: "Submit", "Login", "Reboot", "Commit"
- Link: "Devices", "Overview", "Settings"
- Form: "login form" with fields "username, password"
- Dropdown: "Serial number" from "Filter by"

## Output

The tool produces an FSM graph with:
- All manually recorded states (tagged with `"discovered_manually": true`)
- Transitions between states (showing the order you navigated)
- ARIA snapshots and actionable elements for each state
- Complete metadata with timestamps

### Example Output

```json
{
  "base_url": "http://localhost:3000",
  "graph_type": "fsm_mbt",
  "discovery_method": "manual_interactive_recording",
  "nodes": [
    {
      "id": "V_STATE_001",
      "node_type": "state",
      "state_type": "form",
      "discovered_manually": true,
      "discovery_timestamp": "2025-12-16T10:30:00Z",
      "fingerprint": {
        "url": "http://localhost:3000/#/login",
        "title": "Login - GenieACS",
        "aria_snapshot": "- banner:\n  - link \"Log in\"\n...",
        "actionable_elements": {
          "buttons": [
            {
              "role": "button",
              "name": "Login",
              "locator_strategy": "getByRole('button', { name: 'Login' })"
            }
          ],
          "inputs": [
            {
              "role": "textbox",
              "name": "username"
            },
            {
              "role": "textbox",
              "name": "password"
            }
          ],
          "total_count": 3
        }
      },
      "verification_logic": {
        "url_pattern": "/login",
        "title_contains": "Login - GenieACS"
      }
    },
    {
      "id": "V_STATE_002",
      "node_type": "state",
      "state_type": "list",
      "discovered_manually": true,
      "discovery_timestamp": "2025-12-16T10:31:00Z",
      "fingerprint": {
        "url": "http://localhost:3000/#/devices",
        "title": "Devices - GenieACS",
        "actionable_elements": {
          "buttons": [{"role": "button", "name": "Refresh"}],
          "links": [{"role": "link", "name": "665A3B-SN665A3BA8824A"}],
          "inputs": [{"role": "textbox"}],
          "total_count": 14
        }
      }
    }
  ],
  "edges": [
    {
      "id": "T_V_STATE_001_TO_V_STATE_002",
      "edge_type": "transition",
      "source": "V_STATE_001",
      "target": "V_STATE_002",
      "action_type": "click",
      "description": "Click 'Devices' link",
      "trigger_locators": {
        "role": "link",
        "name": "Devices",
        "selector": "a:has-text('Devices')"
      },
      "action_data": {},
      "discovered_manually": true,
      "discovery_timestamp": "2025-12-16T10:31:00Z"
    }
  ],
  "statistics": {
    "state_count": 2,
    "transition_count": 1,
    "manually_recorded": true,
    "recording_timestamp": "2025-12-16T10:31:00Z"
  }
}
```

## Integration Workflow

### Approach 1: Two-Step (Automated + Manual)

**Step 1: Run Automated Discovery** (captures high-level pages)
```bash
cd ~/projects/req-tst/StateExplorer
aria-discover \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --max-states 20 \
  --output ~/projects/req-tst/boardfarm-bdd/bf_config/gui_artifacts/genieacs/fsm_graph.json
```
**Result:** 10-12 high-level states (login, overview, devices, etc.)

**Step 2: Run Manual Recording** (captures detailed interactions)
```bash
cd ~/projects/req-tst/boardfarm-bdd
./tools/augment_fsm.sh
```

**During recording:**
1. Browser opens at login page
2. You manually in BROWSER: Fill login form and press Enter to submit
3. Type 's' in TERMINAL after: login complete
4. You manually in BROWSER: Navigate to devices → Open dropdown → Select filter → Search (using Enter as normal)
5. Type 's' in TERMINAL after each: devices page load, dropdown open, filter selected, results shown
6. Type 'q' in TERMINAL when done

**Result:** 15-20 states (pages + dropdowns + overlays + search results)

### Approach 2: Manual Only (Start Fresh)

For exploring new UI or when automated discovery isn't suitable:

```bash
cd ~/projects/req-tst/boardfarm-bdd
./tools/augment_fsm.sh --fresh
```

**Use case:** Recording a complete workflow from scratch, exploring new features, documenting edge cases

### 3. Review and Replace
```bash
# Review the augmented graph
cat bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json | jq '.statistics'

# If satisfied, replace original
cp bf_config/gui_artifacts/genieacs/fsm_graph.json \
   bf_config/gui_artifacts/genieacs/fsm_graph_original.json.bak
   
cp bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json \
   bf_config/gui_artifacts/genieacs/fsm_graph.json
```

### 4. Update Device Implementation
Update `boardfarm/boardfarm3/devices/genie_acs.py`:

```python
class GenieAcsGUI(BaseGui):
    STATE_REGISTRY = {
        # Existing states
        "login_page": "V_LOGIN_FORM_EMPTY",
        "home_page": "V_OVERVIEW_PAGE",
        "devices_page": "V_DEVICES_PAGE",
        
        # New states from manual augmentation
        "search_ready": "V_DEVICES_SEARCH_READY",
        "search_filter_dropdown": "V_DEVICES_SEARCH_FILTER_DROPDOWN",
        "search_serial_selected": "V_DEVICES_SEARCH_SERIAL_SELECTED",
        "search_results": "V_DEVICES_SEARCH_RESULTS",
        "device_details": "V_DEVICE_DETAILS",
        "reboot_pending": "V_REBOOT_TASK_PENDING",
        "reboot_committed": "V_REBOOT_TASK_COMMITTED",
    }
```

### 5. Refactor Test Steps
Replace direct Playwright locators with FSM transitions:

```python
# BEFORE (brittle, manual locators)
async def operator_initiates_reboot_via_gui(bf_context):
    acs = bf_context.board.get_device('acs')
    await acs.gui.browser.page.click('button:has-text("Reboot")')
    await acs.gui.browser.page.click('button:has-text("Commit")')

# AFTER (resilient, FSM-driven)
async def operator_initiates_reboot_via_gui(bf_context):
    acs = bf_context.board.get_device('acs')
    await acs.gui.reboot_device_via_gui_complete(bf_context.cpe_device_id)
```

## Maintenance

When the UI changes:
1. Re-run automated discovery to capture high-level changes
2. Re-run manual augmentation to update interaction details
3. Review diff to see what changed
4. Update test steps if state IDs changed

## Best Practices

1. **Balance granularity**: Capture overlays/dropdowns, but not every hover state
2. **Descriptive IDs**: Use clear state IDs like `V_REBOOT_TASK_PENDING`
3. **Version control**: Keep both `fsm_graph.json` and `fsm_graph_augmented.json`
4. **Document custom workflows**: Add comments when adding new recordings
5. **Test incrementally**: Test each workflow after adding it

## Troubleshooting

### Browser doesn't start
- Check Playwright installation: `playwright install firefox`
- Try visible mode to debug: remove `--headless` flag

### States not captured correctly
- Increase wait times in the script (`await asyncio.sleep(2)`)
- Check element selectors in browser DevTools
- Run in visible mode to observe

### Duplicate states added
- The tool automatically deduplicates using **fingerprint-based detection**
- Compares URL pattern, state type, and element structure (not just IDs)
- If manually recording a state that already exists, it will:
  - Skip adding the duplicate state
  - Remap transitions to use the existing state ID
  - Log: `"Duplicate detected: V_STATE_001 matches existing V_OVERVIEW_PAGE"`
- Check merge output for deduplication summary showing what was skipped

### Missing transitions
- Ensure source and target states are captured before transitions
- Check that element locators are correct

## Dependencies

Required packages (already in `.venv-3.12`):
- `playwright>=1.40.0`
- Python 3.10+

## See Also

- [StateExplorer Documentation](../../StateExplorer/docs/)
- [FSM Implementation Guide](../../StateExplorer/docs/guides/FSM_IMPLEMENTATION_GUIDE.md)
- [UI Testing Guide](../docs/UI_Testing_Guide.md)
