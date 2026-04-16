# Agent Authentication with Microsoft Entra ID

## A2A and MCP Authentication Flows for AI Agents

This document explains how AI agents authenticate using Microsoft Entra ID, covering the differences between user authentication and agent (workload) authentication, and specific flows for A2A (Agent-to-Agent) and MCP (Model Context Protocol) communications.

---

## Table of Contents

1. [Overview: Human vs Agent Identity](#1-overview-human-vs-agent-identity)
2. [Registering an Agent Identity in Entra ID](#2-registering-an-agent-identity-in-entra-id)
3. [Authentication Methods for Agents](#3-authentication-methods-for-agents)
4. [A2A Protocol Authentication Flow](#4-a2a-protocol-authentication-flow)
5. [MCP Server Authentication Flow](#5-mcp-server-authentication-flow)
6. [Managed Identity for Agents (Recommended)](#6-managed-identity-for-agents-recommended)
7. [Key Differences: User vs Agent Authentication](#7-key-differences-user-vs-agent-authentication)
8. [Implementation Examples](#8-implementation-examples)
9. [Security Best Practices](#9-security-best-practices)
10. [References](#10-references)

---

## 1. Overview: Human vs Agent Identity

Microsoft Entra ID supports two fundamental types of identities:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        IDENTITY TYPES IN ENTRA ID                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────────┐          ┌──────────────────────────────┐   │
│   │    HUMAN IDENTITIES  │          │    MACHINE/WORKLOAD          │   │
│   │                      │          │    IDENTITIES                │   │
│   │  • Employees         │          │                              │   │
│   │  • External Users    │          │  ┌────────────────────────┐  │   │
│   │  • Customers         │          │  │  WORKLOAD IDENTITIES   │  │   │
│   │  • Partners          │          │  │                        │  │   │
│   │                      │          │  │  • Applications        │  │   │
│   │  Authentication:     │          │  │  • Service Principals  │  │   │
│   │  - Interactive login │          │  │  • Managed Identities  │  │   │
│   │  - MFA               │          │  │  • AI Agents ← NEW     │  │   │
│   │  - OAuth Auth Code   │          │  │                        │  │   │
│   │                      │          │  │  Authentication:       │  │   │
│   │                      │          │  │  - Client Credentials  │  │   │
│   │                      │          │  │  - Certificates        │  │   │
│   │                      │          │  │  - Managed Identity    │  │   │
│   └──────────────────────┘          │  │  - Federated Creds     │  │   │
│                                     │  └────────────────────────┘  │   │
│                                     │                              │   │
│                                     │  ┌────────────────────────┐  │   │
│                                     │  │  DEVICE IDENTITIES     │  │   │
│                                     │  │  • Computers           │  │   │
│                                     │  │  • IoT Devices         │  │   │
│                                     │  └────────────────────────┘  │   │
│                                     └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why Agents Need Workload Identities

AI Agents are **software workloads** that:
- Operate autonomously without user interaction
- Make API calls to other services (LLMs, databases, other agents)
- Need to authenticate as themselves, not on behalf of users
- Require secure credential management

---

## 2. Registering an Agent Identity in Entra ID

### Step-by-Step: Create an App Registration for Your Agent

#### Option A: Via Azure Portal

1. **Navigate to Microsoft Entra ID**
   ```
   Azure Portal → Microsoft Entra ID → App registrations → New registration
   ```

2. **Configure the Registration**
   | Setting | Value | Notes |
   |---------|-------|-------|
   | Name | `MAF-Agent-<AgentName>` | e.g., `MAF-Agent-ProductsFinder` |
   | Supported account types | Single tenant (recommended) | Or multi-tenant for cross-org agents |
   | Redirect URI | Leave blank for agents | Agents don't use interactive login |

3. **Record the IDs**
   - **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **Directory (tenant) ID**: `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy`

4. **Create a Client Secret or Certificate**
   ```
   App registration → Certificates & secrets → New client secret
   ```
   - Description: `MAF Agent Secret`
   - Expiry: 24 months (max) or use certificates for longer

#### Option B: Via Azure CLI

```bash
# Create the app registration
az ad app create \
  --display-name "MAF-Agent-ProductsFinder" \
  --sign-in-audience "AzureADMyOrg"

# Get the app ID
APP_ID=$(az ad app list --display-name "MAF-Agent-ProductsFinder" --query "[0].appId" -o tsv)

# Create a service principal
az ad sp create --id $APP_ID

# Create a client secret (store securely!)
az ad app credential reset --id $APP_ID --years 2
```

#### Option C: Via Bicep/Terraform (Infrastructure as Code)

```bicep
// Bicep example for agent app registration
resource agentApp 'Microsoft.Graph/applications@v1.0' = {
  displayName: 'MAF-Agent-ProductsFinder'
  signInAudience: 'AzureADMyOrg'
  requiredResourceAccess: [
    {
      resourceAppId: '00000003-0000-0000-c000-000000000000' // Microsoft Graph
      resourceAccess: [
        {
          id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d' // User.Read
          type: 'Scope'
        }
      ]
    }
  ]
}
```

---

## 3. Authentication Methods for Agents

### 3.1 Client Credentials Flow (OAuth 2.0)

The **Client Credentials Grant** is the primary OAuth flow for agents (server-to-server authentication).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLIENT CREDENTIALS FLOW                               │
│                    (Agent-to-Service Authentication)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐                                      ┌──────────────────┐│
│   │          │  1. POST /oauth2/v2.0/token          │                  ││
│   │   AI     │  ─────────────────────────────────→  │   Microsoft      ││
│   │  AGENT   │     client_id + client_secret        │   Entra ID       ││
│   │          │     (or certificate)                 │                  ││
│   │          │                                      │                  ││
│   │          │  2. Access Token (JWT)               │                  ││
│   │          │  ←─────────────────────────────────  │                  ││
│   └────┬─────┘                                      └──────────────────┘│
│        │                                                                 │
│        │  3. API Request + Bearer Token                                 │
│        ▼                                                                 │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                      TARGET RESOURCE                              │  │
│   │  (Azure OpenAI, Microsoft Graph, Another Agent, MCP Server, etc.) │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Token Request (with Client Secret)

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id=00001111-aaaa-2222-bbbb-3333cccc4444
&scope=https://graph.microsoft.com/.default
&client_secret=your_client_secret_here
&grant_type=client_credentials
```

#### Token Request (with Certificate)

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id=00001111-aaaa-2222-bbbb-3333cccc4444
&scope=https://graph.microsoft.com/.default
&client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer
&client_assertion=eyJhbGciOiJSUzI1NiIsIng1dCI6...
&grant_type=client_credentials
```

### 3.2 Managed Identity (Recommended for Azure)

Managed Identities eliminate the need to manage credentials entirely.

| Type | Description | Use Case |
|------|-------------|----------|
| **System-assigned** | Tied to a single Azure resource lifecycle | Single-purpose agents |
| **User-assigned** | Independent lifecycle, can be shared | Multi-agent scenarios |

```python
# Python example using DefaultAzureCredential
from azure.identity import DefaultAzureCredential

# Works automatically with Managed Identity in Azure
credential = DefaultAzureCredential()
token = credential.get_token("https://cognitiveservices.azure.com/.default")
```

### 3.3 Federated Identity Credentials (Cross-Cloud/GitHub Actions)

For agents running outside Azure (e.g., GitHub Actions, Kubernetes, AWS):

```json
{
  "name": "github-actions-federation",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:myorg/myrepo:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}
```

---

## 4. A2A Protocol Authentication Flow

The **Agent-to-Agent (A2A)** protocol enables AI agents to communicate using JSON-RPC. When mediated through Azure API Management, multiple authentication options are available.

### 4.1 A2A Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        A2A AUTHENTICATION FLOW                                   │
│                        (via Azure API Management)                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────────┐                                                              │
│   │   Calling    │                                                              │
│   │   Agent      │                                                              │
│   │   (Client)   │                                                              │
│   └──────┬───────┘                                                              │
│          │                                                                       │
│          │ 1. Get Agent Card (Discovery)                                        │
│          │    GET /.well-known/agent.json                                       │
│          ▼                                                                       │
│   ┌──────────────────────────────────────────────────────────────────┐          │
│   │                     AZURE API MANAGEMENT                          │          │
│   │                     (A2A Gateway)                                 │          │
│   │  ┌────────────────────────────────────────────────────────────┐  │          │
│   │  │  Authentication Options:                                    │  │          │
│   │  │                                                             │  │          │
│   │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │  │          │
│   │  │  │ Subscription    │  │ OAuth 2.0 /     │  │ Managed     │ │  │          │
│   │  │  │ Key             │  │ Entra ID JWT    │  │ Identity    │ │  │          │
│   │  │  │                 │  │                 │  │             │ │  │          │
│   │  │  │ Header:         │  │ Header:         │  │ Automatic   │ │  │          │
│   │  │  │ Ocp-Apim-       │  │ Authorization:  │  │ Token       │ │  │          │
│   │  │  │ Subscription-   │  │ Bearer <JWT>    │  │ Injection   │ │  │          │
│   │  │  │ Key: xxx        │  │                 │  │             │ │  │          │
│   │  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │  │          │
│   │  └────────────────────────────────────────────────────────────┘  │          │
│   │                                                                   │          │
│   │  OpenTelemetry Attributes Added:                                 │          │
│   │  • genai.agent.id = <agent_id>                                   │          │
│   │  • genai.agent.name = <api_name>                                 │          │
│   └──────────────────────────────────────────────────────────────────┘          │
│          │                                                                       │
│          │ 2. JSON-RPC Request                                                  │
│          │    POST /a2a-endpoint                                                │
│          ▼                                                                       │
│   ┌──────────────┐                                                              │
│   │   Target     │                                                              │
│   │   Agent      │                                                              │
│   │   (Server)   │                                                              │
│   └──────────────┘                                                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 A2A Agent Card with Security Metadata

When APIM imports an A2A agent, it rewrites the Agent Card to include authentication requirements:

```json
{
  "name": "ProductsFinder Agent",
  "description": "Finds products based on customer queries",
  "url": "https://myapim.azure-api.net/products-agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "authentication": {
    "schemes": [
      {
        "scheme": "apiKey",
        "name": "Ocp-Apim-Subscription-Key",
        "in": "header"
      },
      {
        "scheme": "oauth2",
        "flows": {
          "clientCredentials": {
            "tokenUrl": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "scopes": {
              "api://{client-id}/.default": "Access the agent API"
            }
          }
        }
      }
    ]
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"]
}
```

### 4.3 Calling an A2A Agent with OAuth

```python
import httpx
from azure.identity import ClientSecretCredential

# 1. Authenticate as the calling agent
credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="calling-agent-client-id",
    client_secret="calling-agent-secret"
)

# 2. Get token for the target agent's API
token = credential.get_token("api://target-agent-client-id/.default")

# 3. Call the A2A endpoint
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://myapim.azure-api.net/products-agent/a2a",
        headers={
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        },
        json={
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "task": {
                    "message": {
                        "role": "user",
                        "parts": [{"text": "Find laptops under $1000"}]
                    }
                }
            },
            "id": "task-123"
        }
    )
```

---

## 5. MCP Server Authentication Flow

MCP (Model Context Protocol) servers expose tools that agents can call. Authentication flows differ based on server hosting.

### 5.1 MCP Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MCP SERVER AUTHENTICATION                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────────┐                                                              │
│   │   AI Agent   │                                                              │
│   │   (MCP       │                                                              │
│   │   Client)    │                                                              │
│   └──────┬───────┘                                                              │
│          │                                                                       │
│          │ Which type of MCP Server?                                            │
│          │                                                                       │
│     ┌────┴────┬─────────────────┬────────────────┐                              │
│     ▼         ▼                 ▼                ▼                              │
│  ┌──────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐                  │
│  │Local │  │ Hosted   │  │  APIM-Managed │  │  Custom Remote  │                  │
│  │MCP   │  │ MCP      │  │  MCP Server   │  │  MCP Server     │                  │
│  │(stdio)│  │(Foundry) │  │              │  │                 │                  │
│  └──────┘  └──────────┘  └──────────────┘  └─────────────────┘                  │
│     │           │               │                   │                            │
│     │           │               │                   │                            │
│  No Auth    Foundry         API Key or          OAuth/JWT                       │
│  (local)    Managed ID      OAuth 2.0           Required                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 APIM-Managed MCP Server (REST API Exposed as MCP)

When you expose a REST API as an MCP server through APIM:

```
┌──────────────────────────────────────────────────────────────────────────┐
│           APIM MCP SERVER AUTHENTICATION                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   Agent Request                                                          │
│       │                                                                   │
│       │  MCP Protocol (tools/list, tools/call)                          │
│       │  + Authentication Header                                         │
│       ▼                                                                   │
│   ┌─────────────────────────────────────────────────────────────────┐    │
│   │                    AZURE API MANAGEMENT                          │    │
│   │                                                                  │    │
│   │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │    │
│   │   │ Subscription │    │ JWT Validate │    │ Rate Limit   │     │    │
│   │   │ Key Check    │ → │ Policy       │ → │ by Session   │     │    │
│   │   └──────────────┘    └──────────────┘    └──────────────┘     │    │
│   │           │                                                     │    │
│   │           ▼                                                     │    │
│   │   ┌──────────────────────────────────────────────────────┐    │    │
│   │   │         MCP → REST Translation                        │    │    │
│   │   │                                                       │    │    │
│   │   │  tools/call → POST /api/orders/{orderId}             │    │    │
│   │   │  tools/list → GET /openapi.json (schema parsing)     │    │    │
│   │   └──────────────────────────────────────────────────────┘    │    │
│   │                                                                  │    │
│   └─────────────────────────────────────────────────────────────────┘    │
│                           │                                               │
│                           ▼                                               │
│                   ┌──────────────┐                                       │
│                   │  Backend API │                                       │
│                   │  (REST)      │                                       │
│                   └──────────────┘                                       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.3 MCP Server Configuration in VS Code (with Auth)

```json
{
  "mcpServers": {
    "products-mcp": {
      "type": "http",
      "url": "https://myapim.azure-api.net/products-api-mcp/mcp",
      "headers": {
        "Ocp-Apim-Subscription-Key": "${env:APIM_SUBSCRIPTION_KEY}"
      }
    },
    "secure-mcp": {
      "type": "http",
      "url": "https://myapim.azure-api.net/secure-mcp/mcp",
      "headers": {
        "Authorization": "Bearer ${env:ENTRA_ACCESS_TOKEN}"
      }
    }
  }
}
```

### 5.4 OAuth 2.0 for MCP Servers (Protected Resource Metadata)

For advanced scenarios, MCP servers can use Protected Resource Metadata (PRM):

```python
# MCP Client with OAuth authentication
from mcp import ClientSession
import httpx

class OAuthMCPClient:
    def __init__(self, mcp_url: str, token_provider):
        self.mcp_url = mcp_url
        self.token_provider = token_provider
    
    async def call_tool(self, tool_name: str, arguments: dict):
        token = await self.token_provider.get_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": "1"
                }
            )
        return response.json()
```

---

## 6. Managed Identity for Agents (Recommended)

### 6.1 Why Managed Identity is Best for Agents

| Benefit | Description |
|---------|-------------|
| **No Secrets** | No client secrets or certificates to manage |
| **Auto-Rotation** | Tokens automatically rotated |
| **No Expiry** | Identity never expires |
| **RBAC Integration** | Direct Azure role assignment |
| **Audit Trail** | Full sign-in logs in Entra ID |

### 6.2 Setting Up Managed Identity for an Agent

```
┌──────────────────────────────────────────────────────────────────────────┐
│              MANAGED IDENTITY SETUP FOR AGENTS                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   Step 1: Enable Managed Identity on Compute                             │
│   ─────────────────────────────────────────                              │
│                                                                           │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │  Azure Resource (where agent runs)                              │     │
│   │                                                                 │     │
│   │  • Container Apps  → System-assigned MI                        │     │
│   │  • Azure Functions → System-assigned MI                        │     │
│   │  • AKS            → Workload Identity (User-assigned)          │     │
│   │  • App Service    → System-assigned MI                         │     │
│   │  • Azure VM       → System/User-assigned MI                    │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                           │
│   Step 2: Grant RBAC Permissions                                         │
│   ──────────────────────────────                                         │
│                                                                           │
│   az role assignment create \                                            │
│     --assignee <managed-identity-object-id> \                            │
│     --role "Cognitive Services OpenAI User" \                            │
│     --scope /subscriptions/.../resourceGroups/.../providers/...          │
│                                                                           │
│   Step 3: Use in Code                                                    │
│   ───────────────────                                                    │
│                                                                           │
│   from azure.identity import DefaultAzureCredential                      │
│   credential = DefaultAzureCredential()  # Auto-detects MI               │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Managed Identity in Container Apps (Agent Deployment)

```bicep
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'maf-agent-productsfinder'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
    }
    template: {
      containers: [
        {
          name: 'agent'
          image: 'myregistry.azurecr.io/maf-agent:latest'
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: '' // Leave empty for system-assigned MI
            }
          ]
        }
      ]
    }
  }
}

// Grant the agent access to Azure OpenAI
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerApp.id, openAIAccount.id, 'Cognitive Services OpenAI User')
  scope: openAIAccount
  properties: {
    principalId: containerApp.identity.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    )
    principalType: 'ServicePrincipal'
  }
}
```

---

## 7. Key Differences: User vs Agent Authentication

### 7.1 Comparison Table

| Aspect | User Authentication | Agent Authentication |
|--------|---------------------|----------------------|
| **OAuth Flow** | Authorization Code + PKCE | Client Credentials |
| **Interaction** | Interactive (browser redirect) | Non-interactive (server-to-server) |
| **Identity Type** | Human Identity | Workload Identity |
| **MFA** | Yes (can enforce) | No (not applicable) |
| **Consent** | User grants consent | Admin grants consent |
| **Token Type** | Delegated permissions | Application permissions |
| **Refresh Tokens** | Yes | No (not needed) |
| **Credential Management** | User manages password | App manages secrets/certs |
| **Recommended Credential** | Password + MFA | Managed Identity |

### 7.2 Permission Model Differences

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERMISSION MODELS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   USER (Delegated Permissions)          AGENT (Application Permissions) │
│   ────────────────────────────          ─────────────────────────────── │
│                                                                          │
│   User signs in                         Agent authenticates as itself   │
│        │                                      │                          │
│        ▼                                      ▼                          │
│   ┌─────────────┐                       ┌─────────────┐                 │
│   │ Delegated   │                       │ Application │                 │
│   │ Permissions │                       │ Permissions │                 │
│   │             │                       │             │                 │
│   │ User.Read   │                       │ User.Read   │                 │
│   │ (as user)   │                       │ .All        │                 │
│   └─────────────┘                       │ (as app)    │                 │
│        │                                └─────────────┘                 │
│        ▼                                      │                          │
│   App acts on behalf                    App acts as itself              │
│   of signed-in user                     (no user context)               │
│                                                                          │
│   Example: Read MY profile              Example: Read ALL user profiles │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Admin Consent for Agent Permissions

Unlike user authentication, agents require **admin consent** for application permissions:

```http
GET https://login.microsoftonline.com/{tenant}/adminconsent
    ?client_id=00001111-aaaa-2222-bbbb-3333cccc4444
    &state=12345
    &redirect_uri=https://myapp.com/permissions
```

---

## 8. Implementation Examples

### 8.1 Python: Agent with Client Credentials

```python
# agents/auth/entra_auth.py
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from typing import Optional
import os

class AgentAuthenticator:
    """Handles authentication for AI agents using Entra ID."""
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_managed_identity: bool = True
    ):
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        self.use_managed_identity = use_managed_identity
        
        self._credential = self._create_credential()
    
    def _create_credential(self):
        """Create the appropriate credential based on configuration."""
        if self.use_managed_identity:
            # Automatically works with Managed Identity in Azure
            # Falls back to other credentials locally
            return DefaultAzureCredential()
        else:
            # Explicit client credentials
            return ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
    
    def get_token(self, scope: str) -> str:
        """Get an access token for the specified scope."""
        token = self._credential.get_token(scope)
        return token.token
    
    def get_token_for_azure_openai(self) -> str:
        """Get token for Azure OpenAI."""
        return self.get_token("https://cognitiveservices.azure.com/.default")
    
    def get_token_for_graph(self) -> str:
        """Get token for Microsoft Graph."""
        return self.get_token("https://graph.microsoft.com/.default")
    
    def get_token_for_agent(self, target_agent_client_id: str) -> str:
        """Get token for calling another agent."""
        return self.get_token(f"api://{target_agent_client_id}/.default")


# Usage in agent code
authenticator = AgentAuthenticator(use_managed_identity=True)

# Get token for Azure OpenAI
token = authenticator.get_token_for_azure_openai()

# Use with Azure OpenAI client
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token=token,
    api_version="2024-02-01"
)
```

### 8.2 Python: A2A Client with Authentication

```python
# a2a_agents/authenticated_client.py
import httpx
from typing import Any, Dict
from agents.auth.entra_auth import AgentAuthenticator

class AuthenticatedA2AClient:
    """A2A client with Entra ID authentication."""
    
    def __init__(
        self,
        agent_url: str,
        target_agent_client_id: str,
        authenticator: AgentAuthenticator
    ):
        self.agent_url = agent_url
        self.target_agent_client_id = target_agent_client_id
        self.authenticator = authenticator
    
    async def send_task(self, message: str) -> Dict[str, Any]:
        """Send a task to the target agent with authentication."""
        token = self.authenticator.get_token_for_agent(self.target_agent_client_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.agent_url}/a2a",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/send",
                    "params": {
                        "task": {
                            "message": {
                                "role": "user",
                                "parts": [{"text": message}]
                            }
                        }
                    },
                    "id": "1"
                }
            )
            return response.json()
    
    async def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent card (may not require auth)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.agent_url}/.well-known/agent.json")
            return response.json()


# Usage
authenticator = AgentAuthenticator(use_managed_identity=True)
a2a_client = AuthenticatedA2AClient(
    agent_url="https://myapim.azure-api.net/products-agent",
    target_agent_client_id="target-agent-client-id",
    authenticator=authenticator
)

result = await a2a_client.send_task("Find laptops under $1000")
```

### 8.3 C#/.NET: Agent with Managed Identity

```csharp
// Using Microsoft Agent Framework with Entra ID
using Azure.Identity;
using Azure.AI.Projects;
using Microsoft.Agents.AI;

// Create credential (auto-detects Managed Identity)
var credential = new DefaultAzureCredential();

// Create agent with Foundry backend
var endpoint = Environment.GetEnvironmentVariable("AZURE_AI_PROJECT_ENDPOINT");
var agent = new AIProjectClient(new Uri(endpoint), credential)
    .AsAIAgent(
        model: "gpt-4o-mini",
        name: "ProductsFinder",
        instructions: "You help customers find products."
    );

// Run the agent
var response = await agent.RunAsync("Find laptops under $1000");
Console.WriteLine(response);
```

---

## 9. Security Best Practices

### 9.1 Credential Security Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CREDENTIAL SECURITY RANKING                           │
│                    (Most Secure → Least Secure)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   🥇 MANAGED IDENTITY (System-assigned or User-assigned)                │
│      • No secrets to manage                                             │
│      • Automatic token rotation                                         │
│      • Tied to Azure resource lifecycle                                 │
│      └── USE THIS when running in Azure                                 │
│                                                                          │
│   🥈 FEDERATED IDENTITY CREDENTIALS                                     │
│      • No secrets for cross-cloud scenarios                             │
│      • Uses external IdP tokens                                         │
│      └── USE THIS for GitHub Actions, Kubernetes, AWS/GCP              │
│                                                                          │
│   🥉 CERTIFICATES                                                        │
│      • More secure than secrets                                         │
│      • Longer validity (1-2 years)                                      │
│      • Requires certificate management                                  │
│      └── USE THIS for on-premises or non-Azure clouds                  │
│                                                                          │
│   ⚠️  CLIENT SECRETS                                                     │
│      • Easy to implement                                                │
│      • Max 2-year expiry                                                │
│      • Requires secure storage (Key Vault)                              │
│      └── USE THIS only when other options unavailable                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Security Checklist

- [ ] **Use Managed Identity** when running in Azure
- [ ] **Store secrets in Key Vault** if using client secrets
- [ ] **Enable Conditional Access** for workload identities (Entra ID Premium)
- [ ] **Monitor sign-in logs** in Entra ID
- [ ] **Use short token lifetimes** (default 1 hour is good)
- [ ] **Implement least privilege** - only grant required permissions
- [ ] **Enable ID Protection** for workload identity risk detection
- [ ] **Rotate secrets** before expiry (automate with Key Vault)
- [ ] **Use certificate authentication** over secrets when possible
- [ ] **Audit application permissions** regularly

### 9.3 Conditional Access for Agents

```json
{
  "displayName": "Require compliant network for AI agents",
  "conditions": {
    "clientAppTypes": ["all"],
    "applications": {
      "includeApplications": ["<agent-app-id>"]
    },
    "locations": {
      "includeLocations": ["All"],
      "excludeLocations": ["AllTrusted"]
    }
  },
  "grantControls": {
    "operator": "AND",
    "builtInControls": ["block"]
  }
}
```

---

## 10. References

### Microsoft Documentation

| Topic | URL |
|-------|-----|
| OAuth 2.0 Client Credentials Flow | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow |
| Workload Identities Overview | https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-overview |
| Managed Identities | https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview |
| A2A Agent API in APIM | https://learn.microsoft.com/en-us/azure/api-management/agent-to-agent-api |
| MCP Server in APIM | https://learn.microsoft.com/en-us/azure/api-management/export-rest-mcp-server |
| Secure MCP Servers | https://learn.microsoft.com/en-us/azure/api-management/secure-mcp-servers |
| App Roles | https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps |

### Samples & Labs

| Sample | URL |
|--------|-----|
| MCP OAuth with PRM | https://github.com/blackchoey/remote-mcp-apim-oauth-prm/ |
| Secure Remote MCP | https://github.com/Azure-Samples/remote-mcp-apim-functions-python |
| MCP Client Authorization Lab | https://github.com/Azure-Samples/AI-Gateway/tree/main/labs/mcp-client-authorization |

### Related MAF Documentation

- [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) - Architecture diagrams including A2A and MCP flows
- [ARCHITECTURE_V1_AZURE_NATIVE.md](ARCHITECTURE_V1_AZURE_NATIVE.md) - Azure-native architecture with Entra ID
- [Microsoft_Agent_Framework_Features.drawio](Microsoft_Agent_Framework_Features.drawio) - Official MAF features

---

## Summary

| Scenario | Recommended Authentication | Notes |
|----------|---------------------------|-------|
| Agent running in Azure | **Managed Identity** | Zero secrets, auto-rotation |
| Agent calling Azure OpenAI | **Managed Identity** | RBAC: "Cognitive Services OpenAI User" |
| Agent-to-Agent (A2A) via APIM | **OAuth 2.0 + Subscription Key** | JWT validation in APIM policies |
| MCP Server via APIM | **Subscription Key or OAuth** | Configure in MCP server policies |
| GitHub Actions → Azure | **Federated Identity Credential** | OIDC without secrets |
| On-premises agent | **Certificate** | Store cert in secure location |
| Development/testing | **Client Secret** | Store in Key Vault, not code |

---

*Document Version: 1.0*  
*Last Updated: April 2026*  
*Source: Microsoft Learn, Microsoft Agent Framework Documentation*
