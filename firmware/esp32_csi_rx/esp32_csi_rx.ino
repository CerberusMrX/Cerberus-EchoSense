/*
 * ESP32 CSI Receiver (Passive STA)
 * Captures CSI data and streams to backend server
 * 
 * Based on: https://github.com/stevenmhernandez/ESP32-CSI-Tool
 * 
 * Hardware: ESP32-WROOM-32 or compatible
 * Requires: ESP-IDF (Arduino IDE has limited CSI access)
 * 
 * NOTE: Full CSI implementation requires ESP-IDF framework.
 * This is a simplified version for Arduino IDE compatibility.
 * For production CSI sensing, use the ESP32-CSI-Tool directly.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_wifi.h"

// Network Configuration
const char* WIFI_SSID = "YourHomeNetwork";  // Your home WiFi
const char* WIFI_PASS = "yourpassword";

// Backend server
IPAddress backendIP(192, 168, 1, 100);  // Update with your laptop IP
const int backendPort = 8889;  // ESP32 CSI port

// TX ESP32 MAC (update after flashing TX)
uint8_t targetMAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};

WiFiUDP udp;

// CSI callback (simplified - full implementation needs ESP-IDF)
void wifi_csi_cb(void *ctx, wifi_csi_info_t *info) {
  if (!info || !info->buf) return;
  
  // Check if packet is from our TX
  bool match = true;
  for (int i = 0; i < 6; i++) {
    if (info->mac[i] != targetMAC[i]) {
      match = false;
      break;
    }
  }
  
  if (!match) return;
  
  // CSI data is in info->buf
  // Format: Complex values for 64 subcarriers
  // For simplicity, we'll extract amplitude data
  
  String csiData = String(millis()) + ",";
  
  // Extract CSI subcarrier amplitudes
  // Note: This is simplified. Real CSI format is complex.
  // In production, parse the actual CSI buffer structure
  int8_t *data = (int8_t*)info->buf;
  int len = info->len;
  
  // Simulate 64 subcarrier amplitudes (replace with actual parsing)
  for (int i = 0; i < 64; i++) {
    if (i < len) {
      // Calculate amplitude from I/Q components
      float amp = sqrt(data[i*2]*data[i*2] + data[i*2+1]*data[i*2+1]);
      csiData += String(amp, 2);
    } else {
      csiData += "0.0";
    }
    
    if (i < 63) csiData += ",";
  }
  
  // Send CSI data to backend via UDP
  udp.beginPacket(backendIP, backendPort);
  udp.print(csiData);
  udp.endPacket();
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n==================================");
  Serial.println("ESP32 CSI Receiver (Passive STA)");
  Serial.println("==================================");
  
  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  
  Serial.print("Connecting to ");
  Serial.print(WIFI_SSID);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  
  // Configure CSI
  wifi_csi_config_t csi_config;
  csi_config.lltf_en = true;
  csi_config.htltf_en = true;
  csi_config.stbc_htltf2_en = true;
  csi_config.ltf_merge_en = true;
  csi_config.channel_filter_en = false;
  csi_config.manu_scale = true;
  
  esp_wifi_set_csi_config(&csi_config);
  esp_wifi_set_csi_rx_cb(&wifi_csi_cb, NULL);
  esp_wifi_set_csi(true);
  
  Serial.println("\n[CSI] Enabled. Listening for packets...");
  Serial.println("Update targetMAC[] with your TX ESP32 MAC!");
  Serial.println("==================================\n");
}

void loop() {
  // CSI callback handles everything
  delay(100);
  
  // Heartbeat
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 5000) {
    lastPrint = millis();
    Serial.println("[RX] CSI capture active...");
  }
}

/*
 * IMPORTANT NOTES:
 * 
 * 1. CSI Setup requires ESP-IDF for full functionality
 * 2. Arduino IDE has limited CSI buffer access
 * 3. For production use, clone and use:
 *    https://github.com/stevenmhernandez/ESP32-CSI-Tool
 * 
 * 4. This code provides basic structure. Real CSI parsing needs:
 *    - Proper buffer interpretation
 *    - Complex number (I/Q) extraction
 *    - Amplitude/Phase calculation for each subcarrier
 * 
 * 5. Alternative: Use ESP-IDF example:
 *    esp-idf/examples/wifi/getting_started/station/
 *    Then add CSI callbacks
 */
