#!/usr/bin/env python3
"""
Setup script for Tecton MCP Tools
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_env_file():
    """Create .env file from example if it doesn't exist"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("📝 Creating .env file from template...")
            env_example.read_text()
            with open(".env", "w") as f:
                f.write(env_example.read_text())
            print("✅ Created .env file - please edit it with your API credentials")
        else:
            print("❌ .env.example not found")
            sys.exit(1)
    else:
        print("✅ .env file already exists")

def test_servers():
    """Test that all servers can be imported"""
    servers = [
        "servers/chronosphere_server.py",
        "servers/linear_server.py", 
        "servers/jira_server.py",
        "servers/slack_server.py"
    ]
    
    print("🧪 Testing server imports...")
    for server in servers:
        server_path = Path(server)
        if server_path.exists():
            print(f"  Testing {server}...")
            try:
                # Try to import each server to check for basic syntax errors
                subprocess.check_call([
                    sys.executable, "-c", 
                    f"import sys; sys.path.insert(0, '{server_path.parent}'); "
                    f"exec(open('{server_path}').read().replace('mcp.run()', 'pass'))"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"    ✅ {server} import test passed")
            except subprocess.CalledProcessError as e:
                print(f"    ❌ {server} import test failed: {e}")
        else:
            print(f"    ❌ {server} not found")

def show_next_steps():
    """Show next steps for setup"""
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit the .env file with your actual API credentials")
    print("2. Update your Claude MCP configuration with the server paths")
    print("3. Test individual servers by running them directly:")
    print("   python servers/chronosphere_server.py")
    print("   python servers/linear_server.py")
    print("   python servers/jira_server.py")
    print("   python servers/slack_server.py")
    print("\nSee README.md for detailed configuration instructions.")

def main():
    """Main setup function"""
    print("🚀 Setting up Tecton MCP Tools\n")
    
    check_python_version()
    install_dependencies()
    setup_env_file()
    test_servers()
    show_next_steps()

if __name__ == "__main__":
    main()
