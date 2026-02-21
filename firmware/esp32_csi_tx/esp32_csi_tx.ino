/*
 * ESP32 CSI Transmitter (Active AP)
 * Continuously broadcasts WiFi packets for CSI sensing
 * 
 * Based on: https://github.com/stevenmhernandez/ESP32-CSI-Tool
 * 
 * Hardware: ESP32-WROOM-32 or compatible
 * Flash with: ESP-IDF or Arduino IDE with ESP32 support
 */

#include <WiFi.h>
#include <WiFiUdp.h>

// WiFi Configuration
const char* ssid = "CerberusCSI_TX";
const char* password = "cerberus123";

// Packet transmission settings
const int PACKET_RATE_MS = 10;  // 100Hz transmission rate
const int WIFI_CHANNEL = 6;     // Fixed channel
const int TX_POWER = 20;        // Max TX power for stable signal

WiFiUDP udp;
IPAddress broadcastIP(192, 168, 4, 255);
const int broadcastPort = 4210;

unsigned long lastSendTime = 0;
unsigned long packetCount = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=================================");
  Serial.println("ESP32 CSI Transmitter (Active AP)");
  Serial.println("=================================");
  
  // Configure WiFi as AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password, WIFI_CHANNEL);
  
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP Started: ");
  Serial.println(ssid);
  Serial.print("IP Address: ");
  Serial.println(myIP);
  Serial.print("Channel: ");
  Serial.println(WIFI_CHANNEL);
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  
  // Set TX power
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  
  Serial.println("\nTransmitting packets at 100Hz...");
  Serial.println("=================================\n");
}

void loop() {
  unsigned long now = millis();
  
  if (now - lastSendTime >= PACKET_RATE_MS) {
    lastSendTime = now;
    
    // Create packet payload
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "CERB_CSI:%lu", packetCount++);
    
    // Broadcast UDP packet
    udp.beginPacket(broadcastIP, broadcastPort);
    udp.write((uint8_t*)buffer, strlen(buffer));
    udp.endPacket();
    
    // Blink LED
    if (packetCount % 100 == 0) {
      Serial.printf("[TX] Packet count: %lu\n", packetCount);
    }
  }
}
