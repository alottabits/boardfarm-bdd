# Use Case: Remote Worker Accesses Cloud Application

| Field | Value |
| --- | --- |
| ID | UC-SDWAN-02 |
| Status | Approved |
| Author(s) | |
| Date | |
| Test specifications | see [Traceability](#traceability) |

## Goal

A remote worker accesses a cloud-hosted productivity application through the SD-WAN appliance with acceptable page load performance, and the application remains usable under varying WAN link conditions.

## Scope

The end-to-end application delivery path at a single-WAN branch site: the remote worker's browser, the SD-WAN appliance, the single WAN uplink, and the cloud-hosted productivity application. These components form the system under consideration.

## Primary Actor

Remote Worker (end user accessing a cloud application from a branch or home office)

## Stakeholders

| Stakeholder | Interest |
| --- | --- |
| Remote Worker | Expects fast, reliable application access |
| IT Operations | Needs to validate that the SD-WAN deployment meets application SLOs |
| Application Owner | Requires consistent user experience across deployment sites |
| Network Operations | Needs to understand QoE degradation under different WAN conditions |

## Level

User-goal

## Preconditions

1. The SD-WAN appliance is deployed at a site with a single WAN uplink. No alternative WAN path is available for failover or path steering.
2. The appliance is operational and forwarding traffic between LAN and the single WAN link.
3. The remote worker's device is connected on the LAN side of the appliance and has a browser available.
4. A cloud-hosted productivity application (web application) is running and reachable through the appliance.
5. The productivity application serves content over HTTP and HTTPS (with HTTP/3 support).
6. The remote worker's browser trusts the application's TLS certificates.
7. Baseline WAN conditions are nominal.

## Minimal Guarantees

- Every page load attempt either succeeds and delivers content or fails explicitly (timeout, connection refused) — no partial or ambiguous state is left in the browser.
- The remote worker's browser and the productivity application remain operational regardless of WAN conditions.
- After WAN conditions change, the system returns to its previous behaviour when nominal conditions are restored.

## Success Guarantees

1. Under nominal WAN conditions, the productivity page loads with TTFB < 200 ms and total load time < 2500 ms.
2. Under typical subscriber WAN conditions (moderate latency, minor jitter and loss), the page loads with TTFB < 300 ms and total load time < 4000 ms.
3. Under mobile network WAN conditions (elevated latency, jitter, and loss), the page loads with TTFB < 500 ms and total load time < 6000 ms.
4. Under satellite WAN conditions (very high latency and loss), the page loads with TTFB < 3000 ms and total load time < 12000 ms.
5. When the application is accessed over HTTPS under nominal WAN conditions, the page loads with TTFB < 500 ms and total load time < 8000 ms, and the browser negotiates the expected TLS-based protocol (HTTP/2 or HTTP/3). The relaxed thresholds relative to HTTP account for TLS 1.3 handshake overhead and QUIC connection establishment.
6. When the application is unreachable, the browser reports a clear failure (the system does not hang indefinitely).

## Trigger

The remote worker opens their browser and navigates to the cloud-hosted productivity application URL.

## Main Success Scenario

1. The remote worker navigates to the productivity application URL over HTTP through the SD-WAN appliance under nominal WAN conditions.
2. The application server responds with the requested content.
3. The remote worker's browser renders the page with TTFB < 200 ms and total load time < 2500 ms.
4. Use case succeeds.

## Extensions

- **1.a HTTPS with HTTP/3 (QUIC) Protocol**:

  1. The remote worker navigates to the productivity application URL over HTTPS.
  2. The remote worker's browser negotiates HTTP/3 (QUIC) with the application server.
  3. The remote worker's browser renders the page with TTFB < 500 ms and total load time < 8000 ms.
  4. The remote worker confirms the negotiated protocol is HTTP/3.
  5. Use case succeeds.

- **1.b Typical Subscriber WAN Conditions**:

  1. The WAN link exhibits typical subscriber conditions (moderate latency ~15 ms, minor jitter ~5 ms, minimal loss ~0.1%).
  2. The remote worker navigates to the productivity application URL.
  3. The remote worker's browser renders the page with TTFB < 300 ms and total load time < 4000 ms.
  4. Use case succeeds under typical conditions.

- **1.c Mobile Network WAN Conditions**:

  1. The WAN link exhibits mobile network conditions (elevated latency ~80 ms, jitter ~30 ms, ~1% loss).
  2. The remote worker navigates to the productivity application URL.
  3. The remote worker's browser renders the page with TTFB < 500 ms and total load time < 6000 ms.
  4. Use case succeeds under mobile conditions.

- **1.d Satellite WAN Conditions**:

  1. The WAN link exhibits satellite conditions (very high latency ~600 ms, jitter ~50 ms, ~2% loss).
  2. The remote worker navigates to the productivity application URL.
  3. The remote worker's browser renders the page with TTFB < 3000 ms and total load time < 12000 ms.
  4. Use case succeeds under satellite conditions.

- **2.a Application Unreachable**:

  1. The remote worker navigates to an application URL that is not reachable (server down or invalid address).
  2. The remote worker's browser reports a connection error or timeout.
  3. The remote worker's browser displays an error page.
  4. Use case fails gracefully. Minimal guarantees are met.

## Technology and Data Variations

### Protocol Variations

| Variation | URL Scheme | Expected Protocol | TLS | Notes |
|-----------|-----------|-------------------|-----|-------|
| **HTTP** | `http://` | HTTP/1.1 | No | Baseline — no encryption overhead |
| **HTTPS/H2** | `https://` | HTTP/2 | TLS 1.3 | Standard encrypted access |
| **HTTPS/H3** | `https://` | HTTP/3 (QUIC) | QUIC (TLS 1.3 integrated) | Modern low-latency encrypted transport |

### WAN Condition Variations

| Condition | Latency | Jitter | Loss | TTFB SLO | Load Time SLO |
|-----------|---------|--------|------|----------|---------------|
| **Nominal** | ~5 ms | ~1 ms | ~0% | < 200 ms | < 2500 ms |
| **Typical subscriber** | ~15 ms | ~5 ms | ~0.1% | < 300 ms | < 4000 ms |
| **Mobile network** | ~80 ms | ~30 ms | ~1% | < 500 ms | < 6000 ms |
| **Satellite** | ~600 ms | ~50 ms | ~2% | < 3000 ms | < 12000 ms |

## Traceability

| Artifact | pytest-bdd | Robot Framework |
| --- | --- | --- |
| Test specification | | |
| Step / keyword impl | | |
| Use case code | `boardfarm3/use_cases/qoe.py`, `boardfarm3/use_cases/traffic_control.py` | |

## Related Information

- This use case assumes a single-WAN deployment where no alternative path exists. For dual-WAN sites where the appliance can steer traffic to a healthier path under degradation, see UC-SDWAN-01 (WAN Failover Maintains Application Continuity).
- HTTP/3 (QUIC) uses UDP as the underlying transport and integrates TLS 1.3 into the protocol. Browser support for HTTP/3 depends on the server advertising support via the `Alt-Svc` HTTP response header.
- Page load performance metrics follow web performance standards: TTFB (Time To First Byte) and total load time (Navigation Timing API).
- SLO thresholds are based on industry guidance for acceptable web application responsiveness (Google RAIL model: 200 ms for perceived instant, 1000 ms for maintained attention).
