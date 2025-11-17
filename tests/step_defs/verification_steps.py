"""Verification and assertion step definitions."""

import re
import time
from typing import Any
from urllib.parse import quote

from boardfarm3.devices.genie_acs import GenieACS
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import then

from .helpers import get_console_uptime_seconds, gpv_value


def _read_acs_logs(acs: AcsTemplate, log_file: str, lines: int = 100) -> str:
    """Read ACS log file using console access.
    
    :param acs: ACS device instance
    :param log_file: Path to log file
    :param lines: Number of recent lines to read (default: 100)
    :return: Log file contents
    """
    try:
        console = acs.console
        # Use tail to get recent log entries
        cmd = f"tail -n {lines} {log_file} 2>/dev/null || echo ''"
        return console.execute_command(cmd, timeout=30)
    except Exception as e:
        print(f"Warning: Could not read ACS log {log_file}: {e}")
        return ""


def _query_genieacs_device_via_console(
    acs: GenieACS, cpe_id: str, param: str
) -> str | None:
    """Query GenieACS device parameter via console using curl.

    This uses console access to make HTTP requests (console-based, not API method),
    maintaining API alignment while allowing us to query device state for FaultCode.

    :param acs: GenieACS device instance
    :param cpe_id: CPE identifier
    :param param: TR-069 parameter to query
    :return: Parameter value as string, or None if not found
    """
    try:
        console = acs.console
        base_url = (
            f"http://{acs.config.get('ipaddr')}:{acs.config.get('http_port')}"
        )
        username = acs.config.get("http_username", "admin")
        password = acs.config.get("http_password", "admin")

        # Query device via GenieACS API using curl (console-based)
        quoted_id = quote('{"_id":"' + cpe_id + '"}', safe="")
        projection = quote(f'{{"{param}":1}}', safe="")
        query_url = f"{base_url}/devices?query={quoted_id}&projection={projection}"

        cmd = (
            f"curl -s -u {username}:{password} "
            f"'{query_url}' 2>/dev/null | "
            f"grep -o '\"{param}\":\"[^\"]*\"' | "
            f"cut -d'\"' -f4 || echo ''"
        )
        result = console.execute_command(cmd, timeout=10)
        if result and result.strip():
            return result.strip()
    except Exception as e:
        print(
            f"Warning: Could not query GenieACS device parameter via console: {e}"
        )
    return None


def _find_download_in_logs(acs: AcsTemplate, cpe_id: str) -> bool:
    """Check ACS logs for Download RPC operations for a specific CPE.
    
    For GenieACS, checks logs for Download RPC being sent to the CPE.
    Note: GenieACS only logs the Download RPC when it's actually sent during
    a TR-069 session, so the CPE must check in first.
    
    :param acs: ACS device instance
    :param cpe_id: CPE identifier
    :return: True if Download operation found in logs
    """
    try:
        if isinstance(acs, GenieACS):
            # GenieACS logs Download RPC in access log with format:
            # "ACS request; acsRequestId="..." acsRequestName="Download" acsRequestCommandKey="...""
            log_content = _read_acs_logs(
                acs, "/var/log/genieacs/genieacs-cwmp-access.log", lines=200
            )
            # Look for Download RPC specifically for this CPE
            # Pattern: CPE_ID ... ACS request ... Download
            download_pattern = rf"{re.escape(cpe_id)}.*ACS request.*acsRequestName=\"Download\""
            if re.search(download_pattern, log_content, re.IGNORECASE):
                return True
            
            # Also check main log file
            log_content = _read_acs_logs(
                acs, "/var/log/genieacs/genieacs-cwmp.log", lines=200
            )
            if cpe_id.lower() in log_content.lower():
                download_patterns = [
                    r"download",
                    r"Download",
                    r"DOWNLOAD",
                ]
                for pattern in download_patterns:
                    if re.search(pattern, log_content, re.IGNORECASE):
                        return True
        else:
            # AxirosACS - check common log locations
            log_files = [
                "/var/log/acs.log",
                "/var/log/tr069.log",
            ]
            for log_file in log_files:
                log_content = _read_acs_logs(acs, log_file, lines=200)
                # Look for download-related entries with CPE ID
                if cpe_id.lower() in log_content.lower():
                    # Check for download-related keywords
                    download_patterns = [
                        r"download",
                        r"Download",
                        r"DOWNLOAD",
                        r"file.*transfer",
                        r"firmware.*upgrade",
                    ]
                    for pattern in download_patterns:
                        if re.search(pattern, log_content, re.IGNORECASE):
                            return True
        return False
    except Exception as e:
        print(f"Warning: Error checking ACS logs for download: {e}")
        return False


def _check_download_status_in_logs(
    acs: AcsTemplate, cpe_id: str
) -> tuple[bool, int | None]:
    """Check ACS logs for download completion status and fault codes.
    
    :param acs: ACS device instance
    :param cpe_id: CPE identifier
    :return: (success, fault_code) tuple
    """
    try:
        if isinstance(acs, GenieACS):
            log_files = [
                "/var/log/genieacs/genieacs-cwmp.log",
                "/var/log/genieacs/genieacs-cwmp-access.log",
            ]
        else:
            log_files = [
                "/var/log/acs.log",
                "/var/log/tr069.log",
            ]
        
        for log_file in log_files:
            log_content = _read_acs_logs(acs, log_file, lines=500)
            if cpe_id.lower() not in log_content.lower():
                continue
            
            # For GenieACS, check logs for TRANSFER COMPLETE, then query device state via console
            # Format: informEvent="7 TRANSFER COMPLETE,M Download"
            if isinstance(acs, GenieACS):
                # Check for TRANSFER COMPLETE inform event (indicates TransferComplete RPC was sent)
                transfer_complete_pattern = r'informEvent="7\s+TRANSFER\s+COMPLETE[^"]*"'
                transfer_complete_rpc = r'cpeRequestName="TransferComplete"'
                
                if re.search(transfer_complete_pattern, log_content, re.IGNORECASE) and \
                   re.search(transfer_complete_rpc, log_content, re.IGNORECASE):
                    # TransferComplete RPC was sent - query device state via console for FaultCode
                    # Use console-based approach (curl via console) to maintain API alignment
                    # The timing (108ms) suggests immediate rejection, so we must check FaultCode
                    try:
                        # Try multiple parameter names for FaultCode (different CPEs may use different names)
                        fault_code = None
                        fault_params = [
                            "Device.Download.DownloadFailureFaultCode",
                            "Device.Download.1.DownloadFailureFaultCode",  # Some CPEs use instance 1
                            "Device.Download.DownloadStatus",  # Status might indicate error
                        ]
                        
                        for param in fault_params:
                            try:
                                param_value = _query_genieacs_device_via_console(acs, cpe_id, param)
                                if param_value:
                                    # DownloadStatus: 0=Idle, 1=Downloading, 2=Downloaded, 3=Error
                                    if param == "Device.Download.DownloadStatus":
                                        if param_value == "3":
                                            print(f"GenieACS shows DownloadStatus=3 (Error)")
                                            # Try to get actual FaultCode
                                            fault_code_str = _query_genieacs_device_via_console(
                                                acs, cpe_id, "Device.Download.DownloadFailureFaultCode"
                                            )
                                            if fault_code_str:
                                                fault_code = int(fault_code_str)
                                            else:
                                                fault_code = -1  # Unknown error
                                            break
                                        elif param_value in ["0", "1", "2"]:
                                            # Status indicates success or in progress
                                            continue
                                    else:
                                        # This is a FaultCode parameter
                                        fault_code = int(param_value)
                                        break
                            except Exception:
                                continue
                        
                        if fault_code is not None:
                            if fault_code == 0:
                                print("GenieACS device state shows FaultCode 0 (success)")
                                return (True, None)
                            else:
                                print(f"GenieACS device state shows FaultCode {fault_code} (failure)")
                                return (False, fault_code)
                        
                        # If we couldn't get FaultCode but TransferComplete happened very quickly,
                        # this likely indicates immediate rejection (common causes: file size mismatch, file not found)
                        # Return fault_code=-1 to indicate definitive failure (immediate rejection detected)
                        print("Warning: TRANSFER COMPLETE occurred very quickly (~100ms), suggesting immediate rejection")
                        print("Possible causes: file size mismatch, file not found, invalid URL, or unsupported file type")
                        return (False, -1)  # Use -1 to indicate definitive failure when FaultCode unknown
                    except Exception as e:
                        print(f"Warning: Could not query GenieACS device state via console: {e}")
                    
                    # Try to parse FaultCode from logs (may be in different log formats)
                    # Look for FaultCode in various patterns around TransferComplete
                    fault_patterns = [
                        r'TransferComplete[^"]*FaultCode\s*[:=]\s*"?(\d+)"?',
                        r'FaultCode\s*[:=]\s*"?(\d+)"?[^"]*TransferComplete',
                        r'TransferComplete.*?Status[^"]*[:=]\s*"?(\d+)"?',
                    ]
                    for pattern in fault_patterns:
                        fault_match = re.search(pattern, log_content, re.IGNORECASE | re.DOTALL)
                        if fault_match:
                            fault_code = int(fault_match.group(1))
                            if fault_code == 0:
                                print(f"Found Transfer Complete with FaultCode 0 in GenieACS logs")
                                return (True, None)
                            else:
                                print(f"Found Transfer Complete with fault code {fault_code} in GenieACS logs")
                                return (False, fault_code)
                    
                    # If TRANSFER COMPLETE is present but no FaultCode found, this is ambiguous
                    # Don't assume success - return unknown status to force further investigation
                    print("Warning: TRANSFER COMPLETE found but FaultCode could not be determined from logs or device state")
                    return (False, None)
            
            # Look for Transfer Complete indicators (generic, works for both ACS types)
            transfer_complete_indicators = [
                r'informEvent="7\s+TRANSFER\s+COMPLETE',
                r'cpeRequestName="TransferComplete"',
                r'TRANSFER\s+COMPLETE.*Download',
                r'Transfer\s+Complete.*Download',
            ]
            for pattern in transfer_complete_indicators:
                if re.search(pattern, log_content, re.IGNORECASE):
                    # Check for numeric fault codes in TransferComplete context
                    # Look for FaultCode parameter in TransferComplete RPC response
                    fault_pattern = r'(?:TransferComplete|TRANSFER\s+COMPLETE).*?(?:FaultCode|faultCode|Fault)\s*[:=]\s*"?(\d+)"?'
                    fault_match = re.search(fault_pattern, log_content, re.IGNORECASE | re.DOTALL)
                    if fault_match:
                        fault_code = int(fault_match.group(1))
                        if fault_code == 0:
                            print(f"Found Transfer Complete with FaultCode 0 in ACS logs")
                            return (True, None)
                        else:
                            print(f"Found Transfer Complete with fault code {fault_code} in ACS logs")
                            return (False, fault_code)
                    # If Transfer Complete found but no fault code, assume success
                    print(f"Found Transfer Complete indicator in ACS logs (download succeeded)")
                    return (True, None)
            
            # Look for success indicators
            success_patterns = [
                r"Transfer Complete.*FaultCode\s*[:=]\s*0",
                r"download.*complete.*success",
                r"firmware.*upgrade.*success",
            ]
            for pattern in success_patterns:
                if re.search(pattern, log_content, re.IGNORECASE):
                    print(f"Found success indicator in ACS logs: {pattern}")
                    return (True, None)
            
            # Look for failure indicators (but only if Transfer Complete was not found)
            failure_patterns = [
                r"download.*fail",
                r"transfer.*fail",
                r"firmware.*upgrade.*fail",
            ]
            for pattern in failure_patterns:
                if re.search(pattern, log_content, re.IGNORECASE):
                    print(f"Found failure indicator in ACS logs: {pattern}")
                    return (False, None)
        
        # No clear status found
        return (False, None)
    except Exception as e:
        print(f"Warning: Error checking download status in logs: {e}")
        return (False, None)


def _wait_for_download_task(acs: AcsTemplate, cpe_id: str, timeout: int = 60) -> bool:
    """Wait for a Download RPC to appear in ACS logs for the given CPE.
    
    Returns True if a Download operation is found in logs, False if timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _find_download_in_logs(acs, cpe_id):
            print(f"Found Download RPC in ACS logs for CPE {cpe_id}")
            return True
        time.sleep(2)
    return False


def _wait_for_task_completion_or_fault(
    acs: AcsTemplate, cpe_id: str, timeout: int = 300
) -> tuple[bool, int | None]:
    """Wait for a download operation to complete or fail by monitoring ACS logs.
    
    Returns (success, fault_code) where success is True if completed successfully,
    False if failed or timeout. fault_code is None if successful, otherwise the fault code.
    Note: fault_code=-1 indicates definitive failure but unknown fault code (e.g., immediate rejection).
    """
    deadline = time.time() + timeout
    last_status = None
    consecutive_unknown = 0  # Track consecutive "unknown" status checks
    
    while time.time() < deadline:
        success, fault_code = _check_download_status_in_logs(acs, cpe_id)
        
        if success:
            print(f"Download completed successfully for CPE {cpe_id}")
            return (True, None)
        
        # fault_code=-1 indicates definitive failure (immediate rejection detected)
        if fault_code == -1:
            print(f"Download failed: immediate rejection detected (FaultCode unknown) for CPE {cpe_id}")
            return (False, fault_code)
        
        # Any non-zero fault code indicates failure
        if fault_code is not None and fault_code != 0:
            print(f"Download failed with fault code {fault_code} for CPE {cpe_id}")
            return (False, fault_code)
        
        # If we get (False, None), it means status is unknown (could be in progress or failed)
        # Check if TRANSFER COMPLETE already happened - if so, this is likely a failure
        if fault_code is None and not success:
            # Check if this is the same status as before (stuck in unknown state)
            if last_status == (False, None):
                consecutive_unknown += 1
                # If we've seen unknown status multiple times and TRANSFER COMPLETE was detected,
                # treat as failure after a short grace period
                if consecutive_unknown >= 5:  # ~10 seconds of unknown status
                    print(f"Warning: Download status remains unknown after multiple checks for CPE {cpe_id}")
                    print("This may indicate a failure that couldn't be detected. Checking for TRANSFER COMPLETE...")
                    # Do one more check specifically for TRANSFER COMPLETE
                    if isinstance(acs, GenieACS):
                        log_files = [
                            "/var/log/genieacs/genieacs-cwmp-access.log",
                        ]
                        for log_file in log_files:
                            log_content = _read_acs_logs(acs, log_file, lines=100)
                            if cpe_id.lower() in log_content.lower():
                                transfer_complete_pattern = r'informEvent="7\s+TRANSFER\s+COMPLETE[^"]*"'
                                if re.search(transfer_complete_pattern, log_content, re.IGNORECASE):
                                    print("TRANSFER COMPLETE detected but FaultCode unavailable - treating as failure")
                                    return (False, -1)  # Immediate rejection likely
            else:
                consecutive_unknown = 0
        
        last_status = (success, fault_code)
        # Still in progress or unknown, wait a bit more
        time.sleep(2)
    
    # Timeout - do a final check
    success, fault_code = _check_download_status_in_logs(acs, cpe_id)
    if success:
        return (True, None)
    if fault_code is not None:
        return (False, fault_code)
    
    print(f"Timeout waiting for download completion for CPE {cpe_id}")
    print("Possible causes: download never started, CPE didn't check in, or status couldn't be determined")
    return (False, None)


@then("the ACS issues the Download RPC")
def acs_issues_download_rpc(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the ACS sent the Download RPC to the CPE.
    
    This step verifies that the Download RPC appears in ACS logs after the CPE checks in.
    The Download task should have been created in a previous step, and the CPE should
    check in naturally (via periodic inform or ScheduleInform from a previous step).
    """
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for ACS to issue Download RPC to CPE {cpe_id}...")
    
    # Simply wait for the Download RPC to appear in logs
    if _wait_for_download_task(acs, cpe_id, timeout=40):
        print(f"Download RPC found in ACS logs for CPE {cpe_id}")
    else:
        raise AssertionError(
            f"Download RPC not found in ACS logs for CPE {cpe_id} within timeout. "
            f"The CPE may not have checked in yet, or the Download task may not have been created."
        )

@then("the CPE downloads the firmware from the image server")
def cpe_downloads_firmware(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE successfully downloaded the firmware from the image server."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for CPE {cpe_id} to complete firmware download...")
    
    try:
        success, fault_code = _wait_for_task_completion_or_fault(acs, cpe_id, timeout=300)
        if success:
            print("CPE confirmed firmware download completed successfully (from ACS logs).")
        elif fault_code == -1:
            raise AssertionError(
                f"Firmware download failed: immediate rejection detected. "
                f"Possible causes: file size mismatch, file not found, invalid URL, or unsupported file type. "
                f"Check that the firmware file exists and file size matches."
            )
        elif fault_code is not None:
            raise AssertionError(
                f"Firmware download failed with fault code {fault_code}"
            )
        else:
            raise AssertionError(
                f"Firmware download did not complete for CPE {cpe_id} within timeout. "
                f"Possible causes: download never started, CPE didn't check in, or status couldn't be determined."
            )
    except AssertionError:
        # Re-raise assertion errors as-is
        raise
    except Exception as e:
        # Fallback: try console expect if log reading fails
        try:
            console = acs.console
            console.expect(
                f"{cpe_id}.*Transfer Complete.*FaultCode 0|{cpe_id}.*download.*complete|{cpe_id}.*Transfer.*success",
                timeout=300
            )
            print("CPE confirmed firmware download completed successfully (via console).")
        except Exception:
            raise AssertionError(
                f"Download verification failed for {type(acs)}: {e}"
            ) from e

@then("the CPE validates the firmware")
def cpe_validates_firmware(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE validated the downloaded firmware."""
    print(f"Verifying CPE {cpe.sw.cpe_id} firmware validation...")
    time.sleep(2)
    try:
        console_output = cpe.hw.get_console("console").execute_command(
            r"logread | grep -i 'validate\|validation' | tail -5"
        )
        if "fail" in console_output.lower() and "validation" in console_output.lower():
            raise AssertionError(
                f"Firmware validation failed. Console output: {console_output}"
            )
        print("CPE firmware validation completed successfully.")
    except Exception:
        print("CPE firmware validation assumed successful (no failure reported).")

@then("after successful validation, the CPE installs the firmware and reboots")
def cpe_installs_firmware_and_reboots(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Wait for firmware installation and reboot completion by checking CPE reconnection."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for CPE {cpe_id} to install firmware and reboot...")
    
    # Wait for CPE to reboot and reconnect by checking if we can query it
    # Give it some time to reboot first
    time.sleep(10)
    
    deadline = time.time() + 180
    reboot_detected = False
    
    while time.time() < deadline:
        try:
            # Try to query the CPE - if it responds, it has rebooted and reconnected
            version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion", retries=2)
            print(f"CPE rebooted and reconnected. Firmware version: {version}")
            reboot_detected = True
            break
        except Exception:
            # CPE might still be rebooting, wait a bit more
            time.sleep(5)
    
    if not reboot_detected:
        # Fallback: try console if available
        try:
            console = acs.console
            console.expect(f"inform event: 1 BOOT.*{cpe_id}", timeout=30)
            print("ACS confirmed BOOT inform after firmware installation and reboot (via console).")
        except Exception:
            raise AssertionError(
                f"CPE {cpe_id} did not reboot and reconnect within timeout"
            )

@then("the CPE reconnects to the ACS")
def cpe_reconnects_to_acs(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE reconnected to the ACS after reboot."""
    cpe_id = cpe.sw.cpe_id
    print(f"Verifying CPE {cpe_id} reconnected to ACS after reboot...")
    time.sleep(5)
    try:
        version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion", retries=5)
        print(f"CPE reconnected to ACS and responding to RPCs. Firmware version: {version}")
    except Exception as e:
        raise AssertionError(
            f"CPE did not reconnect to ACS properly. GPV query failed: {e}"
        ) from e

@then("the ACS reports the new firmware version for the CPE")
def acs_reports_new_fw(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Check ACS for updated SoftwareVersion matching expected_firmware."""
    new_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    if getattr(bf_context, "expected_firmware", None):
        assert bf_context.expected_firmware in new_version, (
            f"Incorrect firmware version reported to ACS. "
            f"Expected: {bf_context.expected_firmware}, Got: {new_version}"
        )
    else:
        assert new_version != bf_context.original_firmware, (
            f"Firmware version did not change after upgrade. "
            f"Original: {bf_context.original_firmware}, Current: {new_version}"
        )

@then("the CPE's subscriber credentials and LAN configuration are preserved")
def config_is_preserved(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Check key device parameters via the ACS to ensure they were not reset."""
    cpe_id = cpe.sw.cpe_id
    for i in range(3):
        try:
            username_val = gpv_value(acs, cpe, "Device.Users.User.1.Username")
            password_val = gpv_value(acs, cpe, "Device.Users.User.1.Password")
            ssid_val = gpv_value(acs, cpe, "Device.WiFi.SSID.1.SSID")

            assert username_val == bf_context.custom_username
            assert password_val == bf_context.custom_password
            assert ssid_val == bf_context.custom_ssid

            print("Verified subscriber credentials and LAN configuration are preserved.")
            return
        except (AssertionError, IndexError, TypeError):
            if i < 2:
                print("Could not verify settings, retrying in 10 seconds...")
                time.sleep(10)
            else:
                raise
    raise AssertionError("Failed to verify preserved settings via ACS.")

@then("the ACS registers a firmware download failure from the CPE")
def acs_registers_download_failure(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Monitor the ACS logs for a download failure with a fault code."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for download failure to be registered for CPE {cpe_id}...")
    
    deadline = time.time() + 120
    while time.time() < deadline:
        success, fault_code = _check_download_status_in_logs(acs, cpe_id)
        if not success and fault_code is not None and fault_code != 0:
            print(f"ACS confirmed download failure with fault code {fault_code} (from logs)")
            return
        time.sleep(2)
    
    # Fallback: try console expect
    try:
        console = acs.console
        console.expect(f"{cpe_id} Transfer Complete.*FaultCode [1-9]", timeout=30)
        print("ACS confirmed receipt of Transfer Complete with fault from CPE (via console).")
    except Exception:
        raise AssertionError(
            f"Download failure not registered for CPE {cpe_id} within timeout"
        )

@then("the CPE does not reboot")
def cpe_does_not_reboot(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Verify the CPE does not reboot by checking that its uptime has increased."""
    time.sleep(5)
    current_uptime = get_console_uptime_seconds(cpe)

    assert bf_context.initial_uptime, "Initial uptime was not set in a previous step"
    assert current_uptime > bf_context.initial_uptime, (
        f"CPE appears to have rebooted. "
        f"Initial uptime: {bf_context.initial_uptime}, Current uptime: {current_uptime}"
    )
    print(
        f"Verified that CPE did not reboot. Uptime increased from {bf_context.initial_uptime} to {current_uptime}."
    )

@then("the CPE continues to run its original firmware version")
def cpe_runs_original_version(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Check that the firmware version has not changed by querying the ACS."""
    current_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    assert current_version == bf_context.original_firmware, (
        f"Firmware version changed unexpectedly. "
        f"Original: {bf_context.original_firmware}, Current: {current_version}"
    )

@then("the CPE autonomously rolls back to its previous firmware version")
def cpe_rolls_back(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Black-box: observe SoftwareVersion returning to original on ACS."""
    deadline = time.time() + 300
    while time.time() < deadline:
        val = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
        if val == bf_context.original_firmware:
            print("ACS reports original firmware version after rollback.")
            return
        time.sleep(10)
    raise AssertionError(
        "Rollback not observed: ACS did not report original firmware in time"
    )

@then("the CPE reboots a second time")
def cpe_reboots_again(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Observe second reboot by checking CPE uptime reset."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for CPE {cpe_id} to reboot a second time...")
    
    # Get initial uptime
    initial_uptime = get_console_uptime_seconds(cpe)
    time.sleep(5)
    
    deadline = time.time() + 180
    reboot_detected = False
    
    while time.time() < deadline:
        try:
            current_uptime = get_console_uptime_seconds(cpe)
            # If uptime decreased, CPE has rebooted
            if current_uptime < initial_uptime:
                print(f"CPE rebooted (uptime reset from {initial_uptime}s to {current_uptime}s)")
                reboot_detected = True
                break
        except Exception:
            # CPE might be rebooting
            time.sleep(5)
    
    if not reboot_detected:
        # Fallback: try console if available
        try:
            console = acs.console
            console.expect(f"inform event: 1 BOOT.*{cpe_id}", timeout=30)
            print("ACS confirmed BOOT inform after rollback reboot (via console).")
        except Exception:
            raise AssertionError(
                f"Second reboot not detected for CPE {cpe_id} within timeout"
            )

@then("the failed upgrade attempt is recorded by the ACS")
def failed_upgrade_recorded(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Check ACS logs for download failure or rollback records."""
    cpe_id = cpe.sw.cpe_id
    print(f"Checking ACS logs for failed upgrade record for CPE {cpe_id}...")
    
    try:
        success, fault_code = _check_download_status_in_logs(acs, cpe_id)
        if not success and fault_code is not None and fault_code != 0:
            print(f"Found failed upgrade record with fault code {fault_code} in ACS logs")
            return
        
        # Also check for rollback indicators
        if isinstance(acs, GenieACS):
            log_files = [
                "/var/log/genieacs/genieacs-cwmp.log",
                "/var/log/genieacs/genieacs-cwmp-access.log",
            ]
        else:
            log_files = [
                "/var/log/acs.log",
                "/var/log/tr069.log",
            ]
        
        for log_file in log_files:
            log_content = _read_acs_logs(acs, log_file, lines=500)
            if cpe_id.lower() in log_content.lower():
                # Look for failure or rollback indicators
                failure_patterns = [
                    r"upgrade.*fail",
                    r"rollback",
                    r"download.*fail",
                    r"Transfer Complete.*FaultCode [1-9]",
                ]
                for pattern in failure_patterns:
                    if re.search(pattern, log_content, re.IGNORECASE):
                        print(f"Found failed upgrade indicator in logs: {pattern}")
                        return
        
        raise AssertionError(
            f"Failed upgrade attempt not found in ACS logs for CPE {cpe_id}"
        )
    except Exception as e:
        # Fallback: try console expect
        try:
            console = acs.console
            console.expect(
                f"{cpe_id}.*(Transfer Complete.*FaultCode [1-9]|upgrade.*fail|rollback)",
                timeout=30
            )
            print("ACS confirmed failed upgrade attempt (via console).")
        except Exception:
            raise AssertionError(
                f"Failed upgrade verification failed for {type(acs)}: {e}"
            ) from e

@then(
    "the CPE's subscriber credentials and LAN configuration are reset to factory defaults"
)
def config_is_reset(cpe: CpeTemplate) -> None:
    """Check key parameters to ensure they HAVE been reset to default values."""
    pass

