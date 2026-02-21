# ESP32 CSI Transmitter Firmware

## Overview
ESP32-based WiFi transmitter for advanced CSI (Channel State Information) sensing.

## Hardware Requirements
- ESP32-WROOM-32 or compatible
- USB cable

## Flashing Options

### Option A: Arduino IDE (Simplified)

1. **Install ESP32 Board Support**
   - Arduino IDE → Preferences
   - Additional Board Manager URLs:
     ```
     https://dl.espressif.com/dl/package_esp32_index.json
     ```
   - Tools → Board Manager → Search "ESP32" → Install

2. **Select Board**
   - Tools → Board → ESP32 Arduino → ESP32 Dev Module

3. **Upload**
   - Open `esp32_csi_tx.ino`
   - Click Upload

### Option B: ESP-IDF (Recommended for Production)

For full CSI functionality, use the ESP32-CSI-Tool:

```bash
git clone https://github.com/stevenmhernandez/ESP32-CSI-Tool
cd ESP32-CSI-Tool/active_ap
idf.py build flash monitor
```

## Configuration

Default settings:
- SSID: `CerberusCSI_TX`
- Password: `cerberus123`
- Channel: 6
- Transmit rate: 100Hz

## Verification

Serial Monitor should show:
```
AP Started: CerberusCSI_TX
IP Address: 192.168.4.1
Channel: 6
MAC Address: XX:XX:XX:XX:XX:XX
```

**Note the MAC address** - you'll need it for the RX firmware!

## LED Indicator
Built-in LED blinks rapidly during packet transmission.
