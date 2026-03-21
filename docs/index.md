# Documentation Index

This page provides a categorized index of all documentation in the
boardfarm-bdd repository. For a high-level overview, see the
[root README](../README.md).

---

## Architecture

Cross-cutting architecture and conventions shared by all application examples.

| Document | Description |
|---|---|
| [Five-Layer Model](architecture/boardfarm-five-layer-model.md) | Boardfarm test automation architecture — five layers from system use cases to device templates |
| [Use Case Template](architecture/use-case-template.md) | Template for writing system-level use cases in Markdown |
| [Configuration Cleanup](architecture/configuration-cleanup.md) | Guidelines for restoring device configuration after tests |
| [Log Collector](architecture/log-collector.md) | Centralized log collector design for all testbeds |
| [UI Testing Guide](architecture/ui-testing-guide.md) | FSM-based GUI testing with accessibility-tree discovery and state-graph navigation |

## Architecture Decision Records

| Document | Description |
|---|---|
| [ADR-0001](adr/0001-scope-to-digital-twin-phase-3.5.md) | Scope WAN Edge Testing Framework to Digital Twin (Phase 3.5) |

---

## Application Examples

### Dockerized CPE Testing

Full TR-069/ACS testbed with containerized PrplOS CPE, SIP voice, DHCP, and LAN clients.

| Document | Description |
|---|---|
| [Overview](examples/cpe-docker/README.md) | Quick-start, testbed topology, use cases exercised |
| [Testbed Topology](examples/cpe-docker/testbed-topology.md) | Network architecture and component reference |
| [ACS URL Discovery](examples/cpe-docker/acs-url-discovery.md) | How the CPE discovers the ACS URL via DHCP |
| [GenieACS Reboot Analysis](examples/cpe-docker/genieacs-reboot-analysis.md) | TR-069 flow analysis for CPE reboot via GenieACS |
| [SIP Phone Configuration](examples/cpe-docker/sip-phone-configuration.md) | Voice testing setup and SIP phone configuration |
| [ACS GUI Testing](examples/cpe-docker/ui-testing-guide.md) | GenieACS-specific GUI testing (references generic [UI Testing Guide](architecture/ui-testing-guide.md)) |
| [Log Locations](examples/cpe-docker/log-locations.md) | Where to find GenieACS and TR-069 proxy logs |
| [Password Handling](examples/cpe-docker/password-handling.md) | Default password flow and cleanup after modification |

### Physical CPE Testing

Same services as dockerized CPE, but with a physical Raspberry Pi as the gateway device.

| Document | Description |
|---|---|
| [Overview](examples/cpe-physical/README.md) | Quick-start, hardware requirements, USB dongle setup |
| [Raikou Physical Integration](examples/cpe-physical/raikou-physical-integration.md) | Integrating a physical device with Raikou OVS bridges |
| [prplOS RPi Implementation](examples/cpe-physical/prplos-rpi-implementation.md) | RPi4 gateway integration plan and status |
| [prplOS RPi Build Guide](examples/cpe-physical/prplos-rpi-build-guide.md) | Step-by-step prplOS build for Raspberry Pi 4 |
| [prplOS RPi Console API](examples/cpe-physical/prplos-rpi-console-api.md) | Console API for Boardfarm device class integration |
| [CPE Device Class Development](examples/cpe-physical/cpe-deviceclass-development.md) | RPiPrplOSCPE device class development plan |

### Dockerized SD-WAN Testing

Digital twin testbed for WAN edge appliance validation with dual-WAN topology.

| Document | Description |
|---|---|
| [Overview](examples/sdwan-digital-twin/README.md) | Quick-start, component map, use cases exercised |
| [Architecture](examples/sdwan-digital-twin/architecture.md) | WAN Edge Appliance Testing Framework architecture overview |
| [Testbed Configuration](examples/sdwan-digital-twin/testbed-configuration.md) | Raikou/Docker Compose configuration for the SD-WAN testbed |
| [Testbed CA Setup](examples/sdwan-digital-twin/testbed-ca-setup.md) | Certificate authority and TLS certificate generation |
| [Linux SD-WAN Router](examples/sdwan-digital-twin/linux-sdwan-router.md) | LinuxSDWANRouter digital twin design |
| [QoE Client](examples/sdwan-digital-twin/qoe-client.md) | Playwright-based QoE measurement client design |
| [Application Services](examples/sdwan-digital-twin/application-services.md) | North-side application servers (Productivity, Streaming, Conferencing) |
| [Traffic Management](examples/sdwan-digital-twin/traffic-management.md) | TrafficController architecture and `tc netem` impairment |
| [App Router](examples/sdwan-digital-twin/app-router.md) | Application router / split north-segment topology |
| [QoE Verification Brief](examples/sdwan-digital-twin/qoe-verification-brief.md) | Technical brief on automated QoE verification |
| [Cross-Vendor API Analysis](examples/sdwan-digital-twin/cross-vendor-api-analysis.md) | WANEdgeDevice template mapping across SD-WAN vendors |

**Future designs (not yet implemented):**

| Document | Description |
|---|---|
| [Traffic Generator](examples/sdwan-digital-twin/future/traffic-generator.md) | iPerf3 background load generator design (descoped — ADR-0001) |
| [Security Testing](examples/sdwan-digital-twin/future/security-testing.md) | MaliciousHost and security test scenario design (descoped — ADR-0001) |

---

## Test Framework Guides

| Document | Description |
|---|---|
| [pytest-bdd Getting Started](frameworks/pytest-bdd/getting-started.md) | Setup, conventions, and first test with pytest-bdd |
| [Robot Framework Getting Started](frameworks/robot-framework/getting-started.md) | Setup, conventions, and first test with Robot Framework |
| [Robot Framework Best Practices](frameworks/robot-framework/best-practices.md) | Keyword library conventions and patterns |
| [Robot Framework Keyword Reference](frameworks/robot-framework/keyword-reference.md) | Complete keyword reference |

---

## Historical

Superseded documents kept for reference. See [historical/README.md](historical/README.md).

| Document | Superseded by |
|---|---|
| [WAN_Edge_Appliance_testing.md](historical/WAN_Edge_Appliance_testing.md) | [SD-WAN Architecture](examples/sdwan-digital-twin/architecture.md) |
| [LinuxSDWANRouter_Implementation_Plan.md](historical/LinuxSDWANRouter_Implementation_Plan.md) | [Linux SD-WAN Router](examples/sdwan-digital-twin/linux-sdwan-router.md) |
| [QoE_Client_Implementation_Plan.md](historical/QoE_Client_Implementation_Plan.md) | [QoE Client](examples/sdwan-digital-twin/qoe-client.md) |
| [Application_Services_Implementation_Plan.md](historical/Application_Services_Implementation_Plan.md) | [Application Services](examples/sdwan-digital-twin/application-services.md) |

## Migration

Completed internal migration and process documents.

| Document | Description |
|---|---|
| [Dual Framework Restructure](migration/dual-framework-restructure.md) | Plan for pytest-bdd + Robot Framework dual support |
| [Robot Keyword Migration](migration/robot-keyword-migration.md) | Keyword library migration to use_cases pattern |
| [Step Migration Guide](migration/step-migration-guide.md) | Step definition migration to use_cases pattern |
