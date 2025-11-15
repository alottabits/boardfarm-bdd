"""Background step definitions for BDD tests."""

from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given

from .helpers import get_console_uptime_seconds, gpv_value


@given("a CPE is online and fully provisioned")
def cpe_is_online_and_provisioned(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Black-box: confirm online/provisioned state via ACS.

    Store baseline state. Note: Boardfarm initializes the testbed and
    reboots the CPE, which causes it to connect to the ACS. By the time
    this step runs, the CPE should already be connected. We query the ACS
    directly to confirm the CPE is available and get baseline state.
    """
    cpe_id = cpe.sw.cpe_id
    print(
        f"Querying CPE {cpe_id} via ACS to confirm it's online "
        "and provisioned..."
    )

    # Query the CPE for firmware version (gpv_value has built-in retry)
    bf_context.original_firmware = gpv_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )
    bf_context.initial_uptime = get_console_uptime_seconds(cpe)
    print(
        f"CPE baseline state captured: firmware="
        f"{bf_context.original_firmware}, "
        f"uptime={bf_context.initial_uptime}s"
    )
