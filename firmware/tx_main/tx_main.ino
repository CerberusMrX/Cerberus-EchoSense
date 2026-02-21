#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

// --- CONFIGURATION ---
const char* STASSID = "Cerberus_Echo"; // Name of the target network (or AP)
const char* STAPSK  = "cerberus123";   // Password
const int   PACKET_RATE_MS = 20;       // Send packet every 20ms (50Hz)

// Target IP to flood (doesn't need to exist, just needs to generate air traffic)
// We use broadcast or a dummy IP.
IPAddress targetIP(192, 168, 4, 255); 
unsigned int targetPort = 4210;

WiFiUDP Udp;
char packetBuffer[64]; 
unsigned long lastSendTime = 0;
unsigned long packetCount = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("\n[TX] Initializing...");

  // We set PHY mode to G for better range/stability
  WiFi.setPhyMode(WIFI_PHY_MODE_11G);
  
  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(STASSID, STAPSK);

  Serial.print("[TX] Connecting to ");
  Serial.println(STASSID);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n[TX] Connected!");
  Serial.print("[TX] IP Address: ");
  Serial.println(WiFi.localIP());

  // Set output power to max for consistent baseline
  WiFi.setOutputPower(20.5); 
}

void loop() {
  unsigned long now = millis();
  
  if (now - lastSendTime >= PACKET_RATE_MS) {
    lastSendTime = now;
    
    // Create a data payload
    // We include a magic header "CERB" and a counter
    snprintf(packetBuffer, 64, "CERB:%lu", packetCount++);
    
    // Broadcast the packet
    // This puts the frame in the air, which the RX will sniff
    Udp.beginPacket(targetIP, targetPort);
    Udp.write(packetBuffer);
    Udp.endPacket();
    
    // Blink LED briefly
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
}
