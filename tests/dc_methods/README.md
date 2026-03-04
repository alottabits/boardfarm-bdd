# Device Class Method Tests (dc_methods)

Pytest tests that validate the methods of boardfarm device classes against their templates (e.g. WANEdgeDevice, CPE). These tests use boardfarm fixtures and require the appropriate board configuration.

## Structure

- `test_linux_sdwan_router.py` — validates LinuxSDWANRouter against WANEdgeDevice template

## Prerequisites

- `linux-sdwan-router` container running (start the SD-WAN testbed first)
- Python venv with boardfarm3 installed (e.g. `.venv-3.12`)

## Running

Device method tests require full boardfarm args (`--board-name`, `--env-config`, `--inventory-config`). Example for SD-WAN:

```bash
pytest tests/dc_methods/test_linux_sdwan_router.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy
```

With boot (power cycle) and console logs:

```bash
pytest tests/dc_methods/test_linux_sdwan_router.py -v \
    --board-name sdwan \
    --env-config bf_config/bf_env_sdwan.json \
    --inventory-config bf_config/bf_config_sdwan.json \
    --legacy --save-console-logs ""
```

**Important:** `--board-name` is required so the BoardfarmPlugin registers and provides the `devices` fixture.
