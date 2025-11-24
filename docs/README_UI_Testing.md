# GenieACS UI Testing Documentation - Index

## Overview

This directory contains documentation for implementing UI-based testing for GenieACS while minimizing maintenance burden and maximizing portability.

## Recommended Approach: Test-Layer UI Abstraction

The recommended approach keeps UI specifics in the test layer (not in boardfarm framework) using YAML configuration files for selectors. This provides:
- **Minimal maintenance** - Update YAML configs, not Python code
- **Maximum portability** - Support multiple GenieACS versions
- **Clean architecture** - Framework stays stable, tests stay flexible

## Core Documentation

### 1. [scalable_ui_testing_summary.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/scalable_ui_testing_summary.md) ⭐ **START HERE**
Quick reference and overview of the scalable UI testing approach.

**What it covers:**
- Architecture overview
- Key benefits
- Quick start guide
- Best practices

**When to read:** First document to understand the approach

---

### 2. [scalable_ui_testing_approach.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/scalable_ui_testing_approach.md)
Detailed architecture and strategy document.

**What it covers:**
- Complete architecture explanation
- Layer-by-layer breakdown
- Version management strategies
- Migration path from other approaches

**When to read:** When you need detailed understanding of the architecture

---

### 3. [scalable_ui_testing_example.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/scalable_ui_testing_example.md)
Complete working example with code.

**What it covers:**
- Step-by-step implementation
- Fixture setup
- Step definition examples
- Selector configuration examples

**When to read:** When you're ready to implement

---

## Supporting Documentation

### 4. [automated_ui_maintenance_strategy.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/automated_ui_maintenance_strategy.md)
Automation tools and strategies for maintaining UI tests.

**What it covers:**
- Automated navigation discovery
- Change detection system
- Automated POM generation
- CI/CD integration

**When to read:** After implementing basic UI tests, when you want to automate maintenance

---

### 5. [ui_discovery_quick_start.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/ui_discovery_quick_start.md)
Quick start guide for the UI discovery tool.

**What it covers:**
- Tool installation
- Running discovery
- Generating selector configs
- Troubleshooting

**When to read:** When you want to use the automated discovery tool

---

### 6. [ui_discovery_toolkit.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/ui_discovery_toolkit.md)
Manual UI discovery tools and techniques.

**What it covers:**
- Browser console scripts
- Manual element discovery
- Selector testing
- Best practices for selectors

**When to read:** When you need to manually discover or verify selectors

---

## Reference Documentation

### 7. [GenieACS_Reboot_Button_Analysis.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/GenieACS_Reboot_Button_Analysis.md)
Technical analysis of GenieACS reboot functionality.

**What it covers:**
- Reboot flow via NBI API
- TR-069 protocol details
- Implementation in boardfarm

**When to read:** When you need to understand the NBI reboot implementation

---

## Implementation Files

### Created Files

```
boardfarm-bdd/
├── docs/                                    # Documentation (you are here)
├── tests/
│   └── ui_helpers/
│       ├── __init__.py                      # Package initialization
│       ├── acs_ui_helpers.py                # UI helper class
│       └── acs_ui_selectors.yaml            # Selector configuration
└── tools/
    └── ui_discovery_complete.py             # Automated discovery tool
```

---

## Quick Start Guide

### For New Users

1. **Read** [scalable_ui_testing_summary.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/scalable_ui_testing_summary.md)
2. **Review** [scalable_ui_testing_example.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/scalable_ui_testing_example.md)
3. **Implement** using the example code
4. **Automate** using [ui_discovery_quick_start.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/ui_discovery_quick_start.md)

### For Maintenance

1. **Update selectors** in `tests/ui_helpers/acs_ui_selectors.yaml`
2. **Run discovery** to auto-generate configs
3. **Test** with your scenarios

---

## Key Concepts

### Test-Layer UI Abstraction

```
┌─────────────────────────────────────┐
│ Boardfarm Framework                 │
│ - NBI methods only                  │
│ - No UI code                        │
└─────────────────────────────────────┘
              ▲
              │ Uses
              │
┌─────────────────────────────────────┐
│ Test Layer                          │
│ - UI helpers (Python)               │
│ - Selectors (YAML)                  │
│ - Step definitions                  │
└─────────────────────────────────────┘
```

### YAML-Based Selectors

```yaml
device_details:
  reboot_button:
    by: "css_selector"
    selector: "button[title='Reboot']"
```

**Benefits:**
- Easy to update (no code changes)
- Version-specific configs
- Human-readable

### UI Helpers

```python
@when("operator initiates reboot via UI")
def step(acs_ui_helpers, cpe):
    acs_ui_helpers.login()
    acs_ui_helpers.navigate_to_device(cpe_id)
    acs_ui_helpers.click_reboot_button()
```

**Benefits:**
- Reusable across scenarios
- Loads selectors from YAML
- Easy to test independently

---

## Frequently Asked Questions

### Q: Why not put UI methods in the device class?

**A:** UI elements change frequently. Putting UI code in the framework creates high maintenance burden and poor portability. Keeping UI in the test layer allows easy updates without framework changes.

### Q: How do I support multiple GenieACS versions?

**A:** Create version-specific YAML configs:
- `acs_ui_selectors.yaml` (default)
- `acs_ui_selectors_v1.2.8.yaml`
- `acs_ui_selectors_v1.3.0.yaml`

### Q: What happens when the UI changes?

**A:** Just update the YAML file - no code changes needed!

### Q: Can I automate selector discovery?

**A:** Yes! Use `tools/ui_discovery_complete.py` to automatically discover UI elements and generate selector configs.

---

## Related Documentation

- [Testbed Network Topology.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/Testbed%20Network%20Topology.md) - Network setup
- [Configuration Cleanup Process.md](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/docs/Configuration%20Cleanup%20Process.md) - Test cleanup

---

## Changelog

### 2025-11-24
- ✅ Created scalable UI testing approach
- ✅ Implemented test-layer UI abstraction
- ✅ Created YAML-based selector configuration
- ✅ Removed outdated dual-method approach
- ✅ Added automated discovery tools

---

## Contributing

When updating UI tests:

1. **Update selectors** in YAML files (not code)
2. **Test changes** with actual GenieACS instance
3. **Document** version-specific changes
4. **Run discovery** tool to verify selectors

---

## Support

For questions or issues:
1. Review the documentation in order listed above
2. Check the example implementations
3. Use the discovery tool to verify selectors
4. Consult the team

---

**Last Updated:** 2025-11-24
