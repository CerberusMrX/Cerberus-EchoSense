# Hardware Setup & Flashing Guide

This guide explains how to set up Cerberus EchoSense with different hardware configurations.

## 🎯 Choose Your Hardware Mode

Cerberus EchoSense supports **5 different hardware configurations**. Choose based on what you have:

| Mode | Hardware Required | Features | Difficulty |
|------|------------------|----------|------------|
| **1. Camera Only** | USB Webcam | Object detection, pose estimation, activity recognition | ⭐ Easy |
| **2. ESP8266 RSSI** | 2x ESP8266 boards | WiFi presence detection, through-wall motion | ⭐⭐ Medium |
| **3. ESP32 CSI** | 2x ESP32 boards | Advanced WiFi sensing, ML classification | ⭐⭐⭐ Advanced |
| **4. WiFi Adapter** | Monitor-capable WiFi adapter | Ambient WiFi traffic analysis | ⭐⭐ Medium |
| **5. Hybrid** | Camera + any WiFi hardware | Best: Camera + WiFi handoff tracking | ⭐⭐⭐ Advanced |

---

## Mode 1: Camera Only 🎥

**Perfect for:** Pure computer vision, no WiFi hardware needed

### Prerequisites
- USB webcam or Raspberry Pi CSI camera
- Python 3.9+
- (Optional) NVIDIA GPU for faster processing

### Setup Steps

1. **Run Setup Wizard**
   ```bash
   python setup_wizard.py
   ```
   - Select option `1` (Camera Only)
   - Wizard will auto-detect your camera
   - Choose GPU acceleration if available

2. **Test Camera**
   ```bash
   python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
   ```

3. **Start System**
   ```bash
   # Terminal 1
   cd backend && python server.py

   # Terminal 2
   cd frontend && npm run dev
   ```

4. **Open Browser**
   - Navigate to `http://localhost:5173`
   - You should see camera feed with bounding boxes

### Features Available
- ✅ Real-time object detection (YOLO)
- ✅ Pose estimation (17 keypoints)
- ✅ Activity recognition (walking, standing, sitting)
- ✅ Multi-person tracking
- ❌ Through-wall detection
- ❌ Out-of-camera motion tracking

---

## Mode 2: ESP8266 RSSI 📡

**Perfect for:** Through-wall motion detection, existing ESP8266 hardware

### Prerequisites
- **2x ESP8266 boards** (NodeMCU, Wemos D1 Mini, etc.)
- USB cables
- Arduino IDE or PlatformIO
- Your home WiFi credentials

### Hardware Setup

1. **Flash Transmitter (TX)**
   - Open `firmware/tx_main/tx_main.ino` in Arduino IDE
   - Select board: `NodeMCU 1.0 (ESP-12E Module)`
   - Flash to first ESP8266
   - **Important:** Note the MAC address printed in Serial Monitor

2. **Flash Receiver (RX)**
   - Open `firmware/rx_main/rx_main.ino`
   - **Edit these lines:**
     ```cpp
     const char* WIFI_SSID = "YourWiFiName";     // Your WiFi
     const char* WIFI_PASS = "YourPassword";
     uint8_t targetMAC[] = {0xAA, 0xBB, 0xCC...}; // TX MAC from step 1
     IPAddress backendIP(192, 168, 1, 100);      // Your laptop IP
     ```
   - Flash to second ESP8266

3. **Physical Placement**
   - Place **TX** in one corner (powered by USB or battery)
   - Place **RX** 2-5 meters away (connected to laptop or powered separately)
   - RX must be on same WiFi network as your laptop

4. **Run Setup Wizard**
   ```bash
   python setup_wizard.py
   ```
   - Select option `2` (ESP8266)
   - Update `config.yaml` with TX MAC address

5. **Start Backend**
   ```bash
   cd backend && python server.py
   ```
   - You should see: `[UDP] Listening on 0.0.0.0:8888`
   - Walk between TX and RX to test

### Features Available
- ✅ Presence detection
- ✅ Motion variance analysis
- ✅ Through-wall/obstacle detection
- ❌ Camera vision
- ❌ Pose estimation
- ✅ (Optional) Add camera for hybrid mode

### Troubleshooting
- **No UDP packets received?**
  - Check RX Serial Monitor for errors
  - Verify laptop firewall allows UDP port 8888
  - Confirm RX and laptop are on same network

- **High variance even when static?**
  - Adjust `variance_threshold` in `config.yaml`
  - Let system calibrate for 10 seconds

---

## Mode 3: ESP32 CSI 🔬

**Perfect for:** Research-grade WiFi sensing, high-precision motion analysis

### Prerequisites
- **2x ESP32 boards** (ESP32-WROOM-32 or compatible)
- **ESP-IDF framework** (Arduino IDE has limited CSI support)
- USB cables

### ESP-IDF Installation

1. **Install ESP-IDF** (Linux/Mac)
   ```bash
   mkdir -p ~/esp
   cd ~/esp
   git clone --recursive https://github.com/espressif/esp-idf.git
   cd esp-idf
   ./install.sh esp32
   . ./export.sh
   ```

2. **Verify Installation**
   ```bash
   idf.py --version
   ```

### Firmware Options

**Option A: Use Provided Firmware (Simplified)**
- Use `firmware/esp32_csi_tx/` and `firmware/esp32_csi_rx/`
- Limited CSI functionality, Arduino-compatible
- Good for testing

**Option B: Use ESP32-CSI-Tool (Recommended for Production)**
1. Clone the official tool:
   ```bash
   git clone https://github.com/stevenmhernandez/ESP32-CSI-Tool
   cd ESP32-CSI-Tool
   ```

2. Flash Active AP (TX):
   ```bash
   cd active_ap
   idf.py build flash monitor
   ```

3. Flash Passive STA (RX):
   ```bash
   cd ../passive_sta
   # Edit main/csi_component.c to set your WiFi SSID/password
   idf.py build flash monitor
   ```

### Backend Configuration

1. **Run Setup Wizard**
   ```bash
   python setup_wizard.py
   ```
   - Select option `3` (ESP32 CSI)

2. **Update config.yaml**
   - Set ESP32 TX MAC address
   - Set UDP port (default: 8889)

3. **Start System**
   ```bash
   cd backend && python server.py
   ```

### CSI Data Format
ESP32 streams CSV format:
```
timestamp,subcarrier_0_amp,phase_0,...,subcarrier_63_amp,phase_63
```

### Features Available
- ✅ Advanced motion classification (ML-based)
- ✅ Posture detection (sitting vs standing)
- ✅ Through-wall sensing
- ✅ Activity recognition from CSI patterns
- ❌ Camera vision (add camera for hybrid mode)

### Training ML Model
After collecting CSI data:
```bash
python backend/train_csi_model.py --data calibration_data/
```

---

## Mode 4: WiFi Adapter Monitor 📶

**Perfect for:** No ESP hardware, have a WiFi adapter with monitor mode

### Prerequisites
- **WiFi adapter with monitor mode support**
  - Recommended: Alfa AWUS036ACH, AWUS036NHA
  - Built-in adapters: Check with `iw list | grep monitor`
- Linux (Ubuntu, Kali, etc.)
- Root/sudo access

### Setup Steps

1. **Check Monitor Mode Support**
   ```bash
   sudo iw list | grep -A 10 "Supported interface modes"
   ```
   - Should list "monitor" mode

2. **Enable Monitor Mode**
   ```bash
   sudo airmon-ng check kill  # Stop interfering processes
   sudo airmon-ng start wlan0  # Creates wlan0mon
   ```

3. **Run Setup Wizard**
   ```bash
   python setup_wizard.py
   ```
   - Select option `4` (WiFi Adapter)
   - Specify interface (e.g., wlan0mon)

4. **Start WiFi Monitor Script**
   ```bash
   sudo python backend/wifi_monitor.py --interface wlan0mon --channel 6
   ```

5. **Start Backend** (in another terminal)
   ```bash
   cd backend && python server.py
   ```

### How It Works
- Captures ambient WiFi packets from nearby devices
- Analyzes RSSI variance to detect motion
- Human movement disrupts WiFi signals → detected as variance spikes

### Features Available
- ✅ Presence detection
- ✅ Motion detection via ambient WiFi
- ✅ No ESP hardware needed
- ❌ Camera vision (add for hybrid mode)
- ⚠️ Requires root privileges

---

## Mode 5: Hybrid (Camera + WiFi) 🎯

**Perfect for:** Complete coverage, camera + out-of-frame WiFi tracking

### Prerequisites
- Camera (webcam)
- **Any one** of: ESP8266, ESP32, or WiFi adapter
- All dependencies from chosen modes

### The Power of Hybrid Mode

**Intelligent Handoff Logic:**
1. **In Camera View:** YOLO detects person, tracks with bounding boxes
2. **Person Exits Frame:** System notes last known position
3. **WiFi Takes Over:** Continues detecting motion via WiFi signals
4. **Person Re-enters:** Camera re-acquires, tracking ID preserved

### Setup Steps

1. **Setup Camera** (see Mode 1)
2. **Setup WiFi Hardware** (ESP8266/ESP32/WiFi Adapter)
3. **Run Setup Wizard**
   ```bash
   python setup_wizard.py
   ```
   - Select option `5` (Hybrid)
   - Select which WiFi hardware you have

4. **Configure Fusion Settings** in `config.yaml`:
   ```yaml
   fusion:
     camera_priority: true      # Use camera when available
     handoff_delay_ms: 500      # Wait 500ms before WiFi handoff
     tracking_timeout_s: 5      # Max time to track without detection
     confidence_threshold: 0.4  # Min confidence for valid detection
   ```

5. **Start System**
   ```bash
   # Terminal 1: Backend
   cd backend && python server.py

   # Terminal 2: Frontend
   cd frontend && npm run dev

   # Terminal 3: WiFi Monitor (if using adapter)
   sudo python backend/wifi_monitor.py --interface wlan0mon
   ```

### Features Available
- ✅ All camera features (YOLO, pose, activity)
- ✅ All WiFi features (presence, through-wall)
- ✅ **Intelligent handoff** when exiting camera
- ✅ Persistent tracking IDs across modalities
- ✅ 24/7 coverage (indoors + outdoors)

### UI Indicators
- **Green box:** Camera tracking
- **Orange box:** WiFi handoff active (out of camera)
- **Label:** `PERSON #1 (WiFi)` vs `PERSON #1 (Camera)`

---

## 🔧 Hardware Placement Tips

### ESP8266/ESP32 Placement
- **TX-RX Distance:** 2-5 meters optimal
- **Height:** Chest-height (1-1.5m) for best human detection
- **Obstructions:** Works through walls, but sensitivity decreases
- **Power:** USB or battery (5V, 500mA+)

### Camera Placement
- **FOV:** Position to cover entry/exit points
- **Lighting:** Ensure adequate lighting for YOLO
- **Angle:** Slight downward angle captures faces better
- **Privacy:** Respect privacy laws in your jurisdiction

### WiFi Adapter Placement
- **Central Location:** Place laptop/adapter centrally
- **Interference:** Avoid placing near microwave, metal objects
- **Channel:** Use channel with least congestion (`iwlist wlan0 scan`)

---

## 📊 Calibration Guide

### ESP8266/ESP32 Calibration
1. Keep area **empty and static** for 10 seconds
2. System auto-calibrates baseline variance
3. Adjust `variance_threshold` in config if needed:
   - Too sensitive? Increase threshold
   - Not detecting? Decrease threshold

### Camera Calibration
No calibration needed - YOLO is pre-trained!

### CSI Model Training
```bash
# 1. Collect data with labels
python backend/collect_csi_data.py --action walking --duration 60
python backend/collect_csi_data.py --action sitting --duration 60
python backend/collect_csi_data.py --action standing --duration 60

# 2. Train model
python backend/train_csi_model.py --epochs 50

# 3. Model saved to backend/models/csi_lstm.h5
```

---

## 🆘 Troubleshooting

### General Issues

**"Config not found" error**
```bash
# Run setup wizard first
python setup_wizard.py
```

**Frontend won't start**
```bash
cd frontend
npm install
npm run dev
```

**Backend crashes on startup**
```bash
# Check Python version
python --version  # Must be 3.9+

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Hardware-Specific Issues

**ESP8266: No RSSI data**
- Check Serial Monitor for WiFi connection
- Verify laptop IP in RX firmware
- Check firewall (allow UDP 8888)

**ESP32: CSI not working**
- Use ESP-IDF, not Arduino IDE
- Check ESP32-CSI-Tool repo for help
- Verify CSI is enabled in code

**WiFi Adapter: Permission denied**
- Run monitor script with sudo
- Check monitor mode: `iwconfig`

**Camera: No frame**
- Check camera permissions
- Verify device index in config.yaml
- Test: `ls /dev/video*`

---

## 📚 Next Steps

After hardware setup:
1. ✅ Verify detection in web dashboard
2. ✅ Tune sensitivity in config.yaml
3. ✅ Experiment with different placements
4. ✅ Train custom CSI models (ESP32)
5. ✅ Add activity recognition rules

## 🔗 Additional Resources

- [ESP32-CSI-Tool GitHub](https://github.com/stevenmhernandez/ESP32-CSI-Tool)
- [ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [MediaPipe Pose](https://google.github.io/mediapipe/solutions/pose.html)
- [Aircrack-ng Suite](https://www.aircrack-ng.org/)

---

**Author:** Sudeepa Wanigarathna  
**License:** MIT  
**Support:** Open an issue on GitHub
