# Boardfarm Use Case Tests (bf_use_cases)

Pytest tests that verify the boardfarm use-case layer functions.  Unlike the
`dc_methods/` tests (which test *device class* methods against real containers),
these tests sit one layer higher — they test the **use-case functions** that BDD
step definitions and scenario code actually call.

## Structure

| File | Type | Description |
|------|------|-------------|
| `test_traffic_control_unit.py` | Unit | Mock-based isolation tests — no containers required |
| `test_traffic_control_integration.py` | Integration | End-to-end tests against running TC containers |
| `conftest.py` | Config | Autouse fixture overrides + TC device fixtures |

## Test types

### Unit tests (`test_traffic_control_unit.py`)

Verify use-case logic in complete isolation using `unittest.mock`.
No running containers, no boardfarm plugin, no network access.

Covers:
- `get_traffic_controller()` — device selection, all error paths (DeviceNotFound, ValueError)
- `_get_preset_from_config()` — preset lookup and KeyError on unknown preset
- `apply_preset()` — sustained (→ `set_impairment_profile`) and transient (→ `inject_transient`) paths; event key extraction
- `set_impairment_profile()` — delegation of ImpairmentProfile and plain dict
- `get_impairment_profile()` — delegation and return value forwarding
- `clear_impairment()` — delegation to `controller.clear()`
- `inject_blackout()` — correct event string and duration
- `inject_brownout()` — default (200ms/5%) and custom parameters
- `inject_latency_spike()` — default (500ms) and custom spike
- `inject_packet_storm()` — default (10%) and custom loss

**Run:**

```bash
pytest tests/bf_use_cases/test_traffic_control_unit.py -v
```

No boardfarm flags required.

---

### Integration tests (`test_traffic_control_integration.py`)

Exercise all use-case functions through the boardfarm device manager against
real `LinuxTrafficController` containers.  Verify that the use-case layer
correctly orchestrates the device class and that kernel state matches
expectations.

Covers:
- `get_traffic_controller()` — by name, no-name-multiple-TCs error, unknown-name error
- `set_impairment_profile()` / `get_impairment_profile()` — round-trips (object and dict)
- `clear_impairment()` — removes all qdiscs
- `apply_preset()` — all five named presets (pristine, cable_typical, 4g_mobile, satellite, congested); unknown preset KeyError; timed transient with auto-restore
- `inject_blackout()` — active 100% loss + auto-restore
- `inject_brownout()` — default and custom latency/loss
- `inject_latency_spike()` — default and custom spike
- `inject_packet_storm()` — default and custom loss
- Consecutive transient calls — second inject cancels first restore

**Prerequisites:**

- SD-WAN testbed running: `docker compose -p boardfarm-bdd-sdwan -f raikou/docker-compose-sdwan.yaml up -d`
- Raikou has injected `eth-north` and `eth-dut` into `wan1-tc` and `wan2-tc`

**Run:**

```bash
pytest tests/bf_use_cases/test_traffic_control_integration.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --skip-boot
```

**Run both unit and integration together:**

```bash
pytest tests/bf_use_cases/ -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --skip-boot
```
