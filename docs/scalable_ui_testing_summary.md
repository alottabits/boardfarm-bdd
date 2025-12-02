# Summary: A Compositional Architecture for Scalable UI Testing

## The Architecture: Composition by Interface

This document summarizes a production-ready architecture for testing devices. It uses a compositional pattern that is clean, maintainable, and consistent with the project's structure.

### Core Architectural Principles
1.  **Generics in `lib`**: The `boardfarm/lib` directory contains reusable, generic components, like `BaseGuiComponent` in its own file (`base_gui_component.py`). `gui_helper.py` remains as the WebDriver factory.
2.  **Specifics in `devices`**: The `boardfarm/devices` directory contains all vendor-specific logic. A device file (e.g., `acs.py`) defines its specific components (`AcsNbi`, `AcsGui`) and assembles them into a final composite device class.
3.  **Decouple UI Selectors**: The `gui` component is always configured by a `selectors.yaml` file from the test suite.

## Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│ boardfarm/devices/acs.py                                  │
│                                                           │
│  ┌──────────────────┐  ┌────────────────┐  ┌───────────┐  │
│  │ GenieACS (Device)├──►│ GenieAcsNbi  ├──►│ NbiApi    │  │
│  │ - .nbi           │  │ (Specific)   │  │ (Template)│  │
│  │ - .gui           │  └────────────────┘  └───────────┘  │
│  │ - init_gui()     │  ┌────────────────┐  ┌───────────┐  │
│  └──────────────────┘  │ GenieAcsGui  ├──►│ BaseGui   │  │
│                        │ (Specific)   │  │ Component │  │
│                        └────────────────┘  └───────────┘  │
└───────────────────────────────────────────────────────────┘
               ▲ Is configured by
               │
┌───────────────────────────────────────────────────────────┐
│ Test Suite Artifact (acs_selectors.yaml)                  │
└───────────────────────────────────────────────────────────┘
```

## Key Benefits

### ✅ Clarity and Consistency
- The code is self-documenting (`acs.nbi.Reboot()`).
- The structure is consistent: `lib` is for generics, `devices` is for specifics.

### ✅ Minimal Maintenance
- UI changes only require editing the `selectors.yaml` test artifact.

### ✅ Maximum Portability
- Support multiple UI versions by creating different YAML files.

## Usage Example

### The Composed Device Class in `devices`

```python
# In boardfarm/boardfarm3/devices/acs.py
class GenieAcsNbi(LinuxDevice, ACS): # Specific NBI implementation
    def Reboot(self, ...): # ...

class GenieAcsGui(BaseGuiComponent): # Specific GUI actions, inherits from BaseGuiComponent
    def login(self): # ...

class GenieACS(BoardfarmDevice): # The composite device
    def __init__(self, ...):
        self.nbi = GenieAcsNbi(...)
        self.gui: GenieAcsGui | None = None

    def init_gui(self, selector_file: str) -> GenieAcsGui:
        # ... factory logic ...
```

### The Step Definition Consumer

```python
# In boardfarm-bdd/tests/step_defs/some_steps.py
@when("operator reboots via UI")
def step(acs: GenieACS):
    gui = acs.init_gui(selector_file="path/to/selectors.yaml")
    gui.click_reboot_button()
```

## Architectural Rationale: Why This Structure?

This model provides the best of all worlds:
-   **Cohesion**: All code for a specific device is co-located in one file.
-   **Low Coupling**: The most volatile part of UI testing—the selectors—is completely decoupled from the framework.
-   **Clarity**: The separation between the WebDriver factory (`GuiHelper`) and the page interaction logic (`BaseGuiComponent`) is clear.
-   **Consistency**: The pattern aligns perfectly with the existing separation of `lib` and `devices` in the `boardfarm` project.

This makes it the most logical, scalable, and maintainable solution.
