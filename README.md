# Tecton MCP Tools

A collection of FastMCP servers providing integrations with various tools used at Tecton.

## 🛠️ Available Integrations

- **Chronosphere** - Query Prometheus/PromQL metrics from Chronosphere
- **Linear** - Search issues, get issue details, and track project status
- **Jira** - Retrieve tickets, comments, and project information
- **Slack** - Search messages, get threads, and monitor channel activity
- **Observe** - Query and analyze log data using OPAL (Observe Processing and Analysis Language)

## 🚀 Quick Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd tecton-mcp-tools
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env` with your actual API keys and credentials (see [Configuration](#configuration) below).

### 4. Update MCP Configuration
Add the servers to your Claude MCP configuration file (typically `~/.config/claude-desktop/config.json`):

```json
{
  "mcp": {
    "servers": {
      "chronosphere": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/chronosphere_server.py"],
        "env": {
          "CHRONOSPHERE_DOMAIN": "tecton",
          "CHRONOSPHERE_API_TOKEN": "your-token-here"
        }
      },
      "linear": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/linear_server.py"],
        "env": {
          "LINEAR_API_KEY": "your-key-here"
        }
      },
      "jira": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/jira_server.py"],
        "env": {
          "JIRA_URL": "https://your-domain.atlassian.net",
          "JIRA_EMAIL": "your-email@example.com",
          "JIRA_API_TOKEN": "your-api-token"
        }
      },
      "slack": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/slack_server.py"],
        "env": {
          "SLACK_BOT_TOKEN": "xoxb-your-bot-token-here"
        }
      },
      "observe": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/observe_server.py"],
        "env": {
          "OBSERVE_TENANT_URL": "https://your-tenant-id.observeinc.com",
          "OBSERVE_USER_EMAIL": "your-email@example.com",
          "OBSERVE_API_TOKEN": "your-observe-bearer-token"
        }
      }
    }
  }
}
```

Alternatively, you can use the shared environment file approach by sourcing the `.env` file:

```json
{
  "mcp": {
    "servers": {
      "chronosphere": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/chronosphere_server.py"]
      },
      "linear": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/linear_server.py"]
      },
      "jira": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/jira_server.py"]
      },
      "slack": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/slack_server.py"]
      },
      "observe": {
        "command": "python",
        "args": ["/path/to/tecton-mcp-tools/servers/observe_server.py"]
      }
    }
  }
}
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Chronosphere Configuration
CHRONOSPHERE_DOMAIN=tecton
CHRONOSPHERE_API_TOKEN=your-chronosphere-token

# Linear Configuration
LINEAR_API_KEY=your-linear-api-key

# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Observe Configuration
OBSERVE_TENANT_URL=https://your-tenant-id.observeinc.com
OBSERVE_USER_EMAIL=your-email@example.com
OBSERVE_API_TOKEN=your-observe-bearer-token
```

### Getting API Credentials

#### Chronosphere
1. Log in to your Chronosphere instance
2. Navigate to Settings → API Tokens
3. Create a new API token with appropriate permissions

#### Linear
1. Go to Linear Settings → API
2. Create a new Personal API Key
3. Copy the key (starts with `lin_api_`)

#### Jira
1. Go to Atlassian Account Settings → Security → API tokens
2. Create a new API token
3. Use your Atlassian email and the generated token

#### Slack
1. Go to api.slack.com → Your Apps
2. Create a new app or use existing
3. Navigate to OAuth & Permissions
4. Add the following Bot Token Scopes:
   - `channels:history`
   - `channels:read` 
   - `groups:history`
   - `groups:read`
   - `im:history`
   - `im:read`
   - `mpim:history`
   - `mpim:read`
   - `search:read`
5. Install the app to your workspace
6. Copy the Bot User OAuth Token (starts with `xoxb-`)

#### Observe
1. Contact your IT/DevOps team or check with your Observe administrator
2. Use the delegated login API to get a bearer token:
   ```bash
   curl -d '{"userEmail":"your-email@company.com", "integration":"observe-tool-mcp","clientToken":"MCP setup"}' https://your-tenant-id.observeinc.com/v1/login/delegated
   ```
3. Copy the `serverToken` from the response and use it as `OBSERVE_API_TOKEN`
4. Set `OBSERVE_TENANT_URL` to your Observe tenant URL (e.g., `https://168585119059.observeinc.com`)
5. Set `OBSERVE_USER_EMAIL` to your email address

## 🔧 Individual Server Details

### Chronosphere Server
- **File**: `servers/chronosphere_server.py`
- **Purpose**: Query Prometheus/PromQL metrics from Chronosphere
- **Key Tools**:
  - `list_clusters()` - List all available Tecton clusters
  - `query_metrics()` - Execute PromQL queries with time ranges
  - `instant_query_metrics()` - Get current metric values
  - `get_dynamodb_latency()` - Specific DynamoDB latency metrics
  - `discover_metrics()` - Find available metrics by pattern

### Linear Server
- **File**: `servers/linear_server.py`
- **Purpose**: Interact with Linear for issue tracking and project management
- **Key Tools**:
  - `linear_health_check()` - Test connection and get user info
  - `linear_search_issues()` - Search issues by various criteria
  - `linear_get_issue_details()` - Get detailed issue information
  - `linear_get_issue_by_identifier()` - Get issue by ID (e.g., ENG-123)

### Jira Server
- **File**: `servers/jira_server.py`
- **Purpose**: Retrieve Jira tickets and related information
- **Key Tools**:
  - `jira_health_check()` - Test Jira connection
  - `get_jira_ticket()` - Get ticket details by key
  - `get_jira_ticket_comments()` - Get ticket comments

### Slack Server
- **File**: `servers/slack_server.py`
- **Purpose**: Search and monitor Slack activity
- **Key Tools**:
  - `slack_health_check()` - Test Slack connection
  - `search_slack_messages()` - Search messages across channels
  - `get_slack_thread()` - Get thread details by permalink
  - `get_recent_channel_activity()` - Monitor channel activity
  - `list_slack_channels()` - List accessible channels

### Observe Server
- **File**: `servers/observe_server.py`
- **Purpose**: Query and analyze log data using OPAL (Observe Processing and Analysis Language)
- **Key Tools**:
  - `observe_health_check()` - Test Observe API connection
  - `observe_query_logs()` - Flexible log querying with filtering and extraction
  - `observe_raw_query()` - Execute raw OPAL queries for advanced users
  - `observe_search_errors()` - Convenience function to search for error logs
  - `observe_search_http_errors()` - Search for HTTP errors (non-200 status codes)

## 🧪 Testing

Each server can be tested individually:

```bash
# Test Chronosphere
python servers/chronosphere_server.py

# Test Linear  
python servers/linear_server.py

# Test Jira
python servers/jira_server.py

# Test Slack
python servers/slack_server.py

# Test Observe
python servers/observe_server.py
```

## 📁 Project Structure

```
tecton-mcp-tools/
├── README.md
├── requirements.txt
├── .env.example
├── .env (create from .env.example)
├── .gitignore
└── servers/
    ├── chronosphere_server.py
    ├── linear_server.py
    ├── jira_server.py
    ├── slack_server.py
    └── observe_server.py
```

## 🔒 Security Notes

- Never commit your `.env` file to version control
- Use environment-specific API tokens (dev vs prod)
- Regularly rotate API tokens
- Ensure proper scopes/permissions for each integration

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test the affected servers
4. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Troubleshooting

### Common Issues

1. **"Environment variable not set" errors**
   - Ensure your `.env` file is properly configured
   - Check that the server can access environment variables

2. **Authentication failures**
   - Verify API tokens are correct and not expired
   - Check that tokens have necessary permissions

3. **Connection timeouts**
   - Check network connectivity
   - Verify service URLs are correct

### Getting Help

- Check the individual server files for specific error handling
- Review API documentation for each service
- Test servers individually before using with Claude

---

Built with ❤️ for the Tecton team using [FastMCP](https://github.com/jlowin/fastmcp)
