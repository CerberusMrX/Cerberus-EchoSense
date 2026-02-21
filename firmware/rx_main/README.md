# ESP8266 Receiver (RX) Firmware

## Overview
This firmware receives WiFi packets from the TX module and streams RSSI data to the backend server.

## Hardware
- ESP8266 board (NodeMCU, Wemos D1 Mini, etc.)
- USB cable

## Setup

1. **Configure WiFi Settings**
   
   Edit these lines in `rx_main.ino`:
   
   ```cpp
   const char* WIFI_SSID = "YourWiFiName";        // Your home WiFi
   const char* WIFI_PASS = "YourPassword";
   ```

2. **Set TX MAC Address**
   
   Update with the MAC from your TX module:
   
   ```cpp
   uint8_t targetMAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};
   ```

3. **Set Backend IP**
   
   Update with your laptop's IP address:
   
   ```cpp
   IPAddress backendIP(192, 168, 1, 100);  // Change to your laptop IP
   ```
   
   **To find your laptop IP:**
   - Linux/Mac: `ip addr` or `ifconfig`
   - Windows: `ipconfig`
   - Look for IP on same network as ESP8266

4. **Flash Firmware**
   - Arduino IDE → Upload
   - Open Serial Monitor (115200 baud)
   - Should see:
     ```
     [RX] Connecting to WiFi...
     [RX] Connected.
     [RX] Sniffer Enabled.
     ```

5. **Verify Data Stream**
   - Start backend: `python backend/server.py`
   - Serial Monitor should show: `RSS:-XX` values
   - Backend should log: `[UDP] Received RSSI...`

## Troubleshooting

**Won't connect to WiFi?**
- Double-check SSID and password
- Ensure 2.4GHz WiFi (ESP8266 doesn't support 5GHz)
- Try placing closer to router

**No RSSI data?**
- Verify TX MAC address is correct
- Check that TX is powered on and transmitting
- Ensure RX and TX are on same WiFi channel

**UDP not reaching backend?**
- Verify laptop IP is correct
- Check firewall allows UDP port 8888
- Ensure RX and laptop are on same network
- Try pinging laptop from another device

**High variance even when static?**
- Normal during first 10 seconds (calibration)
- Adjust `VARIANCE_THRESHOLD` in backend config
- Ensure antennas (if external) are oriented correctly

## Placement Tips
- 2-5 meters from TX module
- Chest height (1-1.5m) for best human detection
- Connected to laptop via USB, or powered separately
- Must be on same WiFi network as backend server
