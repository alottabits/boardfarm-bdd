# Testbed Validation Plan: pfSense/OPNsense Proxy Phase

## 1. Objective

To verify the **Boardfarm Orchestration** and **QoE Measurement** logic using an open-source routing appliance (pfSense or OPNsense) as a functional proxy for the Meraki MX.

## 2. Implementation Approach

Since pfSense/OPNsense requires a BSD kernel, the functional testbed will use a **KVM/QEMU** instance or a specialized container (like `v-pfsense`) integrated into the Raikou network topology.

### Proxy Mapping: pfSense to Meraki MX

|   |   |   |
|---|---|---|
|**Meraki Feature**|**pfSense Proxy Equivalent**|**Validation Goal**|
|**SD-WAN Policies**|Gateway Groups (Multi-WAN)|Test Boardfarm's ability to trigger path shifts.|
|**QoS / Shaper**|ALTQ / Limiters|Verify that QoE scripts detect throttled traffic.|
|**L7 Visibility**|ntopng / Snort|Ensure classification logic doesn't break metrics.|
|**API/Management**|pfSense XML-RPC or Config|Test the "Telemetry" collection scripts.|

## 3. Pre-Hardware Validation Scenarios

### 3.1 Orchestration Handshake

- **Goal:** Ensure Boardfarm can talk to the "Device Under Test" (DUT).
    
- **Method:** Create a Boardfarm `pfsense_device.py` driver.
    
- **Success:** Boardfarm successfully fetches interface status and CPU load from the pfSense container.
    

### 3.2 Impairment Trigger Loop

- **Goal:** Verify that applying a "Satellite" profile via the `ISPGateway` actually triggers a failover in the DUT.
    
- **Method:** Configure pfSense Gateway Monitoring (dpinger) to watch for latency. Inject 600ms latency via `tc` on the ISP container.
    
- **Success:** pfSense marks the WAN "Down"; Playwright Client records the transient QoE dip during the switch.
    

### 3.3 Measurement Baseline

- **Goal:** Establish "Clean Path" baselines for your 4K Video and MOS scripts.
    
- **Method:** Run the full QoE suite through a "Pristine" pfSense configuration.
    
- **Success:** Results show 0% rebuffer and > 4.2 MOS, confirming the test harness adds no artificial lag.
    

## 4. Required Modifications to Testbed

1. **Topology Change:** Replace the `ApplicationGateway` placeholder with a Virtual Machine instance of pfSense.
    
2. **Interface Mapping:** Map the virtual LAN/WAN bridges to the Boardfarm bridge network.
    
3. **Automation Driver:** Implement a basic SSH-based driver for pfSense to allow Boardfarm to reset states between tests.
    

## 5. Summary of Benefits

By using pfSense now, you isolate **test harness bugs** (broken Playwright scripts, incorrect `tc` commands) from **device bugs**. When the Meraki MX arrives, you will have a "Certified Stable" testbed, ensuring that any failures found are truly attributable to the Meraki's performance.