"""
Cerberus EchoSense - Modular AI Detection Engine
Supports multiple hardware configurations with intelligent sensor fusion
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from pathlib import Path
import cv2

logger = logging.getLogger(__name__)

class DetectionMode(Enum):
    CAMERA_ONLY = "camera_only"
    ESP8266 = "esp8266"
    ESP32 = "esp32"
    WIFI_ADAPTER = "wifi_adapter"
    HYBRID = "hybrid"

class TrackingSource(Enum):
    CAMERA = "camera"
    WIFI_RSSI = "wifi_rssi"
    WIFI_CSI = "wifi_csi"
    WIFI_MONITOR = "wifi_monitor"
    FUSION = "fusion"
    LOST = "lost"

@dataclass
class DetectionResult:
    """Unified detection result from any source"""
    timestamp: float
    source: TrackingSource
    motion_detected: bool
    confidence: float
    
    # Camera-specific
    bboxes: List[Tuple[int, int, int, int]] = None  # [(x1,y1,x2,y2), ...]
    class_ids: List[int] = None
    class_names: List[str] = None
    tracking_ids: List[int] = None
    poses: List[Dict] = None  # [{'keypoints': [[x,y,conf], ...]}]
    
    # WiFi-specific
    rssi: float = None
    rssi_variance: float = None
    csi_data: List[float] = None
    
    # Activity recognition
    activity: str = "UNKNOWN"
    activity_confidence: float = 0.0
    
    # Metadata
    out_of_frame: bool = False
    handoff_active: bool = False

class CameraVisionModule:
    """Computer vision with YOLO + MediaPipe pose estimation"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config['hardware']['camera']['enabled']
        self.latest_frame = None
        
        if not self.enabled:
            return
        
        self.device = config['hardware']['camera']['device']
        self.yolo_config = config['detection']['yolo']
        self.pose_config = config['detection']['pose']
        
        self._init_camera()
        self._init_yolo()
        self._init_pose()
        
        self.tracking_id_counter = 0
        self.tracked_objects = {}
        
        logger.info("Camera Vision Module initialized")
    
    def _init_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.device)
            
            res = self.config['hardware']['camera']['resolution']
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.config['hardware']['camera']['fps'])
            
            logger.info(f"Camera opened: device {self.device}")
        except Exception as e:
            logger.error(f"Camera init failed: {e}")
            self.enabled = False
    
    def _init_yolo(self):
        """Initialize YOLO model"""
        try:
            from ultralytics import YOLO
            self.yolo = YOLO(self.yolo_config['model'])
            logger.info(f"YOLO model loaded: {self.yolo_config['model']}")
        except Exception as e:
            logger.error(f"YOLO init failed: {e}")
            self.yolo = None
    
    def _init_pose(self):
        """Initialize MediaPipe Pose"""
        if not self.pose_config['enabled']:
            self.poser = None
            return

        try:
            import mediapipe as mp
            
            # Handle different mediapipe version structures
            if hasattr(mp, 'solutions'):
                self.mp_pose = mp.solutions.pose
            else:
                import mediapipe.python.solutions.pose as mp_pose
                self.mp_pose = mp_pose
                
            self.poser = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe Pose initialized")
        except Exception as e:
            logger.warning(f"Pose estimation init failed: {e}")
            self.poser = None
    
    def detect(self) -> Optional[DetectionResult]:
        """Run detection on current frame"""
        if not self.enabled or self.cap is None or not self.cap.isOpened():
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        # Run YOLO detection with configured classes
        results = self.yolo(
            frame, 
            conf=self.yolo_config['confidence'], 
            classes=self.yolo_config.get('classes', [0]),
            verbose=False
        )[0]
        self.latest_frame = results.plot() # Store annotated frame for streaming
        
        boxes = results.boxes
        bboxes = []
        class_ids = []
        class_names = []
        tracking_ids = []
        poses = []
        
        if len(boxes) > 0:
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                cls_id = int(box.cls[0])
                cls_name = results.names[cls_id]
                conf = float(box.conf[0])
                
                bboxes.append((x1, y1, x2, y2))
                class_ids.append(cls_id)
                class_names.append(cls_name)
                
                # Simple centroid tracking
                tracking_id = getattr(box, 'id', None)
                if tracking_id is not None:
                    tracking_ids.append(int(tracking_id[0]))
                else:
                    tracking_ids.append(self._assign_tracking_id((x1, y1, x2, y2)))
                
                # Pose estimation for person
                if cls_name == "person" and self.poser:
                    person_crop = frame[y1:y2, x1:x2]
                    if person_crop.size > 0:
                        rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                        pose_results = self.poser.process(rgb)
                        if pose_results.pose_landmarks:
                            # Convert normalized coordinates to pixel coordinates in the full frame
                            h, w = person_crop.shape[:2]
                            kp = []
                            for lm in pose_results.pose_landmarks.landmark:
                                # lm.x/y are 0-1 within the crop
                                pkx = x1 + (lm.x * w)
                                pky = y1 + (lm.y * h)
                                kp.append([pkx, pky, lm.visibility])
                            poses.append({'keypoints': kp, 'is_animal': False})
                        else:
                            poses.append(None)
                    else:
                        poses.append(None)
                elif cls_name in ["cat", "dog", "bird"]:
                    # Synthetic skeletal representation for animals (4 legs/corners + head/tail approximation)
                    # We just use the bbox to create a "technical" representation
                    w = x2 - x1
                    h = y2 - y1
                    # 5 points: Center, 4 corners
                    animal_kp = [
                        [x1 + w/2, y1 + h/2, 1.0], # Center
                        [x1 + 0.1*w, y1 + 0.1*h, 1.0], # Top Left
                        [x2 - 0.1*w, y1 + 0.1*h, 1.0], # Top Right
                        [x1 + 0.1*w, y2 - 0.1*h, 1.0], # Bottom Left
                        [x2 - 0.1*w, y2 - 0.1*h, 1.0], # Bottom Right
                    ]
                    poses.append({'keypoints': animal_kp, 'is_animal': True})
                else:
                    poses.append(None)
        
        motion_detected = len(bboxes) > 0
        
        return DetectionResult(
            timestamp=time.time(),
            source=TrackingSource.CAMERA,
            motion_detected=motion_detected,
            confidence=float(np.mean([float(b.conf[0]) for b in boxes])) if len(boxes) > 0 else 0.0,
            bboxes=bboxes,
            class_ids=class_ids,
            class_names=class_names,
            tracking_ids=tracking_ids,
            poses=poses
        )
    
    def _assign_tracking_id(self, bbox: Tuple[int, int, int, int]) -> int:
        """Simple centroid-based tracking"""
        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        centroid = (cx, cy)
        
        min_dist = float('inf')
        closest_id = None
        
        for tid, tracked in self.tracked_objects.items():
            dist = np.sqrt((tracked['centroid'][0] - cx)**2 + (tracked['centroid'][1] - cy)**2)
            if dist < min_dist and dist < 100:
                min_dist = dist
                closest_id = tid
        
        if closest_id is not None:
            self.tracked_objects[closest_id]['centroid'] = centroid
            self.tracked_objects[closest_id]['last_seen'] = time.time()
            return closest_id
        else:
            new_id = self.tracking_id_counter
            self.tracking_id_counter += 1
            self.tracked_objects[new_id] = {'centroid': centroid, 'last_seen': time.time()}
            return new_id
    
    def get_frame(self):
        """Get latest processed frame"""
        return self.latest_frame
    
    def cleanup(self):
        if hasattr(self, 'cap'):
            self.cap.release()

class ESP8266RSSIModule:
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config['hardware']['esp8266']['enabled']
        if not self.enabled: return
        self.rssi_config = config['detection']['rssi']
        self.window = []
        logger.info("ESP8266 RSSI Module initialized")
    
    def process_rssi(self, rssi: int) -> DetectionResult:
        self.window.append(rssi)
        if len(self.window) > self.rssi_config['window_size']:
            self.window.pop(0)
        
        if len(self.window) < 5:
            return DetectionResult(time.time(), TrackingSource.WIFI_RSSI, False, 0.0, rssi=float(rssi))
            
        variance = np.var(self.window)
        motion = variance > self.rssi_config['variance_threshold']
        confidence = min(variance / 20.0, 1.0)
        
        return DetectionResult(
            timestamp=time.time(),
            source=TrackingSource.WIFI_RSSI,
            motion_detected=motion,
            confidence=float(confidence),
            rssi=float(rssi),
            rssi_variance=float(variance),
            activity="WALKING" if motion else "STILL"
        )

class ESP32CSIModule:
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config['hardware']['esp32']['enabled']
        if not self.enabled: return
        self.csi_config = config['detection']['csi']
        self.window = []
        self.ml_model = None
        if self.csi_config['use_ml_classifier']:
            self._load_ml_model()
        logger.info("ESP32 CSI Module initialized")
    
    def _load_ml_model(self):
        try:
            import tensorflow as tf
            p = self.csi_config['model_path']
            if Path(p).exists():
                self.ml_model = tf.keras.models.load_model(p)
                logger.info(f"CSI ML model loaded: {p}")
        except Exception as e:
            logger.warning(f"CSI ML load failed: {e}")
            
    def process_csi(self, csi_data: List[float]) -> DetectionResult:
        self.window.append(csi_data)
        if len(self.window) > self.csi_config['window_size']:
            self.window.pop(0)
            
        variance = np.var(csi_data)
        motion = variance > self.csi_config['motion_threshold']
        confidence = min(variance / 1.0, 1.0)
        
        return DetectionResult(
            timestamp=time.time(),
            source=TrackingSource.WIFI_CSI,
            motion_detected=motion,
            confidence=float(confidence),
            csi_data=csi_data,
            activity="MOTION" if motion else "CLEAR"
        )

class WiFiMonitorModule:
    def __init__(self, config: Dict):
        self.enabled = config['hardware']['wifi_adapter']['enabled']
        if not self.enabled: return
        self.config = config['detection']['wifi_monitor']
        self.packets = []
        logger.info("WiFi Monitor Module initialized")
        
    def process_packet(self, data: Dict) -> DetectionResult:
        self.packets.append(data.get('rssi', -100))
        if len(self.packets) > self.config['packet_window']:
            self.packets.pop(0)
        
        variance = np.var(self.packets) if len(self.packets) > 5 else 0
        motion = variance > 10.0
        return DetectionResult(time.time(), TrackingSource.WIFI_MONITOR, motion, 0.5)

class SensorFusionEngine:
    def __init__(self, config: Dict):
        self.config = config['fusion']
        self.handoff_start = None
        
    def fuse(self, cam: Optional[DetectionResult], wifi: Optional[DetectionResult]) -> DetectionResult:
        now = time.time()
        
        if cam and cam.motion_detected:
            self.handoff_start = None
            res = cam
            res.source = TrackingSource.FUSION
            return res
            
        if cam and not cam.motion_detected:
            if self.handoff_start is None: self.handoff_start = now
            if (now - self.handoff_start) * 1000 > self.config['handoff_delay_ms']:
                if wifi and wifi.motion_detected:
                    res = wifi
                    res.handoff_active = True
                    res.out_of_frame = True
                    res.source = TrackingSource.FUSION
                    return res
                    
        return cam or wifi or DetectionResult(now, TrackingSource.LOST, False, 0.0)

class MLEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.mode = DetectionMode(config['hardware']['mode'])
        self.camera = CameraVisionModule(config) if config['hardware']['camera']['enabled'] else None
        self.esp8266 = ESP8266RSSIModule(config) if config['hardware']['esp8266']['enabled'] else None
        self.esp32 = ESP32CSIModule(config) if config['hardware']['esp32']['enabled'] else None
        self.wifi_mon = WiFiMonitorModule(config) if config['hardware']['wifi_adapter']['enabled'] else None
        self.fusion = SensorFusionEngine(config) if self.mode == DetectionMode.HYBRID else None
        logger.info("ML Engine Ready")
        
    def process_camera_frame(self) -> Optional[DetectionResult]:
        return self.camera.detect() if self.camera else None
        
    def process_esp8266_rssi(self, rssi: int) -> DetectionResult:
        return self.esp8266.process_rssi(rssi) if self.esp8266 else None
        
    def process_esp32_csi(self, csi: List[float]) -> DetectionResult:
        return self.esp32.process_csi(csi) if self.esp32 else None
        
    def get_fused_result(self, cam, wifi) -> DetectionResult:
        if self.fusion: return self.fusion.fuse(cam, wifi)
        return cam or wifi
        
    def get_camera_frame(self):
        return self.camera.get_frame() if self.camera else None
        
    def cleanup(self):
        if self.camera: self.camera.cleanup()
