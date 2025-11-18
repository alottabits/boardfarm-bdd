# Option 4 Investigation: Direct cwmpd Download Without Firmware Controller

## Executive Summary

**Status**: ❌ **NOT FEASIBLE** - Direct cwmpd download bypassing the firmware controller is not possible without significant source code modifications.

## Investigation Findings

### 1. Current Architecture

The PrplOS firmware upgrade flow has evolved from a simple direct download to a more complex architecture:

**Old Flow (Documented but Not Implemented)**:
```
TR-069 Download RPC
  ↓
cwmpd downloads firmware to /tmp/image_name
  ↓
/usr/bin/tr069_1_fw_upgrade /tmp/image_name
```

**Actual Flow (Current Implementation)**:
```
TR-069 Download RPC
  ↓
cwmp_plugin receives Download RPC
  ↓
cwmp_plugin calls DeviceInfo.FirmwareImage.active.Download() via UBUS
  ↓
deviceinfo-manager requires firmware controller (mod-fwi-swupdate)
  ↓
Firmware controller downloads file and calls tr069_1_fw_upgrade
```

### 2. Key Components

#### 2.1 cwmpd
- **Location**: `/usr/bin/cwmpd`
- **Role**: TR-069 protocol handler (SOAP/HTTP)
- **Capability**: Does NOT download files directly
- **Dependency**: Requires `libwebsockets.so.18` (not available in container)

#### 2.2 cwmp_plugin
- **Location**: `/usr/lib/amx/cwmp_plugin/cwmp_plugin.so`
- **Role**: TR-069 data model implementation
- **Functions**:
  - `firmwareimage_download()` - Calls DeviceInfo.FirmwareImage.Download()
  - `firmware_upgrade()` - Orchestrates upgrade process
  - `filetransfer_download_finished()` - Handles download completion
- **Dependency**: Uses `libfiletransfer.so` for actual file transfers
- **Flow**: Always routes firmware downloads through DeviceInfo.FirmwareImage.Download()

#### 2.3 libfiletransfer
- **Location**: `/usr/lib/libfiletransfer.so`
- **Role**: File transfer library (HTTP/HTTPS downloads)
- **Capability**: Can download files directly
- **Usage**: Used by firmware controller, not directly by cwmp_plugin for firmware

#### 2.4 deviceinfo-manager
- **Role**: Manages DeviceInfo data model
- **Firmware Controller**: Requires `mod-fwi-swupdate` or `mod-deviceinfo-firmware`
- **Download Method**: `DeviceInfo.FirmwareImage.{instance}.Download()` UBUS method

### 3. Attempted Bypass Methods

#### 3.1 Direct UBUS Call to AddTransfer
**Attempt**: Call `ManagementServer.ACSTransfers.ACSTransfer.AddTransfer` via UBUS
**Result**: ❌ Method not found
**Reason**: `AddTransfer` is defined in the data model but not exposed via UBUS

#### 3.2 Device Model _exec Call
**Attempt**: Use `_exec` method to call `AddTransfer`
**Command**: 
```bash
ubus call ManagementServer.ACSTransfers _exec '{"method":"AddTransfer","args":{...}}'
```
**Result**: ❌ Returns `false`
**Reason**: Method exists but requires proper initialization/context

#### 3.3 Configuration Override
**Attempt**: Modify cwmp_plugin configuration to bypass firmware controller
**Result**: ❌ No configuration option exists
**Reason**: Firmware download path is hardcoded in cwmp_plugin source

### 4. Code Flow Analysis

From `cwmp_plugin.so` strings analysis:

```
firmwareimage_download() [cwmp_plugin_transfer.c:564]
  ↓
Calls: DeviceInfo.FirmwareImage.active.Download() via UBUS
  ↓
deviceinfo-manager._Download() [deviceinfo_firmwareImage.c:155]
  ↓
Requires: firmware controller (mod-fwi-swupdate)
  ↓
If controller fails: Returns error, download never starts
```

**Key Finding**: The firmware download path is **hardcoded** to go through the firmware controller. There is no fallback mechanism.

### 5. Why Direct Download Is Not Possible

1. **Architectural Dependency**: cwmp_plugin is designed to use DeviceInfo.FirmwareImage.Download(), which requires the firmware controller.

2. **No Fallback Mechanism**: When the firmware controller fails, cwmp_plugin does not attempt an alternative download method.

3. **File Transfer Library Usage**: While `libfiletransfer.so` exists and can download files, it's only used by the firmware controller, not directly by cwmp_plugin for firmware upgrades.

4. **Configuration Limitations**: No configuration option exists to change the download path or bypass the firmware controller.

5. **Source Code Dependency**: The download flow is implemented in compiled binaries (`cwmp_plugin.so`, `deviceinfo-manager.so`) with no runtime configuration to change behavior.

### 6. What Would Be Required

To implement direct cwmpd download bypassing the firmware controller, the following would be required:

1. **Modify cwmp_plugin Source Code**:
   - Add fallback logic in `firmwareimage_download()` function
   - When DeviceInfo.FirmwareImage.Download() fails, call `libfiletransfer` directly
   - Handle download completion and call `tr069_1_fw_upgrade` manually

2. **Rebuild PrplOS**:
   - Compile modified cwmp_plugin
   - Package and deploy new image

3. **Testing**:
   - Verify download works without firmware controller
   - Ensure TransferComplete messages are sent correctly
   - Validate upgrade process completes

### 7. Alternative: Stub Firmware Controller

Instead of bypassing the firmware controller, a **stub firmware controller module** could be created that:
- Provides the Download() method interface
- Uses `libfiletransfer` to download files
- Calls `tr069_1_fw_upgrade` on completion
- Bypasses the missing `mod-fwi-swupdate` functionality

This would be less invasive than modifying cwmp_plugin, but still requires:
- C development (creating a .so module)
- Understanding of PrplOS module interface
- Rebuilding and deploying

### 8. Conclusion

**Direct cwmpd download bypassing the firmware controller is NOT feasible** without:
1. Modifying PrplOS source code (cwmp_plugin)
2. Rebuilding PrplOS image
3. Significant development effort

**Recommended Path Forward**:
- **Option A**: Rebuild PrplOS with firmware controller modules included (most reliable)
- **Option B**: Create stub firmware controller module (moderate complexity)
- **Option C**: Modify cwmp_plugin to add fallback logic (high complexity, maintenance burden)

Given that PrplOS is open source, **Option A (rebuild with modules)** is the most sustainable long-term solution.

