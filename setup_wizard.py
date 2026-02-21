#!/usr/bin/env python3
"""
Cerberus EchoSense Setup Wizard
Interactive configuration and dependency installer
"""

import os
import sys
import subprocess
import platform
import shutil
import site
import importlib
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def check_python_version():
    """Check if Python version is 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python 3.9+ required. You have {version.major}.{version.minor}")
        sys.exit(1)
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")

def detect_camera():
    """Auto-detect available cameras"""
    try:
        import cv2
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    return i
        return None
    except:
        return None

def detect_wifi_adapter():
    """Detect WiFi adapters capable of monitor mode"""
    if platform.system() != "Linux":
        return None
    
    try:
        result = subprocess.run(['iw', 'dev'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Interface' in line:
                    return line.split()[-1]
    except:
        pass
    return None

def select_hardware_mode():
    """Interactive hardware selection"""
    print_header("HARDWARE CONFIGURATION")
    
    print("Detecting available hardware...")
    camera_id = detect_camera()
    wifi_adapter = detect_wifi_adapter()
    
    print(f"\n{Colors.BOLD}Auto-Detection Results:{Colors.END}")
    print(f"  📷 Camera: {Colors.GREEN}Found (device {camera_id}){Colors.END}" if camera_id is not None else f"  📷 Camera: {Colors.YELLOW}Not detected{Colors.END}")
    print(f"  📶 WiFi Adapter: {Colors.GREEN}Found ({wifi_adapter}){Colors.END}" if wifi_adapter else f"  📶 WiFi Adapter: {Colors.YELLOW}Not detected{Colors.END}")
    
    print(f"\n{Colors.BOLD}Available Modes:{Colors.END}")
    print(f"  {Colors.CYAN}1{Colors.END}. Camera Only (YOLO + Pose Detection)")
    print(f"  {Colors.CYAN}2{Colors.END}. ESP8266 RSSI (WiFi presence detection)")
    print(f"  {Colors.CYAN}3{Colors.END}. ESP32 CSI (Advanced WiFi sensing)")
    print(f"  {Colors.CYAN}4{Colors.END}. WiFi Adapter Monitor Mode")
    print(f"  {Colors.CYAN}5{Colors.END}. Hybrid (Camera + WiFi hardware)")
    
    while True:
        choice = input(f"\n{Colors.BOLD}Select mode [1-5]:{Colors.END} ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            return int(choice), camera_id, wifi_adapter
        print_error("Invalid choice. Please enter 1-5.")

def install_dependencies(mode, use_gpu=False):
    """Install required dependencies based on mode"""
    print_header("INSTALLING DEPENDENCIES")
    
    base_deps = ["fastapi", "uvicorn", "websockets", "numpy", "pyyaml", "python-multipart"]
    
    mode_deps = {
        1: ["opencv-python", "ultralytics", "mediapipe", "pillow"],  # Camera
        2: [],  # ESP8266 - no extra deps
        3: ["tensorflow", "scikit-learn", "pandas"],  # ESP32 CSI
        4: ["scapy"],  # WiFi Monitor
        5: ["opencv-python", "ultralytics", "mediapipe", "pillow", "tensorflow", "scikit-learn"]  # Hybrid
    }
    
    all_deps = base_deps + mode_deps.get(mode, [])
    
    # Detect if we are in a virtual environment
    is_venv = sys.prefix != sys.base_prefix
    pip_args = ["--user"] if not is_venv else []
    
    # Update pip first
    print_info("Updating pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"] + pip_args, 
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Invalidate caches to see new packages
    try:
        importlib.invalidate_caches()
        if hasattr(site, 'main'):
            site.main()
    except:
        pass

    # Install dependencies
    for dep in all_deps:
        print(f"  Installing {dep}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", dep] + pip_args,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓{Colors.END}")
        else:
            msg = f"pip install {dep}" + (" --user" if not is_venv else "")
            print(f"{Colors.YELLOW}⚠ (check connection or run manually: {msg}){Colors.END}")
    
    # Torch for GPU support
    if use_gpu and mode in [1, 3, 5]:
        print_info("Installing PyTorch with GPU support...")
        subprocess.run([sys.executable, "-m", "pip", "install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cu118"],
                       check=False)

def download_models(mode):
    """Download required ML models"""
    if mode not in [1, 3, 5]:
        return
    
    print_header("DOWNLOADING ML MODELS")
    
    models_dir = Path("backend/models")
    models_dir.mkdir(exist_ok=True)
    
    if mode in [1, 5]:  # Camera modes
        print_info("Downloading YOLOv8 nano model...")
        try:
            from ultralytics import YOLO
            model = YOLO('yolov8n.pt')
            print_success("YOLOv8 downloaded")
        except Exception as e:
            print_warning(f"YOLO download failed: {e}")
        
        print_info("MediaPipe will auto-download on first use")
    
    if mode in [3, 5]:  # ESP32 modes
        print_info("CSI LSTM model requires training data")
        print_warning("Run 'python backend/train_csi_model.py' after collecting calibration data")

def create_config(mode, camera_id, wifi_adapter, use_gpu):
    """Generate config.yaml based on selections"""
    print_header("GENERATING CONFIGURATION")
    
    import yaml
    
    config_path = Path("config.yaml")
    config = {}
    
    if config_path.exists():
        backup = config_path.with_suffix('.yaml.bak')
        # Copy instead of rename so we can read from it, or just read then rename
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Now backup the old one
        import shutil
        shutil.copy(config_path, backup)
        print_info(f"Backed up existing config to {backup}")
    else:
        # Create a default structure if no config exists
        config = {
            'hardware': {
                'mode': 'auto',
                'camera': {'enabled': False, 'device': 0, 'resolution': [640, 480], 'fps': 30, 'backend': 'opencv'},
                'esp8266': {'enabled': False, 'udp_port': 8888, 'tx_mac': 'AA:BB:CC:DD:EE:FF'},
                'esp32': {'enabled': False, 'udp_port': 8889, 'csi_format': 'csv', 'tx_mac': 'AA:BB:CC:DD:EE:FF'},
                'wifi_adapter': {'enabled': False, 'interface': 'wlan0', 'monitor_mode': True, 'channel': 6}
            },
            'detection': {
                'yolo': {'model': 'yolov8n.pt', 'confidence': 0.5, 'iou_threshold': 0.4, 'classes': [0], 'device': 'cpu'},
                'pose': {'enabled': True, 'model': 'mediapipe', 'min_confidence': 0.5},
                'rssi': {'window_size': 50, 'variance_threshold': 5.0, 'calibration_duration': 10},
                'csi': {'window_size': 100, 'motion_threshold': 0.3, 'use_ml_classifier': True, 'model_path': 'models/csi_lstm.h5'},
                'wifi_monitor': {'packet_window': 200, 'rssi_threshold': -70, 'motion_algorithm': 'variance'},
                'activity': {'enabled': True, 'classes': ['WALKING', 'STANDING', 'SITTING', 'RUNNING', 'LYING'], 'model_path': 'models/activity_rf.pkl'}
            },
            'fusion': {'camera_priority': True, 'handoff_delay_ms': 500, 'tracking_timeout_s': 5, 'confidence_threshold': 0.4},
            'server': {'host': '0.0.0.0', 'port': 8000, 'cors_origins': ['*'], 'websocket_ping_interval': 30},
            'logging': {'level': 'INFO', 'file': 'cerberus.log', 'console': True}
        }
    
    # Update based on mode
    mode_names = {1: "camera_only", 2: "esp8266", 3: "esp32", 4: "wifi_adapter", 5: "hybrid"}
    config['hardware']['mode'] = mode_names[mode]
    
    if mode in [1, 5]:
        config['hardware']['camera']['enabled'] = True
        if camera_id is not None:
            config['hardware']['camera']['device'] = camera_id
        if use_gpu:
            config['detection']['yolo']['device'] = 'cuda'
    
    if mode == 2:
        config['hardware']['esp8266']['enabled'] = True
    
    if mode in [3, 5]:
        config['hardware']['esp32']['enabled'] = True
    
    if mode == 4:
        config['hardware']['wifi_adapter']['enabled'] = True
        if wifi_adapter:
            config['hardware']['wifi_adapter']['interface'] = wifi_adapter
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print_success(f"Configuration saved to {config_path}")

def setup_frontend():
    """Install frontend dependencies"""
    print_header("SETTING UP FRONTEND")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print_error("Frontend directory not found")
        return
    
    print_info("Installing Node.js packages...")
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Frontend dependencies installed")
        else:
            print_error("npm install failed. Run manually: cd frontend && npm install")
    except FileNotFoundError:
        print_error("npm command not found. Please install Node.js and npm.")
    except Exception as e:
        print_error(f"Failed to run npm: {e}")

def print_next_steps(mode):
    """Print instructions for next steps"""
    print_header("SETUP COMPLETE!")
    
    print(f"\n{Colors.BOLD}📋 Next Steps:{Colors.END}\n")
    
    if mode == 2:
        print(f"{Colors.YELLOW}ESP8266 Setup:{Colors.END}")
        print("  1. Flash TX: firmware/tx_main/tx_main.ino")
        print("  2. Flash RX: firmware/rx_main/rx_main.ino")
        print("  3. Update TX MAC address in config.yaml")
        print("  4. Configure RX with your WiFi credentials\n")
    
    elif mode == 3:
        print(f"{Colors.YELLOW}ESP32 Setup:{Colors.END}")
        print("  1. Install ESP-IDF: https://docs.espressif.com/projects/esp-idf")
        print("  2. Flash firmware: firmware/esp32_csi_tx/ and firmware/esp32_csi_rx/")
        print("  3. Update config.yaml with ESP32 MAC addresses\n")
    
    elif mode == 4:
        print(f"{Colors.YELLOW}WiFi Adapter Setup:{Colors.END}")
        print(f"  1. Enable monitor mode: sudo airmon-ng start {wifi_adapter or 'wlan0'}")
        print("  2. Update config.yaml with monitor interface name\n")
    
    print(f"{Colors.BOLD}🚀 Start the system:{Colors.END}")
    print(f"  {Colors.CYAN}Terminal 1:{Colors.END} cd backend && python server.py")
    print(f"  {Colors.CYAN}Terminal 2:{Colors.END} cd frontend && npm run dev")
    print(f"\n  Open browser: {Colors.GREEN}http://localhost:5173{Colors.END}\n")
    
    print(f"{Colors.BOLD}📖 Documentation:{Colors.END}")
    print("  README.md - System overview")
    print("  HARDWARE_GUIDE.md - Hardware setup details\n")

def main():
    print_header("CERBERUS ECHOSENSE SETUP WIZARD")
    print(f"{Colors.CYAN}Author: Sudeepa Wanigarathna{Colors.END}\n")
    
    # Check Python version
    print_info("Checking Python version...")
    check_python_version()
    
    # Select hardware mode
    mode, camera_id, wifi_adapter = select_hardware_mode()
    
    # GPU support
    use_gpu = False
    if mode in [1, 3, 5]:
        gpu_choice = input(f"\n{Colors.BOLD}Enable GPU acceleration? [y/N]:{Colors.END} ").strip().lower()
        use_gpu = gpu_choice == 'y'
    
    # Install dependencies
    install_dependencies(mode, use_gpu)
    
    # Download models
    download_models(mode)
    
    # Create config
    create_config(mode, camera_id, wifi_adapter, use_gpu)
    
    # Setup frontend
    setup_frontend()
    
    # Print next steps
    print_next_steps(mode)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelled by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)
