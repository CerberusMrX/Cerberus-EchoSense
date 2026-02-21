import asyncio
import uvicorn
import yaml
import logging
import json
import base64
import cv2
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional

# Import ML Engine
from ml_engine import MLEngine, DetectionResult, TrackingSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config_path = Path(__file__).parent.parent / "config.yaml"
if not config_path.exists():
    logger.error(f"Config file not found: {config_path}")
    logger.error("Run setup_wizard.py first!")
    exit(1)

with open(config_path, 'r') as f:
    CONFIG = yaml.safe_load(f)

logger.info(f"Loaded configuration: mode={CONFIG['hardware']['mode']}")

# FastAPI app
app = FastAPI(title="Cerberus EchoSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG['server']['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
websocket_clients: List[WebSocket] = []
ml_engine: Optional[MLEngine] = None
latest_detection: Optional[DetectionResult] = None

# ================== ML Engine Initialization ==================

@app.on_event("startup")
async def startup_event():
    """Initialize ML engine and start UDP listener"""
    global ml_engine
    
    logger.info("Starting Cerberus EchoSense Backend...")
    
    # Initialize ML Engine
    try:
        ml_engine = MLEngine(CONFIG)
        logger.info("✓ ML Engine initialized")
    except Exception as e:
        logger.error(f"ML Engine init failed: {e}")
        ml_engine = None
    
    # Start UDP listeners for ESP hardware
    if CONFIG['hardware']['esp8266']['enabled']:
        port = CONFIG['hardware']['esp8266']['udp_port']
        asyncio.create_task(start_esp8266_udp_listener(port))
        logger.info(f"✓ ESP8266 UDP listener on port {port}")
    
    if CONFIG['hardware']['esp32']['enabled']:
        port = CONFIG['hardware']['esp32']['udp_port']
        asyncio.create_task(start_esp32_udp_listener(port))
        logger.info(f"✓ ESP32 UDP listener on port {port}")
    
    # Start camera processing loop if enabled
    if CONFIG['hardware']['camera']['enabled']:
        asyncio.create_task(camera_processing_loop())
        logger.info("✓ Camera processing loop started")
    
    logger.info("=" * 60)
    logger.info(f"Mode: {CONFIG['hardware']['mode'].upper()}")
    logger.info("Backend ready!")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global ml_engine
    if ml_engine:
        ml_engine.cleanup()
    logger.info("Backend shutdown complete")

# ================== UDP Listeners ==================

class ESP8266UDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol for ESP8266 RSSI data"""
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        message = data.decode().strip()
        
        try:
            # Expected format: "RSS:-50"
            if message.startswith("RSS:"):
                rssi_val = int(message.split(":")[1])
                
                if ml_engine:
                    result = ml_engine.process_esp8266_rssi(rssi_val)
                    asyncio.create_task(broadcast_detection(result))
        except Exception as e:
            logger.error(f"ESP8266 packet parse error: {e}")

class ESP32UDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol for ESP32 CSI data"""
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        message = data.decode().strip()
        
        try:
            # Expected format: CSV with 64 subcarrier amplitudes
            # "timestamp,amp0,amp1,...,amp63"
            parts = message.split(',')
            if len(parts) >= 64:
                csi_data = [float(x) for x in parts[1:65]]  # Skip timestamp
                
                if ml_engine:
                    result = ml_engine.process_esp32_csi(csi_data)
                    asyncio.create_task(broadcast_detection(result))
        except Exception as e:
            logger.error(f"ESP32 CSI parse error: {e}")

async def start_esp8266_udp_listener(port: int):
    """Start ESP8266 UDP server"""
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(
        lambda: ESP8266UDPProtocol(),
        local_addr=("0.0.0.0", port)
    )

async def start_esp32_udp_listener(port: int):
    """Start ESP32 UDP server"""
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(
        lambda: ESP32UDPProtocol(),
        local_addr=("0.0.0.0", port)
    )

# ================== Camera Processing ==================

async def camera_processing_loop():
    """Continuous camera frame processing"""
    global latest_detection
    
    fps = CONFIG['hardware']['camera']['fps']
    frame_delay = 1.0 / fps
    
    logger.info(f"Camera loop started at {fps} FPS")
    
    while True:
        try:
            if ml_engine and ml_engine.camera:
                result = ml_engine.process_camera_frame()
                
                if result:
                    # In hybrid mode, fuse with WiFi
                    if CONFIG['hardware']['mode'] == 'hybrid':
                        # Get latest WiFi result (cached from UDP)
                        wifi_result = getattr(ml_engine, '_last_wifi_result', None)
                        result = ml_engine.get_fused_result(result, wifi_result)
                    
                    latest_detection = result
                    await broadcast_detection(result)
            
            await asyncio.sleep(frame_delay)
            
        except Exception as e:
            logger.error(f"Camera processing error: {e}")
            await asyncio.sleep(1.0)

# ================== WebSocket Broadcasting ==================

async def broadcast_detection(result: DetectionResult):
    """Broadcast detection result to all WebSocket clients"""
    global latest_detection
    latest_detection = result
    
    # Serialize result
    message = serialize_detection_result(result)
    
    # Broadcast to all connected clients
    dead_clients = []
    for client in websocket_clients:
        try:
            await client.send_text(json.dumps(message))
        except:
            dead_clients.append(client)
    
    # Remove dead clients
    for client in dead_clients:
        websocket_clients.remove(client)

def serialize_detection_result(result: DetectionResult) -> dict:
    """Convert DetectionResult to JSON-serializable dict"""
    return {
        "timestamp": result.timestamp,
        "source": result.source.value,
        "motion": result.motion_detected,
        "confidence": result.confidence,
        
        # Camera data
        "bboxes": result.bboxes or [],
        "class_ids": result.class_ids or [],
        "class_names": result.class_names or [],
        "tracking_ids": result.tracking_ids or [],
        "poses": result.poses or [],
        
        # WiFi data
        "rssi": result.rssi,
        "rssi_var": result.rssi_variance,
        "csi": result.csi_data or [],
        
        # Activity
        "activity": result.activity,
        "activity_conf": result.activity_confidence,
        
        # Metadata
        "out_of_frame": result.out_of_frame,
        "handoff_active": result.handoff_active
    }

# ================== WebSocket Endpoint ==================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket for detection data"""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    logger.info(f"WebSocket client connected. Total: {len(websocket_clients)}")
    
    # Send initial status
    await websocket.send_text(json.dumps({
        "type": "status",
        "mode": CONFIG['hardware']['mode'],
        "camera_enabled": CONFIG['hardware']['camera']['enabled'],
        "esp8266_enabled": CONFIG['hardware']['esp8266']['enabled'],
        "esp32_enabled": CONFIG['hardware']['esp32']['enabled'],
        "wifi_adapter_enabled": CONFIG['hardware']['wifi_adapter']['enabled']
    }))
    
    try:
        while True:
            # Keep connection alive (client may send pings)
            data = await websocket.receive_text()
            
            # Handle client commands if needed
            if data == "get_latest":
                if latest_detection:
                    msg = serialize_detection_result(latest_detection)
                    await websocket.send_text(json.dumps(msg))
                    
    except WebSocketDisconnect:
        websocket_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(websocket_clients)}")

# ================== Camera Feed Streaming ==================

@app.websocket("/ws/camera")
async def camera_feed_websocket(websocket: WebSocket):
    """Stream camera feed with bounding boxes"""
    await websocket.accept()
    
    if not ml_engine or not ml_engine.camera:
        await websocket.send_text(json.dumps({"error": "Camera not enabled"}))
        await websocket.close()
        return
    
    logger.info("Camera feed WebSocket connected")
    
    try:
        while True:
            frame = ml_engine.get_camera_frame()
            
            if frame is not None:
                # Draw bounding boxes if we have detections
                annotated_frame = frame.copy()
                
                if latest_detection and latest_detection.bboxes:
                    for i, bbox in enumerate(latest_detection.bboxes):
                        x1, y1, x2, y2 = bbox
                        
                        # Draw bbox
                        color = (0, 255, 0) if not latest_detection.out_of_frame else (0, 165, 255)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                        
                        # Draw label
                        label = latest_detection.class_names[i] if i < len(latest_detection.class_names) else "object"
                        tid = latest_detection.tracking_ids[i] if i < len(latest_detection.tracking_ids) else i
                        conf = latest_detection.confidence
                        
                        text = f"{label} #{tid} ({conf:.2f})"
                        cv2.putText(annotated_frame, text, (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        # Draw pose if available
                        if latest_detection.poses and i < len(latest_detection.poses):
                            pose = latest_detection.poses[i]
                            if pose and pose.get('keypoints'):
                                kp = pose['keypoints']
                                is_animal = pose.get('is_animal', False)
                                
                                # Color based on type
                                pose_color = (0, 255, 65) if not is_animal else (0, 212, 255) # Green for human, Cyan for animal
                                
                                if not is_animal and len(kp) >= 33: # Standard MediaPipe
                                    # Define stick figure connections (indices)
                                    connections = [
                                        (11, 12), (11, 13), (13, 15), # L-Arm
                                        (12, 14), (14, 16), # R-Arm
                                        (11, 23), (12, 24), (23, 24), # Torso
                                        (23, 25), (25, 27), # L-Leg
                                        (24, 26), (26, 28)  # R-Leg
                                    ]
                                    
                                    # Draw joints
                                    for idx in [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]:
                                        if kp[idx][2] > 0.5:
                                            cv2.circle(annotated_frame, (int(kp[idx][0]), int(kp[idx][1])), 3, pose_color, -1)
                                            
                                    # Draw bones
                                    for start_idx, end_idx in connections:
                                        if kp[start_idx][2] > 0.5 and kp[end_idx][2] > 0.5:
                                            cv2.line(annotated_frame, 
                                                    (int(kp[start_idx][0]), int(kp[start_idx][1])), 
                                                    (int(kp[end_idx][0]), int(kp[end_idx][1])), 
                                                    pose_color, 1)
                                                    
                                elif is_animal: # Synthetic animal skeleton
                                    # 0: Center, 1-4: Corners
                                    for idx in range(1, 5):
                                        cv2.line(annotated_frame, 
                                                (int(kp[0][0]), int(kp[0][1])), 
                                                (int(kp[idx][0]), int(kp[idx][1])), 
                                                pose_color, 1)
                                        cv2.circle(annotated_frame, (int(kp[idx][0]), int(kp[idx][1])), 2, pose_color, -1)
                
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                jpg_bytes = base64.b64encode(buffer).decode('utf-8')
                
                await websocket.send_text(json.dumps({
                    "frame": jpg_bytes,
                    "timestamp": latest_detection.timestamp if latest_detection else 0
                }))
            
            await asyncio.sleep(1.0 / 15)  # 15 FPS for streaming
            
    except WebSocketDisconnect:
        logger.info("Camera feed WebSocket disconnected")

# ================== HTTP Endpoints ==================

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "Cerberus EchoSense API",
        "version": "2.0",
        "mode": CONFIG['hardware']['mode'],
        "endpoints": {
            "ws": "/ws - Main detection data stream",
            "ws_camera": "/ws/camera - Camera feed stream",
            "config": "/api/config - Get configuration",
            "status": "/api/status - System status"
        }
    }

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return CONFIG

@app.get("/api/status")
async def get_status():
    """Get system status"""
    status = {
        "mode": CONFIG['hardware']['mode'],
        "ml_engine_initialized": ml_engine is not None,
        "connected_clients": len(websocket_clients),
        "latest_detection": serialize_detection_result(latest_detection) if latest_detection else None
    }
    
    if ml_engine:
        status["modules"] = {
            "camera": ml_engine.camera is not None and ml_engine.camera.enabled,
            "esp8266": ml_engine.esp8266 is not None and ml_engine.esp8266.enabled,
            "esp32": ml_engine.esp32 is not None and ml_engine.esp32.enabled,
            "wifi_monitor": ml_engine.wifi_monitor is not None and ml_engine.wifi_monitor.enabled,
            "fusion": ml_engine.fusion is not None
        }
    
    return status

# ================== Main Entry Point ==================

if __name__ == "__main__":
    server_config = CONFIG['server']
    
    uvicorn.run(
        app,
        host=server_config['host'],
        port=server_config['port'],
        log_level=CONFIG['logging']['level'].lower()
    )
