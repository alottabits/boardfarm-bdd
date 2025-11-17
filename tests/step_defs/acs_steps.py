"""ACS (Auto Configuration Server) interaction step definitions."""

import re
from typing import Any

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
    """Configure the ACS to send a Download RPC on the CPE's next inform."""
    http_server_ip = http_server.get_eth_interface_ipv4_address()
    http_url = f"http://{http_server_ip}/{filename}"

    # Get actual file size from the HTTP server
    # This is critical - if fileSize doesn't match actual file size, download will fail
    tftpboot_path = f"/tftpboot/{filename}"
    try:
        # First verify file exists
        check_output = http_server.console.execute_command(
            f"test -f {tftpboot_path} && echo 'exists' || echo 'missing'"
        )
        if "missing" in check_output.strip():
            raise FileNotFoundError(
                f"Firmware file {filename} does not exist at {tftpboot_path}"
            )
        
        # Get file size
        size_output = http_server.console.execute_command(
            f"stat -c %s {tftpboot_path} 2>/dev/null || echo '0'"
        )
        filesize = int(size_output.strip() or "0")
        if filesize == 0:
            raise ValueError(f"Could not determine file size for {filename}")
        print(f"Determined file size for {filename}: {filesize} bytes")
    except (FileNotFoundError, ValueError) as e:
        # Don't use fallback - fail fast if file doesn't exist or size can't be determined
        raise RuntimeError(
            f"Cannot proceed with Download RPC: {e}. "
            f"Ensure {filename} exists at {tftpboot_path} before running the test."
        ) from e
    except Exception as e:
        # For other errors, still fail but provide more context
        raise RuntimeError(
            f"Error checking firmware file {filename}: {e}"
        ) from e

    acs.Download(
        url=http_url,
        filetype="1 Firmware Upgrade Image",
        targetfilename="",  # PrplOS does not support TargetFileName parameter at all
        filesize=filesize,
        commandkey=f"upgrade-{filename}",  # Some CPEs require non-empty CommandKey
        delayseconds=0,  # Set to 0 for immediate download (faster testing)
        cpe_id=cpe.sw.cpe_id,
    )

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



