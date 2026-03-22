# How to Automate GUI Testing with FSM-Based UI Discovery

| Field | Value |
| --- | --- |
| Audience | Test engineers, device class authors |
| Prerequisites | Boardfarm3 installed, Playwright browsers, StateExplorer packages |
| Time estimate | 30 min initial discovery; 5 min incremental refresh |

## Overview

Boardfarm's GUI testing uses a **Finite State Machine (FSM)** approach powered by the [StateExplorer](https://github.com/alottabits/StateExplorer) monorepo. Instead of traditional page-object selectors, the framework
discovers UI states through **accessibility tree fingerprinting** and builds a state graph that tests navigate programmatically.

This guide covers the end-to-end workflow — from discovering a web application's UI structure to writing device-independent BDD scenarios that work across different implementations.

## Why FSM Over Page Object Model

The traditional Page Object Model (POM) maps pages to CSS/XPath selectors.
When the UI changes, selectors break and tests fail even though the business
logic is unchanged.

The FSM approach identifies states by **what they are** (accessibility tree
structure), not **how they look** (CSS classes). This provides resilience to
UI changes through multi-dimensional fingerprinting:

| Dimension | Weight | What it captures |
|---|---|---|
| Semantic | 60% | Accessibility tree structure (roles, names, hierarchy) |
| Functional | 25% | Interactive elements (buttons, inputs, links) |
| Structural | 10% | DOM nesting depth and patterns |
| Content | 4% | Visible text content |
| Style | 1% | Visual layout cues |

States with ≥80% fingerprint similarity are treated as the same state,
absorbing minor UI changes automatically.

## Architecture

### StateExplorer Packages

| Package | Purpose |
|---|---|
| `model-resilience-core` | Platform-agnostic state fingerprinting and weighted fuzzy matching |
| `aria-state-mapper` | Web UI state mapping via Playwright and ARIA accessibility trees |
| `app-state-mapper` | Native app state mapping via Appium (future) |

```
┌─────────────────────────────────────┐
│         Boardfarm Tests             │
│  (BDD scenarios, step definitions)  │
└──────────────┬──────────────────────┘
               │
      ┌────────▼────────┐
      │ FsmGuiComponent  │  Navigates states, finds elements
      └────────┬────────┘
               │
      ┌────────▼────────┐     ┌──────────────────┐
      │ AriaStateMapper │     │ AppStateMapper   │
      │  (Playwright)   │     │   (Appium)       │
      └────────┬────────┘     └───────┬──────────┘
               │                      │
               └──────────┬───────────┘
                          │
                 ┌────────▼─────────┐
                 │ModelResilienceCore│
                 │ (Fingerprinting) │
                 └──────────────────┘
```

### Five-Layer Mapping

GUI testing follows the [five-layer architecture](boardfarm-five-layer-model.md)
and the [Boardfarm Test Automation Architecture](../Boardfarm%20Test%20Automation%20Architecture.md):

| Layer                      | GUI Testing Role                                                 |
| -------------------------- | ---------------------------------------------------------------- |
| **0 System Use Cases**     | Requirements involving a GUI workflow                            |
| **1 Test Definitions**     | Gherkin scenarios — no selectors, no interface details           |
| **2 Step Defs / Keywords** | Thin wrappers calling **Boardfarm use cases** with `via="gui"`   |
| **3 Boardfarm Use Cases**  | Business logic; delegates to `device.gui.fsm.*` when `via="gui"` |
| **4 Device Templates**     | `FsmGuiComponent` — the stable GUI interface contract            |

Step definitions **never** call device methods directly. They call use cases,
and the `via` parameter selects which device interface the use case operates
through. This keeps test logic portable and avoids the anti-pattern of
embedding device-specific calls in step definitions.

### Output Artifact

Discovery produces a single **FSM graph JSON file** containing:

- **Nodes** — UI states with accessibility-tree fingerprints, element
  descriptors, and verification logic
- **Edges** — transitions between states with action type, trigger locators,
  and action data
- **Statistics** — state/transition counts, coverage metrics

```json
{
  "base_url": "http://localhost:3000",
  "graph_type": "fsm_mbt",
  "nodes": [
    {
      "id": "V_LOGIN_FORM_EMPTY",
      "state_type": "form",
      "fingerprint": { ... },
      "element_descriptors": [ ... ]
    }
  ],
  "edges": [
    {
      "source": "V_LOGIN_FORM_EMPTY",
      "target": "V_OVERVIEW_PAGE",
      "action_type": "fill_form",
      "trigger_locators": { ... }
    }
  ],
  "statistics": {
    "state_count": 46,
    "transition_count": 125
  }
}
```

## Prerequisites

- Python 3.10+ with a boardfarm-bdd virtual environment
- StateExplorer packages installed (assumes the
  [StateExplorer](https://github.com/alottabits/StateExplorer) repo is cloned
  as a sibling directory):

```bash
pip install -e ../StateExplorer/packages/model-resilience-core
pip install -e ../StateExplorer/packages/aria-state-mapper
playwright install chromium firefox
pip install -e ".[gui]"
```

## Steps

### 1. Fresh Automated Discovery

Run `aria-discover` against the target web application to capture base
states through accessibility-tree-driven crawling:

```bash
aria-discover \
  --url http://<device url> \
  --username admin \
  --password admin \
  --max-states 20 \
  --output bf_config/gui_artifacts/<device>/fsm_graph_fresh.json
```

The tool launches a browser, logs in, and explores the UI using depth-first
or breadth-first search. Each page/view is fingerprinted via its accessibility
tree. Forms are filled and submitted, safe buttons are clicked, and modals
are detected.

**Typical result:** 10–15 states, 40–60 transitions, covering page-level
navigation (60–70% of the UI).

### 2. Manual Recording (Complex Interactions)

Automated discovery cannot reach states hidden behind dropdowns, multi-step
forms, or overlay dialogs. The manual recording tool lets you walk through
these flows while the system captures each state:

```bash
python tools/manual_fsm_augmentation.py \
  --url http://<device url> \
  --input bf_config/gui_artifacts/<device>/fsm_graph_fresh.json \
  --output bf_config/gui_artifacts/<device>/fsm_graph_augmented.json
```

A browser opens. Interact with it normally, then press `s` + Enter in the
terminal to snapshot the current state. Press `q` + Enter to quit and save.

The tool merges your manually captured states into the existing graph with
**fingerprint-based deduplication** — if a manually captured state matches
an existing one at ≥80% similarity, it is recognised as a duplicate and
skipped.

**Typical result:** 20–25 states, 65–70 transitions (base + complex
interactions like dropdowns, overlays, confirmation dialogs).

### 3. Incremental Discovery

Re-run automated discovery seeded with the augmented graph. The tool starts
from known states and explores outward, discovering variations and deeper
paths:

```bash
aria-discover \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --seed-graph bf_config/gui_artifacts/<device>/fsm_graph_augmented.json \
  --output bf_config/gui_artifacts/<device>/fsm_graph_expanded.json \
  --max-states 50
```

**Typical result:** 40–50 states, 100–150 transitions, ≥90% UI coverage.

### 4. Register States in the Device Class

Map discovered FSM state IDs to semantic names used by the device class:

```python
STATE_REGISTRY = {
    "login": "V_LOGIN_FORM_EMPTY",
    "overview": "V_OVERVIEW_PAGE",
    "devices": "V_DEVICES",
    "devices_dropdown_open": "V_STATE_003",
    "device_details": "V_STATE_006",
    "reboot_overlay": "V_STATE_007",
}
```

The `FsmGuiComponent` uses this registry to navigate between states and
locate elements within them.

### 5. Write BDD Scenarios

Scenarios describe **what** is tested, not **how** or **via which interface**.
The `via GUI` qualifier signals that this test exercises the GUI path:

```gherkin
Feature: Device Management
  As an ISP operator
  I want to manage customer devices through the web UI

  Scenario: Reboot a device via ACS GUI
    Given a CPE is online and provisioned
    When the operator reboots the CPE via the ACS GUI
    Then the CPE should reboot successfully
```

### 6. Implement Boardfarm Use Cases (Layer 3)

The use case contains the FSM navigation logic and accepts a `via`
parameter. When `via="gui"`, it delegates to `device.gui.fsm.*`:

```python
# boardfarm3/use_cases/acs.py
from typing import Literal

InterfaceType = Literal["nbi", "gui"]

def reboot_device(
    acs: ACS,
    cpe: CPE,
    via: InterfaceType = "nbi",
) -> bool:
    """Reboot CPE via ACS.

    .. hint:: This Use Case implements statements from the test suite such as:

        - the operator reboots the CPE via the ACS
        - the operator reboots the CPE via the ACS GUI

    :param via: "nbi" for REST API (default), "gui" for web interface
    """
    if via == "gui":
        acs.gui.fsm.navigate_to_state("devices")
        acs.gui.search_device(cpe.sw.cpe_id)
        acs.gui.fsm.navigate_to_state("device_details")
        element = acs.gui.fsm.find_element(role="button", name="Reboot")
        element.click()
        acs.gui.fsm.navigate_to_state("reboot_overlay")
        confirm = acs.gui.fsm.find_element(role="button", name="Commit")
        confirm.click()
        return True
    return acs.nbi.Reboot(cpe_id=cpe.sw.cpe_id)
```

### 7. Implement Step Definitions (Layer 2)

Step definitions are **thin wrappers** — they call use cases, not device
methods:

```python
# tests/step_defs/acs_steps.py
from boardfarm3.use_cases import acs as acs_use_cases

@when("the operator reboots the CPE via the ACS GUI")
def operator_reboots_via_gui(acs, cpe, bf_context):
    """Reboot via GUI — delegates to use_case with via='gui'."""
    result = acs_use_cases.reboot_device(acs, cpe, via="gui")
    assert result, "Failed to initiate reboot via GUI"
    print("✓ Reboot initiated via ACS GUI")
```

This pattern means the same use case can be tested through different
interfaces without changing the step definition logic:

```python
@when("the operator reboots the CPE via the ACS")
def operator_reboots_via_nbi(acs, cpe, bf_context):
    """Reboot via NBI (default) — same use_case, different interface."""
    result = acs_use_cases.reboot_device(acs, cpe)  # via="nbi" by default
    assert result, "Failed to initiate reboot via NBI"
    print("✓ Reboot initiated via ACS NBI")
```

## Testing Modes

The FSM approach supports three testing modes:

| Mode | Purpose | How |
|---|---|---|
| **Functional** | Verify business goals (reboot, configure) | Navigate states, interact, assert outcomes |
| **Navigation** | Validate graph structure and UI resilience | Traverse all states/transitions, verify reachability |
| **Visual Regression** | Detect unintended UI changes | Compare screenshots at known states against baselines |

## Verification

After completing the three-stage pipeline:

```bash
# Compare growth across stages
for f in fsm_graph_fresh.json fsm_graph_augmented.json fsm_graph_expanded.json; do
  echo "$f: $(jq '.nodes | length' $f) states, $(jq '.edges | length' $f) transitions"
done

# All states should have fingerprints
jq '[.nodes[] | select(.fingerprint == null)] | length' fsm_graph_expanded.json
# Expected: 0

# All transitions should have action metadata
jq '[.edges[] | select(.action_type == null)] | length' fsm_graph_expanded.json
# Expected: 0
```

## Maintenance

### When the UI Changes

1. Re-run incremental discovery seeded with the current graph:
   ```bash
   aria-discover --seed-graph fsm_graph_current.json \
     --output fsm_graph_updated.json
   ```
2. New states are added automatically; existing states are matched by
   fingerprint similarity.
3. Update the `STATE_REGISTRY` only if new business-relevant states
   were discovered.

### CI/CD Integration

```bash
aria-discover --url http://staging.example.com \
  --seed-graph fsm_graph_production.json \
  --output fsm_graph_staging_$(date +%Y%m%d).json \
  --max-states 100
```

Run nightly to detect UI drift early. Compare state counts and flag
regressions.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Login fails during discovery | Credentials or URL incorrect | Verify with `curl -X POST http://localhost:3000/login` |
| No states discovered | App not running or network unreachable | Check `curl http://localhost:3000` |
| Many duplicate warnings in Stage 3 | Expected for stable UIs | Not a problem — fingerprint deduplication is working correctly |
| Browser doesn't open | Playwright not installed | Run `playwright install chromium firefox` |
| `aria-discover` command not found | Package not installed | Run `pip install -e ../StateExplorer/packages/aria-state-mapper` (see [Prerequisites](#prerequisites)) |

## Artifact Management

```
bf_config/gui_artifacts/<device>/
├── fsm_graph_fresh.json        # Stage 1: automated base states
├── fsm_graph_augmented.json    # Stage 2: + manual complex interactions
└── fsm_graph_expanded.json     # Stage 3: comprehensive coverage (commit this)
```

Commit the final expanded graph. Intermediate graphs can be regenerated.

## Next Steps

- [Boardfarm Five-Layer Model](boardfarm-five-layer-model.md) — architecture
  context for how GUI testing fits the framework
- [CPE Docker: ACS GUI Testing](../examples/cpe-docker/ui-testing-guide.md) —
  ACS-specific application of this guide with GenieACS
- [StateExplorer Complete Workflow Guide](https://github.com/alottabits/StateExplorer/blob/main/COMPLETE_WORKFLOW_GUIDE.md) —
  detailed three-stage pipeline reference
