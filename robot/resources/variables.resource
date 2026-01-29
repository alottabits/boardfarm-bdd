*** Settings ***
Documentation    Shared variables for Robot Framework tests.
...              This resource defines common variables used across test suites.
...              
...              Variable naming conventions:
...              - ${UPPER_CASE}: Constants and configuration values
...              - ${lower_case}: Computed or dynamic values (set at runtime)

*** Variables ***
# =============================================================================
# Default Credentials
# =============================================================================
${DEFAULT_ACS_USERNAME}     admin
${DEFAULT_ACS_PASSWORD}     admin
${DEFAULT_CPE_USERNAME}     admin
${DEFAULT_CPE_PASSWORD}     admin
${TEST_PASSWORD}            p@ssw0rd123!

# =============================================================================
# Timeouts (in seconds)
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
# TR-069 Parameter Paths
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
# SIP Phone Configuration
# =============================================================================
${LAN_PHONE_NUMBER}             1000
${WAN_PHONE_NUMBER}             2000
${WAN_PHONE2_NUMBER}            3000
${SIP_DOMAIN}                   sipcenter

# =============================================================================
# Network Configuration
# =============================================================================
${LAN_SUBNET}                   192.168.1.0/24
${WAN_SUBNET}                   10.0.0.0/24

# =============================================================================
# Test Data Paths
# =============================================================================
${SHARED_DATA_DIR}              ${CURDIR}/../../shared/test_data
${CPE_PARAMS_FILE}              ${SHARED_DATA_DIR}/cpe_parameters.yaml
${SIP_CONFIG_FILE}              ${SHARED_DATA_DIR}/sip_configs.yaml

# =============================================================================
# Test Tags
# =============================================================================
${TAG_SMOKE}                    smoke
${TAG_REBOOT}                   reboot
${TAG_VOICE}                    voice
${TAG_GUI}                      gui
${TAG_WIFI}                     wifi

# =============================================================================
# Status Values
# =============================================================================
${STATUS_ONLINE}                online
${STATUS_OFFLINE}               offline
${STATUS_REBOOTING}             rebooting
${STATUS_REGISTERED}            registered
${STATUS_UNREGISTERED}          unregistered
