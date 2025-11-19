"""Shared helper functions for step definitions."""

import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

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


def docker_exec_router_command(
    command: str,
    container_name: str = "router",
    timeout: int = 15,
) -> str:
    """Execute a command in the router container using docker exec.

    This is the recommended way to access router container files/logs,
    as documented in TR069_PROXY_README.md. Much more reliable than SSH.

    :param command: Command to execute in router container
    :type command: str
    :param container_name: Docker container name, defaults to "router"
    :type container_name: str
    :param timeout: Command timeout in seconds, defaults to 15
    :type timeout: int
    :return: Command output (stdout)
    :rtype: str
    :raises TimeoutError: If command times out
    :raises RuntimeError: If command returns non-zero exit code
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        return result.stdout
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(
            f"docker exec command timed out after {timeout}s: {command}"
        ) from e
    except subprocess.CalledProcessError as e:
        # Include stderr in error message for debugging
        error_msg = (
            f"docker exec command failed (exit code {e.returncode}): "
            f"{command}\n"
            f"stdout: {e.stdout}\n"
            f"stderr: {e.stderr}"
        )
        raise RuntimeError(error_msg) from e


def docker_exec_cpe_command(
    command: str,
    container_name: str = "cpe",
    timeout: int = 15,
) -> str:
    """Execute a command in the CPE container using docker exec.

    This allows direct access to CPE container logs and system information.

    :param command: Command to execute in CPE container
    :type command: str
    :param container_name: Docker container name, defaults to "cpe"
    :type container_name: str
    :param timeout: Command timeout in seconds, defaults to 15
    :type timeout: int
    :return: Command output (stdout)
    :rtype: str
    :raises TimeoutError: If command times out
    :raises RuntimeError: If command returns non-zero exit code
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        return result.stdout
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(
            f"docker exec command timed out after {timeout}s: {command}"
        ) from e
    except subprocess.CalledProcessError as e:
        # Include stderr in error message for debugging
        error_msg = (
            f"docker exec command failed (exit code {e.returncode}): "
            f"{command}\n"
            f"stdout: {e.stdout}\n"
            f"stderr: {e.stderr}"
        )
        raise RuntimeError(error_msg) from e


def parse_log_timestamp(log_line: str) -> datetime | None:
    """Parse timestamp from a GenieACS log line.

    GenieACS logs use ISO 8601 format with UTC timezone:
    - "2024-01-01T12:00:00.123Z" (with milliseconds and Z timezone)
    - "2024-01-01T12:00:00Z" (without milliseconds)

    This function extracts and parses these timestamps, converting them
    to naive datetime objects (assuming UTC).

    :param log_line: Log line to parse
    :type log_line: str
    :return: Parsed datetime object (naive, assumed UTC), or None if no timestamp found
    :rtype: datetime | None
    """
    # Try ISO format with Z timezone and optional milliseconds
    # Format: "2024-01-01T12:00:00.123Z" or "2024-01-01T12:00:00Z"
    iso_z_match = re.search(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z", log_line
    )
    if iso_z_match:
        timestamp_str = iso_z_match.group(1)
        milliseconds = iso_z_match.group(2)
        try:
            # Parse without milliseconds first
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
            # Add milliseconds if present
            if milliseconds:
                microseconds = int(float(milliseconds) * 1000000)
                dt = dt.replace(microsecond=microseconds)
            # Return as naive datetime (assumed UTC)
            return dt
        except ValueError:
            pass

    # Try proxy log format: "2025-11-19 16:41:17 [INFO] ..."
    proxy_match = re.search(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_line
    )
    if proxy_match:
        timestamp_str = proxy_match.group(1)
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Try ISO format without Z (fallback)
    iso_match = re.search(
        r"(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2})", log_line
    )
    if iso_match:
        timestamp_str = iso_match.group(1).replace("T", " ").replace("/", "-")
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Try time-only format (less reliable, assumes today's date)
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", log_line)
    if time_match:
        time_str = time_match.group(1)
        try:
            # Use today's date with the parsed time
            today = datetime.now().date()
            return datetime.combine(
                today, datetime.strptime(time_str, "%H:%M:%S").time()
            )
        except ValueError:
            pass

    return None


def filter_logs_by_timestamp(
    log_lines: list[str], start_timestamp: datetime | None
) -> list[str]:
    """Filter log lines to only include entries after start_timestamp.

    Log timestamps are parsed as naive datetime (assumed UTC).
    If start_timestamp is timezone-aware, it's converted to naive UTC
    for comparison.

    :param log_lines: List of log lines to filter
    :type log_lines: list[str]
    :param start_timestamp: Timestamp to filter from (inclusive)
    :type start_timestamp: datetime | None
    :return: Filtered list of log lines
    :rtype: list[str]
    """
    if start_timestamp is None:
        # If no start timestamp provided, return all lines
        return log_lines

    # Convert start_timestamp to naive UTC if it's timezone-aware
    if start_timestamp.tzinfo is not None:
        start_timestamp_naive = start_timestamp.astimezone(
            timezone.utc
        ).replace(tzinfo=None)
    else:
        start_timestamp_naive = start_timestamp

    filtered_lines = []
    for line in log_lines:
        if not line.strip():
            continue

        line_timestamp = parse_log_timestamp(line)
        if line_timestamp is None:
            # If we can't parse timestamp, include the line
            # (better to be inclusive than miss relevant entries)
            filtered_lines.append(line)
        elif line_timestamp >= start_timestamp_naive:
            filtered_lines.append(line)

    return filtered_lines


def filter_logs_by_cpe_id(
    log_lines: list[str], cpe_id: str | None
) -> list[str]:
    """Filter log lines to only include entries for a specific CPE.

    GenieACS logs include the CPE ID in the log line format:
    "2024-01-01T12:00:00.123Z [INFO] ::ffff:172.25.1.1 CPE_ID: ..."

    The CPE ID format is: OUI-SERIAL (e.g., "C6B840-SNC6B840D611BB")
    It appears after the IP address and before the colon.

    :param log_lines: List of log lines to filter
    :type log_lines: list[str]
    :param cpe_id: CPE ID (OUI-SERIAL format) to filter for, or None to return all lines
    :type cpe_id: str | None
    :return: Filtered list of log lines
    :rtype: list[str]
    """
    if cpe_id is None:
        # If no CPE ID provided, return all lines
        return log_lines

    filtered_lines = []
    for line in log_lines:
        if not line.strip():
            continue

        # Check if CPE ID appears in the log line
        # Match pattern: " CPE_ID:" (space before, colon after) to ensure
        # we match the device identifier, not just any substring
        # Also check for " CPE_ID " (space before and after) for cases
        # where colon might not be present
        cpe_id_pattern = f" {cpe_id}:"
        cpe_id_pattern_alt = f" {cpe_id} "
        if cpe_id_pattern in line or cpe_id_pattern_alt in line or cpe_id in line:
            filtered_lines.append(line)

    return filtered_lines

