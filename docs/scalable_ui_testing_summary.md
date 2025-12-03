# Summary: A Compositional Architecture for Scalable UI Testing

## The Architecture: The "Flat Name" Convention

This document summarizes a production-ready architecture for UI testing that is clean, maintainable, and deterministic.

### Core Architectural Principles
1.  **Generics in `lib`**: `boardfarm/lib` contains reusable components, like `BaseGuiComponent`.
2.  **Specifics in `devices`**: `boardfarm/devices` contains vendor-specific logic, like `GenieAcsGui`.
3.  **Decouple UI Artifacts**: The `gui` component is configured by two test suite artifacts:
    *   `selectors.yaml`: Maps names to UI elements.
    *   `navigation.yaml`: Maps a unique, descriptive "flat name" (e.g., `Path_Home_to_DeviceDetails_via_Search`) to a specific user journey.

## Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│ boardfarm/devices/acs.py                                  │
│  - GenieACS (Composite)                                   │
│  - GenieAcsGui (Specific Actions)                         │
│     - Inherits generic navigate_path() engine             │
└───────────────────────────────────────────────────────────┘
               ▲ Is configured by
               │
┌───────────────────────────────────────────────────────────┐
│ Test Suite Artifacts                                      │
│ - acs_selectors.yaml (Element locators)                   │
│ - acs_navigation.yaml (Named user paths)                  │
└───────────────────────────────────────────────────────────┘
               ▲ Referenced by
               │
┌───────────────────────────────────────────────────────────┐
│ BDD Scenario (.feature file)                              │
│ - "Given user navigates using path 'Path_..._via_Search'" │
└───────────────────────────────────────────────────────────┘
```

## Key Benefits

### ✅ Clarity and Determinism
- The BDD scenario explicitly states the exact user journey under test.
- Tests are stable and reproducible.

### ✅ Minimal Maintenance
- A change to a user journey only requires an update to its definition in the central `navigation.yaml` file. The BDD scenarios remain unchanged.

## Usage Example

### The BDD Scenario

The Gherkin step specifies the *intent* by referencing a unique path name.
```gherkin
Given the user navigates to the device details using path "Path_Home_to_DeviceDetails_via_Search"
```

### The Step Definition

The step definition passes the path name directly to the GUI component's engine.
```python
@given('... using path "{path_name}"')
def navigate_with_path(acs: GenieACS, path_name: str):
    gui = acs.init_gui(...)
    gui.navigate_path(path_name)
```
