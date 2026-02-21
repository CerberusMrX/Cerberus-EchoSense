#!/usr/bin/env python3
"""
Cerberus EchoSense - Quick Start Script
Automatically start backend and frontend

Usage:
    python start.py
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import signal

class TermColors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    banner = f"""{TermColors.CYAN}
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║         CERBERUS ECHOSENSE - Quick Start             ║
    ║         Multi-Modal Detection System                 ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    {TermColors.END}"""
    print(banner)

def check_config():
    """Check if config.yaml exists"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"{TermColors.RED}✗ config.yaml not found!{TermColors.END}")
        print(f"{TermColors.YELLOW}  Run setup wizard first:{TermColors.END}")
        print(f"  python setup_wizard.py\n")
        return False
    
    print(f"{TermColors.GREEN}✓ Configuration found{TermColors.END}")
    return True

def start_backend():
    """Start backend server"""
    print(f"\n{TermColors.CYAN}[Backend] Starting server...{TermColors.END}")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print(f"{TermColors.RED}✗ Backend directory not found{TermColors.END}")
        return None
    
    # Check if server.py exists
    if not (backend_dir / "server.py").exists():
        print(f"{TermColors.RED}✗ server.py not found{TermColors.END}")
        return None
    
    # Use venv python if available
    venv_python = Path(__file__).parent / "backend" / "venv" / "bin" / "python3"
    executable = str(venv_python) if venv_python.exists() else sys.executable
    
    print(f"{TermColors.CYAN}[Backend] Using executable: {executable}{TermColors.END}")

    # Start backend process - No redirection so logs appear in terminal
    process = subprocess.Popen(
        [executable, "server.py"],
        cwd=backend_dir
    )
    
    # Wait for backend to start
    time.sleep(2)
    
    if process.poll() is None:
        print(f"{TermColors.GREEN}✓ Backend started (PID: {process.pid}){TermColors.END}")
        return process
    else:
        print(f"{TermColors.RED}✗ Backend failed to start{TermColors.END}")
        return None

def start_frontend():
    """Start frontend dev server"""
    print(f"\n{TermColors.CYAN}[Frontend] Starting dev server...{TermColors.END}")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print(f"{TermColors.RED}✗ Frontend directory not found{TermColors.END}")
        return None
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print(f"{TermColors.YELLOW}⚠ node_modules not found. Running npm install...{TermColors.END}")
        install_process = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir
        )
        if install_process.returncode != 0:
            print(f"{TermColors.RED}✗ npm install failed{TermColors.END}")
            return None
    
    # Start frontend - No redirection so logs appear in terminal
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir
    )
    
    # Wait for frontend to start
    time.sleep(3)
    
    if process.poll() is None:
        print(f"{TermColors.GREEN}✓ Frontend started (PID: {process.pid}){TermColors.END}")
        return process
    else:
        print(f"{TermColors.RED}✗ Frontend failed to start{TermColors.END}")
        return None

def main():
    print_banner()
    
    # Check config
    if not check_config():
        sys.exit(1)
    
    # Start services
    backend_process = start_backend()
    if not backend_process:
        print(f"\n{TermColors.RED}Failed to start backend{TermColors.END}")
        sys.exit(1)
    
    frontend_process = start_frontend()
    if not frontend_process:
        print(f"\n{TermColors.RED}Failed to start frontend{TermColors.END}")
        backend_process.terminate()
        sys.exit(1)
    
    # Success message
    print(f"\n{TermColors.BOLD}{TermColors.GREEN}{'='*60}{TermColors.END}")
    print(f"{TermColors.BOLD}{TermColors.GREEN}✓ System Started Successfully!{TermColors.END}")
    print(f"{TermColors.BOLD}{TermColors.GREEN}{'='*60}{TermColors.END}\n")
    
    print(f"{TermColors.CYAN}🌐 Open your browser:{TermColors.END}")
    print(f"   {TermColors.BOLD}http://localhost:5173{TermColors.END}\n")
    
    print(f"{TermColors.YELLOW}📝 Services Running:{TermColors.END}")
    print(f"   Backend:  PID {backend_process.pid}")
    print(f"   Frontend: PID {frontend_process.pid}\n")
    
    print(f"{TermColors.YELLOW}Press Ctrl+C to stop all services{TermColors.END}\n")
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print(f"\n\n{TermColors.YELLOW}Shutting down...{TermColors.END}")
        print(f"{TermColors.CYAN}Stopping backend...{TermColors.END}")
        backend_process.terminate()
        print(f"{TermColors.CYAN}Stopping frontend...{TermColors.END}")
        frontend_process.terminate()
        
        # Wait for processes to stop
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)
        
        print(f"{TermColors.GREEN}✓ All services stopped{TermColors.END}\n")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print(f"\n{TermColors.RED}✗ Backend stopped unexpectedly{TermColors.END}")
                frontend_process.terminate()
                break
            
            if frontend_process.poll() is not None:
                print(f"\n{TermColors.RED}✗ Frontend stopped unexpectedly{TermColors.END}")
                backend_process.terminate()
                break
                
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
