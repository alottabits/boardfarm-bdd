# AI-Driven Security Testing Agent — Design Specification

> **Date:** 2026-04-09
> **Status:** Draft
> **Scope:** SD-WAN / CPE testbed security validation using AI-driven attack generation

---

## 1. Overview

An external AI agent conducts intelligent security testing against testbeds provisioned by Boardfarm. Rather than replaying scripted attacks, the AI reasons about what to probe, generates novel payloads and attack sequences, executes them via Boardfarm's standardized device interfaces, and produces structured reports of its findings.

The primary focus is testing the security stack of the device under test (DUT) — IPS, AMP, content filtering, firewall rules — by generating synthetic attack payloads and observing whether they are detected and blocked. The system is DUT-agnostic: it works with any device that exposes security capabilities through a Boardfarm device class template.

### Goals

- Discover gaps in DUT security policy and signature coverage through AI-generated attack variations
- Provide reproducible evidence for every finding (replay scripts + human-readable reports)
- Work with any DUT type (SD-WAN appliance, CPE router) without agent modification
- Configurable autonomy — from fully manual to autonomous exploration

### Non-Goals

- Real malware or functional exploit code — all payloads are synthetic signature triggers
- SD-WAN device hardening testing (future extension)
- Modifications to Boardfarm core or existing device templates
- AI model training or fine-tuning

---

## 2. Architecture

### Components

| Component | Runs On | Role |
|---|---|---|
| **External AI Agent** | Cloud API (e.g., Claude) | Security reasoning — decides what to test, interprets results, iterates |
| **Security Agent** | Test execution host | Orchestrator — translates AI decisions into Boardfarm device interactions, manages sessions, generates reports |
| **LinuxMaliciousHost** | Malicious Host (VM or container) | Attack executor — receives and runs payloads/scans via Boardfarm device class |
| **DUT** | Device under test | Target — its security stack is what we're probing |
| **Client Endpoint** | Client host (VM or container) | Observation — confirms whether attacks were blocked, passed, or modified in transit |
| **Log Aggregator** | Log Aggregator host (VM or container) | Observation — collects security events from the DUT for cross-component correlation |

### Dependency Map

```
                 External AI Agent
                   (Claude API)
                       |
                       | MCP protocol
                       |
                 Security Agent
              (test execution host)
              |        |        |        |
              | Boardfarm fixtures (pytest)
              |        |        |        |
          Malicious   DUT    Client    Log
            Host    (WAN    Endpoint  Aggregator
                    Edge
                    / CPE)
```

### Key Design Decisions

- **AI reasoning is external.** The heavy inference runs on a cloud API (Claude). The Security Agent on the test execution host handles orchestration, not reasoning.
- **The Malicious Host design is unchanged.** The existing design (Ubuntu 22.04, nmap, hping3, scapy, netcat, tcpdump, payload HTTP server) is sufficient whether deployed as a VM or container. No MCP server or intelligence on the host itself. The `LinuxMaliciousHost` Boardfarm device class abstracts away the deployment model.
- **The Security Agent consumes Boardfarm fixtures.** It uses the same pytest fixture mechanism that regular automated tests use, ensuring portability and consistency.
- **Three-point observation.** Every attack is correlated across what was sent (Malicious Host), what was detected (DUT), and what was received (Client Endpoint).

---

## 3. MCP Server — Tool Interface

The MCP server runs on the test execution host within the Security Agent. It exposes tools to the external AI agent in four categories.

### Testbed Discovery

| Tool | Description |
|---|---|
| `get_testbed_topology()` | Returns the provisioned testbed: devices, roles, interfaces, VLANs, connectivity |
| `get_dut_security_capabilities()` | Introspects the DUT's Boardfarm device class to discover available security methods and current configuration |

### Attack Execution

| Tool | Description |
|---|---|
| `send_packet(target, protocol, payload, flags)` | Craft and send arbitrary packets via scapy on the Malicious Host |
| `run_scan(target, tool, parameters)` | Execute nmap/hping3 with specified parameters |
| `serve_payload(content, filename, port)` | Stage a file on the Malicious Host HTTP server for download-based attacks |
| `capture_traffic(interface, filter, duration)` | Start/stop tcpdump on the Malicious Host for attack verification |

The `target` for attack tools defaults to a reachable endpoint on the far side of the DUT (discovered via `get_testbed_topology()`). All traffic from the Malicious Host's attack VLAN is routed through the DUT, guaranteeing security stack inspection regardless of the destination.

### Observation

| Tool | Description |
|---|---|
| `get_security_events(since_seconds)` | Retrieve DUT security log events via the DUT's device class |
| `get_firewall_decisions(since_seconds)` | Query firewall allow/block decisions from the DUT |
| `query_log_aggregator(source, filter, timerange)` | Search aggregated logs across all testbed components |
| `capture_client_traffic(filter, duration)` | tcpdump on the client side — did the packet arrive? |
| `check_payload_received(expected_signature)` | Verify whether a specific payload was received intact, modified, or blocked at the client |
| `start_client_listener(port, protocol)` | Open a listener on the client for the Malicious Host to target |

### Session Management

| Tool | Description |
|---|---|
| `configure_session(scope, autonomy, max_duration, max_tool_calls)` | Set session parameters |
| `get_session_journal()` | Retrieve the current session's full action log |
| `generate_report()` | Produce the final report: test coverage + findings with replay scripts |

All tool calls are automatically journaled with timestamps, parameters, and results.

---

## 4. Device Portability

The Security Agent works with any DUT, regardless of which Boardfarm template it implements. During the DISCOVERY phase, it introspects the DUT's device class to determine available security methods.

### Capability Discovery

The Security Agent inspects the DUT's Boardfarm device class and presents the AI agent with a capability profile:

```python
# Example: SD-WAN appliance (WANEdgeDevice template)
dut_profile = {
    "device_type": "meraki_mx",
    "template": "WANEdgeDevice",
    "security_capabilities": {
        "get_security_log_events": True,
        "get_firewall_rules": True,
        "get_ips_settings": True,
        "configure_ips": True,
        "get_malware_settings": True,
        "get_content_filter_settings": True,
    }
}

# Example: CPE router (CPE template)
dut_profile = {
    "device_type": "prplos_cpe",
    "template": "CPE",
    "security_capabilities": {
        "get_firewall_rules": True,
        "get_port_forwarding": True,
        "get_dmz_settings": True,
    }
}
```

### AI Adaptation

The AI agent adapts based on the DUT's actual capabilities:

- **Attack strategy** — probes only features the DUT has (no AMP evasion testing on a device without AMP)
- **Observation interpretation** — reads whatever log format the DUT's device class returns
- **Severity assessment** — a missing detection on an enabled feature is a finding; on an absent feature, it's expected

### Adding a New DUT

A new DUT works with the Security Agent if its Boardfarm device class:

1. Implements a Boardfarm template (WANEdgeDevice, CPE, or other)
2. Provides concrete implementations for its supported security methods
3. Returns empty results or raises `NotImplementedError` for unsupported features

No changes to the Security Agent, MCP server, or Malicious Host are required.

---

## 5. Session Lifecycle & Autonomy

### Session Configuration

```python
session_config = {
    "scope": "ips",                    # ips | amp | content_filter | firewall | all
    "autonomy": "goal_directed",       # time_bounded | goal_directed | autonomous | manual
    "budget": {
        "max_duration_minutes": 60,
        "max_tool_calls": 500,
    },
    "objective": "Probe IPS evasion on HTTP and HTTPS traffic",
    "prior_sessions": ["session-2026-04-01-001"],
}
```

### Autonomy Modes

| Mode | Behavior |
|---|---|
| **time_bounded** | Agent explores freely within the budget. Reports when budget exhausted. |
| **goal_directed** | Agent pursues a specific objective. Reports back after each finding for operator review before continuing. |
| **autonomous** | Agent explores all in-scope security features. Runs until it determines it has exhausted viable attack vectors. |
| **manual** | Agent proposes one attack at a time. Operator approves or rejects before execution. |

### Session Phases

**1. DISCOVERY** — AI agent calls `get_testbed_topology()` and `get_dut_security_capabilities()`. Builds understanding of the target environment. Reviews prior session reports if provided.

**2. PLANNING** — AI agent reasons about attack strategy based on DUT capabilities, network topology, and prior session findings. Produces an initial attack plan (logged in journal).

**3. EXECUTION** — AI agent iterates: select/generate attack, execute via MCP tools, observe three-point results (sent / DUT events / client received), assess outcome, adapt strategy. Autonomy mode governs whether the AI agent pauses for operator input between iterations.

**4. REPORTING** — AI agent produces the full report (coverage + findings). Replay scripts generated for each finding. Session committed to git, working directory cleaned.

### Security Testing Skill

At the start of every session, the Security Agent loads a dedicated **Security Testing Skill** into the AI agent's context. This skill is the domain expertise layer — it turns a general-purpose AI into a structured security testing agent with consistent, reproducible behavior.

The skill is version-controlled alongside the Security Agent codebase. As the system matures and testing methodology evolves, the skill is updated accordingly.

The skill covers:

**Session phase protocol** — What the AI agent must do in each phase and when to transition. DISCOVERY must complete before PLANNING begins. PLANNING produces an explicit attack plan before EXECUTION starts. EXECUTION follows the three-point observation discipline. REPORTING is triggered by budget exhaustion, objective completion, or the AI agent's determination that it has exhausted viable vectors.

**MCP tool usage guidance** — When to use which tool, expected return formats, how to chain tools effectively. For example: always call `capture_client_traffic()` before `send_packet()` so the client capture is running when the payload arrives.

**Attack methodology per category:**

| Category | Methodology |
|---|---|
| **IPS** | Start with known signatures, then systematically apply evasion techniques: fragmentation, encoding, protocol-level obfuscation, timing variations. Escalate from simple to complex. |
| **AMP** | Begin with EICAR baseline, then vary delivery method (HTTP chunked, encoded, nested archives), file type, and content obfuscation. |
| **Content Filter** | Test category boundaries, URL encoding variations, redirect chains, domain fronting patterns. |
| **Firewall** | Map the rule set via `get_firewall_rules()`, then probe boundaries: port ranges, protocol edge cases, fragmented packets, connection state manipulation. |

**Three-point observation discipline** — Every attack must be correlated across all three observation points (Malicious Host, DUT, Client Endpoint) before the AI agent assesses the outcome. A missing check at any point makes the assessment unreliable.

**Adaptive strategy** — How to use observations to inform next steps. A successful evasion should trigger variations to map the boundary of the gap. A consistent detection should prompt the AI agent to move to a different technique rather than exhausting minor variations.

**Budget awareness** — How to prioritize when resources are limited. Breadth-first across categories before depth in any single category. When the budget warning is received, wrap up the current attack sequence and transition to REPORTING.

**Severity assessment criteria:**

| Severity | Criteria |
|---|---|
| **CRITICAL** | Payload reaches client completely undetected — no DUT event, no block. Active security feature was enabled. |
| **HIGH** | DUT detects but does not block (detection-only bypass), or blocks without logging (silent drop — operational blind spot). |
| **MEDIUM** | Evasion requires complex multi-step technique unlikely in automated attacks but feasible for a targeted adversary. |
| **LOW** | Minor inconsistency in detection (e.g., delayed logging, imprecise event categorization) that doesn't affect security posture. |

### Budget Enforcement

The Security Agent (not the AI) enforces the budget. Tool calls are counted and duration is tracked. When approaching a threshold (e.g., 80%), the agent informs the AI so it can prioritize remaining exploration and wrap up gracefully.

---

## 6. Reporting

Every session produces a report with two sections.

### Section A: Test Coverage

A complete record of everything tested, regardless of outcome.

Each entry contains:

- **ID** — sequential identifier
- **Timestamp** — when executed
- **Category** — IPS, AMP, Content Filter, Firewall, Other
- **Description** — what was attempted
- **Target** — destination endpoint and port
- **Tool calls** — MCP tools invoked
- **Three-point result:**
  - Malicious Host: what was sent (payload hash, pcap reference)
  - DUT: security events observed (or "none")
  - Client: what was received (or "nothing received")
- **Outcome** — `DETECTED_AND_BLOCKED` | `DETECTED_NOT_BLOCKED` | `NOT_DETECTED` | `BLOCKED_NO_LOG` | `ERROR`

### Section B: Security Findings

Only entries where the DUT's security stack failed (outcomes: `DETECTED_NOT_BLOCKED`, `NOT_DETECTED`, `BLOCKED_NO_LOG`).

Each finding contains:

- **Severity** — CRITICAL, HIGH, MEDIUM, LOW (AI-assessed)
- **Title** — concise description
- **Category** — which security feature failed
- **Description** — what happened, why it matters
- **Evidence:**
  - Payload sent (raw or file reference)
  - DUT events (or absence thereof)
  - Client capture (what arrived)
- **Reproduction:**
  - Replay script (standalone pytest file)
  - Manual steps (human-readable instructions)
- **DUT configuration** — relevant security settings at time of test

### Report Artifacts

```
reports/
  session-<id>/
    report.json              # Machine-readable full report
    report.html              # Human-readable rendered report
    coverage.csv             # Test coverage summary for dashboarding
    findings/
      finding-001/
        replay_test.py       # Standalone pytest file
        payload.bin           # Exact payload used
        sent.pcap             # Malicious Host capture
        received.pcap         # Client-side capture
        dut_events.json       # DUT security log extract
      finding-002/
        ...
    journal.jsonl            # Raw session journal (all MCP tool calls)
```

### Replay Scripts

Replay scripts are standalone pytest files that use Boardfarm fixtures. They are deterministic — hardcoded payload, target, parameters, no AI reasoning at runtime.

Assertions use normal polarity: the test asserts what a secure DUT should do (e.g., "IPS should detect this payload," "client should not receive it"). When the vulnerability exists, the test **fails**. When it's fixed, the test **passes** — making replay scripts directly reusable as regression tests.

### Session Archival

1. Session completes — report and replay scripts generated in `reports/session-<id>/`
2. Operator reviews findings
3. Full session directory committed to git
4. Working directory cleaned after commit

Git history serves as the archive. Prior session reports can be retrieved from git and provided to future sessions via the `prior_sessions` configuration.

For findings worth permanent regression testing, the operator can promote a replay script into the regular test suite — a deliberate human decision.

---

## 7. Prior Session Awareness

When `prior_sessions` is configured, the Security Agent retrieves committed session reports from git and provides them to the AI agent.

This enables:

- **Avoiding redundancy** — the AI skips attack patterns already explored in prior sessions
- **Building on findings** — the AI deepens investigation of previously discovered gaps (e.g., trying variations of a successful evasion technique)
- **Tracking regression** — after a DUT update, the agent re-verifies prior findings to confirm they've been addressed

### What Gets Passed to the AI

The Security Agent extracts from prior reports:

- Test coverage summary: categories tested, techniques used, outcomes
- Findings: what failed, the attack description, severity
- DUT configuration at the time

This is compact enough to fit in the AI context while giving meaningful history to reason from.

---

## 8. New vs. Existing Components

| Component | Status |
|---|---|
| Malicious Host (VM or container) | **Designed** — VM and Docker specs exist, not yet implemented |
| `LinuxMaliciousHost` device class | **Needs implementation** — thin SSH wrapper around attack tools |
| `WANEdgeDevice` template | **Exists** — security methods already defined |
| `CPE` template | **Exists** — security methods already defined |
| Client endpoint device class | **Exists** — may need `capture_traffic()` and `check_payload_received()` added |
| Log Aggregator device class | **Needs verification** — log query methods may need to be added |
| Security Agent | **New** — core of the new work |
| MCP server | **New** — runs within the Security Agent |
| Report generator | **New** — produces reports, replay scripts, session archives |

---

## 9. Scope Boundaries

### In Scope

- Security Agent application on the test execution host
- MCP server exposing testbed interaction tools
- `LinuxMaliciousHost` Boardfarm device class
- Client endpoint extensions for observation
- Log Aggregator query methods (if not already present)
- Session lifecycle: configuration, journaling, budget enforcement
- Report generation: coverage + findings with replay scripts
- Git-based session archival
- DUT-agnostic capability discovery

### Out of Scope

- **Malicious Host design changes** — existing design is sufficient (VM and Docker specs exist)
- **WANEdgeDevice / CPE template changes** — the Security Agent adapts to what's there
- **Boardfarm core modifications** — the Security Agent consumes fixtures, doesn't change Boardfarm
- **AI model training or fine-tuning** — uses a general-purpose model with security context via prompt
- **SD-WAN device hardening testing** — future extension
- **Real malware or live exploit code** — all payloads are synthetic (EICAR-style test artifacts, crafted signatures, protocol anomalies). The AI generates patterns that trigger security detection, not functional exploits. The architecture supports functional payloads if ever needed as a deliberate policy decision, but this is not part of the initial scope.
- **Network topology modifications during a session** — the testbed as provisioned by Boardfarm is fixed for the duration

### Assumptions

- Boardfarm provisions the testbed and presents device fixtures before the Security Agent starts
- The test execution host has network access to all testbed components via the management VLAN
- The external AI agent (Claude API) is reachable from the test execution host
- DUT device classes expose security-related methods consistently
