#!/usr/bin/env python3
"""
Slack MCP Server using FastMCP

This server provides basic Slack integration with tools to:
- Search messages across channels
- Get thread details
- Get recent channel activity
- List accessible channels

Setup:
1. pip install fastmcp requests python-dotenv
2. Create a Slack app and get a Bot User OAuth Token with these scopes:
   - channels:history, channels:read, groups:history, groups:read, 
   - im:history, im:read, mpim:history, mpim:read, search:read
3. Set SLACK_BOT_TOKEN environment variable in .env file
4. Run: python slack_server.py
"""

import os
import requests
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("Slack Integration")

# Slack configuration from environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_API_BASE = "https://slack.com/api"

if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable must be set")

def get_slack_headers():
    """Get Slack API headers with authentication"""
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

def make_slack_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make authenticated request to Slack API"""
    headers = get_slack_headers()
    url = f"{SLACK_API_BASE}/{endpoint}"
    
    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    
    data = response.json()
    if not data.get("ok", False):
        raise Exception(f"Slack API error: {data.get('error', 'Unknown error')}")
    
    return data

@mcp.tool()
def search_slack_messages(
    query: str, 
    count: Optional[int] = 20,
    sort: Optional[str] = "timestamp"
) -> Dict[str, Any]:
    """
    Search for messages across Slack channels you have access to
    
    Args:
        query: Search query (supports Slack search syntax)
        count: Number of results to return (default: 20, max: 100)
        sort: Sort order - 'timestamp' or 'score' (default: timestamp)
    
    Returns:
        Dictionary containing search results with message details
    """
    try:
        params = {
            "query": query,
            "count": min(count, 100),
            "sort": sort
        }
        
        data = make_slack_request("search.messages", params)
        
        messages = []
        for match in data.get("messages", {}).get("matches", []):
            message_info = {
                "text": match.get("text", ""),
                "user": match.get("username", "Unknown"),
                "channel": match.get("channel", {}).get("name", "Unknown"),
                "timestamp": match.get("ts", ""),
                "permalink": match.get("permalink", ""),
                "score": match.get("score", 0),
                # Format timestamp for readability
                "formatted_time": datetime.fromtimestamp(float(match.get("ts", "0"))).strftime("%Y-%m-%d %H:%M:%S") if match.get("ts") else "Unknown"
            }
            messages.append(message_info)
        
        return {
            "query": query,
            "total_found": data.get("messages", {}).get("total", 0),
            "returned_count": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        return {"error": f"Failed to search messages: {str(e)}"}

@mcp.tool()
def get_slack_thread(message_link: str, include_replies: Optional[bool] = True) -> Dict[str, Any]:
    """
    Get a Slack thread by message permalink
    
    Args:
        message_link: Slack permalink to the message
        include_replies: Whether to include thread replies (default: True)
    
    Returns:
        Dictionary containing the thread messages
    """
    try:
        # Parse the permalink to extract channel and timestamp
        # Format: https://workspace.slack.com/archives/C1234567890/p1234567890123456
        if "archives/" not in message_link:
            return {"error": "Invalid Slack permalink format"}
        
        parts = message_link.split("/")
        channel_id = None
        timestamp = None
        
        for i, part in enumerate(parts):
            if part == "archives" and i + 1 < len(parts):
                channel_id = parts[i + 1]
            elif part.startswith("p") and len(part) > 1:
                # Convert permalink timestamp format (p1234567890123456) to API format (1234567890.123456)
                ts_raw = part[1:]  # Remove 'p' prefix
                timestamp = f"{ts_raw[:10]}.{ts_raw[10:]}"
        
        if not channel_id or not timestamp:
            return {"error": "Could not parse channel ID and timestamp from permalink"}
        
        # Get the thread
        params = {
            "channel": channel_id,
            "ts": timestamp
        }
        
        data = make_slack_request("conversations.replies", params)
        
        messages = []
        for msg in data.get("messages", []):
            message_info = {
                "text": msg.get("text", ""),
                "user": msg.get("user", "Unknown"),
                "timestamp": msg.get("ts", ""),
                "formatted_time": datetime.fromtimestamp(float(msg.get("ts", "0"))).strftime("%Y-%m-%d %H:%M:%S") if msg.get("ts") else "Unknown",
                "is_thread_root": msg.get("ts") == timestamp
            }
            messages.append(message_info)
        
        return {
            "channel_id": channel_id,
            "thread_timestamp": timestamp,
            "message_count": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        return {"error": f"Failed to get thread: {str(e)}"}

@mcp.tool()
def get_recent_channel_activity(
    channel_name: str, 
    hours_back: Optional[int] = 24,
    limit: Optional[int] = 50
) -> Dict[str, Any]:
    """
    Get recent activity from a specific Slack channel
    
    Args:
        channel_name: Channel name (with or without #)
        hours_back: How many hours back to look (default: 24)
        limit: Maximum number of messages (default: 50)
    
    Returns:
        Dictionary containing recent messages from the channel
    """
    try:
        # Remove # if present
        channel_name = channel_name.lstrip('#')
        
        # First, find the channel ID
        channels_data = make_slack_request("conversations.list", {"types": "public_channel,private_channel"})
        
        channel_id = None
        for channel in channels_data.get("channels", []):
            if channel.get("name") == channel_name:
                channel_id = channel.get("id")
                break
        
        if not channel_id:
            return {"error": f"Channel '{channel_name}' not found or not accessible"}
        
        # Calculate timestamp for X hours ago
        oldest_time = datetime.now() - timedelta(hours=hours_back)
        oldest_ts = str(oldest_time.timestamp())
        
        # Get recent messages
        params = {
            "channel": channel_id,
            "oldest": oldest_ts,
            "limit": limit
        }
        
        data = make_slack_request("conversations.history", params)
        
        messages = []
        for msg in data.get("messages", []):
            message_info = {
                "text": msg.get("text", ""),
                "user": msg.get("user", "Unknown"),
                "timestamp": msg.get("ts", ""),
                "formatted_time": datetime.fromtimestamp(float(msg.get("ts", "0"))).strftime("%Y-%m-%d %H:%M:%S") if msg.get("ts") else "Unknown",
                "has_thread": bool(msg.get("reply_count", 0) > 0),
                "reply_count": msg.get("reply_count", 0)
            }
            messages.append(message_info)
        
        return {
            "channel_name": channel_name,
            "channel_id": channel_id,
            "hours_back": hours_back,
            "message_count": len(messages),
            "messages": sorted(messages, key=lambda x: x["timestamp"])  # Sort chronologically
        }
        
    except Exception as e:
        return {"error": f"Failed to get channel activity: {str(e)}"}

@mcp.tool()
def list_slack_channels(types: Optional[str] = "public_channel,private_channel") -> Dict[str, Any]:
    """
    List Slack channels you have access to
    
    Args:
        types: Comma-separated list of channel types (default: public_channel,private_channel)
               Options: public_channel, private_channel, mpim, im
    
    Returns:
        Dictionary containing list of accessible channels
    """
    try:
        params = {
            "types": types,
            "exclude_archived": True
        }
        
        data = make_slack_request("conversations.list", params)
        
        channels = []
        for channel in data.get("channels", []):
            channel_info = {
                "name": channel.get("name", ""),
                "id": channel.get("id", ""),
                "is_private": channel.get("is_private", False),
                "is_member": channel.get("is_member", False),
                "member_count": channel.get("num_members", 0),
                "topic": channel.get("topic", {}).get("value", ""),
                "purpose": channel.get("purpose", {}).get("value", "")
            }
            channels.append(channel_info)
        
        return {
            "channel_count": len(channels),
            "channels": sorted(channels, key=lambda x: x["name"])
        }
        
    except Exception as e:
        return {"error": f"Failed to list channels: {str(e)}"}

@mcp.tool()
def slack_health_check() -> Dict[str, Any]:
    """
    Check if Slack connection is working
    
    Returns:
        Dictionary with connection status and basic info
    """
    try:
        # Test the connection with auth.test
        data = make_slack_request("auth.test")
        
        return {
            "status": "connected",
            "team": data.get("team"),
            "user": data.get("user"),
            "user_id": data.get("user_id"),
            "team_id": data.get("team_id"),
            "url": data.get("url")
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
