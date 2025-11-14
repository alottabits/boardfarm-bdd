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

    acs.Download(
        url=http_url,
        filetype="1 Firmware Upgrade Image",
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



