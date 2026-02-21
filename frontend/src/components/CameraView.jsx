import React, { useEffect, useRef, useState } from 'react';

/**
 * CameraView Component
 * Displays live camera feed with detection overlays
 * Shows bounding boxes, tracking IDs, and pose skeletons
 */
const CameraView = ({ wsUrl }) => {
  const canvasRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [fps, setFps] = useState(0);
  const wsRef = useRef(null);
  const lastFrameTime = useRef(Date.now());
  const frameCount = useRef(0);

  useEffect(() => {
    // Connect to camera feed WebSocket
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[CameraView] WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          console.error('[CameraView] Error:', data.error);
          return;
        }

        if (data.frame) {
          renderFrame(data.frame);
          updateFPS();
        }
      } catch (err) {
        console.error('[CameraView] Parse error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('[CameraView] WebSocket error:', error);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('[CameraView] WebSocket closed');
      setConnected(false);
    };

    return () => {
      if (ws) ws.close();
    };
  }, [wsUrl]);

  const renderFrame = (base64Frame) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };

    img.src = `data:image/jpeg;base64,${base64Frame}`;
  };

  const updateFPS = () => {
    frameCount.current++;
    const now = Date.now();
    const elapsed = (now - lastFrameTime.current) / 1000;

    if (elapsed >= 1.0) {
      setFps(Math.round(frameCount.current / elapsed));
      frameCount.current = 0;
      lastFrameTime.current = now;
    }
  };

  return (
    <div className="camera-view">
      <div className="camera-header">
        <h3>📹 Camera Feed</h3>
        <div className="camera-status">
          <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '🟢 Live' : '🔴 Offline'}
          </span>
          {connected && <span className="fps-counter">{fps} FPS</span>}
        </div>
      </div>

      <div className="camera-container">
        <canvas
          ref={canvasRef}
          className="camera-canvas"
        />
        {!connected && (
          <div className="camera-placeholder">
            <p>📷 Waiting for camera feed...</p>
            <p style={{ fontSize: '0.9em', opacity: 0.7 }}>
              Make sure camera is enabled in config.yaml
            </p>
          </div>
        )}
      </div>

    </div>
  );
};

export default CameraView;
