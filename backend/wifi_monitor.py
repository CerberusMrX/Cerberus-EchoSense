#!/usr/bin/env python3
"""
WiFi Monitor Mode Script
Captures WiFi packets for motion detection without ESP hardware

Requirements:
- WiFi adapter with monitor mode support (e.g., Alfa AWUS036ACH)
- Linux with airmon-ng or similar tools
- Root/sudo privileges
- Scapy library

Usage:
    sudo python wifi_monitor.py --interface wlan0 --channel 6
"""

import argparse
import sys
import socket
import struct
import time
import logging
from typing import Dict

try:
    from scapy.all import *
except ImportError:
    print("Error: Scapy not installed")
    print("Install: pip install scapy")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WiFiMonitor:
    def __init__(self, interface: str, channel: int, backend_host: str, backend_port: int):
        self.interface = interface
        self.channel = channel
        self.backend_host = backend_host
        self.backend_port = backend_port
        
        # UDP socket to send data to backend
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.packet_count = 0
        self.last_print = time.time()
    
    def enable_monitor_mode(self):
        """Enable monitor mode on interface"""
        logger.info(f"Enabling monitor mode on {self.interface}...")
        
        try:
            # Try to enable monitor mode
            os.system(f"sudo ip link set {self.interface} down")
            os.system(f"sudo iw {self.interface} set monitor control")
            os.system(f"sudo ip link set {self.interface} up")
            os.system(f"sudo iw dev {self.interface} set channel {self.channel}")
            
            logger.info(f"✓ Monitor mode enabled on channel {self.channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable monitor mode: {e}")
            logger.info("Try manually: sudo airmon-ng start wlan0")
            return False
    
    def packet_handler(self, pkt):
        """Process captured packet"""
        self.packet_count += 1
        
        # Extract useful information
        if pkt.haslayer(Dot11):
            # Get RSSI if available (from RadioTap header)
            rssi = None
            if pkt.haslayer(RadioTap):
                # RadioTap dBm signal strength
                try:
                    rssi = pkt[RadioTap].dBm_AntSignal
                except:
                    rssi = -80  # Default
            
            # Get addresses
            addr1 = pkt.addr1 if hasattr(pkt, 'addr1') else None
            addr2 = pkt.addr2 if hasattr(pkt, 'addr2') else None
            
            # Packet type
            pkt_type = pkt.type
            subtype = pkt.subtype
            
            # Send data to backend
            packet_data = {
                "timestamp": time.time(),
                "rssi": rssi or -80,
                "addr1": addr1,
                "addr2": addr2,
                "type": pkt_type,
                "subtype": subtype
            }
            
            # Send via UDP
            message = f"WIFI:{rssi or -80},{pkt_type},{subtype}"
            try:
                self.sock.sendto(message.encode(), (self.backend_host, self.backend_port))
            except Exception as e:
                logger.error(f"UDP send failed: {e}")
        
        # Status update
        if time.time() - self.last_print > 5.0:
            logger.info(f"Captured {self.packet_count} packets...")
            self.last_print = time.time()
    
    def start_capture(self):
        """Start packet capture"""
        logger.info(f"Starting packet capture on {self.interface}...")
        logger.info(f"Sending data to {self.backend_host}:{self.backend_port}")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            sniff(iface=self.interface, prn=self.packet_handler, store=0)
        except KeyboardInterrupt:
            logger.info("\nCapture stopped by user")
        except Exception as e:
            logger.error(f"Capture error: {e}")
        finally:
            self.sock.close()

def main():
    parser = argparse.ArgumentParser(description="WiFi Monitor Mode for Cerberus EchoSense")
    parser.add_argument("--interface", "-i", default="wlan0mon", help="Monitor interface (default: wlan0mon)")
    parser.add_argument("--channel", "-c", type=int, default=6, help="WiFi channel (default: 6)")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=9000, help="Backend port (default: 9000)")
    parser.add_argument("--enable-monitor", action="store_true", help="Auto-enable monitor mode")
    
    args = parser.parse_args()
    
    # Check root
    if os.geteuid() != 0:
        logger.error("This script requires root/sudo privileges")
        logger.info("Usage: sudo python wifi_monitor.py")
        sys.exit(1)
    
    monitor = WiFiMonitor(args.interface, args.channel, args.host, args.port)
    
    if args.enable_monitor:
        if not monitor.enable_monitor_mode():
            sys.exit(1)
    
    monitor.start_capture()

if __name__ == "__main__":
    main()
