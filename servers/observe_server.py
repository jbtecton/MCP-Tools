#!/usr/bin/env python3
"""
FastMCP server for Observe log analysis integration
Allows natural language querying of Observe log data using OPAL
"""

import asyncio
import httpx
import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
OBSERVE_TENANT_URL = os.getenv("OBSERVE_TENANT_URL")  # e.g., "https://168585119059.observeinc.com"
OBSERVE_USER_EMAIL = os.getenv("OBSERVE_USER_EMAIL")  # e.g., "jason.barr@tecton.ai"
OBSERVE_API_TOKEN = os.getenv("OBSERVE_API_TOKEN")  # Bearer token from delegated login
OBSERVE_DATASET_ID = os.getenv("OBSERVE_DATASET_ID", "42310100")  # Default to Container Logs dataset
OBSERVE_TENANT_ID = os.getenv("OBSERVE_TENANT_ID", "168585119059")  # Tenant ID for auth header

if not OBSERVE_TENANT_URL:
    raise ValueError("OBSERVE_TENANT_URL environment variable must be set")
if not OBSERVE_USER_EMAIL:
    raise ValueError("OBSERVE_USER_EMAIL environment variable must be set")
if not OBSERVE_API_TOKEN:
    raise ValueError("OBSERVE_API_TOKEN environment variable must be set")

# Initialize FastMCP
mcp = FastMCP("Observe Log Analysis Integration")

class ObserveClient:
    def __init__(self):
        self.tenant_url = OBSERVE_TENANT_URL.rstrip('/')
        self.user_email = OBSERVE_USER_EMAIL
        self.dataset_id = OBSERVE_DATASET_ID
        self.tenant_id = OBSERVE_TENANT_ID
        self.headers = {
            "Authorization": f"Bearer {OBSERVE_TENANT_ID} {OBSERVE_API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def get_bearer_token(self) -> Optional[str]:
        """Get a fresh bearer token via delegated login (if needed)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                login_data = {
                    "userEmail": self.user_email,
                    "integration": "observe-tool-mcp",
                    "clientToken": f"MCP login {datetime.now().isoformat()}"
                }
                
                response = await client.post(
                    f"{self.tenant_url}/v1/login/delegated",
                    json=login_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("serverToken")
                else:
                    return None
        except Exception:
            return None
    
    def _parse_time_range(self, time_range: str) -> tuple[datetime, datetime]:
        """Parse time range string to start and end datetime objects"""
        end_time = datetime.utcnow()
        
        if time_range.endswith('m'):
            minutes = int(time_range[:-1])
            start_time = end_time - timedelta(minutes=minutes)
        elif time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = end_time - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = end_time - timedelta(days=days)
        elif time_range.endswith('w'):
            weeks = int(time_range[:-1])
            start_time = end_time - timedelta(weeks=weeks)
        else:
            # Default to 1 hour if format not recognized
            start_time = end_time - timedelta(hours=1)
        
        return start_time, end_time
    
    def _build_simple_filter(self, field_name: str, values: List[str]) -> str:
        """Build a simple filter for a single field with multiple values"""
        if len(values) == 1:
            return f'filter {field_name} = "{values[0]}"'
        else:
            # Use multiple individual filters instead of complex OR syntax
            filters = []
            for value in values:
                filters.append(f'{field_name} = "{value}"')
            return 'filter (' + ' or '.join(filters) + ')'
    
    def _build_search_filter(self, search_terms: List[str]) -> str:
        """Build a simple search filter for log content"""
        if len(search_terms) == 1:
            return f'filter contains(log, "{search_terms[0]}")'
        else:
            # Use multiple contains conditions
            filters = []
            for term in search_terms:
                filters.append(f'contains(log, "{term}")')
            return 'filter (' + ' or '.join(filters) + ')'
    
    def _build_opal_query(
        self,
        container_names: Optional[List[str]] = None,
        clusters: Optional[List[str]] = None,
        time_range: str = "1h",
        search_terms: Optional[List[str]] = None,
        log_levels: Optional[List[str]] = None,
        http_methods: Optional[List[str]] = None,
        http_status_codes: Optional[List[str]] = None,
        endpoint_patterns: Optional[List[str]] = None,
        extract_pattern: Optional[str] = None,
        extract_field_name: Optional[str] = None,
        limit: int = 100
    ) -> str:
        """Build OPAL query from parameters with simplified syntax"""
        
        start_time, end_time = self._parse_time_range(time_range)
        
        # Start with base log dataset and time filter using correct field name
        query_parts = [
            f'filter timestamp >= "{start_time.isoformat()}Z"',
            f'filter timestamp <= "{end_time.isoformat()}Z"'
        ]
        
        # Container name filters - simplified
        if container_names:
            query_parts.append(self._build_simple_filter("container_name", container_names))
        
        # Cluster filters - simplified  
        if clusters:
            query_parts.append(self._build_simple_filter("cluster", clusters))
        
        # Log level filters - simplified to check only common fields
        if log_levels:
            level_filters = []
            for level in log_levels:
                level_upper = level.upper()
                level_filters.append(f'log_level = "{level_upper}"')
            if level_filters:
                query_parts.append('filter (' + ' or '.join(level_filters) + ')')
        
        # Search terms in log content - simplified
        if search_terms:
            query_parts.append(self._build_search_filter(search_terms))
        
        # HTTP method filters - simplified
        if http_methods:
            method_filters = []
            for method in http_methods:
                method_filters.append(f'http_method = "{method}"')
            if method_filters:
                query_parts.append('filter (' + ' or '.join(method_filters) + ')')
        
        # HTTP status code filters - use regex to parse from nginx logs
        if http_status_codes:
            # HTTP status codes are embedded in nginx logs like: "POST /path HTTP/1.1" 200
            # Use regex to match the status codes in the log content
            status_filters = []
            
            for code in http_status_codes:
                if code.startswith('!'):
                    # Exclude this status code - pattern: "METHOD /path HTTP/1.1" NOT_THIS_CODE
                    actual_code = code[1:]
                    status_filters.append(f'not regex_match(log, r"\\"[A-Z]+ [^\\"]+\\s+HTTP/\\d\\.\\d\\"\\s+{actual_code}\\s+")')
                else:
                    # Include this status code - pattern: "METHOD /path HTTP/1.1" THIS_CODE
                    status_filters.append(f'regex_match(log, r"\\"[A-Z]+ [^\\"]+\\s+HTTP/\\d\\.\\d\\"\\s+{code}\\s+")')
            
            if status_filters:
                query_parts.append('filter (' + ' or '.join(status_filters) + ')')
        
        # Endpoint pattern filters - simplified
        if endpoint_patterns:
            endpoint_filters = []
            for pattern in endpoint_patterns:
                endpoint_filters.append(f'contains(log, "{pattern}")')
            if endpoint_filters:
                query_parts.append('filter (' + ' or '.join(endpoint_filters) + ')')
        
        # Add field extraction if specified
        if extract_pattern and extract_field_name:
            query_parts.append(f'make {extract_field_name} = extract_regex(message, r"{extract_pattern}", 1)')
        
        # Add limit
        query_parts.append(f'limit {limit}')
        
        # Join all query parts with proper OPAL syntax
        return '\n| '.join(query_parts)
    
    async def execute_opal_query(self, opal_pipeline: str, time_range: str = "1h", output_format: str = "json") -> Dict[str, Any]:
        """Execute an OPAL query against Observe using the correct API format"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Build the correct JSON structure
                payload = {
                    "query": {
                        "stages": [
                            {
                                "input": [
                                    {
                                        "inputName": "system",
                                        "datasetId": self.dataset_id
                                    }
                                ],
                                "stageID": "main",
                                "pipeline": opal_pipeline
                            }
                        ]
                    }
                }
                
                # Add time range as URL parameter
                url_params = {"interval": time_range}
                
                response = await client.post(
                    f"{self.tenant_url}/v1/meta/export/query",
                    headers=self.headers,
                    json=payload,
                    params=url_params
                )
                
                if response.status_code == 200:
                    # Parse response - it's newline-delimited JSON by default
                    response_text = response.text.strip()
                    if output_format == "json" and response_text:
                        # Parse newline-delimited JSON into a list
                        lines = response_text.split('\n')
                        data = []
                        for line in lines:
                            if line.strip():
                                try:
                                    data.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue
                        return {
                            "status": "success",
                            "data": data,
                            "count": len(data),
                            "pipeline": opal_pipeline
                        }
                    else:
                        return {
                            "status": "success",
                            "data": response_text,
                            "pipeline": opal_pipeline
                        }
                else:
                    return {
                        "status": "error",
                        "error": f"API request failed: {response.status_code} - {response.text}",
                        "pipeline": opal_pipeline
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": f"Exception: {str(e)}",
                "pipeline": opal_pipeline
            }

# Initialize client
client = ObserveClient()

@mcp.tool()
async def observe_health_check() -> str:
    """Test Observe API connectivity and authentication"""
    try:
        # Try a simple pipeline to test connectivity using correct field name
        test_pipeline = '''filter timestamp >= "2024-01-01T00:00:00Z"
| limit 1'''
        
        result = await client.execute_opal_query(test_pipeline, time_range="1h")
        
        if result["status"] == "success":
            return json.dumps({
                "status": "connected",
                "message": "Observe API connection successful",
                "tenant_url": client.tenant_url,
                "user_email": client.user_email,
                "test_pipeline": test_pipeline
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to connect to Observe API",
                "error": result.get("error", "Unknown error"),
                "test_pipeline": test_pipeline
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }, indent=2)

@mcp.tool()
async def observe_query_logs(
    container_names: Optional[str] = None,  # Comma-separated string
    clusters: Optional[str] = None,         # Comma-separated string
    time_range: str = "1h",
    search_terms: Optional[str] = None,     # Comma-separated string
    log_levels: Optional[str] = None,       # Comma-separated string
    http_methods: Optional[str] = None,     # Comma-separated string
    http_status_codes: Optional[str] = None, # Comma-separated string
    endpoint_patterns: Optional[str] = None, # Comma-separated string
    extract_pattern: Optional[str] = None,
    extract_field_name: Optional[str] = None,
    limit: int = 100,
    output_format: str = "json"
) -> str:
    """
    Query Observe logs with flexible filtering and extraction capabilities
    
    Args:
        container_names: Comma-separated container names to filter by (e.g., "java-orchestrator,controller")
        clusters: Comma-separated cluster names to filter by (e.g., "block-production,hf-prod")
        time_range: Time range for logs (e.g., "1h", "1d", "1w")
        search_terms: Comma-separated terms to search for in log content (e.g., "error,exception,failed")
        log_levels: Comma-separated log levels to filter by (e.g., "error,warning")
        http_methods: Comma-separated HTTP methods to filter by (e.g., "POST,GET")
        http_status_codes: Comma-separated status codes to filter by (e.g., "500,404" or "!200" to exclude 200)
        endpoint_patterns: Comma-separated endpoint patterns to search for (e.g., "get-features,api/v1")
        extract_pattern: Regex pattern to extract specific data from log messages
        extract_field_name: Name for the extracted field (required if extract_pattern is provided)
        limit: Maximum number of log entries to return (default 100)
        output_format: Output format - "json" or "csv"
    
    Returns:
        JSON string with query results
    """
    
    return await _observe_query_logs_impl(
        container_names=container_names,
        clusters=clusters,
        time_range=time_range,
        search_terms=search_terms,
        log_levels=log_levels,
        http_methods=http_methods,
        http_status_codes=http_status_codes,
        endpoint_patterns=endpoint_patterns,
        extract_pattern=extract_pattern,
        extract_field_name=extract_field_name,
        limit=limit,
        output_format=output_format
    )

@mcp.tool()
async def observe_raw_query(opal_query: str, output_format: str = "json") -> str:
    """
    Execute a raw OPAL query against Observe for advanced users
    
    Args:
        opal_query: Raw OPAL query string
        output_format: Output format - "json" or "csv"
    
    Returns:
        JSON string with query results
    """
    
    result = await client.execute_opal_query(opal_query, "1h", output_format)
    return json.dumps(result, indent=2)

# Extract the actual function before decoration for internal use
async def _observe_query_logs_impl(
    container_names: Optional[str] = None,
    clusters: Optional[str] = None,
    time_range: str = "1h",
    search_terms: Optional[str] = None,
    log_levels: Optional[str] = None,
    http_methods: Optional[str] = None,
    http_status_codes: Optional[str] = None,
    endpoint_patterns: Optional[str] = None,
    extract_pattern: Optional[str] = None,
    extract_field_name: Optional[str] = None,
    limit: int = 100,
    output_format: str = "json"
) -> str:
    """Internal implementation of observe_query_logs for use by convenience functions"""
    # Parse comma-separated strings into lists
    def parse_csv_param(param: Optional[str]) -> Optional[List[str]]:
        if param:
            return [item.strip() for item in param.split(',') if item.strip()]
        return None
    
    container_list = parse_csv_param(container_names)
    cluster_list = parse_csv_param(clusters)
    search_list = parse_csv_param(search_terms)
    level_list = parse_csv_param(log_levels)
    method_list = parse_csv_param(http_methods)
    status_list = parse_csv_param(http_status_codes)
    endpoint_list = parse_csv_param(endpoint_patterns)
    
    # Validate extract parameters
    if extract_pattern and not extract_field_name:
        return json.dumps({
            "status": "error",
            "error": "extract_field_name is required when extract_pattern is provided"
        }, indent=2)
    
    try:
        # Build OPAL query with better error handling
        opal_query = client._build_opal_query(
            container_names=container_list,
            clusters=cluster_list,
            time_range=time_range,
            search_terms=search_list,
            log_levels=level_list,
            http_methods=method_list,
            http_status_codes=status_list,
            endpoint_patterns=endpoint_list,
            extract_pattern=extract_pattern,
            extract_field_name=extract_field_name,
            limit=limit
        )
        
        # Execute query  
        result = await client.execute_opal_query(opal_query, time_range, output_format)
        
        # Add query parameters to result for reference
        result["query_parameters"] = {
            "container_names": container_list,
            "clusters": cluster_list,
            "time_range": time_range,
            "search_terms": search_list,
            "log_levels": level_list,
            "http_methods": method_list,
            "http_status_codes": status_list,
            "endpoint_patterns": endpoint_list,
            "extract_pattern": extract_pattern,
            "extract_field_name": extract_field_name,
            "limit": limit,
            "output_format": output_format
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"Failed to build or execute query: {str(e)}",
            "query_parameters": {
                "container_names": container_list,
                "clusters": cluster_list,
                "time_range": time_range,
                "search_terms": search_list,
                "log_levels": level_list,
                "http_methods": method_list,
                "http_status_codes": status_list,
                "endpoint_patterns": endpoint_list,
                "extract_pattern": extract_pattern,
                "extract_field_name": extract_field_name,
                "limit": limit,
                "output_format": output_format
            }
        }, indent=2)

@mcp.tool()
async def observe_search_errors(
    container_names: Optional[str] = None,
    clusters: Optional[str] = None,
    time_range: str = "1h",
    additional_terms: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Convenience function to search for error-level logs
    
    Args:
        container_names: Comma-separated container names
        clusters: Comma-separated cluster names  
        time_range: Time range for search
        additional_terms: Additional search terms to include
        limit: Maximum results to return
    
    Returns:
        JSON string with error logs
    """
    
    # Build search terms for errors - simplified approach
    error_terms = ["error", "exception", "failed"]
    if additional_terms:
        error_terms.extend([term.strip() for term in additional_terms.split(',') if term.strip()])
    
    return await _observe_query_logs_impl(
        container_names=container_names,
        clusters=clusters,
        time_range=time_range,
        search_terms=','.join(error_terms),
        log_levels="error,warning",
        limit=limit
    )

@mcp.tool()
async def observe_search_http_errors(
    container_names: Optional[str] = None,
    clusters: Optional[str] = None,
    time_range: str = "1h",
    http_methods: Optional[str] = None,
    endpoint_patterns: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Convenience function to search for HTTP errors (non-200 status codes)
    
    Args:
        container_names: Comma-separated container names
        clusters: Comma-separated cluster names
        time_range: Time range for search
        http_methods: Comma-separated HTTP methods (e.g., "POST,GET")
        endpoint_patterns: Comma-separated endpoint patterns to search
        limit: Maximum results to return
    
    Returns:
        JSON string with HTTP error logs
    """
    
    # Search for common HTTP error status codes - simplified
    error_status_codes = "400,401,403,404,500,502,503,504"
    
    return await _observe_query_logs_impl(
        container_names=container_names,
        clusters=clusters,
        time_range=time_range,
        http_methods=http_methods,
        http_status_codes=error_status_codes,
        endpoint_patterns=endpoint_patterns,
        search_terms="error,failed,exception",
        limit=limit
    )

if __name__ == "__main__":
    mcp.run()
