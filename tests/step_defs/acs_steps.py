"""ACS (Auto Configuration Server) interaction step definitions."""

import json
import re
import time
from typing import Any
from urllib.parse import quote

from boardfarm3.devices.genie_acs import GenieACS
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate
from pytest_bdd import given, parsers, when
from pytest_boardfarm3.boardfarm_fixtures import bf_context


@given(parsers.parse('the ACS is configured to upgrade the CPE with "{filename}"'))
def acs_configured_for_upgrade(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    http_server: WanTemplate,
    filename: str,
    bf_context: Any,
) -> None:
    """Configure the ACS to send a Download RPC using NBI API with external HTTP URL.
    
    Uses GenieACS NBI API to create a download task that downloads from the WAN HTTP server.
    The MITM proxy will handle removing unsupported parameters (TargetFileName, FileSize, etc.)
    from the Download RPC before it reaches the CPE.
    """
    if not isinstance(acs, GenieACS):
        raise NotImplementedError(
            f"NBI API download task creation is only supported for GenieACS, "
            f"got {type(acs).__name__}"
        )
    
    http_server_ip = http_server.get_eth_interface_ipv4_address()
    http_url = f"http://{http_server_ip}/{filename}"
    cpe_id = cpe.sw.cpe_id
    command_key = f"upgrade-{filename}"

    # Verify file exists on HTTP server (for validation, not used in RPC)
    tftpboot_path = f"/tftpboot/{filename}"
    try:
        check_output = http_server.console.execute_command(
            f"test -f {tftpboot_path} && echo 'exists' || echo 'missing'"
        )
        if "missing" in check_output.strip():
            raise FileNotFoundError(
                f"Firmware file {filename} does not exist at {tftpboot_path}"
            )
        print(f"Verified firmware file exists on HTTP server: {tftpboot_path}")
    except Exception as e:
        raise RuntimeError(
            f"Cannot proceed with Download RPC: {e}. "
            f"Ensure {filename} exists at {tftpboot_path} before running the test."
        ) from e

    # Use NBI API to create download task with external HTTP URL
    # For external URLs, we use SetParameterValues with Downloads virtual parameter
    # This approach allows full control over the download URL and avoids GenieACS file server
    
    # Generate unique timestamp for Downloads instance
    timestamp = int(time.time() * 1000)  # milliseconds
    
    # Create SetParameterValues task for Downloads virtual parameter
    # Format: Downloads.{timestamp}.{parameter} = value
    # This triggers GenieACS to send a Download RPC with the specified URL
    # Note: parameterValues must be an array of arrays: [["param.name", "value"], ...]
    parameter_values = [
        [f"Downloads.{timestamp}.FileType", "1 Firmware Upgrade Image"],
        [f"Downloads.{timestamp}.URL", http_url],
        [f"Downloads.{timestamp}.CommandKey", command_key],
        [f"Downloads.{timestamp}.DelaySeconds", "0"],
        # Note: We don't set TargetFileName, FileSize, SuccessURL, or FailureURL
        # as PrplOS doesn't support them. The MITM proxy will remove any empty ones
        # that GenieACS might add.
    ]
    
    # Create the task via NBI API using console-based curl
    # POST /devices/{deviceId}/tasks?connection_request= triggers immediate execution
    task_payload = {
        "name": "setParameterValues",
        "parameterValues": parameter_values,
    }
    
    print(f"Creating download task via NBI API for CPE {cpe_id}")
    print(f"  URL: {http_url}")
    print(f"  CommandKey: {command_key}")
    print(f"  FileType: 1 Firmware Upgrade Image")
    
    try:
        # Use GenieACS NBI API via console curl (similar to verification_steps.py)
        console = acs.console
        base_url = (
            f"http://{acs.config.get('ipaddr')}:{acs.config.get('http_port')}"
        )
        username = acs.config.get("http_username", "admin")
        password = acs.config.get("http_password", "admin")
        
        # URL encode the device ID
        encoded_cpe_id = quote(cpe_id, safe="")
        
        # Create JSON payload
        json_payload = json.dumps([task_payload])
        
        # Make POST request via curl
        # The ?connection_request= query parameter triggers immediate connection request
        api_url = f"{base_url}/devices/{encoded_cpe_id}/tasks?connection_request="
        curl_cmd = (
            f"curl -s -u {username}:{password} -X POST "
            f"-H 'Content-Type: application/json' "
            f"-d '{json_payload}' "
            f"'{api_url}'"
        )
        
        response_output = console.execute_command(curl_cmd, timeout=30)
        
        # Parse response
        try:
            response_data = json.loads(response_output.strip())
            if isinstance(response_data, list) and len(response_data) > 0:
                task_info = response_data[0]
                task_id = task_info.get("_id", "unknown")
                print(f"Download task created successfully: {task_id}")
            else:
                print(f"Download task created (response: {response_data})")
        except json.JSONDecodeError:
            # If JSON parsing fails, check for HTTP errors
            if "401" in response_output or "Unauthorized" in response_output:
                raise RuntimeError("Authentication failed for GenieACS NBI API")
            elif "404" in response_output:
                raise RuntimeError(f"Device {cpe_id} not found in GenieACS")
            else:
                print(f"Warning: Could not parse response as JSON: {response_output[:200]}")
                print(f"Assuming task was created (check GenieACS logs if issues occur)")
            
    except Exception as e:
        raise RuntimeError(
            f"Failed to create download task via NBI API: {e}"
        ) from e

    version_match = re.search(r"-v(\d+(\.\d+)*)", filename) or re.search(
        r"prplos-(\d+)", filename
    )
    if version_match:
        bf_context.expected_firmware = (
            version_match.group(1)
            if version_match.lastindex
            else version_match.group(0)
        )
    else:
        bf_context.expected_firmware = None


@when("the CPE performs its periodic TR-069 check-in")
def cpe_checks_in(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """
    Trigger the CPE's TR-069 inform via an ACS ScheduleInform RPC.
    This is faster and more deterministic than waiting for the periodic interval.
    """
    cpe_id = cpe.sw.cpe_id
    acs.ScheduleInform(CommandKey="Test", DelaySeconds=0, cpe_id=cpe_id)
    print("Requesting immediate CPE TR-069 check-in via acs.ScheduleInform...")



