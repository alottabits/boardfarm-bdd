"""Shared helper functions for step definitions."""

import os
from boardfarm3.lib.utils import retry
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate


def gpv_value(acs: AcsTemplate, cpe: CpeTemplate, param: str, retries: int = 6) -> str:
    """Robustly fetch a TR-069 parameter value via ACS with retries."""
    def _fn() -> str | None:
        res = acs.GPV(param, cpe_id=cpe.sw.cpe_id)
        if not res:
            return None
        item = res[0]
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
    try:
        return int(cpe.sw.get_seconds_uptime())
    except Exception:
        out = cpe.hw.get_console("console").execute_command("cut -d' ' -f1 /proc/uptime")
        return int(float(out.strip() or "0"))

def install_file_on_http_server(http_server: WanTemplate, filename: str) -> None:
    """Helper to copy a firmware file to the HTTP server.
    
    Removes any existing file with the same name first to ensure a clean state.
    """
    # Remove existing file first to ensure clean state
    remove_file_from_http_server(http_server, filename)
    
    current_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(os.path.dirname(current_dir))
    local_file_path = os.path.abspath(
        os.path.join(project_root, "tests", "test_artifacts", filename)
    )
    if not os.path.exists(local_file_path):
        local_file_path = os.path.abspath(
            os.path.join(project_root, "tests", "test_artifacts", "cpe_images", filename)
        )
    assert os.path.exists(
        local_file_path
    ), f"Firmware file not found at {local_file_path}"
    http_server.copy_local_file_to_tftpboot(local_file_path)


def remove_file_from_http_server(http_server: WanTemplate, filename: str) -> None:
    """Helper to remove a firmware file from the HTTP server."""
    # Files are stored in /tftpboot on the WAN server
    tftpboot_path = f"/tftpboot/{filename}"
    try:
        http_server.console.execute_command(f"rm -f {tftpboot_path}")
        print(f"Removed {filename} from WAN server at {tftpboot_path}")
    except Exception as e:
        print(f"Warning: Could not remove {filename} from WAN server: {e}")



