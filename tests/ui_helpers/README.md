# UI Helpers - Reference Data

**Status**: Code and documentation have been migrated to StateExplorer monorepo.

---

## ⚠️ Migration Notice

All UI discovery code, tests, and documentation have been **migrated to StateExplorer**.

### Migrated Components

**Code (100% migrated):**
- ~~`ui_mbt_discovery.py`~~ → `StateExplorer/packages/`
- ~~`test_*.py`~~ → `StateExplorer/tests/`
- ~~`discover_ui.py`~~ → Replaced by `aria-discover` CLI

**Documentation (reorganized & condensed):**
- ~~ACCESSIBILITY_TREE_STRATEGY.md~~ → `StateExplorer/docs/architecture/FINGERPRINTING_STRATEGY.md`
- ~~Architecting UI Test Resilience.md~~ → `StateExplorer/docs/architecture/RESILIENCE_PRINCIPLES.md`
- ~~Hybrid_MBT.md~~ → `StateExplorer/docs/architecture/FSM_VS_POM.md` + `MODEL_BASED_TESTING.md`
- ~~README.md (old)~~ → `StateExplorer/docs/guides/GETTING_STARTED.md`

**Historical records:**
- PHASE_*.md → `archive/`
- NEXT_STEPS.md, PRIORITY_1_FIXES.md → `archive/`

---

## 📁 What Remains Here

### Reference Data & Output Files

- **`fsm_graph.json`** (360KB) - FSM graph from NEW tool (aria-discover)


### Historical Archive

- **`archive/`** - Historical milestone documents and notes
  - `PHASE_1_COMPLETE.md`
  - `PHASE_2_COMPLETE.md`
  - `NEXT_STEPS.md`
  - `PRIORITY_1_FIXES.md`
  - etc.

---

## 🚀 Using the New Tool

### Installation

```bash
cd /path/to/StateExplorer

# Install packages
pip install -e packages/model-resilience-core
pip install -e packages/aria-state-mapper

# Install Playwright browsers
playwright install chromium
```

### Running Discovery

```bash
# New CLI command (replaces python ui_mbt_discovery.py)
aria-discover \
  --url http://127.0.0.1:3000 \
  --username admin \
  --password admin \
  --output fsm_graph.json
```

### Documentation

All documentation is now in StateExplorer:

- **Quick Start**: `StateExplorer/docs/guides/GETTING_STARTED.md`
- **Migration Guide**: `StateExplorer/docs/MIGRATION_GUIDE.md`
- **Architecture**: `StateExplorer/docs/architecture/`
- **Research**: `StateExplorer/docs/research/`

---

## 📊 Comparison: Old vs New Tool

### Graph Output Comparison

| Metric | Old Tool | New Tool (aria-discover) | Improvement |
|--------|----------|--------------------------|-------------|
| **States** | 32 | 10 | 3x fewer (more logical) |
| **Transitions** | 58 | 58 | Same coverage |
| **File Size** | 833 KB | 215 KB | 4x smaller |
| **Fingerprinting** | DOM-based | Accessibility tree | More resilient |
| **State Identity** | URL + DOM hash | ARIA + semantic | Behavioral focus |

### Key Improvements

✅ **Accessibility-first fingerprinting** (resilient to CSS/DOM changes)  
✅ **ARIA state differentiation** (menu open/closed as separate states)  
✅ **Weighted fuzzy matching** (semantic 60%, functional 25%, etc.)  
✅ **Modular architecture** (reusable core, extensible for mobile)  
✅ **Professional CLI** (installed command, not script)

---

## 📦 StateExplorer Package Structure

```
StateExplorer/
├── packages/
│   ├── model-resilience-core/     # Platform-agnostic algorithms
│   │   ├── models/                 # UIState, StateTransition
│   │   ├── fingerprinting/         # StateFingerprinter
│   │   └── matching/               # StateComparer
│   │
│   └── aria-state-mapper/         # Playwright implementation
│       ├── discovery/              # UIStateMachineDiscovery
│       ├── playwright_integration/ # Async wrappers
│       └── cli.py                  # aria-discover command
│
├── docs/                          # Reorganized documentation
│   ├── architecture/
│   ├── guides/
│   └── research/
│
├── tests/                         # Pytest test suite
└── examples/                      # Working code samples
```

---

## 🗂️ Legacy File Retention

These files are kept for **reference and comparison**:

1. **`fsm_graph.json`** - Latest output from new tool
2. **`fsm_graph_old.json`** - Output from original tool for validation
3. **`ui_map.json`**, **`seed_test.json`** - Seed data that may still be useful
4. **`archive/`** - Historical project documentation

---

## 📚 Further Reading

- StateExplorer main README: `../../StateExplorer/README.md`
- Getting started guide: `../../StateExplorer/docs/guides/GETTING_STARTED.md`
- Migration guide: `../../StateExplorer/docs/MIGRATION_GUIDE.md`
- Documentation index: `../../StateExplorer/docs/DOCUMENTATION_INDEX.md`

---

**Last Updated**: December 13, 2025  
**Migration Status**: ✅ Complete (100%)

