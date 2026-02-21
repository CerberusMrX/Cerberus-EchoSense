import React, { useState, useEffect, useRef } from 'react';
import { Camera, Activity, Crosshair, Target, Shield, Zap, Info, Radio } from 'lucide-react';
import CameraView from './components/CameraView';
import Radar from './components/Radar';
import './App.css';

/**
 * Cerberus EchoSense - Multi-Modal Dashboard
 * Integrates Camera Vision, WiFi Sensing, and Sensor Fusion
 */
function App() {
  const [status, setStatus] = useState({
    mode: 'loading',
    camera_enabled: false,
    esp8266_enabled: false,
    esp32_enabled: false,
    wifi_adapter_enabled: false
  });

  const [latestDetection, setLatestDetection] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  // Initialize WebSocket Connection
  useEffect(() => {
    const connectWS = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[Dashboard] WebSocket Connected');
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'status') {
            setStatus(data);
          } else {
            setLatestDetection(data);
          }
        } catch (err) {
          console.error('[Dashboard] Parse error:', err);
        }
      };

      ws.onclose = () => {
        console.log('[Dashboard] WebSocket Disconnected');
        setConnected(false);
        setTimeout(connectWS, 3000); // Reconnect
      };

      ws.onerror = (err) => {
        console.error('[Dashboard] WebSocket Error:', err);
        ws.close();
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const getSourceIcon = (source) => {
    switch (source) {
      case 'camera': return <Camera size={14} />;
      case 'wifi_rssi':
      case 'wifi_csi':
      case 'wifi_monitor': return <Radio size={14} />;
      case 'fusion': return <Zap size={14} />;
      default: return <Info size={14} />;
    }
  };

  return (
    <div className="dashboard-root">
      {/* CRT Effects */}
      <div className="crt-overlay" />
      <div className="vignette" />

      {/* Header */}
      <header className="main-header">
        <div className="header-brand">
          <div className="logo-container">
            <Shield className="logo-icon" size={32} />
          </div>
          <div>
            <h1>CERBERUS ECHOSENSE <span>v2.0</span></h1>
            <div className="system-status">
              <span className={`status-dot ${connected ? 'status-online' : 'status-offline'}`} />
              {connected ? 'SYSTEM OPERATIONAL' : 'OFFLINE - RECONNECTING...'}
              <span className="mode-tag">{status.mode.toUpperCase()} MODE</span>
            </div>
          </div>
        </div>

        <div className="header-stats">
          <div className="stat-box">
            <span className="stat-label">HARDWARE</span>
            <div className="hardware-indicators">
              <div className={`hw-pill ${status.camera_enabled ? 'active' : ''}`}>CAM</div>
              <div className={`hw-pill ${status.esp32_enabled ? 'active' : ''}`}>CSI</div>
              <div className={`hw-pill ${status.esp8266_enabled ? 'active' : ''}`}>RSSI</div>
              <div className={`hw-pill ${status.wifi_adapter_enabled ? 'active' : ''}`}>MON</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Grid */}
      <main className="dashboard-grid">
        {/* Left Column: Visual Senses */}
        <section className="grid-column visual-column">
          <div className="module-container">
            <CameraView wsUrl="ws://localhost:8000/ws/camera" />
          </div>

          <div className="module-container radar-section">
            <h3 className="section-title"><Crosshair size={18} /> SPATIAL RADAR</h3>
            <Radar data={latestDetection} />
          </div>
        </section>

        {/* Right Column: Data Analysis */}
        <aside className="grid-column data-column">
          {/* Signal Stats */}
          <div className="data-module signal-stats">
            <h3 className="section-title"><Zap size={18} /> SIGNAL METRICS</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">RSSI</span>
                <span className="stat-value">{latestDetection?.rssi?.toFixed(1) || '-'} <span>dBm</span></span>
              </div>
              <div className="stat-item">
                <span className="stat-label">VARIANCE</span>
                <span className="stat-value">{latestDetection?.rssi_var?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">CONFIDENCE</span>
                <span className="stat-value">{(latestDetection?.confidence * 100)?.toFixed(1) || '0.0'}<span>%</span></span>
              </div>
            </div>
          </div>

          {/* Activity Log */}
          <div className="data-module activity-log">
            <h3 className="section-title"><Activity size={18} /> DETECTION EVENTS</h3>
            <div className="activity-list">
              {latestDetection ? (
                <div className="event-item pulse">
                  <div className="event-source">
                    {getSourceIcon(latestDetection.source)}
                    {latestDetection.source.toUpperCase()}
                  </div>
                  <div className="event-detail">
                    <span className="activity-name">{latestDetection.activity}</span>
                    <span className="timestamp">
                      {new Date(latestDetection.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                  {latestDetection.handoff_active && (
                    <div className="handoff-tag">HANDOFF ACTIVE</div>
                  )}
                </div>
              ) : (
                <div className="empty-state">No signal detected</div>
              )}
            </div>
          </div>

          {/* Active Entities */}
          <div className="data-module entities-module">
            <h3 className="section-title"><Target size={18} /> ACTIVE TARGETS</h3>
            <div className="entity-grid">
              {latestDetection?.tracking_ids?.length > 0 ? (
                latestDetection.tracking_ids.map((id, i) => (
                  <div key={id} className="entity-card">
                    <div className="entity-id">ID #{id}</div>
                    <div className="entity-type">
                      {latestDetection.class_names[i]?.toUpperCase() || 'PERSON'}
                    </div>
                    {latestDetection.out_of_frame && (
                      <div className="out-of-frame-notice">OUT OF CAM</div>
                    )}
                  </div>
                ))
              ) : (
                <div className="empty-state">No targets tracked</div>
              )}
            </div>
          </div>
        </aside>
      </main>

    </div>
  );
}

export default App;
