import socket
import time
import math
import random

UDP_IP = "127.0.0.1"
UDP_PORT = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Simulating ESP8266 RX on {UDP_IP}:{UDP_PORT}")
print("Press Ctrl+C to stop")

counter = 0

try:
    while True:
        # Simulate a baseline RSSI of -50 with some noise
        noise = random.uniform(-2, 2)
        rssi = -50 + noise
        
        # Simulate "Motion" every 10 seconds (sine wave disturbance)
        if (counter % 500) > 400: # Every 10s (assuming 50Hz -> 500 ticks)
             rssi += math.sin(counter * 0.5) * 10
             
        message = f"RSS:{int(rssi)}"
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        
        time.sleep(0.02) # 50Hz
        counter += 1
        
        if counter % 50 == 0:
            print(f"Sent: {message}")

except KeyboardInterrupt:
    print("Stopped.")
