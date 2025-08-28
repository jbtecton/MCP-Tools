#!/usr/bin/env python3
"""
FastMCP server for Chronosphere/PromQL integration
Allows natural language querying of Chronosphere metrics
"""

import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
CHRONOSPHERE_DOMAIN = os.getenv("CHRONOSPHERE_DOMAIN", "tecton")
CHRONOSPHERE_API_TOKEN = os.getenv("CHRONOSPHERE_API_TOKEN")

if not CHRONOSPHERE_API_TOKEN:
    raise ValueError("CHRONOSPHERE_API_TOKEN environment variable must be set")

BASE_URL = f"https://{CHRONOSPHERE_DOMAIN}.chronosphere.io"

# List of available clusters
CLUSTERS = [
    "demo-sa-gcp-serving", "gyg", "schibsted-dev", "tecton-dev-saasv3",
    "atlassian-satellite-staging", "depop-production", "hdp", "schibsted-prod", "tecton-dev-shared",
    "atlassian-staging", "depop-staging", "hdp-dev", "sf-efs-claims-test", "tecton-dev-trex",
    "atlassian2-production", "dev-cluster-creator", "hf-prod", "sf-efs-disc-prod", "tecton-dev-zeus",
    "atlassian2-sat-production", "dev-dbr-vpc", "hf-staging", "sf-efs-disc-test", "tecton-production",
    "attentive-prod", "dev-dbr-vpc-admin", "htg-rift", "sf-efs-prod", "tecton-spark",
    "baton-corp-prod", "dev-drift-dataplane", "interac-dev", "sf-efs-test", "tecton-spark-edge",
    "betterhelp-prod", "dev-emr-compute", "interac-staging-cac1", "sf-sat-efs-disc-prod", "tecton-staging",
    "betterhelp-staging", "dev-emr-vpc", "internal-developer-platform", "sf-sat-efs-prod", "tecton-tests",
    "block-production", "dev-explore", "lab", "sf-sat-efs-test", "tecton-tests-dataplane",
    "block-sat-production", "dev-gen-ai", "marshmallow-prod", "sie-ml-prod", "tempo-prod-na",
    "block-staging", "dev-rift", "movjd-cashapp", "sie-ml-prodlab", "testing",
    "cluster-creation1", "dev-rift-dataplane", "nab-prod", "signifyd", "tide-prod-in",
    "coinbase-development", "dev-sat-emr-vpc", "nab-staging", "signifyd-prod", "tide-prod-uk",
    "coinbase-production", "dev-saturn-poc-serving", "neon-hml", "signifyd-staging", "tide-stg-in",
    "community", "dev-serving", "neon-prod", "snowflakepartner", "tide-stg-uk",
    "community-dev", "dev-serving-dataplane", "oscilar-prod", "solutions-sandbox", "usaa-dev",
    "creditgenie-prod", "dev-short", "parafin-prod", "stage1-cashapp", "usaa-prod",
    "daryl-prod", "dev-terra", "plaid", "tecton-analytics", "varo-production",
    "daryl-prod-dataplane", "dev-trex-dataplane", "preply-prod", "tecton-aux", "varo-uat",
    "daryl-prod-emr", "explore", "prima-production", "tecton-central-1", "workday-dsml-dev1",
    "daryl-prod-emr-dataplane", "flohealth-staging", "prima-staging", "tecton-demo-calla", "workday-dsml-prod1",
    "demo-data", "flohealth2-production", "progressive", "tecton-dev-acl", "wry-cashapp",
    "demo-elevate", "fs-poc-tecton", "progressive-dev", "tecton-dev-emr-vpc-admin", "zhou-mfttest",
    "demo-fiber", "gd-gdml-stage", "remitly-preprod", "tecton-dev-ops-dataplane",
    "demo-flex", "grammarly-prod", "remitly-prod", "tecton-dev-ops2",
    "demo-horizon", "scalapay-tecton-prd", "tecton-dev-ops3"
]

# Initialize FastMCP
mcp = FastMCP("Chronosphere PromQL Integration")

class ChronosphereClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = {
            "Authorization": f"Bearer {CHRONOSPHERE_API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def query_prometheus(self, query: str, time_range: str = "1h") -> Dict[str, Any]:
        """Execute a PromQL query against Chronosphere"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # For range queries
            end_time = datetime.utcnow()
            
            # Parse time range
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
                start_time = end_time - timedelta(hours=1)  # default 1 hour
            
            params = {
                "query": query,
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z",
                "step": "60s"  # 1 minute resolution
            }
            
            response = await client.get(
                f"{self.base_url}/data/metrics/api/v1/query_range",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                return {"error": f"API request failed: {response.status_code} - {response.text}"}
            
            return response.json()
    
    async def instant_query(self, query: str) -> Dict[str, Any]:
        """Execute an instant PromQL query"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"query": query}
            
            response = await client.get(
                f"{self.base_url}/data/metrics/api/v1/query",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                return {"error": f"API request failed: {response.status_code} - {response.text}"}
            
            return response.json()
    
    async def get_label_values(self, label: str) -> Dict[str, Any]:
        """Get all values for a specific label"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/data/metrics/api/v1/label/{label}/values",
                headers=self.headers
            )
            
            if response.status_code != 200:
                return {"error": f"API request failed: {response.status_code} - {response.text}"}
            
            return response.json()
    
    async def get_series_metadata(self, match: str = None) -> Dict[str, Any]:
        """Get series metadata/metric names"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {}
            if match:
                params["match[]"] = match
            
            response = await client.get(
                f"{self.base_url}/data/metrics/api/v1/series",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                return {"error": f"API request failed: {response.status_code} - {response.text}"}
            
            return response.json()

# Initialize client
client = ChronosphereClient()

@mcp.tool()
async def list_clusters() -> str:
    """List all available Tecton clusters"""
    return json.dumps({
        "clusters": CLUSTERS,
        "count": len(CLUSTERS)
    }, indent=2)

@mcp.tool()
async def query_metrics(query: str, time_range: str = "1h", cluster: str = None) -> str:
    """
    Execute a PromQL query against Chronosphere
    
    Args:
        query: PromQL query string
        time_range: Time range (e.g., '1h', '1d', '1w')  
        cluster: Optional cluster name to filter by
    """
    # Add cluster filter if specified
    if cluster and cluster in CLUSTERS:
        # Check if query already has braces for labels
        if '{' in query:
            # Insert cluster filter into existing label set
            query = query.replace('{', f'{{cluster="{cluster}",', 1)
        else:
            # Add cluster filter to metric name
            metric_name = query.split('(')[0].split()[0]
            query = query.replace(metric_name, f'{metric_name}{{cluster="{cluster}"}}', 1)
    
    result = await client.query_prometheus(query, time_range)
    return json.dumps(result, indent=2)

@mcp.tool()
async def instant_query_metrics(query: str, cluster: str = None) -> str:
    """
    Execute an instant PromQL query (current values only)
    
    Args:
        query: PromQL query string
        cluster: Optional cluster name to filter by
    """
    # Add cluster filter if specified
    if cluster and cluster in CLUSTERS:
        if '{' in query:
            query = query.replace('{', f'{{cluster="{cluster}",', 1)
        else:
            metric_name = query.split('(')[0].split()[0]
            query = query.replace(metric_name, f'{metric_name}{{cluster="{cluster}"}}', 1)
    
    result = await client.instant_query(query)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_dynamodb_latency(cluster: str, time_range: str = "1w") -> str:
    """
    Get DynamoDB latency metrics for a specific cluster
    
    Args:
        cluster: Cluster name (e.g., 'block-production')
        time_range: Time range to query (e.g., '1h', '1d', '1w')
    """
    if cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {cluster}. Use list_clusters() to see available clusters."})
    
    # Common DynamoDB latency metric patterns
    queries = [
        f'aws_dynamodb_successful_request_latency{{cluster="{cluster}"}}',
        f'aws_dynamodb_request_latency{{cluster="{cluster}"}}',
        f'dynamodb_request_latency_seconds{{cluster="{cluster}"}}',
        f'dynamodb_latency{{cluster="{cluster}"}}',
    ]
    
    results = {}
    for query in queries:
        result = await client.query_prometheus(query, time_range)
        if result.get('data', {}).get('result'):
            results[query] = result
    
    if not results:
        return json.dumps({
            "message": f"No DynamoDB latency metrics found for cluster '{cluster}' in the last {time_range}",
            "suggestion": "Try using discover_metrics() to see available metrics for this cluster"
        }, indent=2)
    
    return json.dumps(results, indent=2)

@mcp.tool()
async def discover_metrics(pattern: str = "", cluster: str = None) -> str:
    """
    Discover available metrics, optionally filtered by pattern and cluster
    
    Args:
        pattern: Metric name pattern to search for (e.g., 'dynamodb', 'latency')
        cluster: Optional cluster to filter by
    """
    match_query = f'{{__name__=~".*{pattern}.*"}}'
    if cluster:
        match_query = f'{{__name__=~".*{pattern}.*",cluster="{cluster}"}}'
    
    result = await client.get_series_metadata(match_query)
    
    if "error" in result:
        return json.dumps(result, indent=2)
    
    # Extract unique metric names
    metric_names = set()
    for series in result.get('data', []):
        metric_names.add(series.get('__name__'))
    
    return json.dumps({
        "pattern": pattern,
        "cluster": cluster,
        "metric_count": len(metric_names),
        "metrics": sorted(list(metric_names))
    }, indent=2)

@mcp.tool()
async def get_cluster_metrics_summary(cluster: str) -> str:
    """
    Get a summary of key metrics for a specific cluster
    
    Args:
        cluster: Cluster name
    """
    if cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {cluster}"})
    
    # Common infrastructure metrics to check
    summary_queries = {
        "cpu_usage": f'avg(rate(cpu_usage_seconds_total{{cluster="{cluster}"}}[5m]))',
        "memory_usage": f'avg(memory_usage_bytes{{cluster="{cluster}"}}) / 1024 / 1024 / 1024',
        "disk_usage": f'avg(disk_usage_percent{{cluster="{cluster}"}})',
        "network_io": f'rate(network_io_bytes_total{{cluster="{cluster}"}}[5m])',
        "pod_count": f'count(kube_pod_info{{cluster="{cluster}"}})',
        "node_count": f'count(kube_node_info{{cluster="{cluster}"}})'
    }
    
    results = {}
    for metric_name, query in summary_queries.items():
        result = await client.instant_query(query)
        if result.get('data', {}).get('result'):
            results[metric_name] = result
    
    return json.dumps({
        "cluster": cluster,
        "summary": results
    }, indent=2)

if __name__ == "__main__":
    mcp.run()
