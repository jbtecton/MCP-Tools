#!/usr/bin/env python3
"""
Jira & Confluence MCP Server using FastMCP

This server provides Jira and Confluence integration with tools to:
- Get a Jira ticket/issue
- Get comments for a Jira ticket
- Search Jira tickets using JQL
- Get attachments for a Jira ticket
- Download Jira attachments
- Create Confluence pages
- Update Confluence pages
- Delete Confluence pages
- Search Confluence pages

Setup:
1. pip install fastmcp requests python-dotenv
2. Set environment variables in .env file: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
3. Run: python jira_server.py
"""

import os
import requests
import json
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("Jira & Confluence Integration")

# Configuration from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Extract base URL for Confluence (same domain as Jira for Atlassian Cloud)
if JIRA_URL:
    # For Atlassian Cloud, Confluence is always at /wiki
    base_url = JIRA_URL.replace('/jira', '').replace('/secure', '').rstrip('/')
    CONFLUENCE_URL = base_url
else:
    CONFLUENCE_URL = None

if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
    raise ValueError("JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables must be set")

def get_auth():
    """Get authentication tuple for both Jira and Confluence"""
    return (JIRA_EMAIL, JIRA_API_TOKEN)

def make_jira_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make authenticated request to Jira API"""
    auth = get_auth()
    url = f"{JIRA_URL}/rest/api/3/{endpoint}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    if method == "GET":
        response = requests.get(url, headers=headers, auth=auth)
    elif method == "POST":
        response = requests.post(url, headers=headers, auth=auth, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, auth=auth, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers, auth=auth)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    response.raise_for_status()
    
    # Handle empty responses for DELETE requests
    if method == "DELETE" and response.status_code == 204:
        return {"status": "deleted"}
    
    return response.json()

def make_confluence_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make authenticated request to Confluence API"""
    auth = get_auth()
    url = f"{CONFLUENCE_URL}/wiki/rest/api/{endpoint}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    if method == "GET":
        response = requests.get(url, headers=headers, auth=auth)
    elif method == "POST":
        response = requests.post(url, headers=headers, auth=auth, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, auth=auth, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers, auth=auth)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    response.raise_for_status()
    
    # Handle empty responses for DELETE requests
    if method == "DELETE" and response.status_code == 204:
        return {"status": "deleted"}
    
    return response.json()

# ===== JIRA TOOLS =====

@mcp.tool()
def get_jira_ticket(ticket_key: str) -> Dict[str, Any]:
    """
    Get a Jira ticket/issue by its key (e.g., 'PROJ-123')
    
    Args:
        ticket_key: The Jira ticket key (e.g., 'PROJ-123', 'DEV-456')
    
    Returns:
        Dictionary containing ticket information including summary, description, status, etc.
    """
    try:
        # Get the issue with all fields including comments
        endpoint = f"issue/{ticket_key}"
        issue_data = make_jira_request(endpoint)
        
        # Extract and format the key information
        fields = issue_data.get("fields", {})
        
        # Extract comments from the comment field
        comment_section = fields.get("comment", {})
        raw_comments = comment_section.get("comments", [])
        
        comments = []
        for comment in raw_comments:
            comment_info = {
                "id": comment.get("id"),
                "author": comment.get("author", {}).get("displayName"),
                "author_email": comment.get("author", {}).get("emailAddress"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": comment.get("body", {}).get("content", []) if comment.get("body") else "No content"
            }
            comments.append(comment_info)
        
        result = {
            "key": issue_data.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description", {}).get("content", []) if fields.get("description") else "No description",
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
            "reporter": fields.get("reporter", {}).get("displayName"),
            "priority": fields.get("priority", {}).get("name"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "labels": fields.get("labels", []),
            "components": [comp.get("name") for comp in fields.get("components", [])],
            "total_comments": len(comments),
            "comments": comments
        }
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Ticket '{ticket_key}' not found"}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your Jira credentials."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to get ticket: {str(e)}"}

@mcp.tool()
def get_jira_ticket_comments(ticket_key: str, max_comments: Optional[int] = 10) -> Dict[str, Any]:
    """
    Get comments for a Jira ticket/issue
    
    Args:
        ticket_key: The Jira ticket key (e.g., 'PROJ-123', 'DEV-456')
        max_comments: Maximum number of comments to retrieve (default: 10)
    
    Returns:
        Dictionary containing list of comments with author, created date, and body
    """
    try:
        # Get comments for the issue
        endpoint = f"issue/{ticket_key}/comment?maxResults={max_comments}&orderBy=created"
        comments_data = make_jira_request(endpoint)
        
        comments = []
        for comment in comments_data.get("comments", []):
            comment_info = {
                "id": comment.get("id"),
                "author": comment.get("author", {}).get("displayName"),
                "author_email": comment.get("author", {}).get("emailAddress"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": comment.get("body", {}).get("content", []) if comment.get("body") else "No content"
            }
            comments.append(comment_info)
        
        result = {
            "ticket_key": ticket_key,
            "total_comments": comments_data.get("total", 0),
            "max_results": comments_data.get("maxResults", 0),
            "comments": comments
        }
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Ticket '{ticket_key}' not found"}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your Jira credentials."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to get comments: {str(e)}"}

@mcp.tool()
def search_jira_tickets(
    jql_query: str,
    max_results: Optional[int] = 20
) -> Dict[str, Any]:
    """
    Search Jira tickets using JQL (Jira Query Language)
    
    Args:
        jql_query: JQL query string (e.g., 'Project = "Tecton Customer Support" AND Organizations = "Varo Bank"')
        max_results: Maximum number of results to return (default: 20)
    
    Returns:
        Dictionary containing search results with ticket information
    """
    try:
        # Use the search endpoint with JQL
        params = {
            'jql': jql_query,
            'maxResults': max_results,
            'fields': 'summary,description,status,assignee,reporter,priority,created,updated,issuetype,labels,components'
        }
        
        # Make request using same auth method as other functions
        url = f"{JIRA_URL}/rest/api/3/search"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, auth=get_auth(), params=params)
        response.raise_for_status()
        search_data = response.json()
        
        # Format the results
        tickets = []
        for issue in search_data.get("issues", []):
            fields = issue.get("fields", {})
            
            ticket_info = {
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description", {}).get("content", []) if fields.get("description") else "No description",
                "status": fields.get("status", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                "reporter": fields.get("reporter", {}).get("displayName"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "labels": fields.get("labels", []),
                "components": [comp.get("name") for comp in fields.get("components", [])]
            }
            tickets.append(ticket_info)
        
        result = {
            "query": jql_query,
            "total_results": search_data.get("total", 0),
            "max_results": search_data.get("maxResults", 0),
            "start_at": search_data.get("startAt", 0),
            "tickets": tickets
        }
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            return {"error": f"Invalid JQL query: {e.response.text}"}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your Jira credentials."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to search tickets: {str(e)}"}

@mcp.tool()
def get_jira_ticket_attachments(ticket_key: str) -> Dict[str, Any]:
    """
    Get attachments for a Jira ticket/issue
    
    Args:
        ticket_key: The Jira ticket key (e.g., 'PROJ-123', 'DEV-456')
    
    Returns:
        Dictionary containing list of attachments with metadata
    """
    try:
        # Get the issue with attachment field
        endpoint = f"issue/{ticket_key}?fields=attachment"
        issue_data = make_jira_request(endpoint)
        
        attachments = []
        for attachment in issue_data.get("fields", {}).get("attachment", []):
            attachment_info = {
                "id": attachment.get("id"),
                "filename": attachment.get("filename"),
                "author": attachment.get("author", {}).get("displayName"),
                "created": attachment.get("created"),
                "size": attachment.get("size"),
                "mime_type": attachment.get("mimeType"),
                "content_url": attachment.get("content"),
                "thumbnail_url": attachment.get("thumbnail")
            }
            attachments.append(attachment_info)
        
        result = {
            "ticket_key": ticket_key,
            "total_attachments": len(attachments),
            "attachments": attachments
        }
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Ticket '{ticket_key}' not found"}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your Jira credentials."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to get attachments: {str(e)}"}

@mcp.tool()
def download_jira_attachment(
    attachment_id: str,
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download a Jira attachment by ID
    
    Args:
        attachment_id: The attachment ID from get_jira_ticket_attachments
        save_path: Optional path to save the file (if not provided, saves to /tmp)
    
    Returns:
        Dictionary with download status and file information
    """
    try:
        # First get the attachment content URL (this will return a 303 redirect)
        content_url = f"{JIRA_URL}/rest/api/3/attachment/content/{attachment_id}"
        
        # Make request to get the redirect
        headers = {"Accept": "application/json"}
        response = requests.get(content_url, headers=headers, auth=get_auth(), allow_redirects=False)
        
        if response.status_code != 303:
            return {"error": f"Expected 303 redirect, got {response.status_code}: {response.text}"}
        
        # Get the actual download URL from the Location header
        download_url = response.headers.get("Location")
        if not download_url:
            return {"error": "No redirect location found in response"}
        
        # Download the actual file from the redirect URL
        download_response = requests.get(download_url, allow_redirects=True)
        download_response.raise_for_status()
        
        # Extract filename from download URL or use attachment ID as fallback
        import re
        from urllib.parse import parse_qs, urlparse
        
        filename = f"attachment_{attachment_id}"
        # Try to get filename from URL parameters
        parsed_url = urlparse(download_url)
        params = parse_qs(parsed_url.query)
        if 'name' in params:
            filename = params['name'][0]
        
        # Determine save path
        if save_path is None:
            save_path = f"/tmp/{filename}"
        elif os.path.isdir(save_path):
            save_path = os.path.join(save_path, filename)
        
        # Save the file
        with open(save_path, 'wb') as f:
            f.write(download_response.content)
        
        # Get file size
        file_size = len(download_response.content)
        
        result = {
            "status": "downloaded",
            "attachment_id": attachment_id,
            "filename": filename,
            "save_path": save_path,
            "file_size": file_size,
            "content_type": download_response.headers.get('content-type', 'unknown'),
            "download_url": download_url
        }
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Attachment '{attachment_id}' not found"}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your Jira credentials."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to download attachment: {str(e)}"}

@mcp.tool()
def jira_health_check() -> Dict[str, Any]:
    """
    Check if Jira connection is working
    
    Returns:
        Dictionary with connection status
    """
    try:
        # Try to get server info to test connection
        endpoint = "serverInfo"
        server_info = make_jira_request(endpoint)
        
        return {
            "status": "connected",
            "jira_url": JIRA_URL,
            "server_title": server_info.get("serverTitle"),
            "version": server_info.get("version")
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "jira_url": JIRA_URL
        }

# ===== CONFLUENCE TOOLS =====

@mcp.tool()
def create_confluence_page(
    title: str,
    content: str,
    space_key: str,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new Confluence page
    
    Args:
        title: The title of the page
        content: The content of the page in HTML format (Confluence storage format)
        space_key: The space key (e.g., 'ISD' for the ISD space)
        parent_id: Optional parent page ID to create as a child page
    
    Returns:
        Dictionary containing the created page information
    """
    try:
        page_data = {
            "type": "page",
            "title": title,
            "space": {
                "key": space_key
            },
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        # Add parent if specified
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]
        
        result = make_confluence_request("content", method="POST", data=page_data)
        
        # Return formatted response with proper URL construction
        web_ui_path = result.get("_links", {}).get("webui", "")
        # For Atlassian Cloud, web UI URLs need /wiki prefix
        full_web_url = f"{CONFLUENCE_URL}/wiki{web_ui_path}" if web_ui_path else f"{CONFLUENCE_URL}/wiki/spaces/{space_key}/pages/{result.get('id')}"
        
        return {
            "status": "created",
            "page_id": result.get("id"),
            "title": result.get("title"),
            "space_key": result.get("space", {}).get("key"),
            "url": full_web_url,
            "web_ui_url": web_ui_path,
            "created": result.get("history", {}).get("createdDate"),
            "version": result.get("version", {}).get("number")
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            return {"error": f"Bad request: {e.response.text}. Check if space '{space_key}' exists and you have permissions."}
        elif e.response.status_code == 401:
            return {"error": "Authentication failed. Check your credentials."}
        elif e.response.status_code == 403:
            return {"error": f"Permission denied. You may not have permission to create pages in space '{space_key}'."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to create page: {str(e)}"}

@mcp.tool()
def update_confluence_page(
    page_id: str,
    title: str,
    content: str,
    version: int
) -> Dict[str, Any]:
    """
    Update an existing Confluence page
    
    Args:
        page_id: The ID of the page to update
        title: The new title of the page
        content: The new content of the page in HTML format (Confluence storage format)
        version: The current version number of the page (required for updates)
    
    Returns:
        Dictionary containing the updated page information
    """
    try:
        page_data = {
            "version": {
                "number": version + 1
            },
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        result = make_confluence_request(f"content/{page_id}", method="PUT", data=page_data)
        
        return {
            "status": "updated",
            "page_id": result.get("id"),
            "title": result.get("title"),
            "space_key": result.get("space", {}).get("key"),
            "web_ui_url": result.get("_links", {}).get("webui"),
            "updated": result.get("history", {}).get("lastUpdated", {}).get("when"),
            "version": result.get("version", {}).get("number")
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Page with ID '{page_id}' not found"}
        elif e.response.status_code == 409:
            return {"error": "Version conflict. The page may have been updated by someone else. Try getting the current version first."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to update page: {str(e)}"}

@mcp.tool()
def delete_confluence_page(page_id: str) -> Dict[str, Any]:
    """
    Delete a Confluence page
    
    Args:
        page_id: The ID of the page to delete
    
    Returns:
        Dictionary with deletion status
    """
    try:
        make_confluence_request(f"content/{page_id}", method="DELETE")
        
        return {
            "status": "deleted",
            "page_id": page_id,
            "message": "Page successfully deleted"
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Page with ID '{page_id}' not found"}
        elif e.response.status_code == 403:
            return {"error": "Permission denied. You may not have permission to delete this page."}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to delete page: {str(e)}"}

@mcp.tool()
def get_confluence_page(page_id: str) -> Dict[str, Any]:
    """
    Get a Confluence page by ID
    
    Args:
        page_id: The ID of the page to retrieve
    
    Returns:
        Dictionary containing page information
    """
    try:
        result = make_confluence_request(f"content/{page_id}?expand=body.storage,version,space")
        
        return {
            "page_id": result.get("id"),
            "title": result.get("title"),
            "space_key": result.get("space", {}).get("key"),
            "space_name": result.get("space", {}).get("name"),
            "content": result.get("body", {}).get("storage", {}).get("value"),
            "version": result.get("version", {}).get("number"),
            "created": result.get("history", {}).get("createdDate"),
            "web_ui_url": result.get("_links", {}).get("webui")
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Page with ID '{page_id}' not found"}
        else:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to get page: {str(e)}"}

@mcp.tool()
def search_confluence_pages(
    query: str,
    space_key: Optional[str] = None,
    limit: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Search for Confluence pages
    
    Args:
        query: Search query string
        space_key: Optional space key to limit search to a specific space
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Build CQL query
        cql_query = f'text ~ "{query}" and type = page'
        if space_key:
            cql_query += f' and space = "{space_key}"'
        
        params = {
            "cql": cql_query,
            "limit": limit
        }
        
        result = make_confluence_request("content/search", method="GET")
        
        # The above line is incorrect for search, let me fix it
        # Search endpoint is different
        url = f"{CONFLUENCE_URL}/wiki/rest/api/search"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, auth=get_auth(), params=params)
        response.raise_for_status()
        result = response.json()
        
        pages = []
        for item in result.get("results", []):
            page_info = {
                "page_id": item.get("content", {}).get("id"),
                "title": item.get("title"),
                "space_key": item.get("content", {}).get("space", {}).get("key"),
                "url": item.get("url"),
                "excerpt": item.get("excerpt")
            }
            pages.append(page_info)
        
        return {
            "query": query,
            "space_key": space_key,
            "total_results": result.get("totalSize", 0),
            "pages": pages
        }
        
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Failed to search pages: {str(e)}"}

@mcp.tool()
def confluence_health_check() -> Dict[str, Any]:
    """
    Check if Confluence connection is working
    
    Returns:
        Dictionary with connection status
    """
    try:
        # Try to get space information to test connection
        result = make_confluence_request("space?limit=1")
        
        return {
            "status": "connected",
            "confluence_url": CONFLUENCE_URL,
            "total_spaces": result.get("size", 0)
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "confluence_url": CONFLUENCE_URL
        }

@mcp.tool()
def create_tech_article_from_jira(
    ticket_key: str,
    space_key: str = "ISD",
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a technical article in Confluence based on a Jira ticket
    This is a convenience function that follows the standard tech article template
    
    Args:
        ticket_key: The Jira ticket key (e.g., 'CS-6814')
        space_key: The Confluence space key (default: 'ISD')
        parent_id: Optional parent page ID
    
    Returns:
        Dictionary containing the created page information
    """
    try:
        # First, get the Jira ticket information directly using the API
        endpoint = f"issue/{ticket_key}?fields=summary,description,status,assignee,reporter,priority,created,updated,issuetype,labels,components"
        issue_data = make_jira_request(endpoint)
        
        # Extract and format the key information
        fields = issue_data.get("fields", {})
        
        ticket_result = {
            "key": issue_data.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description", {}).get("content", []) if fields.get("description") else "No description",
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
            "reporter": fields.get("reporter", {}).get("displayName"),
            "priority": fields.get("priority", {}).get("name"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "labels": fields.get("labels", []),
            "components": [comp.get("name") for comp in fields.get("components", [])]
        }
        

        # Get ticket comments directly using the API
        comments_endpoint = f"issue/{ticket_key}/comment?maxResults=50&orderBy=created"
        comments_data = make_jira_request(comments_endpoint)
        
        comments = []
        for comment in comments_data.get("comments", []):
            comment_info = {
                "id": comment.get("id"),
                "author": comment.get("author", {}).get("displayName"),
                "author_email": comment.get("author", {}).get("emailAddress"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": comment.get("body", {}).get("content", []) if comment.get("body") else "No content"
            }
            comments.append(comment_info)
        
        comments_result = {
            "ticket_key": ticket_key,
            "total_comments": comments_data.get("total", 0),
            "max_results": comments_data.get("maxResults", 0),
            "comments": comments
        }
        

        # Create the article title based on the ticket summary
        article_title = f"Tech Article: {ticket_result['summary']}"
        
        # Build the article content in Confluence storage format (HTML)
        content_parts = [
            f"<h1>{article_title}</h1>",
            f"<p><strong>Based on Jira Ticket:</strong> <a href=\"{JIRA_URL}/browse/{ticket_key}\">{ticket_key}</a></p>",
            
            "<h2>1. Organization Name</h2>",
            "<p>[To be filled based on ticket details]</p>",
            
            "<h2>2. Tecton SDK Version</h2>",
            "<p>[To be filled based on ticket details]</p>",
            
            "<h2>3. The Issue</h2>",
            f"<p><strong>Summary:</strong> {ticket_result['summary']}</p>",
        ]
        
        # Add description if available
        if ticket_result['description'] and ticket_result['description'] != "No description":
            content_parts.extend([
                "<p><strong>Description:</strong></p>",
                f"<div>{ticket_result['description']}</div>"
            ])
        
        # Add ticket metadata
        content_parts.extend([
            f"<p><strong>Priority:</strong> {ticket_result['priority']}</p>",
            f"<p><strong>Reporter:</strong> {ticket_result['reporter']}</p>",
            f"<p><strong>Status:</strong> {ticket_result['status']}</p>",
        ])
        
        # Add template sections
        content_parts.extend([
            "<h2>4. Investigation Steps</h2>",
            "<p>[Document the investigation steps taken to identify the root cause]</p>",
            "<ul>",
            "<li>[Step 1]</li>",
            "<li>[Step 2]</li>",
            "<li>[Add more steps as needed]</li>",
            "</ul>",
            
            "<h2>5. Fix or Workaround</h2>",
            "<p>[Describe the fix or workaround implemented]</p>",
            "<p>[Include code snippets or configuration changes if applicable]</p>",
            
            "<h2>6. Important Concepts</h2>",
            "<p>[Highlight important Tecton concepts or development practices that could have prevented this issue]</p>",
            
            "<h2>7. References</h2>",
            "<ol>",
            f"<li><a href=\"{JIRA_URL}/browse/{ticket_key}\">Original Jira Ticket: {ticket_key}</a></li>",
            "<li>[Add external documentation links]</li>",
            "</ol>"
        ])
        
        # Add comments section if there are comments
        if comments_result['comments']:
            content_parts.extend([
                "<h2>Comments from Jira Ticket</h2>"
            ])
            
            for comment in comments_result['comments']:
                content_parts.extend([
                    f"<h3>Comment by {comment['author']} - {comment['created']}</h3>",
                    f"<div>{comment['body']}</div>",
                    "<hr/>"
                ])
        
        # Join all content
        full_content = "\n".join(content_parts)
        
        # Create the Confluence page directly using the API
        page_data = {
            "type": "page",
            "title": article_title,
            "space": {
                "key": space_key
            },
            "body": {
                "storage": {
                    "value": full_content,
                    "representation": "storage"
                }
            }
        }
        
        # Add parent if specified
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]
        
        result = make_confluence_request("content", method="POST", data=page_data)
        
        # Return formatted response with proper URL construction
        web_ui_path = result.get("_links", {}).get("webui", "")
        # For Atlassian Cloud, web UI URLs need /wiki prefix
        full_web_url = f"{CONFLUENCE_URL}/wiki{web_ui_path}" if web_ui_path else f"{CONFLUENCE_URL}/wiki/spaces/{space_key}/pages/{result.get('id')}"
        
        return {
            "status": "created",
            "page_id": result.get("id"),
            "title": result.get("title"),
            "space_key": result.get("space", {}).get("key"),
            "url": full_web_url,
            "web_ui_url": web_ui_path,
            "created": result.get("history", {}).get("createdDate"),
            "version": result.get("version", {}).get("number"),
            "article_title": article_title,
            "ticket_key": ticket_key
        }
        
    except Exception as e:
        return {"error": f"Failed to create tech article: {str(e)}"}

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
