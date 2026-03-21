# ACS GUI Testing — GenieACS

This document covers the ACS-specific application of the FSM-based UI testing
framework for the dockerized CPE testbed. For the generic guide covering the
discovery pipeline, architecture, and testing modes, see
[UI Testing Guide](../../architecture/ui-testing-guide.md).

## GenieACS UI Discovery

The GenieACS web interface runs on port 3000 inside the `acs` container.
UI discovery uses the [StateExplorer](https://github.com/alottabits/StateExplorer)
`aria-discover` CLI to build an FSM graph of the application.

### Stage 1 — Fresh Automated Discovery

```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

aria-discover \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --max-states 20 \
  --output bf_config/gui_artifacts/genieacs/fsm_graph_fresh.json
```

This captures 10–15 base states (login, overview, devices list, etc.)
covering page-level navigation.

### Stage 2 — Manual Recording

Complex interactions (search filter dropdowns, reboot confirmation overlays,
multi-step device provisioning) require manual capture:

```bash
python tools/manual_fsm_augmentation.py \
  --url http://localhost:3000 \
  --input bf_config/gui_artifacts/genieacs/fsm_graph_fresh.json \
  --output bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json
```

A browser opens. Interact normally, then press `s` + Enter in the terminal
to snapshot each state. Press `q` + Enter to save.

**GenieACS states to capture manually:**

- Search filter dropdown (open and closed)
- Filter type selection (Serial number, Product class, etc.)
- Device search results
- Device details page
- Reboot confirmation overlay
- Task pending / task completed views

### Stage 3 — Incremental Discovery

Expand coverage by re-running automated discovery seeded with the
augmented graph:

```bash
aria-discover \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --seed-graph bf_config/gui_artifacts/genieacs/fsm_graph_augmented.json \
  --output bf_config/gui_artifacts/genieacs/fsm_graph_expanded.json \
  --max-states 50
```

### Generated Artifact

```
bf_config/gui_artifacts/genieacs/
├── fsm_graph_fresh.json        # Stage 1 output (regeneratable)
├── fsm_graph_augmented.json    # Stage 2 output (regeneratable)
└── fsm_graph_expanded.json     # Final graph — commit this
```

Only `fsm_graph_expanded.json` needs to be committed. It contains all
discovered states with accessibility-tree fingerprints, element descriptors,
and transition metadata.

## ACS GUI Template

The ACS GUI template defines the standard interface for all ACS
implementations. It follows Boardfarm's compositional pattern — the ACS
device exposes a `.gui` component backed by an `FsmGuiComponent`:

```python
class AcsGuiTemplate(BaseGuiComponent):
    """Standard GUI interface for ACS devices."""

    def navigate_to_device_list(self): ...
    def navigate_to_admin_settings(self): ...
    def search_device(self, device_id: str): ...
    def select_device(self, device_id: str): ...
    def reboot_device(self): ...
    def delete_device(self): ...
    def get_device_parameter(self, parameter_path: str) -> str: ...
    def set_device_parameter(self, parameter_path: str, value: str): ...
```

## GenieACS Implementation

The GenieACS device class implements the template using FSM state navigation
instead of hard-coded selectors:

```python
class GenieAcsGui(AcsGuiTemplate):
    STATE_REGISTRY = {
        "login": "V_LOGIN_FORM_EMPTY",
        "overview": "V_OVERVIEW_PAGE",
        "devices": "V_DEVICES",
        "devices_dropdown_open": "V_STATE_003",
        "devices_filter_selected": "V_STATE_004",
        "device_search_results": "V_STATE_005",
        "device_details": "V_STATE_006",
        "reboot_overlay": "V_STATE_007",
        "reboot_pending": "V_STATE_008",
    }

    def __init__(self, device, **kwargs):
        super().__init__(
            device,
            base_url="http://genieacs:3000",
            fsm_graph="bf_config/gui_artifacts/genieacs/fsm_graph_expanded.json",
            state_registry=self.STATE_REGISTRY,
            **kwargs
        )

    def navigate_to_device_list(self):
        self.fsm.navigate_to_state("devices")

    def search_device(self, device_id: str):
        self.fsm.navigate_to_state("devices_dropdown_open")
        element = self.fsm.find_element(role="option", name="Serial number:")
        element.click()
        self.fsm.enter_text(device_id)

    def reboot_device(self):
        element = self.fsm.find_element(role="button", name="Reboot")
        element.click()
        self.fsm.navigate_to_state("reboot_overlay")
        confirm = self.fsm.find_element(role="button", name="Commit")
        confirm.click()
```

The composite device class assembles GUI and NBI components:

```python
class GenieAcsDevice:
    def __init__(self, **kwargs):
        self.gui = GenieAcsGui(self, **kwargs)
        self.nbi = GenieAcsNbi(self, **kwargs)
```

## Use Case: UC-ACS-GUI-01

The ACS GUI Device Management use case exercises the template through a BDD
scenario. Following the
[Boardfarm Test Automation Architecture](../../Boardfarm%20Test%20Automation%20Architecture.md),
step definitions call **Boardfarm use cases** with `via="gui"` — they never
call device methods directly:

```gherkin
Feature: ACS GUI Device Management (UC-ACS-GUI-01)

  Scenario: Reboot a device via ACS GUI
    Given a CPE is online and provisioned
    When the operator reboots the CPE via the ACS GUI
    Then the CPE should reboot successfully
```

Step definitions are thin wrappers delegating to use cases:

```python
# tests/step_defs/acs_steps.py
from boardfarm3.use_cases import acs as acs_use_cases

@when("the operator reboots the CPE via the ACS GUI")
def operator_reboots_via_gui(acs, cpe, bf_context):
    """Reboot via GUI — delegates to use_case with via='gui'."""
    result = acs_use_cases.reboot_device(acs, cpe, via="gui")
    assert result, "Failed to initiate reboot via ACS GUI"
    print("✓ Reboot initiated via ACS GUI")
```

The use case contains the FSM navigation logic:

```python
# boardfarm3/use_cases/acs.py
def reboot_device(acs: ACS, cpe: CPE, via: InterfaceType = "nbi") -> bool:
    if via == "gui":
        acs.gui.navigate_to_device_list()
        acs.gui.search_device(cpe.sw.cpe_id)
        acs.gui.reboot_device()
        return True
    return acs.nbi.Reboot(cpe_id=cpe.sw.cpe_id)
```

This pattern means the same reboot operation can be tested through NBI
(default) or GUI by changing only the `via` parameter — the step definition
logic stays the same.

## GenieACS-Specific Notes

**Login credentials:** The GenieACS container uses `admin:admin` as the
default. This matches the Boardfarm framework convention (see
[Password Handling](password-handling.md)).

**SPA routing:** GenieACS uses hash-based routing (`#!/overview`,
`#!/devices`). The FSM discovery tool handles hash navigation correctly —
state transitions include the URL fragment changes.

**Device parameter display:** GenieACS shows TR-069 parameters in a
tree/table view. The FSM graph captures the parameter view as a distinct
state, and `find_element(role="cell", ...)` locates specific parameter
values using accessibility tree traversal rather than brittle XPath.

**Graph refresh cadence:** Re-run incremental discovery after GenieACS
version upgrades to capture any UI changes. The fingerprint-based matching
absorbs minor changes automatically — only significant layout changes
require manual recording.

## Related Documentation

| Document | Description |
|---|---|
| [UI Testing Guide](../../architecture/ui-testing-guide.md) | Generic FSM-based guide: discovery pipeline, architecture, testing modes |
| [Boardfarm Five-Layer Model](../../architecture/boardfarm-five-layer-model.md) | How GUI testing maps to the five-layer architecture |
| [StateExplorer Workflow Guide](https://github.com/alottabits/StateExplorer/blob/main/COMPLETE_WORKFLOW_GUIDE.md) | Detailed three-stage discovery pipeline reference |
| [UC-ACS-GUI-01](../../../requirements/UC-ACS-GUI-01%20ACS%20GUI%20Device%20Management.md) | ACS GUI Device Management use case |
