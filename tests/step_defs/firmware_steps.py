"""Firmware-related step definitions."""

from boardfarm3.templates.wan import WAN as WanTemplate
from pytest_bdd import given, parsers

from .helpers import install_file_on_http_server, remove_file_from_http_server


@given(
    parsers.parse(
        'the operator installs a new signed firmware file "{filename}" on the image server'
    )
)
def operator_installs_firmware(http_server: WanTemplate, filename: str) -> None:
    """Copy a signed firmware file from the local test suite to the HTTP server."""
    install_file_on_http_server(http_server, filename)


@given(
    parsers.parse(
        'the operator installs a new firmware file "{filename}" with an invalid signature on the image server'
    )
)
def operator_installs_invalid_firmware(
    http_server: WanTemplate, filename: str
) -> None:
    """Copy a firmware file with a bad signature from the local test suite to the HTTP server."""
    install_file_on_http_server(http_server, filename)


@given(
    parsers.parse(
        'the operator removes the firmware file "{filename}" from the image server'
    )
)
def operator_removes_firmware(http_server: WanTemplate, filename: str) -> None:
    """Remove a firmware file from the HTTP server."""
    remove_file_from_http_server(http_server, filename)

