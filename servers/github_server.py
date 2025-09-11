#!/usr/bin/env python3
"""
GitHub MCP Server using FastMCP

This server provides GitHub integration with tools to:
- Read files from repositories
- Search code across repositories
- Browse directory structures
- Get commit history
- List branches and tags
- Search repositories

Setup:
1. pip install fastmcp requests python-dotenv
2. Set environment variables in .env file: GITHUB_TOKEN
3. Run: python github_server.py
"""

import os
import requests
import json
import base64
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("GitHub Integration")

# Configuration from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable must be set")

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

def get_github_headers():
    """Get headers for GitHub API requests"""
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'FastMCP-GitHub-Integration'
    }

def make_github_request(endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a request to the GitHub API"""
    try:
        url = f"{GITHUB_API_BASE}{endpoint}"
        headers = get_github_headers()
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "data": response.json()
            }
        else:
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception: {str(e)}"
        }

@mcp.tool()
async def github_health_check() -> Dict[str, Any]:
    """
    Check if GitHub connection is working and get basic user info
    
    Returns:
        Dictionary with connection status and user info
    """
    result = make_github_request("/user")
    
    if result["status"] == "success":
        user_data = result["data"]
        return {
            "status": "success",
            "message": "GitHub connection working",
            "user": {
                "login": user_data.get("login"),
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "public_repos": user_data.get("public_repos"),
                "private_repos": user_data.get("total_private_repos")
            }
        }
    else:
        return result

@mcp.tool()
async def github_read_file(
    owner: str, 
    repo: str, 
    path: str, 
    ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read a file from a GitHub repository
    
    Args:
        owner: Repository owner (e.g., 'tecton-ai')
        repo: Repository name (e.g., 'tecton')
        path: File path within the repository
        ref: Optional branch/tag/commit (defaults to default branch)
    
    Returns:
        Dictionary with file content and metadata
    """
    endpoint = f"/repos/{owner}/{repo}/contents/{path}"
    params = {}
    if ref:
        params['ref'] = ref
        
    result = make_github_request(endpoint, params)
    
    if result["status"] == "success":
        file_data = result["data"]
        
        if file_data.get("type") == "file":
            # Decode base64 content
            try:
                content = base64.b64decode(file_data["content"]).decode('utf-8')
                return {
                    "status": "success",
                    "file_info": {
                        "name": file_data["name"],
                        "path": file_data["path"],
                        "size": file_data["size"],
                        "sha": file_data["sha"],
                        "url": file_data["html_url"]
                    },
                    "content": content
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to decode file content: {str(e)}"
                }
        else:
            return {
                "status": "error",
                "message": f"Path '{path}' is not a file (type: {file_data.get('type')})"
            }
    else:
        return result

@mcp.tool()
async def github_list_directory(
    owner: str, 
    repo: str, 
    path: Optional[str] = None, 
    ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    List contents of a directory in a GitHub repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: Directory path (empty or None for root)
        ref: Optional branch/tag/commit
    
    Returns:
        Dictionary with directory contents
    """
    path = path or ""
    endpoint = f"/repos/{owner}/{repo}/contents/{path}"
    params = {}
    if ref:
        params['ref'] = ref
        
    result = make_github_request(endpoint, params)
    
    if result["status"] == "success":
        contents = result["data"]
        
        if isinstance(contents, list):
            items = []
            for item in contents:
                items.append({
                    "name": item["name"],
                    "path": item["path"],
                    "type": item["type"],
                    "size": item.get("size", 0),
                    "url": item["html_url"]
                })
            
            return {
                "status": "success",
                "path": path,
                "items": items,
                "count": len(items)
            }
        else:
            return {
                "status": "error",
                "message": f"Path '{path}' is not a directory"
            }
    else:
        return result

@mcp.tool()
async def github_search_code(
    query: str,
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search for code in GitHub repositories
    
    Args:
        query: Search query
        owner: Optional repository owner to limit search
        repo: Optional repository name to limit search
        language: Optional programming language filter
        limit: Maximum number of results (default 20)
    
    Returns:
        Dictionary with search results
    """
    # Build search query
    search_terms = [query]
    
    if owner and repo:
        search_terms.append(f"repo:{owner}/{repo}")
    elif owner:
        search_terms.append(f"user:{owner}")
        
    if language:
        search_terms.append(f"language:{language}")
    
    search_query = " ".join(search_terms)
    
    params = {
        "q": search_query,
        "per_page": min(limit, 100)  # GitHub API limit
    }
    
    result = make_github_request("/search/code", params)
    
    if result["status"] == "success":
        search_data = result["data"]
        
        items = []
        for item in search_data.get("items", []):
            items.append({
                "name": item["name"],
                "path": item["path"],
                "repository": {
                    "name": item["repository"]["name"],
                    "full_name": item["repository"]["full_name"],
                    "owner": item["repository"]["owner"]["login"]
                },
                "score": item["score"],
                "url": item["html_url"],
                "git_url": item["git_url"]
            })
        
        return {
            "status": "success",
            "query": search_query,
            "total_count": search_data.get("total_count", 0),
            "items": items,
            "returned_count": len(items)
        }
    else:
        return result

@mcp.tool()
async def github_get_commits(
    owner: str, 
    repo: str, 
    path: Optional[str] = None,
    branch: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get commit history for a repository or specific file
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: Optional file path to get commits for specific file
        branch: Optional branch name (defaults to default branch)
        limit: Maximum number of commits (default 10)
    
    Returns:
        Dictionary with commit history
    """
    endpoint = f"/repos/{owner}/{repo}/commits"
    params = {
        "per_page": min(limit, 100)
    }
    
    if path:
        params["path"] = path
    if branch:
        params["sha"] = branch
        
    result = make_github_request(endpoint, params)
    
    if result["status"] == "success":
        commits_data = result["data"]
        
        commits = []
        for commit in commits_data:
            commits.append({
                "sha": commit["sha"][:8],  # Short SHA
                "full_sha": commit["sha"],
                "message": commit["commit"]["message"].split('\n')[0],  # First line only
                "author": {
                    "name": commit["commit"]["author"]["name"],
                    "email": commit["commit"]["author"]["email"],
                    "date": commit["commit"]["author"]["date"]
                },
                "url": commit["html_url"]
            })
        
        return {
            "status": "success",
            "repository": f"{owner}/{repo}",
            "path": path,
            "branch": branch,
            "commits": commits,
            "count": len(commits)
        }
    else:
        return result

@mcp.tool()
async def github_get_branches(owner: str, repo: str) -> Dict[str, Any]:
    """
    Get all branches for a repository
    
    Args:
        owner: Repository owner
        repo: Repository name
    
    Returns:
        Dictionary with branch information
    """
    endpoint = f"/repos/{owner}/{repo}/branches"
    
    result = make_github_request(endpoint)
    
    if result["status"] == "success":
        branches_data = result["data"]
        
        branches = []
        for branch in branches_data:
            branches.append({
                "name": branch["name"],
                "sha": branch["commit"]["sha"],
                "protected": branch.get("protected", False)
            })
        
        return {
            "status": "success",
            "repository": f"{owner}/{repo}",
            "branches": branches,
            "count": len(branches)
        }
    else:
        return result

@mcp.tool()
async def github_get_repository_info(owner: str, repo: str) -> Dict[str, Any]:
    """
    Get information about a repository
    
    Args:
        owner: Repository owner
        repo: Repository name
    
    Returns:
        Dictionary with repository information
    """
    endpoint = f"/repos/{owner}/{repo}"
    
    result = make_github_request(endpoint)
    
    if result["status"] == "success":
        repo_data = result["data"]
        
        return {
            "status": "success",
            "repository": {
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data["description"],
                "private": repo_data["private"],
                "default_branch": repo_data["default_branch"],
                "language": repo_data["language"],
                "size": repo_data["size"],
                "stars": repo_data["stargazers_count"],
                "forks": repo_data["forks_count"],
                "open_issues": repo_data["open_issues_count"],
                "created_at": repo_data["created_at"],
                "updated_at": repo_data["updated_at"],
                "clone_url": repo_data["clone_url"],
                "html_url": repo_data["html_url"]
            }
        }
    else:
        return result

@mcp.tool()
async def github_search_repositories(
    query: str,
    user: Optional[str] = None,
    org: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search for repositories on GitHub
    
    Args:
        query: Search query
        user: Optional username to limit search
        org: Optional organization to limit search
        language: Optional programming language filter
        limit: Maximum number of results (default 20)
    
    Returns:
        Dictionary with repository search results
    """
    # Build search query
    search_terms = [query]
    
    if user:
        search_terms.append(f"user:{user}")
    if org:
        search_terms.append(f"org:{org}")
    if language:
        search_terms.append(f"language:{language}")
    
    search_query = " ".join(search_terms)
    
    params = {
        "q": search_query,
        "per_page": min(limit, 100)
    }
    
    result = make_github_request("/search/repositories", params)
    
    if result["status"] == "success":
        search_data = result["data"]
        
        repositories = []
        for repo in search_data.get("items", []):
            repositories.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "language": repo["language"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "updated_at": repo["updated_at"],
                "html_url": repo["html_url"],
                "score": repo["score"]
            })
        
        return {
            "status": "success",
            "query": search_query,
            "total_count": search_data.get("total_count", 0),
            "repositories": repositories,
            "returned_count": len(repositories)
        }
    else:
        return result

if __name__ == "__main__":
    mcp.run()




