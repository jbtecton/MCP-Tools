#!/usr/bin/env python3
"""
Tecton MCP Services Wrapper
Manages multiple FastMCP server instances for Tecton's toolset integration
"""

import sys
import os
import subprocess
import signal
import json
import time
import psutil
from pathlib import Path

# === CONFIG: Configure your MCP services here ===
# Remove 'slack' if you decide against keeping it
SERVICES = ["jira", "chronosphere", "linear", "observe"]  # removed slack for now

# Paths configuration
PROJECT_ROOT = Path("/Users/jbarr/Projects/tecton-mcp-tools")
PYTHON_PATH = sys.executable  # Use the same Python that's running this script
PID_FILE = Path.home() / ".tectonmcp_pids.json"

def get_server_path(service):
    """Get the full path to a server script"""
    return PROJECT_ROOT / "servers" / f"{service}_server.py"

def validate_service(service):
    """Check if a service exists"""
    if service not in SERVICES:
        print(f"❌ Unknown service: {service}")
        print(f"Available services: {', '.join(SERVICES)}")
        return False
    
    server_path = get_server_path(service)
    if not server_path.exists():
        print(f"❌ Server script not found: {server_path}")
        return False
    
    return True

def load_pids():
    """Load PIDs from persistent storage"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("⚠️  Corrupted PID file, starting fresh")
            return {}
    return {}

def save_pids(pids):
    """Save PIDs to persistent storage"""
    try:
        with open(PID_FILE, "w") as f:
            json.dump(pids, f, indent=2)
    except IOError as e:
        print(f"⚠️  Failed to save PID file: {e}")

def is_process_running(pid):
    """Check if a process is actually running"""
    try:
        return psutil.pid_exists(pid)
    except:
        # Fallback if psutil not available
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but we can't signal it

def cleanup_stale_pids():
    """Remove PIDs for processes that are no longer running"""
    pids = load_pids()
    stale_services = []
    
    for service, pid in pids.items():
        if not is_process_running(pid):
            stale_services.append(service)
    
    for service in stale_services:
        print(f"🧹 Cleaning up stale PID for {service}")
        del pids[service]
    
    if stale_services:
        save_pids(pids)
    
    return pids

def start_service(service):
    """Start a single MCP service"""
    if not validate_service(service):
        return False
    
    pids = cleanup_stale_pids()
    
    if service in pids:
        if is_process_running(pids[service]):
            print(f"✅ {service} already running (PID {pids[service]})")
            return True
        else:
            # Clean up stale PID
            del pids[service]
    
    print(f"🚀 Starting {service}...")
    
    server_path = get_server_path(service)
    
    try:
        # Start the server process
        proc = subprocess.Popen(
            [PYTHON_PATH, str(server_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=PROJECT_ROOT
        )
        
        # Give the process a moment to start
        time.sleep(1)
        
        # Check if the process started successfully
        if proc.poll() is None:  # Process is still running
            pids[service] = proc.pid
            save_pids(pids)
            print(f"✅ {service} started successfully (PID {proc.pid})")
            return True
        else:
            # Process died immediately, get error output
            _, stderr = proc.communicate()
            print(f"❌ {service} failed to start:")
            if stderr:
                print(f"   Error: {stderr.decode().strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start {service}: {e}")
        return False

def stop_service(service, graceful=False):
    """Stop a single MCP service"""
    pids = cleanup_stale_pids()
    
    if service not in pids:
        print(f"⚠️  {service} is not running")
        return True
    
    pid = pids.pop(service)
    
    try:
        sig = signal.SIGHUP if graceful else signal.SIGTERM
        os.kill(pid, sig)
        
        # Wait a moment for graceful shutdown
        if graceful:
            time.sleep(2)
            if is_process_running(pid):
                print(f"⚠️  {service} didn't respond to graceful shutdown, forcing...")
                os.kill(pid, signal.SIGTERM)
        
        save_pids(pids)
        print(f"🛑 {'Gracefully ' if graceful else ''}stopped {service} (PID {pid})")
        return True
        
    except ProcessLookupError:
        print(f"⚠️  {service} PID {pid} not found (already stopped)")
        save_pids(pids)
        return True
    except Exception as e:
        print(f"❌ Failed to stop {service}: {e}")
        return False

def start_all():
    """Start all configured services"""
    print(f"🚀 Starting all services: {', '.join(SERVICES)}")
    success_count = 0
    
    for service in SERVICES:
        if start_service(service):
            success_count += 1
    
    print(f"📊 Started {success_count}/{len(SERVICES)} services")
    return success_count == len(SERVICES)

def stop_all(graceful=False):
    """Stop all running services"""
    pids = cleanup_stale_pids()
    
    if not pids:
        print("ℹ️  No services currently running")
        return True
    
    print(f"🛑 Stopping all services: {', '.join(pids.keys())}")
    success_count = 0
    
    for service in list(pids.keys()):
        if stop_service(service, graceful=graceful):
            success_count += 1
    
    print(f"📊 Stopped {success_count}/{len(pids)} services")
    return success_count == len(pids)

def status():
    """Show status of all services"""
    pids = cleanup_stale_pids()
    
    print("📊 Tecton MCP Services Status")
    print("=" * 40)
    
    if not pids:
        print("ℹ️  No services currently running")
        print(f"Available services: {', '.join(SERVICES)}")
        return
    
    print("🟢 Running services:")
    for service, pid in pids.items():
        # Get some basic process info if possible
        try:
            proc = psutil.Process(pid)
            cpu_percent = proc.cpu_percent()
            memory_mb = proc.memory_info().rss / 1024 / 1024
            print(f"   {service:<12} (PID {pid:<6}) CPU: {cpu_percent:>5.1f}% RAM: {memory_mb:>6.1f}MB")
        except:
            print(f"   {service:<12} (PID {pid})")
    
    # Show available but not running services
    not_running = [s for s in SERVICES if s not in pids]
    if not_running:
        print(f"\n⚪ Available but not running: {', '.join(not_running)}")

def restart(service, graceful=False):
    """Restart a single service"""
    print(f"🔄 Restarting {service}...")
    stop_service(service, graceful=graceful)
    time.sleep(1)  # Brief pause between stop and start
    return start_service(service)

def restart_all(graceful=False):
    """Restart all services"""
    print("🔄 Restarting all services...")
    stop_all(graceful=graceful)
    time.sleep(2)  # Brief pause between stop and start
    return start_all()

def print_usage():
    """Print usage information"""
    print("""
Tecton MCP Services Controller

Usage:
  tectonmcpctl <command> [target]

Commands:
  start <service|all>     - Start a service or all services
  stop <service|all>      - Stop a service or all services  
  restart <service|all>   - Restart a service or all services
  graceful <service|all>  - Gracefully restart (SIGHUP instead of SIGTERM)
  status                  - Show status of all services

Available services: {services}

Examples:
  ./tectonmcpctl start jira
  ./tectonmcpctl restart all
  ./tectonmcpctl graceful chronosphere
  ./tectonmcpctl status
    """.format(services=', '.join(SERVICES)))

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()
    target = sys.argv[2].lower() if len(sys.argv) > 2 else None

    # Command routing
    if cmd == "start":
        if target == "all":
            success = start_all()
        elif target and target in SERVICES:
            success = start_service(target)
        elif target:
            print(f"❌ Unknown service: {target}")
            success = False
        else:
            print("❌ Specify a service to start or 'all'")
            success = False

    elif cmd == "stop":
        if target == "all":
            success = stop_all()
        elif target and target in SERVICES:
            success = stop_service(target)
        elif target:
            print(f"❌ Unknown service: {target}")
            success = False
        else:
            print("❌ Specify a service to stop or 'all'")
            success = False

    elif cmd == "restart":
        if target == "all":
            success = restart_all()
        elif target and target in SERVICES:
            success = restart(target)
        elif target:
            print(f"❌ Unknown service: {target}")
            success = False
        else:
            print("❌ Specify a service to restart or 'all'")
            success = False

    elif cmd == "status":
        status()
        success = True

    elif cmd == "graceful":
        if target == "all":
            success = restart_all(graceful=True)
        elif target and target in SERVICES:
            success = restart(target, graceful=True)
        elif target:
            print(f"❌ Unknown service: {target}")
            success = False
        else:
            print("❌ Specify a service to gracefully restart or 'all'")
            success = False

    else:
        print(f"❌ Unknown command: {cmd}")
        print_usage()
        success = False

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
