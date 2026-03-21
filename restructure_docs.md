# Documentation Restructuring Plan

> **Purpose:** Reorganize the `docs/` directory and rewrite the root `README.md`
> to reflect the three application domains demonstrated by this repository and
> the AI-assisted development workflow.
>
> **Date:** 2026-03-20
> **Status:** Implemented — 2026-03-20

---

## 1. Problem Statement

The current documentation has several issues:

| Issue | Detail |
|---|---|
| **Flat directory** | ~43 files in `docs/` with no organizational structure beyond `adr/`, `robot/`, and `tests/` |
| **Outdated README** | References a "four-layer" architecture (should be five), only describes the CPE testbed, links to non-existent `docs/use_case_architecture.md` |
| **Missing domains** | No mention of SD-WAN testing or physical device testing in the README despite major bodies of work |
| **Superseded docs coexist** | Old implementation plans sit alongside their as-built replacements with no distinction |
| **Inconsistent naming** | Mix of spaces (`Testbed Network Topology.md`), underscores (`ACS_URL_discovery.md`), and kebab-case (`linux-sdwan-router-design.md`) |
| **No navigation** | No documentation index; newcomers must scan 43 files to find what they need |
| **No process context** | The AI-assisted workflow (use cases → standardized API → AI generation) is not documented |

---

## 2. Repository Purpose — Reframed

This repository demonstrates how to utilize **Boardfarm** as a standardized test interface to configure testbeds and automate testing. It provides three concrete application examples and shows the end-to-end process of:

1. **Define system behavior** with system-level use cases (Markdown in `requirements/`)
2. **Standardize the test interface API** to all testbed components (`boardfarm3.use_cases`)
3. **Utilize AI** to generate BDD scenarios, automated test scripts, test unit tests, and execute the test suite

### Three Application Domains

| # | Application | Compose File | Description |
|---|---|---|---|
| 1 | **Dockerized CPE Testing** | `raikou/docker-compose.yaml` | Full TR-069/ACS testbed with containerized PrplOS CPE, SIP voice, DHCP, LAN clients |
| 2 | **Physical CPE Testing** | `raikou/docker-compose-openwrt.yaml` | Same services but CPE is a physical Raspberry Pi (OpenWrt/prplOS); USB-Ethernet dongles bridge host to Raikou OVS |
| 3 | **Dockerized SD-WAN Testing** | `raikou/docker-compose-sdwan.yaml` | Digital twin testbed: Linux SD-WAN router, dual-WAN traffic controllers, QoE client (Playwright), application services (HTTPS/H3/WSS), IPsec hub |

### Dual Framework Demonstration

Each application domain demonstrates test implementation in both **pytest-bdd** (`tests/`) and **Robot Framework** (`robot/`), sharing `boardfarm3.use_cases` as the single source of truth.

---

## 3. Proposed Directory Structure

```
docs/
├── index.md                              # Documentation hub / navigation page
│
├── architecture/                         # Cross-cutting architecture
│   ├── boardfarm-five-layer-model.md     # ← "Boardfarm Test Automation Architecture.md"
│   ├── use-case-template.md              # ← "Use Case Template (reflect the goal).md"
│   ├── configuration-cleanup.md          # ← "Configuration Cleanup Process.md"
│   └── log-collector.md                  # ← "Centralized_Log_Collector_Implementation.md"
│
├── adr/                                  # Architecture Decision Records (unchanged)
│   └── 0001-scope-to-digital-twin-phase-3.5.md
│
├── examples/                             # The three application domains
│   │
│   ├── cpe-docker/                       # Application 1: Dockerized CPE testing
│   │   ├── README.md                     # Overview, quick-start, testbed topology
│   │   ├── testbed-topology.md           # ← "Testbed Network Topology.md"
│   │   ├── acs-url-discovery.md          # ← "ACS_URL_discovery.md"
│   │   ├── genieacs-reboot-analysis.md   # ← "GenieACS_Reboot_Button_Analysis.md"
│   │   ├── sip-phone-configuration.md    # ← "sip_phone_configuration.md"
│   │   ├── ui-testing-guide.md           # ← "UI_Testing_Guide.md"
│   │   ├── log-locations.md              # ← "Locations of logs.md"
│   │   └── password-handling.md          # ← merged: default_password_investigation.md
│   │                                     #           + password_cleanup_analysis.md
│   │
│   ├── cpe-physical/                     # Application 2: Physical CPE + dockerized services
│   │   ├── README.md                     # Overview, quick-start, USB dongle setup
│   │   ├── raikou-physical-integration.md  # ← "Raikou_Physical_Interface_Integration.md"
│   │   ├── prplos-rpi-implementation.md  # ← "prplos_rpi_implementation_plan.md"
│   │   ├── prplos-rpi-build-guide.md     # ← "prplos_rpi_phase1_build_guide.md"
│   │   ├── prplos-rpi-console-api.md     # ← "prplos_rpi_console_api.md"
│   │   └── cpe-deviceclass-development.md  # ← "cpe_deviceclass_development_plan.md"
│   │
│   └── sdwan-digital-twin/              # Application 3: Dockerized SD-WAN testing
│       ├── README.md                     # Overview, quick-start, component map
│       ├── architecture.md               # ← "sdwan-testing-architecture.md"
│       ├── testbed-configuration.md      # ← "SDWAN_Testbed_Configuration.md"
│       ├── testbed-ca-setup.md           # ← "Testbed_CA_Setup.md"
│       ├── linux-sdwan-router.md         # ← "linux-sdwan-router-design.md"
│       ├── qoe-client.md                 # ← "qoe-client-design.md"
│       ├── application-services.md       # ← "application-services-design.md"
│       ├── traffic-management.md         # ← "Traffic_Management_Components_Architecture.md"
│       ├── app-router.md                 # ← "app-router-implementation.md"
│       ├── qoe-verification-brief.md     # ← "Technical Brief_ Automated QoE Verification.md"
│       ├── cross-vendor-api-analysis.md  # ← "cross-vendor sdwan API analysis.md"
│       └── future/                       # Retained designs for future work
│           ├── traffic-generator.md      # ← "TrafficGenerator_Implementation_Plan.md"
│           └── security-testing.md       # ← "security-testing-design.md"
│
├── frameworks/                           # Test framework guides
│   ├── pytest-bdd/
│   │   └── getting-started.md            # ← "docs/tests/getting_started.md"
│   └── robot-framework/
│       ├── getting-started.md            # ← "docs/robot/getting_started.md"
│       ├── best-practices.md             # ← "docs/robot/best_practices.md"
│       └── keyword-reference.md          # ← "docs/robot/keyword_reference.md"
│
├── historical/                           # Superseded docs (kept for git-blame reference)
│   ├── README.md                         # Explains these are superseded
│   ├── WAN_Edge_Appliance_testing.md
│   ├── LinuxSDWANRouter_Implementation_Plan.md
│   ├── QoE_Client_Implementation_Plan.md
│   └── Application_Services_Implementation_Plan.md
│
└── migration/                            # Completed internal migration/process docs
    ├── dual-framework-restructure.md     # ← "dual_framework_restructure_plan.md"
    ├── robot-keyword-migration.md        # ← "robot_keyword_migration_plan.md"
    └── step-migration-guide.md           # ← "step_migration_guide.md"
```

### File Move Summary

Total: 43 source files → organized into 8 subdirectories.

| Source (current) | Destination | Action |
|---|---|---|
| `Boardfarm Test Automation Architecture.md` | `architecture/boardfarm-five-layer-model.md` | Move + rename |
| `Use Case Template (reflect the goal).md` | `architecture/use-case-template.md` | Move + rename |
| `Configuration Cleanup Process.md` | `architecture/configuration-cleanup.md` | Move + rename |
| `Centralized_Log_Collector_Implementation.md` | `architecture/log-collector.md` | Move + rename |
| `adr/0001-scope-to-digital-twin-phase-3.5.md` | `adr/0001-scope-to-digital-twin-phase-3.5.md` | Unchanged |
| `Testbed Network Topology.md` | `examples/cpe-docker/testbed-topology.md` | Move + rename |
| `ACS_URL_discovery.md` | `examples/cpe-docker/acs-url-discovery.md` | Move + rename |
| `GenieACS_Reboot_Button_Analysis.md` | `examples/cpe-docker/genieacs-reboot-analysis.md` | Move + rename |
| `sip_phone_configuration.md` | `examples/cpe-docker/sip-phone-configuration.md` | Move + rename |
| `UI_Testing_Guide.md` | `examples/cpe-docker/ui-testing-guide.md` | Move + rename |
| `Locations of logs.md` | `examples/cpe-docker/log-locations.md` | Move + rename |
| `default_password_investigation.md` + `password_cleanup_analysis.md` | `examples/cpe-docker/password-handling.md` | Merge + rename |
| `Raikou_Physical_Interface_Integration.md` | `examples/cpe-physical/raikou-physical-integration.md` | Move + rename |
| `prplos_rpi_implementation_plan.md` | `examples/cpe-physical/prplos-rpi-implementation.md` | Move + rename |
| `prplos_rpi_phase1_build_guide.md` | `examples/cpe-physical/prplos-rpi-build-guide.md` | Move + rename |
| `prplos_rpi_console_api.md` | `examples/cpe-physical/prplos-rpi-console-api.md` | Move + rename |
| `cpe_deviceclass_development_plan.md` | `examples/cpe-physical/cpe-deviceclass-development.md` | Move + rename |
| `sdwan-testing-architecture.md` | `examples/sdwan-digital-twin/architecture.md` | Move |
| `SDWAN_Testbed_Configuration.md` | `examples/sdwan-digital-twin/testbed-configuration.md` | Move + rename |
| `Testbed_CA_Setup.md` | `examples/sdwan-digital-twin/testbed-ca-setup.md` | Move + rename |
| `linux-sdwan-router-design.md` | `examples/sdwan-digital-twin/linux-sdwan-router.md` | Move + rename |
| `qoe-client-design.md` | `examples/sdwan-digital-twin/qoe-client.md` | Move + rename |
| `application-services-design.md` | `examples/sdwan-digital-twin/application-services.md` | Move + rename |
| `Traffic_Management_Components_Architecture.md` | `examples/sdwan-digital-twin/traffic-management.md` | Move + rename |
| `app-router-implementation.md` | `examples/sdwan-digital-twin/app-router.md` | Move + rename |
| `Technical Brief_ Automated QoE Verification.md` | `examples/sdwan-digital-twin/qoe-verification-brief.md` | Move + rename |
| `cross-vendor sdwan API analysis.md` | `examples/sdwan-digital-twin/cross-vendor-api-analysis.md` | Move + rename |
| `TrafficGenerator_Implementation_Plan.md` | `examples/sdwan-digital-twin/future/traffic-generator.md` | Move + rename |
| `security-testing-design.md` | `examples/sdwan-digital-twin/future/security-testing.md` | Move + rename |
| `tests/getting_started.md` | `frameworks/pytest-bdd/getting-started.md` | Move + rename |
| `robot/getting_started.md` | `frameworks/robot-framework/getting-started.md` | Move + rename |
| `robot/best_practices.md` | `frameworks/robot-framework/best-practices.md` | Move + rename |
| `robot/keyword_reference.md` | `frameworks/robot-framework/keyword-reference.md` | Move + rename |
| `WAN_Edge_Appliance_testing.md` | `historical/WAN_Edge_Appliance_testing.md` | Move |
| `LinuxSDWANRouter_Implementation_Plan.md` | `historical/LinuxSDWANRouter_Implementation_Plan.md` | Move |
| `QoE_Client_Implementation_Plan.md` | `historical/QoE_Client_Implementation_Plan.md` | Move |
| `Application_Services_Implementation_Plan.md` | `historical/Application_Services_Implementation_Plan.md` | Move |
| `dual_framework_restructure_plan.md` | `migration/dual-framework-restructure.md` | Move + rename |
| `robot_keyword_migration_plan.md` | `migration/robot-keyword-migration.md` | Move + rename |
| `step_migration_guide.md` | `migration/step-migration-guide.md` | Move + rename |

---

## 4. New README.md Outline

The root `README.md` should be rewritten around the three application domains
and the AI-assisted process flow, rather than around the test frameworks.

### Proposed Sections

```
# Boardfarm BDD — Standardized Test Automation Examples

## 1. What This Repository Demonstrates
   Brief: three application domains, each showing how Boardfarm standardizes
   the test interface and testbed configuration.

## 2. Process Flow
   Three-step workflow with embedded Excalidraw diagram:
   1. Define system behavior with use cases (requirements/)
   2. Standardize the test interface API (boardfarm use_cases)
   3. Utilize AI to generate BDD scenarios, test scripts, unit tests, and execute
   
   References:
   - Excalidraw/process_template.svg (development & release process)
   - Excalidraw/software_architecture.svg (five-layer architecture)

## 3. Five-Layer Architecture
   Updated diagram (Layer 0–4), corrected from four-layer.
   Brief description with link to docs/architecture/boardfarm-five-layer-model.md.

## 4. Application Examples

   ### 4.1 Dockerized CPE Testing
   - What: TR-069/ACS, voice, GUI testing with fully containerized testbed
   - Compose: raikou/docker-compose.yaml
   - Use cases: UC-12347, UC-12348, UC-ACS-GUI-01
   - Quick start: docker compose up + pytest/bfrobot commands
   - Docs: docs/examples/cpe-docker/

   ### 4.2 Physical CPE Testing
   - What: Same services, but CPE is a physical Raspberry Pi
   - Compose: raikou/docker-compose-openwrt.yaml
   - Use cases: UC-12347, UC-12348 (same as dockerized, targeting physical CPE)
   - Quick start: physical setup + docker compose up
   - Docs: docs/examples/cpe-physical/

   ### 4.3 Dockerized SD-WAN Testing
   - What: Digital twin testbed for WAN edge appliance validation
   - Compose: raikou/docker-compose-sdwan.yaml
   - Use cases: UC-SDWAN-01 through UC-SDWAN-05
   - Quick start: docker compose up + pytest commands
   - Docs: docs/examples/sdwan-digital-twin/

## 5. Dual Framework Support
   Table: pytest-bdd vs Robot Framework (keep existing content, moved down).
   Both share boardfarm3.use_cases as single source of truth.

## 6. Quick Start
   Installation commands (keep existing).
   Per-application running commands.

## 7. Use Case → Test Mapping
   Table showing each requirement, which application it belongs to,
   and its feature file / robot suite.

## 8. Documentation Index
   Compact table linking to docs/index.md and key sections.

## 9. Acknowledgements
   Mike Vogel reference, Alistair Cockburn reference (keep existing).
```

### Use Case → Application Mapping Table

| Use Case | Application | Feature File | Robot Suite |
|---|---|---|---|
| UC-12347 Remote CPE Reboot | cpe-docker | `Remote CPE Reboot.feature` | `remote_cpe_reboot.robot` |
| UC-12348 User Makes a One-Way Call | cpe-docker | `UC-12348 User makes a one-way call.feature` | `user_makes_one_way_call.robot` |
| UC-ACS-GUI-01 ACS GUI Device Mgmt | cpe-docker | `ACS GUI Device Management.feature` | — |
| UC-SDWAN-01 WAN Failover | sdwan-digital-twin | `WAN Failover Maintains Application Continuity.feature` | — |
| UC-SDWAN-02 Remote Worker Cloud App | sdwan-digital-twin | — (planned) | — |
| UC-SDWAN-03 Video Conference QoE | sdwan-digital-twin | — (planned) | — |
| UC-SDWAN-04 Encrypted Overlay Tunnel | sdwan-digital-twin | — (planned) | — |
| UC-SDWAN-05 Tunnel Survives Failover | sdwan-digital-twin | — (planned) | — |

---

## 5. Excalidraw Diagrams

The process flow and architecture diagrams exist in two locations:

| Diagram | Source | Action |
|---|---|---|
| Development & Release Process | `reqmgt/Excalidraw/development_and_release_process.excalidraw` | Export SVG → `boardfarm-bdd/Excalidraw/` |
| Software Architecture | `reqmgt/Excalidraw/software_architecture.excalidraw` | Export SVG → `boardfarm-bdd/Excalidraw/` |
| Process Template | `boardfarm-bdd/Excalidraw/process_template.svg` | Already in repo |
| Software Architecture (local) | `boardfarm-bdd/Excalidraw/software_architecture.svg` | Already in repo |
| Dual-WAN Testbed Topology | `boardfarm-bdd/Excalidraw/dual-wan-testbed-topology.svg` | Already in repo |

**Decision needed:** Copy SVG exports from `reqmgt/` into `boardfarm-bdd/Excalidraw/` to
keep the repo self-contained, or reference them as external? Copying is recommended so the
repo stands alone.

%% please copy so the repo stands alone %%

---

## 6. New Documents to Create

| Document | Purpose | Content Source |
|---|---|---|
| `docs/index.md` | Documentation hub with categorized links to all docs | New — generated from directory structure |
| `docs/examples/cpe-docker/README.md` | Overview of CPE docker testbed, quick-start, topology reference | New — drawn from README sections + `Testbed Network Topology.md` |
| `docs/examples/cpe-physical/README.md` | Overview of physical CPE setup, USB dongles, RPi requirements | New — drawn from `Raikou_Physical_Interface_Integration.md` intro |
| `docs/examples/sdwan-digital-twin/README.md` | Overview of SD-WAN digital twin, component map, quick-start | New — drawn from `sdwan-testing-architecture.md` intro + `SDWAN_Testbed_Configuration.md` |
| `docs/historical/README.md` | Explains these documents are superseded and kept for reference | New — brief note |
| `docs/examples/cpe-docker/password-handling.md` | Merged password investigation + cleanup analysis | Merge of two existing docs |

---

## 7. Implementation Steps

| # | Task | Effort | Dependencies | Notes |
|---|---|---|---|---|
| 1 | **Create subdirectory structure** | Small | — | `mkdir -p` for all new directories |
| 2 | **Move and rename files** using `git mv` | Medium | Step 1 | Preserves git history; see §3 move table |
| 3 | **Merge password docs** into `password-handling.md` | Small | Step 2 | Combine `default_password_investigation.md` + `password_cleanup_analysis.md` |
| 4 | **Create `docs/index.md`** | Small | Step 2 | Categorized link table to all docs |
| 5 | **Create `examples/cpe-docker/README.md`** | Medium | Step 2 | Overview, topology, quick-start, use cases exercised |
| 6 | **Create `examples/cpe-physical/README.md`** | Medium | Step 2 | Overview, hardware requirements, USB setup |
| 7 | **Create `examples/sdwan-digital-twin/README.md`** | Medium | Step 2 | Overview, component map, quick-start |
| 8 | **Create `docs/historical/README.md`** | Small | Step 2 | Brief note explaining superseded status |
| 9 | **Rewrite root `README.md`** | Large | Steps 5–7 | Per outline in §4; three applications, process flow, five-layer arch |
| 10 | **Update all internal cross-references** | Large | Step 2 | Every doc that links to another doc needs path updates |
| 11 | **Update ADR-0001** document references | Small | Step 10 | New paths for all referenced docs |
| 12 | **Update `tests/README.md` and `robot/README.md`** | Small | Step 10 | Framework READMEs may link to moved docs |
| 13 | **Copy Excalidraw SVGs** from `reqmgt/` | Small | — | Process flow + software architecture diagrams |
| 14 | **Verify no broken links** | Medium | Step 10 | Grep for `.md)` references and validate |

### Suggested Execution Order

Steps 1–2 first (structural move), then 3–8 in parallel (new content), then 9 (README rewrite),
then 10–12 (cross-reference fixup), and finally 13–14 (diagrams + verification).

---

## 8. Decisions for Review

| # | Question | Recommendation | Impact |
|---|---|---|---|
| 1 | **Excalidraw diagrams:** Copy SVGs from `reqmgt/` or reference externally? | Copy into repo for self-containment | Small — one-time file copy |
| 2 | **Superseded docs:** Move to `historical/` or delete? Git history preserves either way. | Move to `historical/` — easier for occasional reference | Small |
| 3 | **Merge password docs:** Combine `default_password_investigation.md` + `password_cleanup_analysis.md`? | Yes — closely related, single reference is cleaner | Small |
| 4 | **Migration docs:** Archive alongside `historical/` or keep in separate `migration/`? | Keep separate — these are process docs, not superseded designs | None |
| 5 | **File naming convention:** Enforce kebab-case for all doc filenames? | Yes — consistent, URL-friendly, no escaping needed | Medium — affects all renames |
| 6 | **`docs/use_case_architecture.md`:** Currently referenced in README but doesn't exist. Remove link or create? | Remove — the `boardfarm-five-layer-model.md` replaces this intent | Small |

%% agree with all the recommendations %%

---

## 9. Out of Scope

The following are explicitly **not** part of this restructuring:

- Rewriting the content of existing documents (only moving/renaming and updating cross-references)
- Changes to source code, test files, or Raikou configurations
- Changes to `requirements/` directory structure
- Changes to `tests/` or `robot/` directory structure (their own READMEs will be updated with new doc links)
- Creating new use case documents or test scenarios
