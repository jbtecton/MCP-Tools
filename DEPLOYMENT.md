# Deployment Guide

## Quick Start for Coworkers

### 1. Clone and Setup
```bash
git clone <repository-url>
cd tecton-mcp-tools
python setup.py
```

### 2. Configure Credentials
Edit the `.env` file with your API credentials:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Generate Claude Configuration
```bash
python generate_config.py
```

### 4. Test Everything
```bash
python test.py
python cli_test.py all
```

### 5. Update Claude Desktop
Add the generated configuration to your Claude MCP config file and restart Claude Desktop.

---

## Detailed Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Access to Tecton's various services (Chronosphere, Linear, Jira, Slack)

### API Credentials Required

#### Chronosphere
- **Domain**: `tecton` (already configured)
- **API Token**: Get from Chronosphere Settings → API Tokens

#### Linear
- **API Key**: Get from Linear Settings → API → Personal API Key

#### Jira
- **URL**: `https://tecton.atlassian.net`
- **Email**: Your Atlassian account email
- **API Token**: Get from Atlassian Account Settings → Security → API tokens

#### Slack
- **Bot Token**: Get from your Slack app configuration (starts with `xoxb-`)
- **Required Scopes**: `channels:history`, `channels:read`, `groups:history`, `groups:read`, `im:history`, `im:read`, `mpim:history`, `mpim:read`, `search:read`

### Claude Desktop Configuration

Add the servers to `~/.config/claude-desktop/config.json`:

**Option 1: Direct environment variables**
```json
{
  "mcp": {
    "servers": {
      "tecton-chronosphere": {
        "command": "python",
        "args": ["/full/path/to/tecton-mcp-tools/servers/chronosphere_server.py"],
        "env": {
          "CHRONOSPHERE_DOMAIN": "tecton",
          "CHRONOSPHERE_API_TOKEN": "your-actual-token"
        }
      }
    }
  }
}
```

**Option 2: Using .env file (recommended)**
```json
{
  "mcp": {
    "servers": {
      "tecton-chronosphere": {
        "command": "python",
        "args": ["/full/path/to/tecton-mcp-tools/servers/chronosphere_server.py"]
      }
    }
  }
}
```

### Testing Individual Servers

Test each server works:
```bash
# Test all servers
python cli_test.py all

# Test individual servers
python cli_test.py chronosphere
python cli_test.py linear
python cli_test.py jira
python cli_test.py slack
```

### Troubleshooting

#### Common Issues

1. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version: `python --version` (needs 3.8+)

2. **Authentication failures**
   - Verify API credentials in `.env` file
   - Check that tokens haven't expired
   - Ensure proper permissions/scopes

3. **Connection timeouts**
   - Check network connectivity
   - Verify service URLs are correct

4. **Claude Desktop not recognizing servers**
   - Ensure full absolute paths in config
   - Restart Claude Desktop after configuration changes
   - Check Claude Desktop logs for error messages

#### Debug Mode

Run servers individually to see detailed error messages:
```bash
python servers/chronosphere_server.py
python servers/linear_server.py
python servers/jira_server.py
python servers/slack_server.py
```

### Security Best Practices

- Never commit `.env` file to git
- Use environment-specific tokens (dev vs prod)
- Regularly rotate API tokens
- Ensure minimum required permissions for each integration

### Production Considerations

- Consider using environment-specific configuration files
- Set up monitoring for API rate limits
- Implement proper error handling and retry logic
- Document any custom modifications for team knowledge

---

## Available Tools

### Chronosphere
- `list_clusters()` - List all Tecton clusters
- `query_metrics(query, time_range, cluster)` - Execute PromQL queries
- `instant_query_metrics(query, cluster)` - Get current metric values
- `discover_metrics(pattern, cluster)` - Find metrics by pattern
- `get_cluster_metrics_summary(cluster)` - Get cluster overview

### Linear
- `linear_health_check()` - Test connection
- `linear_search_issues(search_term, assignee_email, state, team_key, limit)` - Search issues
- `linear_get_issue_details(issue_id)` - Get detailed issue info
- `linear_get_issue_by_identifier(identifier)` - Get issue by ENG-123 format

### Jira
- `jira_health_check()` - Test connection
- `get_jira_ticket(ticket_key)` - Get ticket details
- `get_jira_ticket_comments(ticket_key, max_comments)` - Get ticket comments

### Slack
- `slack_health_check()` - Test connection
- `search_slack_messages(query, count, sort)` - Search messages
- `get_slack_thread(message_link)` - Get thread details
- `get_recent_channel_activity(channel_name, hours_back, limit)` - Monitor channels
- `list_slack_channels(types)` - List accessible channels
