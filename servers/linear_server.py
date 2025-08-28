#!/usr/bin/env python3
"""
Linear MCP Server
Core tools for searching issues and getting detailed issue information
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")

if not LINEAR_API_KEY:
    raise ValueError("LINEAR_API_KEY environment variable must be set")

# Set up logging (no stdout to avoid MCP protocol interference)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Linear Integration")

def get_linear_headers():
    """Get headers for Linear API requests"""
    return {
        'Content-Type': 'application/json',
        'Authorization': LINEAR_API_KEY
    }

async def execute_graphql_query(query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
    """Execute a GraphQL query against Linear API"""
    try:
        url = "https://api.linear.app/graphql"
        headers = get_linear_headers()
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        # Use requests.post
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                return {
                    "status": "error",
                    "message": "GraphQL errors",
                    "errors": data['errors']
                }
            return {
                "status": "success",
                "data": data.get('data', {})
            }
        else:
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}",
                "response": response.text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception: {str(e)}"
        }

@mcp.tool()
async def linear_health_check() -> Dict[str, Any]:
    """
    Check if Linear connection is working and get basic user info
    
    Returns:
        Dictionary with connection status and user info
    """
    query = """
    query {
        viewer {
            id
            name
            email
        }
    }
    """
    
    result = await execute_graphql_query(query)
    
    if result["status"] == "success" and "viewer" in result["data"]:
        viewer = result["data"]["viewer"]
        return {
            "status": "connected",
            "user_id": viewer.get('id'),
            "user_name": viewer.get('name'),
            "user_email": viewer.get('email'),
            "message": "Linear API connection successful"
        }
    else:
        return result

@mcp.tool()
async def linear_search_issues(
    search_term: Optional[str] = None,
    assignee_email: Optional[str] = None,
    state: Optional[str] = None,
    team_key: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search Linear issues by various criteria
    
    Args:
        search_term: Text to search in issue title and description
        assignee_email: Email of assignee to filter by
        state: Issue state (e.g., "Todo", "In Progress", "Done", "Canceled")
        team_key: Team key to filter by (e.g., "ENG", "DESIGN")
        limit: Maximum number of issues to return (default 20)
    
    Returns:
        Dictionary with search results
    """
    # Build filter conditions
    filters = []
    
    if assignee_email:
        filters.append(f'assignee: {{ email: {{ eq: "{assignee_email}" }} }}')
    
    if state:
        filters.append(f'state: {{ name: {{ eq: "{state}" }} }}')
    
    if team_key:
        filters.append(f'team: {{ key: {{ eq: "{team_key}" }} }}')
    
    search_params = [f"first: {limit}"]
    if filters:
        filter_str = f"filter: {{ {', '.join(filters)} }}"
        search_params.append(filter_str)
    
    query = f"""
    query {{
        issues({', '.join(search_params)}) {{
            nodes {{
                id
                identifier
                title
                description
                url
                priority
                estimate
                createdAt
                updatedAt
                state {{
                    name
                    color
                }}
                assignee {{
                    name
                    email
                }}
                creator {{
                    name
                    email
                }}
                team {{
                    key
                    name
                }}
                labels {{
                    nodes {{
                        name
                        color
                    }}
                }}
            }}
            pageInfo {{
                hasNextPage
                hasPreviousPage
            }}
        }}
    }}
    """
    
    result = await execute_graphql_query(query)
    
    if result["status"] == "success":
        issues_data = result["data"].get("issues", {})
        issues = issues_data.get("nodes", [])
        
        # Client-side text filtering
        if search_term:
            filtered_issues = []
            search_lower = search_term.lower()
            for issue in issues:
                title = issue.get('title', '').lower()
                description = issue.get('description', '') or ''
                description = description.lower()
                if search_lower in title or search_lower in description:
                    filtered_issues.append(issue)
            issues = filtered_issues
        
        return {
            "status": "success",
            "issues": issues,
            "count": len(issues),
            "has_more": issues_data.get("pageInfo", {}).get("hasNextPage", False),
            "search_params": {
                "search_term": search_term,
                "assignee_email": assignee_email,
                "state": state,
                "team_key": team_key,
                "limit": limit
            }
        }
    else:
        return result

@mcp.tool()
async def linear_get_issue_details(issue_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific Linear issue including comments
    
    Args:
        issue_id: Linear issue ID (the full ID, not just the identifier like ENG-123)
    
    Returns:
        Dictionary with detailed issue information including comments
    """
    query = """
    query($issueId: String!) {
        issue(id: $issueId) {
            id
            identifier
            title
            description
            url
            priority
            estimate
            createdAt
            updatedAt
            state {
                name
                color
            }
            assignee {
                name
                email
            }
            creator {
                name
                email
            }
            team {
                key
                name
            }
            comments {
                nodes {
                    id
                    body
                    createdAt
                    user {
                        name
                        email
                    }
                }
            }
        }
    }
    """
    
    variables = {"issueId": issue_id}
    result = await execute_graphql_query(query, variables)
    
    if result["status"] == "success":
        issue = result["data"].get("issue")
        if issue:
            return {
                "status": "success",
                "issue": issue
            }
        else:
            return {
                "status": "error",
                "message": f"Issue not found: {issue_id}"
            }
    else:
        return result

@mcp.tool()
async def linear_get_issue_by_identifier(identifier: str) -> Dict[str, Any]:
    """
    Get issue details by identifier (like ENG-123) - convenience method
    
    Args:
        identifier: Linear issue identifier (e.g., "ENG-123", "DESIGN-45")
    
    Returns:
        Dictionary with detailed issue information including comments
    """
    query = f"""
    query {{
        issues(first: 100) {{
            nodes {{
                id
                identifier
            }}
        }}
    }}
    """
    
    result = await execute_graphql_query(query)
    
    if result["status"] == "success":
        issues = result["data"].get("issues", {}).get("nodes", [])
        for issue in issues:
            if issue["identifier"] == identifier:
                return await linear_get_issue_details(issue["id"])
        
        return {
            "status": "error",
            "message": f"Issue not found with identifier: {identifier}"
        }
    else:
        return result

if __name__ == "__main__":
    mcp.run()
