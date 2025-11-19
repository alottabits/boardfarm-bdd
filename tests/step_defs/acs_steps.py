"""ACS (Auto Configuration Server) interaction step definitions."""

import re
from typing import Any

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

    # Use device class Download() method to create download task
    # This method uses the NBI API with ?connection_request= parameter to trigger
    # immediate connection, causing the CPE to check in and collect the download task
    print(f"Creating download task via GenieACS device class for CPE {cpe_id}")
    print(f"  URL: {http_url}")
    print(f"  CommandKey: {command_key}")
    print(f"  FileType: 1 Firmware Upgrade Image")
    
    try:
        # Use the device class Download() method which handles the NBI API call
        # with proper connection_request parameter
        response = acs.Download(
            url=http_url,
            filetype="1 Firmware Upgrade Image",
            targetfilename="",  # PrplOS doesn't support TargetFileName
            filesize=0,  # PrplOS doesn't support FileSize
            username="",
            password="",
            commandkey=command_key,
            delayseconds=0,
            successurl="",  # PrplOS doesn't support SuccessURL
            failureurl="",  # PrplOS doesn't support FailureURL
            cpe_id=cpe_id,
        )
        
        if response:
            print(f"Download task created successfully")
        else:
            print(f"Download task created (no response data)")
            
    except Exception as e:
        raise RuntimeError(
            f"Failed to create download task via GenieACS device class: {e}"
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



