#!/usr/bin/env python3
"""
CSI Data Collection Script
Collect labeled CSI data for training motion classifier

Usage:
    python collect_csi_data.py --label walking --duration 60
    python collect_csi_data.py --label sitting --duration 120
"""

import argparse
import asyncio
import time
import json
from pathlib import Path
from datetime import datetime

class CSIDataCollector:
    def __init__(self, label: str, duration: int, output_dir: str):
        self.label = label
        self.duration = duration
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.samples = []
        self.start_time = None
        
    async def collect_data(self):
        """Collect CSI data from UDP stream"""
        print(f"\n{'='*60}")
        print(f"CSI Data Collection")
        print(f"{'='*60}")
        print(f"Label: {self.label}")
        print(f"Duration: {self.duration}s")
        print(f"Output: {self.output_dir}")
        print(f"{'='*60}\n")
        
        print(f"⏳ Starting in 3 seconds...")
        print(f"   Prepare to perform: {self.label.upper()}")
        await asyncio.sleep(3)
        
        print(f"\n🎬 Recording started!")
        print(f"   Perform '{self.label}' activity now...")
        print(f"   Will collect for {self.duration} seconds\n")
        
        self.start_time = time.time()
        
        # UDP Protocol
        class UDPProtocol(asyncio.DatagramProtocol):
            def __init__(self, collector):
                self.collector = collector
                
            def connection_made(self, transport):
                self.transport = transport
                
            def datagram_received(self, data, addr):
                message = data.decode().strip()
                
                try:
                    # Parse CSI data (CSV format)
                    parts = message.split(',')
                    if len(parts) >= 65:  # timestamp + 64 subcarriers
                        timestamp = float(parts[0])
                        csi_data = [float(x) for x in parts[1:65]]
                        
                        self.collector.add_sample(csi_data)
                except Exception as e:
                    pass
        
        # Start UDP listener
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPProtocol(self),
            local_addr=("0.0.0.0", 8889)
        )
        
        # Wait for duration
        while (time.time() - self.start_time) < self.duration:
            elapsed = time.time() - self.start_time
            remaining = self.duration - elapsed
            
            print(f"\r   ⏱️  {elapsed:.1f}s / {self.duration}s  |  Samples: {len(self.samples)}  |  Remaining: {remaining:.1f}s", end='')
            await asyncio.sleep(0.1)
        
        print(f"\n\n✅ Collection complete!")
        print(f"   Collected {len(self.samples)} samples")
        
        transport.close()
        
        # Save data
        self.save_data()
        
    def add_sample(self, csi_data):
        """Add CSI sample with label"""
        self.samples.append({
            "timestamp": time.time() - self.start_time,
            "label": self.label,
            "csi": csi_data
        })
    
    def save_data(self):
        """Save collected data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"csi_{self.label}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        data = {
            "label": self.label,
            "duration": self.duration,
            "samples_count": len(self.samples),
            "collection_date": datetime.now().isoformat(),
            "samples": self.samples
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"   Saved to: {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Collect labeled CSI data")
    parser.add_argument("--label", "-l", required=True, 
                       help="Activity label (e.g., walking, sitting, standing, running)")
    parser.add_argument("--duration", "-d", type=int, default=60,
                       help="Collection duration in seconds (default: 60)")
    parser.add_argument("--output", "-o", default="data/csi_samples",
                       help="Output directory (default: data/csi_samples)")
    
    args = parser.parse_args()
    
    collector = CSIDataCollector(args.label, args.duration, args.output)
    
    try:
        asyncio.run(collector.collect_data())
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Collection cancelled by user")
        if len(collector.samples) > 0:
            print(f"   Saving {len(collector.samples)} samples collected so far...")
            collector.save_data()

if __name__ == "__main__":
    main()
