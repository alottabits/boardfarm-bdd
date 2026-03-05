# Device Class Method Tests (dc_methods)

Pytest tests that validate the methods of boardfarm device classes against their templates (e.g. WANEdgeDevice, TrafficController). These tests use boardfarm fixtures and require the appropriate board configuration.

## Structure

- `test_linux_sdwan_router.py` — validates `LinuxSDWANRouter` against the `WANEdgeDevice` template
- `test_linux_traffic_controller.py` — validates `LinuxTrafficController` against the `TrafficController` template

## Prerequisites

- SD-WAN testbed containers running (`docker compose -p boardfarm-bdd-sdwan -f raikou/docker-compose-sdwan.yaml up -d`)
- Raikou has injected `eth-north` and `eth-dut` into the TC containers
- Python venv with boardfarm3 installed (`.venv-3.12`)

## Running

Device method tests require full boardfarm args (`--board-name`, `--env-config`, `--inventory-config`).

### LinuxSDWANRouter

```bash
pytest tests/dc_methods/test_linux_sdwan_router.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --skip-boot --save-console-logs ""
```

### LinuxTrafficController

Tests target `wan1_tc` by default. Set `TC_DEVICE_NAME=wan2_tc` to test the second controller.

```bash
pytest tests/dc_methods/test_linux_traffic_controller.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --skip-boot --save-console-logs ""
```

To target `wan2_tc`:

```bash
TC_DEVICE_NAME=wan2_tc pytest tests/dc_methods/test_linux_traffic_controller.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --skip-boot --save-console-logs ""
```

**Important:** `--board-name` is required so the BoardfarmPlugin registers and provides the `devices` fixture.  `--skip-boot` skips the docker power-cycle and applies the default impairment profile from env config.
