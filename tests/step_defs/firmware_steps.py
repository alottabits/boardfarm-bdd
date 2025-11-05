"""Firmware-related step definitions."""

from boardfarm3.templates.wan import WAN as WanTemplate
from pytest_bdd import given, parsers

from tests.step_defs.helpers import install_file_on_tftp


@given(
    parsers.parse(
        'the operator installs a new signed firmware file "{filename}" on the TFTP server'
    )
)
def operator_installs_firmware(tftp_server: WanTemplate, filename: str) -> None:
    """Copy a signed firmware file from the local test suite to the TFTP server."""
    install_file_on_tftp(tftp_server, filename)


@given(
    parsers.parse(
        'the operator installs a new firmware file "{filename}" with an invalid signature on the TFTP server'
    )
)
def operator_installs_invalid_firmware(
    tftp_server: WanTemplate, filename: str
) -> None:
    """Copy a firmware file with a bad signature from the local test suite to the TFTP server."""
    install_file_on_tftp(tftp_server, filename)

