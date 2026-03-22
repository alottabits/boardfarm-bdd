# Log Collector — Centralized Logging for Boardfarm Testbed

Fluent Bit-based centralized log collector. Provides a unified, chronologically ordered timeline of events across all testbed containers.

## Design

- **Management network only** — Not in Raikou `config_sdwan.json`. Receives no OVS interfaces. Sits exclusively on the Docker management network (192.168.55.0/24).
- **Non-invasive** — Containers write to stdout/stderr as usual; Docker captures; Fluent Bit tails.
- **Works with `network_mode: none`** — Docker captures DUT (linux-sdwan-router) stdout/stderr regardless of network configuration.

## Configuration

| File | Purpose |
|------|---------|
| `fluent-bit.conf` | Main config: tail Docker logs, enrich with testbed label, write unified output |
| `parsers.conf` | Docker JSON log format parser |

## Output

- **Path:** `raikou/logs/sdwan-testbed.log` (mounted from host)
- **Format:** `[timestamp] [container_name] message` (one line per log entry)
- **Board name:** for example `sdwan-testbed` (matches `pytest --board-name sdwan-testbed`)

## Usage

```bash
# Live tail — all containers
tail -f raikou/logs/sdwan-testbed.log

# Filter by container
grep "linux-sdwan-router" raikou/logs/sdwan-testbed.log | tail -50

# Correlate by time window
awk '/2026-02-26T10:23:40/,/2026-02-26T10:23:46/' raikou/logs/sdwan-testbed.log
```

## References

- `docs/Centralized_Log_Collector_Implementation.md`
- `docs/SDWAN_Testbed_Configuration.md §5.4`
