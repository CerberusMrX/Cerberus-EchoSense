# Cerberus EchoSense - Quick Reference

## 🚀 Quick Start

```bash
# First time setup
python setup_wizard.py

# Start system
python start.py

# Open browser → http://localhost:5173
```

---

## 🔧 Hardware Modes

| Mode | Command | Hardware Needed |
|------|---------|-----------------|
| **Camera Only** | `python setup_wizard.py` → 1 | USB webcam |
| **ESP8266** | `python setup_wizard.py` → 2 | 2x ESP8266 |
| **ESP32 CSI** | `python setup_wizard.py` → 3 | 2x ESP32 |
| **WiFi Adapter** | `python setup_wizard.py` → 4 | Monitor-capable adapter |
| **Hybrid** | `python setup_wizard.py` → 5 | Camera + WiFi hardware |

---

## 📡 ESP8266 Setup

```bash
# 1. Flash TX
Arduino IDE → firmware/tx_main/tx_main.ino → Upload
Serial Monitor → Note MAC address

# 2. Flash RX
Edit rx_main.ino:
  - WIFI_SSID = "YourWiFi"
  - WIFI_PASS = "password"
  - targetMAC = TX MAC from step 1
  - backendIP = Your laptop IP

Upload → Done!

# 3. Start backend
cd backend && python server.py
```

---

## 🔬 ESP32 CSI Setup

```bash
# Option A: Arduino (simplified)
firmware/esp32_csi_tx/ → Upload to ESP32 #1
firmware/esp32_csi_rx/ → Upload to ESP32 #2

# Option B: ESP-IDF (production)
git clone https://github.com/stevenmhernandez/ESP32-CSI-Tool
# Follow their guide
```

---

## 📶 WiFi Adapter Mode

```bash
# Enable monitor mode
sudo airmon-ng start wlan0

# Start monitor
sudo python backend/wifi_monitor.py --interface wlan0mon

# Start backend (another terminal)
cd backend && python server.py
```

---

## 🧪 Training CSI Models

```bash
# Collect data
python backend/collect_csi_data.py --label walking --duration 60
python backend/collect_csi_data.py --label sitting --duration 60

# Train model
python backend/train_csi_model.py --data data/csi_samples/

# Update config.yaml
#   csi:
#     use_ml_classifier: true
#     model_path: "models/csi_lstm.h5"
```

---

## 🐛 Troubleshooting

### No camera feed?
```bash
ls /dev/video*  # Check camera exists
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### No ESP8266 data?
```bash
# Check Serial Monitor on RX
# Should see "RSS:-XX" values

# Check backend logs
# Should see "[UDP] Received RSSI..."

# Verify firewall
sudo ufw allow 8888/udp
```

### Frontend won't start?
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### WiFi adapter no monitor mode?
```bash
# Check support
iw list | grep monitor

# Try different adapter
# Recommended: Alfa AWUS036ACH
```

---

## 📝 Configuration

Edit `config.yaml` to customize:

```yaml
# Change camera device
camera:
  device: 1  # If /dev/video1

# Change YOLO model
yolo:
  model: "yolov8s.pt"  # Slower but more accurate

# Adjust WiFi thresholds
rssi:
  variance_threshold: 10.0  # Higher = less sensitive

# GPU acceleration
yolo:
  device: "cuda"  # or "cpu"
```

---

## 🎯 Features by Mode

### Camera Only
✅ Object detection  
✅ Pose estimation  
✅ Activity recognition  
❌ Through-wall  

### ESP8266
✅ Presence detection  
✅ Through-wall  
❌ Precise location  
❌ Pose  

### ESP32
✅ Advanced WiFi sensing  
✅ ML classification  
✅ Through-wall  
✅ Activity via CSI  

### WiFi Adapter
✅ No ESP needed  
✅ Ambient packet analysis  
⚠️ Needs root/sudo  

### Hybrid
✅ ALL features  
✅ Intelligent handoff  
✅ Best coverage  

---

## 📚 Documentation

- [README.md](README.md) - Full overview
- [HARDWARE_GUIDE.md](HARDWARE_GUIDE.md) - Hardware setup
- [setup_wizard.py](setup_wizard.py) - Interactive setup
- [firmware/*/README.md](firmware/) - Firmware guides

---

## 💡 Tips

**Best Placement**:
- Camera: Cover entry/exit points
- ESP8266/32: 2-5m apart, chest height
- TX/RX: Line of sight optimal but works through walls

**Performance**:
- YOLOv8n: Fastest (30+ FPS)
- YOLOv8s: Balanced (15-20 FPS)
- YOLOv8m: Accurate (10-15 FPS)

**GPU Acceleration**:
```bash
# Check CUDA available
python -c "import torch; print(torch.cuda.is_available())"

# Update config.yaml
yolo:
  device: "cuda"
```

---

## 🆘 Get Help

**Common Issues**:
1. Run `python setup_wizard.py` first
2. Check `config.yaml` exists
3. Verify hardware connections
4. Check backend logs for errors

**Still stuck?**
- Check HARDWARE_GUIDE.md for your mode
- Review firmware README files
- Consult walkthrough.md examples

---

**Quick Commands Summary**:
```bash
# Setup
python setup_wizard.py

# Start
python start.py

# Manual start
cd backend && python server.py  # Terminal 1
cd frontend && npm run dev      # Terminal 2

# WiFi Monitor
sudo python backend/wifi_monitor.py --interface wlan0mon

# Collect CSI data
python backend/collect_csi_data.py --label walking --duration 60

# Train model
python backend/train_csi_model.py --data data/csi_samples/
```

---

*Cerberus EchoSense v2.0 - Multi-Modal Detection Made Easy*
