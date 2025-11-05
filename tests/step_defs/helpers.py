"""Shared helper functions for step definitions.

This module contains utility functions that are used across multiple
step definition modules to avoid duplication.
"""

import os
from boardfarm3.lib.utils import retry
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate


def gpv_value(acs: AcsTemplate, cpe: CpeTemplate, param: str, retries: int = 6) -> str:
    """Robustly fetch a TR-069 parameter value via ACS with retries.

    Tries to normalize differences in ACS response shapes and transient empties.
    """

    def _fn() -> str | None:
        # Directly call ACS.GPV to avoid optional dependencies
        res = acs.GPV(param, cpe_id=cpe.sw.tr69_cpe_id)
        if not res:
            return None
        item = res[0]
        # Prefer 'value'; fallback to 'rval' if present
        val = item.get("value") if isinstance(item, dict) else None
        if val is None:
            val = item.get("rval") if isinstance(item, dict) else None
        return str(val) if val is not None else None

    out = retry(_fn, retries)
    if out is None:
        raise AssertionError(f"GPV returned empty/malformed for {param}")
    return out


def get_console_uptime_seconds(cpe: CpeTemplate) -> int:
    """Return CPE uptime in seconds using console for reliability/speed."""
    # Prefer library method if available
    try:
        return int(cpe.sw.get_seconds_uptime())  # type: ignore[attr-defined]
    except Exception:
        out = cpe.hw.get_console("console").execute_command(
            "cut -d' ' -f1 /proc/uptime"
        )
        return int(float(out.strip() or "0"))


def install_file_on_tftp(tftp_server: WanTemplate, filename: str) -> None:
    """Helper to copy a firmware file to the TFTP server."""
    # Construct the absolute path to the firmware file.
    # We need to find the project root (where conftest.py is located)
    # Start from this file's location and go up to find the root
    current_dir = os.path.dirname(__file__)  # tests/step_defs
    project_root = os.path.dirname(os.path.dirname(current_dir))  # project root
    
    # Try test_artifacts first, then fallback to test_artifacts/cpe_images if it exists
    local_file_path = os.path.abspath(
        os.path.join(project_root, "tests", "test_artifacts", filename)
    )
    # If file not found, try cpe_images subdirectory
    if not os.path.exists(local_file_path):
        local_file_path = os.path.abspath(
            os.path.join(project_root, "tests", "test_artifacts", "cpe_images", filename)
        )

    # Check that the source file exists before attempting to copy it.
    assert os.path.exists(
        local_file_path
    ), f"Firmware file not found at {local_file_path}"

    # Copy the file to the TFTP server's tftpboot directory.
    # The copy_local_file_to_tftpboot method handles the SCP transfer.
    tftp_server.copy_local_file_to_tftpboot(local_file_path)

