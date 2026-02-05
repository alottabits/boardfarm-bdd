*** Settings ***
Documentation    Shared variables for Robot Framework tests.
...              This resource defines TRUE CONSTANTS only - values that do not change per testbed.
...              
...              IMPORTANT: Device-specific data (phone numbers, IP addresses, credentials,
...              network subnets) must come from device objects, NOT from this file.
...              See: boardfarm-bdd/docs/robot/best_practices.md
...              
...              Variable naming conventions:
...              - ${UPPER_CASE}: Constants (timeouts, TR-069 paths, tags)
...              - ${lower_case}: Computed or dynamic values (set at runtime from device objects)

*** Variables ***
# =============================================================================
# Timeouts (in seconds) - Sensible defaults, can be overridden
# =============================================================================
${DEFAULT_TIMEOUT}          30
${SHORT_TIMEOUT}            10
${LONG_TIMEOUT}             120
${REBOOT_TIMEOUT}           240
${BOOT_TIMEOUT}             300
${REGISTRATION_TIMEOUT}     60
${CALL_TIMEOUT}             30
${RING_TIMEOUT}             30

# =============================================================================
# TR-069 Parameter Paths - Standard paths that don't change per testbed
# =============================================================================
# Device Info
${PARAM_SOFTWARE_VERSION}       Device.DeviceInfo.SoftwareVersion
${PARAM_MANUFACTURER}           Device.DeviceInfo.Manufacturer
${PARAM_MODEL_NAME}             Device.DeviceInfo.ModelName
${PARAM_SERIAL_NUMBER}          Device.DeviceInfo.SerialNumber
${PARAM_HARDWARE_VERSION}       Device.DeviceInfo.HardwareVersion
${PARAM_UPTIME}                 Device.DeviceInfo.UpTime

# User Management
${PARAM_USER_1_USERNAME}        Device.Users.User.1.Username
${PARAM_USER_1_PASSWORD}        Device.Users.User.1.Password
${PARAM_USER_1_ENABLE}          Device.Users.User.1.Enable

# WiFi Configuration
${PARAM_WIFI_SSID_2G}           Device.WiFi.SSID.1.SSID
${PARAM_WIFI_SSID_5G}           Device.WiFi.SSID.2.SSID
${PARAM_WIFI_ENABLE_2G}         Device.WiFi.Radio.1.Enable
${PARAM_WIFI_ENABLE_5G}         Device.WiFi.Radio.2.Enable

# Management Server (TR-069)
${PARAM_ACS_URL}                Device.ManagementServer.URL
${PARAM_PERIODIC_INFORM}        Device.ManagementServer.PeriodicInformEnable
${PARAM_PERIODIC_INTERVAL}      Device.ManagementServer.PeriodicInformInterval

# =============================================================================
# Test Tags - Organizational metadata
# =============================================================================
${TAG_SMOKE}                    smoke
${TAG_REBOOT}                   reboot
${TAG_VOICE}                    voice
${TAG_GUI}                      gui
${TAG_WIFI}                     wifi

# =============================================================================
# Status Values - Standard status strings
# =============================================================================
${STATUS_ONLINE}                online
${STATUS_OFFLINE}               offline
${STATUS_REBOOTING}             rebooting
${STATUS_REGISTERED}            registered
${STATUS_UNREGISTERED}          unregistered

# =============================================================================
# Default Test Values - Used when tests need to set test passwords etc.
# =============================================================================
# Note: This is a test password used for password change tests, not a real credential
${TEST_PASSWORD}                p@ssw0rd123!

# =============================================================================
# REMOVED - These values should come from device objects, NOT static variables:
# - Phone numbers: Use phone.number property
# - SIP domain: Use sipcenter.domain or sipcenter.ipv4_addr
# - Network subnets: Use device interface properties
# - Credentials: Use device.username, device.password properties
# =============================================================================
