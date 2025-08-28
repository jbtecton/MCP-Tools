#!/usr/bin/env python3
"""
Configuration generator for Claude MCP settings
"""

import json
import os
from pathlib import Path

def get_current_path():
    """Get the current absolute path"""
    return Path(__file__).parent.absolute()

def generate_mcp_config():
    """Generate MCP configuration JSON"""
    base_path = get_current_path()
    
    # Configuration using environment variables approach
    config_with_env = {
        "mcp": {
            "servers": {
                "tecton-chronosphere": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "chronosphere_server.py")],
                    "env": {
                        "CHRONOSPHERE_DOMAIN": "tecton",
                        "CHRONOSPHERE_API_TOKEN": "your-token-here"
                    }
                },
                "tecton-linear": {
                    "command": "python", 
                    "args": [str(base_path / "servers" / "linear_server.py")],
                    "env": {
                        "LINEAR_API_KEY": "your-key-here"
                    }
                },
                "tecton-jira": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "jira_server.py")],
                    "env": {
                        "JIRA_URL": "https://your-domain.atlassian.net",
                        "JIRA_EMAIL": "your-email@example.com",
                        "JIRA_API_TOKEN": "your-api-token"
                    }
                },
                "tecton-slack": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "slack_server.py")],
                    "env": {
                        "SLACK_BOT_TOKEN": "xoxb-your-bot-token-here"
                    }
                },
                "tecton-observe": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "observe_server.py")],
                    "env": {
                        "OBSERVE_TENANT_URL": "https://your-tenant-id.observeinc.com",
                        "OBSERVE_USER_EMAIL": "your-email@example.com",
                        "OBSERVE_API_TOKEN": "your-observe-bearer-token"
                    }
                }
            }
        }
    }
    
    # Alternative configuration using .env file (cleaner)
    config_with_dotenv = {
        "mcp": {
            "servers": {
                "tecton-chronosphere": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "chronosphere_server.py")]
                },
                "tecton-linear": {
                    "command": "python", 
                    "args": [str(base_path / "servers" / "linear_server.py")]
                },
                "tecton-jira": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "jira_server.py")]
                },
                "tecton-slack": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "slack_server.py")]
                },
                "tecton-observe": {
                    "command": "python",
                    "args": [str(base_path / "servers" / "observe_server.py")]
                }
            }
        }
    }
    
    return config_with_env, config_with_dotenv

def main():
    """Generate and display MCP configuration"""
    print("🔧 Tecton MCP Tools - Configuration Generator\n")
    
    config_env, config_dotenv = generate_mcp_config()
    
    print("=" * 80)
    print("OPTION 1: Configuration with explicit environment variables")
    print("=" * 80)
    print("Add this to your Claude MCP config file (~/.config/claude-desktop/config.json):")
    print()
    print(json.dumps(config_env, indent=2))
    
    print("\n" + "=" * 80)
    print("OPTION 2: Configuration using .env file (RECOMMENDED)")  
    print("=" * 80)
    print("Add this to your Claude MCP config file (~/.config/claude-desktop/config.json):")
    print()
    print(json.dumps(config_dotenv, indent=2))
    
    print("\n" + "=" * 80)
    print("NOTES:")
    print("=" * 80)
    print("• Option 1: Replace 'your-token-here' etc. with actual credentials")
    print("• Option 2: Ensure your .env file is properly configured")
    print("• Make sure all file paths are correct for your system")
    print("• Restart Claude Desktop after updating the configuration")
    print("• Test each server individually before using with Claude")

if __name__ == "__main__":
    main()
