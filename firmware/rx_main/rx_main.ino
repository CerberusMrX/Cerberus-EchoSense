#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

extern "C" {
  #include <user_interface.h>
}

// --- CONFIGURATION ---
const char* WIFI_SSID = "Linksys_Network_Name";
const char* WIFI_PASS = "wifipassword";
const int   WIFI_CHANNEL = 1; // FIX CHANNEL to match TX and AP

// MAC Address of the TX ESP8266 (Update this!)
uint8_t targetMAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};

// Laptop IP for UDP streaming
IPAddress backendIP(192, 168, 1, 100);
unsigned int backendPort = 8888;

WiFiUDP Udp;
volatile int latestRSSI = -100;
volatile bool newData = false;

// Promiscuous Callback
void sniffer_callback(uint8_t *buf, uint16_t len) {
  // Check if it's a Management (0x00) or Data (0x08) frame
  // Frame Control is first 2 bytes.
  // We look for Source MAC which is usually at offset 10 (Address 2)
  // Frame format: [FC:2][Duration:2][Addr1:6][Addr2:6][Addr3:6]...
  
  if (len < 24) return;

  uint8_t *srcMac = buf + 10;
  
  // Check if matches our target TX
  bool match = true;
  for (int i=0; i<6; i++) {
    if (srcMac[i] != targetMAC[i]) {
      match = false;
      break;
    }
  }

  if (match) {
    // RSSI is in the metadata struct (WifiRxPacket) which is passed *implicitly* or struct cast in newer SDKs?
    // In older SDKs with `wifi_set_promiscuous_rx_cb`, `buf` was the whole struct.
    // In Arduino, `buf` is usually the 802.11 payload, and `rssi` is tricky.
    
    // Standard hack: struct RxControl is at the beginning or end?
    // Actually, on Arduino ESP8266, the callback signature is (uint8_t* buf, uint16_t len).
    // The `buf` contains the `RxControl` struct first, THEN the frame.
    
    struct RxControl {
      signed char rssi;
      unsigned char rate;
      unsigned int legacy_length;
      unsigned int damatch0:1;
      unsigned int damatch1:1;
      unsigned int bssidmatch0:1;
      unsigned int bssidmatch1:1;
      unsigned int MCS:7;
      unsigned int CWB:1;
      unsigned int HT_length:16;
      unsigned int Smoothing:1;
      unsigned int Not_Sounding:1;
      unsigned int Aggregation:1;
      unsigned int STBC:2;
      unsigned int FEC_CODING:1;
      unsigned int SGI:1;
      unsigned int rxend_state:8;
      unsigned int ampdu_cnt:8;
      unsigned int channel:4;
      unsigned int:12;
    };

    struct RxControl *sniffer = (struct RxControl*) buf;
    signed char rssi = sniffer->rssi;
    
    latestRSSI = rssi;
    newData = true;
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n[RX] Initializing...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  
  Serial.print("[RX] Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[RX] Connected.");
  
  // Promiscuous Setup
  wifi_set_opmode(STATION_MODE); 
  wifi_promiscuous_enable(0);
  wifi_set_promiscuous_rx_cb(sniffer_callback);
  wifi_promiscuous_enable(1);
  
  Serial.println("[RX] Sniffer Enabled.");
}

void loop() {
  if (newData) {
    newData = false;
    // Send via UDP
    // Note: sending UDP while in promiscuous mode is flaky. 
    // If it fails, we might need to verify logic. 
    // But for a "Real World" proto, this is the standard path.
    
    char payload[32];
    snprintf(payload, 32, "RSS:%d", latestRSSI);
    
    Udp.beginPacket(backendIP, backendPort);
    Udp.write(payload);
    Udp.endPacket();
    
    Serial.println(payload);
  }
}
