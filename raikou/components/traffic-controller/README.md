# Traffic Controller Component

**Version:** traffic_controller_0.01  
**Maintainer:** rjvisser@alottabits.com

Linux `tc netem` impairment container for WAN path simulation. Dual-homed: eth-dut (south, to DUT) and eth-north (north, to north-segment). Boardfarm applies impairment via the LinuxTrafficController driver.

**Networking:** Interfaces come from Raikou OVS bridges (config_sdwan.json), NOT Docker networks. Test traffic flows through OVS.

**Per-direction impairment:** tc netem is applied on **both** interfaces for asymmetric support — eth-north egress (forward: client→server), eth-dut egress (return: server→client). No IFB required.

**Reference:** `docs/Traffic_Management_Components_Architecture.md`, `docs/SDWAN_Testbed_Configuration.md`

## Features

- **Base:** ssh:v1.2.0
- **Interfaces:** eth-dut (south), eth-north (north) — Raikou-injected
- **Impairment:** tc netem on eth-north (forward) and eth-dut (return) — per-direction, asymmetric-capable
- **IP forwarding:** Enabled for traffic pass-through
- **Password:** boardfarm

## Build

```bash
cd raikou
docker build -t traffic-controller:traffic_controller_0.01 -f components/traffic-controller/Dockerfile components/traffic-controller
```

## Usage

Requires Raikou to inject eth-dut and eth-north. Use with `docker-compose-sdwan.yaml`:

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**SSH:** wan1-tc port 5001, wan2-tc port 5002 (password: boardfarm)

## Env Overrides

| Env var         | Default   | Description        |
|-----------------|-----------|--------------------|
| `TC_DUT_IFACE`  | eth-dut   | South interface    |
| `TC_NORTH_IFACE`| eth-north | North interface    |
