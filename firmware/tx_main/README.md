# ESP8266 Transmitter (TX) Firmware

## Overview
This firmware turns the ESP8266 into a WiFi packet transmitter for motion detection via RSSI analysis.

## Hardware
- ESP8266 board (NodeMCU, Wemos D1 Mini, etc.)
- USB cable for power

## Quick Setup

1. **Open in Arduino IDE**
   - File → Open → `tx_main.ino`

2. **Select Board**
   - Tools → Board → ESP8266 Boards → NodeMCU 1.0 (ESP-12E Module)
   - Tools → Port → (select your ESP8266 port)

3. **Flash**
   - Click Upload button
   - Wait for "Done uploading"

4. **Get MAC Address**
   - Tools → Serial Monitor (115200 baud)
   - Note the MAC address printed on boot
   - Example: `AA:BB:CC:DD:EE:FF`
   - **You'll need this for the RX firmware!**

## Configuration

Default settings (usually don't need to change):
- Network: `Cerberus_Echo`
- Password: `cerberus123`
- Packet rate: 50Hz (every 20ms)

## Placement
- Place in a **fixed location**
- Power via USB or battery
- 2-5 meters away from RX module

## Troubleshooting

**No WiFi connection?**
- Check power supply (needs 5V, 500mA+)
- Try different USB port/cable

**No packets sent?**
- Check Serial Monitor for errors
- Verify WiFi started successfully

## LED Indicator
- Built-in LED blinks with each packet
- Rapid blinking = normal operation
