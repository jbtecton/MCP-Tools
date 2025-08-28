#!/usr/bin/env python3
"""
FastMCP server for Chronosphere/PromQL and Graphite integration
Supports both Online Store Writer (Graphite) and Feature Server (Prometheus) dashboards
"""

import asyncio
import httpx
import json
import os
import urllib.parse
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
mcp = FastMCP("Chronosphere PromQL and Graphite Integration")

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
    
    async def query_graphite(self, target: str, time_range: str = "2d", format: str = "json") -> Dict[str, Any]:
        """Execute a Graphite query against Chronosphere"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Parse time range to 'from' parameter
            end_time = datetime.utcnow()
            
            if time_range.endswith('m'):
                minutes = int(time_range[:-1])
                from_time = f"-{minutes}minutes"
            elif time_range.endswith('h'):
                hours = int(time_range[:-1])
                from_time = f"-{hours}hours"
            elif time_range.endswith('d'):
                days = int(time_range[:-1])
                from_time = f"-{days}days"
            elif time_range.endswith('w'):
                weeks = int(time_range[:-1])
                from_time = f"-{weeks}weeks"
            else:
                from_time = "-2days"  # default
            
            params = {
                "target": target,
                "format": format,
                "from": from_time
            }
            
            response = await client.get(
                f"{self.base_url}/data/graphite/render",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                return {"error": f"Graphite API request failed: {response.status_code} - {response.text}"}
            
            return response.json()
    
    async def find_graphite_metrics(self, query: str) -> Dict[str, Any]:
        """Find Graphite metrics matching a pattern"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "query": query,
                "format": "json"
            }
            
            response = await client.get(
                f"{self.base_url}/data/graphite/metrics/find",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                return {"error": f"Graphite find API request failed: {response.status_code} - {response.text}"}
            
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

# =============================================================================
# CORE UTILITY TOOLS
# =============================================================================

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
async def query_graphite_metrics(target: str, time_range: str = "2d") -> str:
    """
    Execute a Graphite query against Chronosphere
    
    Args:
        target: Graphite target/query string (e.g., "databricks.block-production.spark.*.*.tecton-online-store-writer.*")
        time_range: Time range (e.g., '2d', '1w', '1h')
    """
    result = await client.query_graphite(target, time_range)
    return json.dumps(result, indent=2)

@mcp.tool()
async def find_graphite_metrics(query: str) -> str:
    """
    Find Graphite metrics matching a pattern
    
    Args:
        query: Graphite query pattern (e.g., "databricks.block-production.spark.*")
    """
    result = await client.find_graphite_metrics(query)
    return json.dumps(result, indent=2)

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

# =============================================================================
# ONLINE STORE WRITER TOOLS (GRAPHITE API)
# =============================================================================

@mcp.tool()
async def get_online_store_writer_metrics(
    spark_env: str = "databricks", 
    tecton_cluster: str = "block-production", 
    app_name: str = "*", 
    interval: str = "15min",
    time_range: str = "2d",
    table_type: str = "data",
    processing_mode: str = "batch"
) -> str:
    """
    Get Online Store Writer metrics using the exact dashboard queries
    
    Args:
        spark_env: Spark environment ('databricks' or 'emr')
        tecton_cluster: Tecton cluster name (e.g., 'block-production')
        app_name: Application name pattern (use '*' for all)
        interval: Time interval for aggregation (e.g., '15min', '1h')
        time_range: Time range for data (e.g., '2d', '1w')
        table_type: Table type ('data', 'status', 'canary')
        processing_mode: Processing mode ('batch' or 'stream')
    """
    
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    # Build the Graphite query from the dashboard definition
    base_pattern = f"{spark_env}.{tecton_cluster}.spark.{app_name}.*.tecton-online-store-writer.cm_feature_write_row_count.*.*.*.{processing_mode}.{table_type}.*"
    
    # Apply the same transformations as the dashboard
    target = f'groupByNodes(summarize(transformNull({base_pattern}), "{interval}", "sum", true), "sum", 1, 7, 8, 9, 10, 12)'
    
    result = await client.query_graphite(target, time_range)
    
    return json.dumps({
        "query_info": {
            "spark_env": spark_env,
            "tecton_cluster": tecton_cluster,
            "app_name": app_name,
            "table_type": table_type,
            "processing_mode": processing_mode,
            "interval": interval,
            "time_range": time_range,
            "graphite_target": target
        },
        "data": result
    }, indent=2)

@mcp.tool()
async def get_all_online_store_writer_data(
    spark_env: str = "databricks",
    tecton_cluster: str = "block-production", 
    app_name: str = "*",
    interval: str = "15min",
    time_range: str = "2d"
) -> str:
    """
    Get all Online Store Writer dashboard data (all combinations of batch/stream and data/status/canary)
    
    Args:
        spark_env: Spark environment ('databricks' or 'emr')
        tecton_cluster: Tecton cluster name (e.g., 'block-production')
        app_name: Application name pattern (use '*' for all)
        interval: Time interval for aggregation (e.g., '15min', '1h')
        time_range: Time range for data (e.g., '2d', '1w')
    """
    
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    results = {}
    
    # Query all combinations as shown in the dashboard
    combinations = [
        ("batch", "data"),
        ("stream", "data"),
        ("batch", "status"),
        ("stream", "status"),
        ("batch", "canary"),
        ("stream", "canary")
    ]
    
    for processing_mode, table_type in combinations:
        base_pattern = f"{spark_env}.{tecton_cluster}.spark.{app_name}.*.tecton-online-store-writer.cm_feature_write_row_count.*.*.*.{processing_mode}.{table_type}.*"
        target = f'groupByNodes(summarize(transformNull({base_pattern}), "{interval}", "sum", true), "sum", 1, 7, 8, 9, 10, 12)'
        
        try:
            result = await client.query_graphite(target, time_range)
            results[f"{processing_mode}_{table_type}"] = {
                "title": f"[{processing_mode.title()}] {table_type.title()} table write count",
                "graphite_target": target,
                "data": result
            }
        except Exception as e:
            results[f"{processing_mode}_{table_type}"] = {
                "title": f"[{processing_mode.title()}] {table_type.title()} table write count",
                "error": str(e)
            }
    
    return json.dumps({
        "query_info": {
            "spark_env": spark_env,
            "tecton_cluster": tecton_cluster,
            "app_name": app_name,
            "interval": interval,
            "time_range": time_range
        },
        "results": results
    }, indent=2)

@mcp.tool()
async def discover_online_store_writer_apps(
    spark_env: str = "databricks",
    tecton_cluster: str = "block-production"
) -> str:
    """
    Discover available Online Store Writer applications for a cluster
    
    Args:
        spark_env: Spark environment ('databricks' or 'emr')
        tecton_cluster: Tecton cluster name (e.g., 'block-production')
    """
    
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    # Query for available apps
    query = f"{spark_env}.{tecton_cluster}.spark.*"
    result = await client.find_graphite_metrics(query)
    
    return json.dumps({
        "spark_env": spark_env,
        "tecton_cluster": tecton_cluster,
        "query": query,
        "available_apps": result
    }, indent=2)

# =============================================================================
# FEATURE SERVER TOOLS (PROMETHEUS API)
# =============================================================================

@mcp.tool()
async def get_feature_server_latency(
    tecton_cluster: str = "block-production",
    aws_region: str = "*", 
    interval: str = "15m",
    percentiles: str = "0.5,0.9,0.95,0.99"
) -> str:
    """
    Get Feature Server latency metrics (GetFeatures|QueryFeatures methods)
    
    Args:
        tecton_cluster: Tecton cluster name (e.g., 'block-production')
        aws_region: AWS region pattern (use '*' for all)
        interval: Time interval for rate calculation (e.g., '15m')
        percentiles: Comma-separated percentiles to query (e.g., '0.5,0.9,0.95,0.99')
    """
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    region_filter = f'aws_region=~"{aws_region}"' if aws_region != "*" else 'aws_region=~".*"'
    
    results = {}
    
    for percentile in percentiles.split(','):
        p = percentile.strip()
        query = f'histogram_quantile({p}, sum by (aws_region, grpc_service, grpc_method, grpc_type, tecton_cluster, lens_service, le) (rate(grpc_server_handling_seconds_bucket_feature_server_rollup_no_job_instance{{grpc_method=~\'(GetFeatures|QueryFeatures)\', tecton_cluster=~"{tecton_cluster}", {region_filter}}}[{interval}])))'
        
        result = await client.query_prometheus(query, "1h")
        results[f"p{int(float(p)*100)}"] = result
    
    return json.dumps({
        "query_info": {
            "tecton_cluster": tecton_cluster,
            "aws_region": aws_region,
            "interval": interval,
            "percentiles": percentiles
        },
        "latency_data": results
    }, indent=2)

@mcp.tool()
async def get_feature_server_requests_by_method(
    tecton_cluster: str = "block-production",
    aws_region: str = "*",
    interval: str = "15m"
) -> str:
    """
    Get Feature Server requests by gRPC method
    
    Args:
        tecton_cluster: Tecton cluster name
        aws_region: AWS region pattern (use '*' for all)
        interval: Time interval for rate calculation
    """
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    region_filter = f'aws_region=~"{aws_region}"' if aws_region != "*" else 'aws_region=~".*"'
    
    query = f'sum by (grpc_method) (rate(grpc_server_handled_total_feature_server_rollup_no_job_instance{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}[{interval}]))'
    
    result = await client.query_prometheus(query, "1h")
    
    return json.dumps({
        "query_info": {
            "tecton_cluster": tecton_cluster,
            "aws_region": aws_region,
            "interval": interval
        },
        "requests_by_method": result
    }, indent=2)

@mcp.tool()
async def get_feature_server_error_rates(
    tecton_cluster: str = "block-production",
    aws_region: str = "*",
    interval: str = "15m"
) -> str:
    """
    Get Feature Server error rates by status and method
    
    Args:
        tecton_cluster: Tecton cluster name
        aws_region: AWS region pattern (use '*' for all)
        interval: Time interval for rate calculation
    """
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    region_filter = f'aws_region=~"{aws_region}"' if aws_region != "*" else 'aws_region=~".*"'
    
    # Error percentage by status
    error_by_status_query = f'sum(rate(grpc_server_handled_total_feature_server_rollup_no_job_instance{{grpc_code!="OK", {region_filter}, tecton_cluster=~"{tecton_cluster}"}}[{interval}])) by (tecton_cluster, grpc_code) / ignoring(grpc_code) group_left sum(rate(grpc_server_handled_total_feature_server_rollup_no_job_instance{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}[{interval}])) by (tecton_cluster)'
    
    # Error percentage by method  
    error_by_method_query = f'sum(rate(grpc_server_handled_total_feature_server_rollup_no_job_instance{{grpc_code!="OK", {region_filter}, tecton_cluster=~"{tecton_cluster}"}}[{interval}])) by (tecton_cluster, grpc_method) / ignoring(grpc_method) group_left sum(rate(grpc_server_handled_total_feature_server_rollup_no_job_instance{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}[{interval}])) by (tecton_cluster)'
    
    results = {
        "error_by_status": await client.query_prometheus(error_by_status_query, "1h"),
        "error_by_method": await client.query_prometheus(error_by_method_query, "1h")
    }
    
    return json.dumps({
        "query_info": {
            "tecton_cluster": tecton_cluster,
            "aws_region": aws_region,
            "interval": interval
        },
        "error_rates": results
    }, indent=2)

@mcp.tool()
async def get_dynamodb_metrics(
    tecton_cluster: str = "block-production",
    aws_region: str = "*",
    feature_view_id: str = "*",
    interval: str = "15m"
) -> str:
    """
    Get DynamoDB metrics (QPS, latency, response size) for Feature Server
    
    Args:
        tecton_cluster: Tecton cluster name
        aws_region: AWS region pattern (use '*' for all)
        feature_view_id: Feature view ID pattern (use '*' for all)
        interval: Time interval for rate calculation
    """
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    region_filter = f'aws_region=~"{aws_region}"' if aws_region != "*" else 'aws_region=~".*"'
    fv_filter = f'feature_view_id=~"{feature_view_id}"' if feature_view_id != "*" else 'feature_view_id=~".*"'
    
    queries = {
        "dynamodb_qps": f'sum(rate(cm_fv_read_count{{type=~"dynamo", {region_filter}, tecton_cluster=~"{tecton_cluster}", {fv_filter}}}[{interval}])) by (tecton_cluster, feature_view_id)',
        "dynamodb_p99_latency": f'histogram_quantile(0.99, sum(rate(dynamodb_query_latency_seconds_bucket_rollup_no_pod{{tecton_cluster=~"{tecton_cluster}", {region_filter}, table=~".*{feature_view_id if feature_view_id != "*" else ""}.*"}}[{interval}])) by (tecton_cluster, table, le))',
        "dynamodb_p99_response_size": f'histogram_quantile(0.99, sum(rate(dynamodb_response_size_per_query_by_table_bucket_rollup_no_pod{{{region_filter}, tecton_cluster=~"{tecton_cluster}", table=~".*{feature_view_id if feature_view_id != "*" else ""}.*"}}[{interval}])) by(le, tecton_cluster, table))',
        "dynamodb_p99_row_count": f'histogram_quantile(0.99, sum(rate(dynamodb_rows_per_query_bucket_rollup_no_pod{{{region_filter}, tecton_cluster=~"{tecton_cluster}", table=~".*{feature_view_id if feature_view_id != "*" else ""}.*"}}[{interval}])) by(le, tecton_cluster, table))'
    }
    
    results = {}
    for metric_name, query in queries.items():
        results[metric_name] = await client.query_prometheus(query, "1h")
    
    return json.dumps({
        "query_info": {
            "tecton_cluster": tecton_cluster,
            "aws_region": aws_region,
            "feature_view_id": feature_view_id,
            "interval": interval
        },
        "dynamodb_metrics": results
    }, indent=2)

@mcp.tool()
async def get_feature_server_scaling_metrics(
    tecton_cluster: str = "block-production",
    aws_region: str = "*"
) -> str:
    """
    Get Feature Server autoscaling and resource metrics
    
    Args:
        tecton_cluster: Tecton cluster name
        aws_region: AWS region pattern (use '*' for all)
    """
    if tecton_cluster not in CLUSTERS:
        return json.dumps({"error": f"Unknown cluster: {tecton_cluster}. Use list_clusters() to see available clusters."})
    
    region_filter = f'aws_region=~"{aws_region}"' if aws_region != "*" else 'aws_region=~".*"'
    
    queries = {
        "current_replicas": f'sum(kube_horizontalpodautoscaler_status_current_replicas{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}) by (tecton_cluster)',
        "desired_replicas": f'sum(kube_horizontalpodautoscaler_status_desired_replicas{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}) by (tecton_cluster)',
        "max_replicas": f'sum(kube_horizontalpodautoscaler_spec_max_replicas{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}) by (tecton_cluster)',
        "min_replicas": f'sum(kube_horizontalpodautoscaler_spec_min_replicas{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}) by (tecton_cluster)',
        "concurrent_requests_utilization": f'max(concurrent_requests_max_percentage{{{region_filter}, tecton_cluster=~"{tecton_cluster}", instance=~"tecton/feature-server-[a-z0-9A-Z]*-[a-z0-9A-Z]*"}}) by (tecton_cluster)',
        "target_utilization": f'max(kube_horizontalpodautoscaler_spec_target_metric{{{region_filter}, tecton_cluster=~"{tecton_cluster}"}}) by (tecton_cluster)'
    }
    
    results = {}
    for metric_name, query in queries.items():
        results[metric_name] = await client.instant_query(query)
    
    return json.dumps({
        "query_info": {
            "tecton_cluster": tecton_cluster,
            "aws_region": aws_region
        },
        "scaling_metrics": results
    }, indent=2)

# =============================================================================
# LEGACY TOOLS (KEPT FOR BACKWARDS COMPATIBILITY)
# =============================================================================

@mcp.tool()
async def get_dynamodb_latency(cluster: str, time_range: str = "1w") -> str:
    """
    Get DynamoDB latency metrics for a specific cluster (Legacy tool)
    
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
            "suggestion": "Try using get_dynamodb_metrics() for Feature Server DynamoDB metrics"
        }, indent=2)
    
    return json.dumps(results, indent=2)

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
