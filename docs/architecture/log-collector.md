# Centralized Log Collector — Implementation Guide

**Date:** February 26, 2026  
**Status:** Design Document  
**Scope:** Generic — applies to all Boardfarm testbeds (home gateway, SD-WAN, and future deployments)

---

## 1. Overview

The **Centralized Log Collector** is a default infrastructure component for Boardfarm testbeds that provides a unified, chronologically ordered timeline of events across all containers. It adds value regardless of testbed size: with few components it simplifies debugging; with many it enables correlation of failover, path steering, security, and QoE events.

### 1.1 Purpose

| Goal | Description |
|------|--------------|
| **Event timeline** | Single stream of all container logs in time order |
| **Cross-container correlation** | Correlate DUT, clients, servers, and infrastructure during failures |
| **Operational debugging** | Live tail, grep by container, or filter by time window without switching between `docker logs` commands |
| **CI artifacts** | One file to attach on test failure for post-mortem analysis |

### 1.2 Board Name Alignment

The unified log filename and `testbed` label should use the Boardfarm `--board-name` value — the top-level key in the inventory config that identifies the testbed profile. This keeps log paths aligned with the test run (`pytest --board-name prplos-docker-1` → `logs/prplos-docker-1.log`).

### 1.3 Design Principles

- **Management network only** — Log traffic never enters the simulated testbed (OVS bridges). The collector reads Docker log files on the host.
- **Non-invasive** — No code changes in test components. Containers write to stdout/stderr as usual; Docker captures; Fluent Bit tails.
- **Works with all connection types** — Supports containers with `network_mode: none` (e.g. CPE, SD-WAN DUT): Docker captures stdout/stderr regardless of network configuration.
- **Lightweight** — Fluent Bit consumes minimal CPU and memory; suitable for CI and local development.

---

## 2. Architecture

### 2.1 Location in the Testbed

The log collector is a **special-case container** that does **not** follow the standard `network_mode: none` pattern used by all other testbed containers. It requires access to the Docker socket and Docker log files on the host, so it retains Docker's default networking (or uses `network_mode: host`). It does not appear in Raikou's `config.json` — it receives no OVS bridges or simulated-network interfaces.

> **Why the log-collector keeps Docker networking:** All other containers use `network_mode: none` with management access via the OVS `mgmt` bridge (see [Management Network Isolation](management-network-isolation.md)). The log-collector is the exception because it needs host volume mounts (`/var/lib/docker/containers`, `/var/run/docker.sock`) that work most reliably with Docker's default networking or `network_mode: host`. It has no testbed-facing interfaces and does not participate in the simulated network.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         OVS MANAGEMENT BRIDGE (mgmt)                              │
│                         192.168.55.0/24                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│   │ Container │  │ Container │  │ Container │  │ Container │  All use             │
│   │   (DUT)   │  │  (WAN)   │  │  (LAN)   │  │  (ACS)   │  network_mode: none  │
│   │ no mgmt   │  │ eth0     │  │ eth0     │  │ eth0     │  + OVS mgmt bridge   │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
│        │              │              │              │                              │
│        └──────────────┴──────────────┴──────────────┘                              │
│                                                                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         DOCKER HOST                                                │
│                                                                                   │
│   ┌─────────────────┐                                                            │
│   │  log-collector   │  Docker networking (special case)                          │
│   │  Fluent Bit      │  Reads /var/lib/docker/containers/*/*.log                 │
│   └────────┬────────┘                                                            │
│            │                                                                      │
│            ▼                                                                      │
│   Docker daemon captures stdout/stderr for ALL containers                         │
│   (including network_mode: none containers)                                       │
│            │                                                                      │
│            ▼                                                                      │
│   ./logs/<testbed-name>.log  (on host)                                            │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SIMULATED NETWORK (OVS)                                   │
│                         (Raikou-managed; log-collector NOT present)               │
├─────────────────────────────────────────────────────────────────────────────────┤
│   Containers may have eth1, eth2, ... on OVS bridges. Log collector has none.   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Instantiation: Docker Compose, Not Raikou

| Layer | Responsibility | Log Collector |
|-------|----------------|---------------|
| **Docker Compose** | Starts all services (containers). | `log-collector` is a compose service. Started with `docker compose up`. |
| **Raikou** | Creates OVS bridges, injects veth pairs into containers listed in `config.json`. | **Excluded** from `config.json` — no OVS interfaces. Raikou does not manage it. |

The log collector is instantiated by **Docker Compose** as a regular service. Raikou only manages the simulated network topology for testbed components; the log collector is infrastructure that runs alongside them.

**Ordering:** The log collector can start as soon as Docker is running. It does not depend on Raikou. Typical pattern:

```yaml
log-collector:
    ...
    # No depends_on for Raikou — starts with compose.
    # Optional: depends_on: [orchestrator] if you want it after OVS wiring.
```

---

## 3. Docker Compose Integration

### 3.1 Service Definition (Generic Template)

Add the following service to any Boardfarm testbed `docker-compose.yaml`:

```yaml
    # ── Centralized Log Collector ──────────────────────────────────────────────────
    log-collector:
        container_name: log-collector
        image: cr.fluentbit.io/fluent/fluent-bit:3.3
        volumes:
            # Docker socket — read-only access to container metadata (optional, for Docker_Mode).
            - /var/run/docker.sock:/var/run/docker.sock:ro
            # Docker log files — Fluent Bit tails these directly. Works for all containers,
            # including network_mode: none (DUT/CPE). Docker captures stdout/stderr regardless.
            - /var/lib/docker/containers:/var/lib/docker/containers:ro
            # Fluent Bit configuration — project-specific paths
            - ./fluent-bit/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
            - ./fluent-bit/parsers.conf:/fluent-bit/etc/parsers.conf:ro
            # Unified log output on the host — grepable, rotating
            - ./logs:/logs
            # Position database — tracks tail offsets across container restarts
            - fluent-bit-db:/fluent-bit/db
        hostname: log-collector
        restart: unless-stopped
        # Management network only; no OVS interfaces. Do NOT add to Raikou config.json.
        deploy:
            resources:
                limits:
                    cpus: '0.25'
                    memory: 128M
                reservations:
                    cpus: '0.1'
                    memory: 64M

volumes:
    fluent-bit-db:
        driver: local
```

### 3.2 Raikou config.json — Exclusion

The log collector **must not** appear in Raikou's `config.json`. That file declares which containers receive OVS bridge interfaces. The log collector needs only Docker host networking and host volume access — it does not use the OVS management bridge.

```json
{
    "bridge": { "lan-segment": {}, "rtr-wan": {}, ... },
    "container": {
        "router": [...],
        "wan": [...],
        "lan": [...],
        "cpe": [...]
        // No "log-collector" entry — it stays on management network only.
    }
}
```

### 3.3 Compose File Placement

| Testbed Type | Compose Location | Notes |
|--------------|------------------|-------|
| Home gateway (Raikou) | `raikou/docker-compose-sdwan.yaml` (currently the only testbed with log collection) | Add `log-collector` service |
| SD-WAN (Raikou) | Project `docker-compose.yaml` (e.g. `sdwan-testbed/docker-compose.yaml`) | Add `log-collector` service |
| Standalone (no Raikou) | Project `docker-compose.yaml` | Same service definition |

---

## 4. Fluent Bit Configuration

### 4.1 Directory Layout

Create a `fluent-bit/` directory in the testbed project root (or alongside `docker-compose.yaml`):

```
<testbed-root>/
├── docker-compose.yaml
├── config.json              # Raikou only; log-collector excluded
├── fluent-bit/
│   ├── fluent-bit.conf
│   └── parsers.conf
└── logs/                    # Created automatically; holds unified output
    └── <board-name>.log     # Matches Boardfarm --board-name
```

### 4.2 fluent-bit.conf

Use a log filename that matches the Boardfarm `--board-name` (inventory config key) so the unified log aligns with the testbed profile in use. This also prevents multiple testbeds on the same host from overwriting each other.

```ini
[SERVICE]
    Flush             5
    Daemon            Off
    Log_Level         info
    Parsers_File      /fluent-bit/etc/parsers.conf

# Tail Docker JSON log files directly. Works for all containers including
# network_mode: none. Docker captures stdout/stderr for all containers.
[INPUT]
    Name              tail
    Tag               docker.*
    Path              /var/lib/docker/containers/*/*.log
    Parser            docker_json
    Docker_Mode       On
    Docker_Mode_Flush 4
    DB                /fluent-bit/db/pos.db
    Refresh_Interval  10
    Rotate_Wait       30

# Enrich each record with container name and testbed label.
[FILTER]
    Name              record_modifier
    Match             docker.*
    Record            testbed <BOARD_NAME>

# Unified rotating log file. Use the Boardfarm --board-name (inventory config key).
[OUTPUT]
    Name              file
    Match             *
    Path              /logs
    File              <BOARD_NAME>.log
    Format            plain
```

**Board name alignment:**

The log filename and `testbed` label should match the Boardfarm `--board-name` parameter. This is the top-level key in the inventory config that identifies the testbed profile. When running `pytest --board-name prplos-docker-1`, the unified log is at `logs/prplos-docker-1.log`.

| Testbed Profile | `--board-name` | Log File |
|-----------------|----------------|----------|
| Home gateway (PrplOS Docker) | `prplos-docker-1` | `logs/prplos-docker-1.log` |
| Home gateway (OpenWrt RPi) | `openwrt-rpi-1` | `logs/openwrt-rpi-1.log` |
| SD-WAN dual WAN | `sdwan-dual-wan` | `logs/sdwan-dual-wan.log` |
| Double-hop CPE | `double-hop` | `logs/double-hop.log` |

### 4.3 parsers.conf

```ini
[PARSER]
    Name        docker_json
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L%z
    Time_Keep   On
```

---

## 5. Component Configuration — Capturing Logs

For logs to appear in the centralized output, components must write to **stdout** or **stderr**. Docker captures these streams for every container.

### 5.1 General Rule

| Output Target | Captured by Docker? | Appears in Unified Log? |
|---------------|--------------------|-------------------------|
| stdout | Yes | Yes |
| stderr | Yes | Yes |
| File (e.g. `/var/log/app.log`) | No | No, unless you add a separate Fluent Bit input for that path |

### 5.2 Per-Component Guidelines

#### Daemons and Services (FRR, Nginx, GenieACS, etc.)

Configure the daemon to log to stdout so Docker captures it:

| Component | Configuration | Example |
|-----------|---------------|---------|
| **FRR** | `log stdout` in `frr.conf` or via vtysh | `log stdout informational` |
| **Nginx** | `daemon off;` + `error_log /dev/stderr;` `access_log /dev/stdout;` | Standard for containerized Nginx |
| **GenieACS** | Environment: `GENIEACS_*_LOG_FILE=/dev/stdout` or file path; if file, consider symlink to stdout | Log files are separate; add optional [INPUT] tail for them |
| **StrongSwan** | `charon { filelog { /dev/stdout { ... } } }` | Output to stdout |
| **pion WebRTC** | Log to stdout by default | No change |
| **iPerf3** | Writes to stdout | No change |

#### Init Scripts and Entrypoints

- Use `exec` to run the main process so it becomes PID 1 and receives signals correctly.
- Redirect script output: `echo "Container ready" >> /dev/stdout` or simply `echo "..."` (stdout).

#### Containers with `network_mode: none`

Docker still captures stdout/stderr. No special configuration needed. The DUT (e.g. Linux SD-WAN Router, CPE) will appear in the unified log if its processes write to stdout/stderr.

### 5.3 Optional: Tail Additional Log Files

If a component writes to a file (e.g. GenieACS CWMP log) and you want it in the unified stream, add an extra Fluent Bit input:

```ini
[INPUT]
    Name   tail
    Tag    genieacs.cwmp
    Path   /var/log/genieacs/genieacs-cwmp-access.log
    DB     /fluent-bit/db/genieacs-cwmp.db
```

This requires mounting the log directory from the ACS container into the log-collector — more complex. For most testbeds, stdout/stderr capture is sufficient.

---

## 6. Accessing Logs

### 6.1 Live Tail — All Containers

```bash
tail -f logs/<board-name>.log
```

### 6.2 Filter by Container

```bash
grep "container-name" logs/<board-name>.log | tail -50
```

### 6.3 Correlate by Time Window

```bash
awk '/2026-02-26T10:23:40/,/2026-02-26T10:23:46/' logs/<board-name>.log
```

### 6.4 Per-Container Logs (Unchanged)

Docker's native commands remain available:

```bash
docker logs <container-name> --timestamps --tail 100
docker logs <container-name> --since 5m
docker logs <container-name> --follow
```

The centralized log is a **supplement**, not a replacement, for `docker logs`.

---

## 7. Resource Allocation

| Setting | Value | Rationale |
|---------|-------|------------|
| CPU limit | 0.25 | Fluent Bit is lightweight; tail + file output is low CPU |
| CPU reservation | 0.1 | Minimal guarantee under contention |
| Memory limit | 128M | Sufficient for buffering and position DB |
| Memory reservation | 64M | Soft guarantee |

For CI runners with 4–8 vCPUs, these limits are negligible.

---

## 8. Optional: Loki + Grafana

For structured querying and visualisation, Fluent Bit can ship to Loki in addition to (or instead of) the file output. This is optional and testbed-specific.

**Additional compose services:**

```yaml
    loki:
        container_name: loki
        image: grafana/loki:3.3.0
        ports:
            - "3100:3100"
        command: -config.file=/etc/loki/local-config.yaml

    grafana:
        container_name: grafana
        image: grafana/grafana:11.5.0
        ports:
            - "3001:3000"
        environment:
            - GF_SECURITY_ADMIN_PASSWORD=testbed
        depends_on:
            - loki
```

**Additional Fluent Bit output** (append to `fluent-bit.conf`):

```ini
[OUTPUT]
    Name            loki
    Match           *
    Host            loki
    Port            3100
    Labels          testbed=<BOARD_NAME>
    Label_Keys      $container_name
    Line_Format     key_value
```

The flat file output continues to run unless removed. Both can run in parallel.

---

## 9. CI Integration

### 9.1 Artifact on Failure

On test failure, copy the relevant portion of the unified log into the pytest/CI artifact directory:

```python
# conftest.py or pytest hook
def pytest_runtest_makereport(item, call):
    if call.when == "call" and call.excinfo is not None:
        # Copy unified log to artifact dir. Use --board-name for path.
        import shutil
        from pathlib import Path
        board_name = item.config.getoption("--board-name", default="default")
        src = Path("logs") / f"{board_name}.log"
        dst = Path("artifacts") / "testbed.log"
        if src.exists():
            shutil.copy(src, dst)
```

### 9.2 Log Retention

- File output: Configure rotation in Fluent Bit if needed (e.g. 7-day retention, max file size).
- CI: Artifacts are typically short-lived; the copy-on-failure approach is usually sufficient.

---

## 10. Verification

```bash
# Ensure log collector is running
docker compose ps log-collector

# Check unified log is being written (use your --board-name)
ls -la logs/<board-name>.log
tail -n 5 logs/<board-name>.log

# Verify all expected containers appear
for c in router wan lan cpe acs; do
    grep -c "$c" logs/<board-name>.log || true
done
```

---

## 11. Summary Checklist

| Item | Action |
|------|--------|
| Add `log-collector` service to `docker-compose.yaml` | Use template in §3.1 |
| Exclude from Raikou `config.json` | Do not add `log-collector` to `container` section |
| Create `fluent-bit/fluent-bit.conf` | Use template in §4.2; set `<BOARD_NAME>` to match `--board-name` |
| Create `fluent-bit/parsers.conf` | Use template in §4.3 |
| Add `fluent-bit-db` volume | In `volumes:` section |
| Configure components for stdout/stderr | Per §5 |
| Create `logs/` directory | Optional; Fluent Bit creates file; ensure writable by container |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [SD-WAN Testbed Configuration](../examples/sdwan-digital-twin/testbed-configuration.md) | SD-WAN-specific deployment including log collector |
| [SD-WAN Testbed Configuration](../examples/sdwan-digital-twin/testbed-configuration.md) | Management vs. simulated network overview |
| `Boardfarm Test Automation Architecture.md` | Framework reference |
| `Locations of logs.md` | Boardfarm framework and device log locations |
