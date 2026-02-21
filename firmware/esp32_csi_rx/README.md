# ESP32 CSI Receiver Firmware

## Overview
ESP32 receiver that captures Channel State Information (CSI) for advanced WiFi sensing.

## ⚠️ Important Notes

This is a **simplified Arduino-compatible version**. For production CSI sensing, we recommend using the ESP32-CSI-Tool which provides full CSI buffer access.

### Limitations of Arduino Version
- Limited CSI buffer access
- Simplified data parsing
- May not capture all 64 subcarriers correctly

### Recommended: Use ESP-IDF Version

```bash
# Clone ESP32-CSI-Tool
git clone https://github.com/stevenmhernandez/ESP32-CSI-Tool
cd ESP32-CSI-Tool/passive_sta

# Edit main/csi_component.c
# Set your WiFi credentials and TX MAC address

# Build and flash
idf.py build flash monitor
```

## Arduino IDE Setup (Testing Only)

1. **Configure WiFi**
   ```cpp
   const char* WIFI_SSID = "YourWiFiName";
   const char* WIFI_PASS = "yourpassword";
   ```

2. **Set TX MAC Address**
   ```cpp
   uint8_t targetMAC[] = {0xAA, 0xBB, 0xCC ...};  // From TX
   ```

3. **Set Backend IP**
   ```cpp
   IPAddress backendIP(192, 168, 1, 100);
   ```

4. **Flash**
   - Tools → Board → ESP32 Dev Module
   - Upload

## CSI Data Format

The receiver streams CSV data to the backend:
```
timestamp,amp0,amp1,amp2,...,amp63
```

Where each `ampN` is the amplitude of CSI subcarrier N (0-63).

## Verification

Serial Monitor should show:
```
Connected!
IP Address: 192.168.1.XXX
[CSI] Enabled. Listening for packets...
```

## Troubleshooting

**No CSI data?**
- ESP-IDF version is much more reliable
- Check TX is broadcasting
- Verify MAC address matches TX
- Ensure on same WiFi network

**For Production Use:**
Follow the ESP32-CSI-Tool guide:
https://github.com/stevenmhernandez/ESP32-CSI-Tool
