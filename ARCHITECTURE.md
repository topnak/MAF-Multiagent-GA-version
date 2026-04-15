# MAFGA Multi-Agent Architecture Diagram

This document contains the architecture diagram for the Multi-Agent POC built on MAF 1.0 GA.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI[Web UI / CLI]
        API_Client[API Client]
    end

    subgraph Gateway["API Gateway"]
        FastAPI[FastAPI Service]
        Auth[EntraID Auth]
        CORS[CORS Middleware]
    end

    subgraph Middleware["Middleware Pipeline"]
        RBAC[RBAC Middleware]
        ContentSafety[Content Safety]
        AuditLog[Audit Log]
    end

    subgraph Orchestration["Orchestration Layer"]
        Magentic[Magentic Orchestrator<br/>Task-Ledger Planning]
        Router[Traffic Router<br/>Intent-Based Routing]
        Parallel[Parallel Executor<br/>Concurrent Execution]
        HITL[Human Approval<br/>Manager]
    end

    subgraph Agents["Agent Layer"]
        MerchPlanner[MerchPlanner Agent]
        SpacePlanner[SpacePlanner Agent]
        LoyaltyAgent[LoyaltyAgent]
        ProductsFinder[ProductsFinder Agent]
        CommercialSales[CommercialSales Agent]
        CampaignAnalyst[CampaignAnalyst Agent]
    end

    subgraph Memory["Memory & State"]
        Redis[(Redis Memory)]
        FileCheckpoint[(File Checkpoint)]
        InMemory[(In-Memory Cache)]
    end

    subgraph MCP["MCP Servers (Tools)"]
        Snowflake[Snowflake MCP<br/>Data Warehouse]
        Salesforce[Salesforce MCP<br/>CRM]
        Weather[Weather MCP<br/>Forecasts]
        Items[Items API MCP<br/>Product Catalog]
        Personal[Personalisation MCP<br/>Preferences]
        Local[Localisation MCP<br/>Regional Data]
    end

    subgraph A2A["A2A External Agents"]
        PricingAgent[Pricing Agent]
        InventoryAgent[Inventory Agent]
        FulfilmentAgent[Fulfilment Agent]
    end

    subgraph LLM["LLM Providers"]
        AzureFoundry[Azure AI Foundry]
        AzureOpenAI[Azure OpenAI]
        OpenAI[OpenAI]
        Anthropic[Anthropic Claude]
        Ollama[Ollama Local]
    end

    subgraph Observability["Observability"]
        Telemetry[OpenTelemetry]
        Jaeger[Jaeger Tracing]
        Prometheus[Prometheus Metrics]
    end

    %% Client connections
    UI --> FastAPI
    API_Client --> FastAPI

    %% Gateway flow
    FastAPI --> Auth
    Auth --> CORS
    CORS --> RBAC

    %% Middleware chain
    RBAC --> ContentSafety
    ContentSafety --> AuditLog

    %% Middleware to Orchestration
    AuditLog --> Magentic
    AuditLog --> Router
    AuditLog --> Parallel

    %% Orchestration dependencies
    Magentic --> HITL
    Magentic --> MerchPlanner
    Magentic --> SpacePlanner
    Magentic --> LoyaltyAgent
    Magentic --> ProductsFinder
    Magentic --> CommercialSales
    Magentic --> CampaignAnalyst

    Router --> MerchPlanner
    Router --> SpacePlanner
    Router --> LoyaltyAgent
    Router --> ProductsFinder
    Router --> CommercialSales
    Router --> CampaignAnalyst

    Parallel --> MerchPlanner
    Parallel --> SpacePlanner

    %% Agent to MCP
    MerchPlanner --> Snowflake
    SpacePlanner --> Snowflake
    LoyaltyAgent --> Personal
    LoyaltyAgent --> Local
    ProductsFinder --> Items
    CommercialSales --> Salesforce
    CommercialSales --> Snowflake
    CampaignAnalyst --> Weather
    CampaignAnalyst --> Snowflake

    %% Agent to A2A
    MerchPlanner --> PricingAgent
    ProductsFinder --> InventoryAgent
    CommercialSales --> FulfilmentAgent

    %% Agent to LLM (via factory)
    MerchPlanner -.-> AzureFoundry
    SpacePlanner -.-> AzureFoundry
    LoyaltyAgent -.-> AzureFoundry
    ProductsFinder -.-> AzureFoundry
    CommercialSales -.-> AzureFoundry
    CampaignAnalyst -.-> AzureFoundry

    %% Memory connections
    MerchPlanner --> Redis
    MerchPlanner --> FileCheckpoint

    %% Observability
    FastAPI --> Telemetry
    Magentic --> Telemetry
    MerchPlanner --> Telemetry
    Telemetry --> Jaeger
    Telemetry --> Prometheus
```

## MAF 1.0 GA Component Detail

```mermaid
flowchart LR
    subgraph AgentPattern["Agent Pattern (MAF 1.0 GA)"]
        Agent[Agent Class]
        ChatClient[ChatClient Interface]
        Instructions[System Instructions]
        Tools[Tool Definitions]
    end

    subgraph ChatClients["Pluggable Chat Clients"]
        AzureFoundryClient[AzureAI<br/>ChatCompletions<br/>Client]
        AzureOpenAIClient[AzureOpenAI<br/>Client]
        OpenAIClient[OpenAI<br/>Client]
        AnthropicClient[Anthropic<br/>Client]
        OllamaClient[Ollama<br/>Client]
    end

    subgraph MCPIntegration["MCP Tool Integration"]
        MCPToolCall[Tool Call Request]
        MCPServer[MCP Server]
        MCPResult[Tool Result]
    end

    Agent --> ChatClient
    Agent --> Instructions
    Agent --> Tools

    ChatClient --> AzureFoundryClient
    ChatClient --> AzureOpenAIClient
    ChatClient --> OpenAIClient
    ChatClient --> AnthropicClient
    ChatClient --> OllamaClient

    Tools --> MCPToolCall
    MCPToolCall --> MCPServer
    MCPServer --> MCPResult
    MCPResult --> Agent
```

## Orchestration Patterns

```mermaid
flowchart TB
    subgraph MagenticPattern["Magentic Orchestration"]
        direction TB
        Goal[User Goal]
        Planner[LLM Planner]
        Plan[Task Ledger / Plan]
        Approval{Human<br/>Approval?}
        ExecuteSteps[Execute Steps]
        Synthesize[Synthesize Results]
        
        Goal --> Planner
        Planner --> Plan
        Plan --> Approval
        Approval -->|Approved| ExecuteSteps
        Approval -->|Rejected| Goal
        ExecuteSteps --> Synthesize
    end

    subgraph HandoffPattern["Handoff (Traffic Routing)"]
        direction TB
        Query[User Query]
        Classifier[Intent Classifier]
        RouteDecision{Select Agent}
        Agent1[Agent A]
        Agent2[Agent B]
        Agent3[Agent C]
        
        Query --> Classifier
        Classifier --> RouteDecision
        RouteDecision --> Agent1
        RouteDecision --> Agent2
        RouteDecision --> Agent3
    end

    subgraph ConcurrentPattern["Concurrent Execution"]
        direction TB
        Task[Multi-task Request]
        Split[Split Tasks]
        ParallelExec["Parallel Execution<br/>(asyncio.gather)"]
        Aggregate[Aggregate Results]
        
        Task --> Split
        Split --> ParallelExec
        ParallelExec --> Aggregate
    end
```

## Human-in-the-Loop Workflow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Orchestrator
    participant ApprovalManager
    participant Agent

    User->>API: POST /orchestration/run
    API->>Orchestrator: run(goal, require_approval=true)
    Orchestrator->>Orchestrator: Create Plan
    Orchestrator->>ApprovalManager: Request Approval
    ApprovalManager-->>API: Return pending approval
    API-->>User: Plan pending approval

    Note over User,ApprovalManager: Human reviews plan

    User->>API: POST /orchestration/approvals/{id}
    API->>ApprovalManager: approve(id)
    ApprovalManager->>Orchestrator: Approval granted
    Orchestrator->>Agent: Execute step 1
    Agent-->>Orchestrator: Result 1
    Orchestrator->>Agent: Execute step 2
    Agent-->>Orchestrator: Result 2
    Orchestrator->>Orchestrator: Synthesize results
    Orchestrator-->>API: Final result
    API-->>User: Orchestration complete
```

## Memory & Checkpoint Flow

```mermaid
flowchart LR
    subgraph Conversation["Conversation Flow"]
        Query1[Query 1]
        Query2[Query 2]
        Query3[Query 3]
    end

    subgraph MemorySystem["Memory System"]
        MemoryProvider[Memory Provider]
        Redis[(Redis)]
        InMem[(In-Memory)]
    end

    subgraph CheckpointSystem["Checkpoint System"]
        CheckpointStore[Checkpoint Store]
        FileStore[(File Store)]
    end

    Query1 -->|Store| MemoryProvider
    Query2 -->|Store| MemoryProvider
    Query3 -->|Store| MemoryProvider

    MemoryProvider --> Redis
    MemoryProvider --> InMem

    MemoryProvider -->|Periodic Save| CheckpointStore
    CheckpointStore --> FileStore

    FileStore -->|Restore on Restart| MemoryProvider
```

## Security Architecture

```mermaid
flowchart TB
    subgraph AuthFlow["Authentication Flow"]
        Request[Incoming Request]
        JWT[JWT Token]
        EntraID[Azure EntraID]
        UserContext[User Context]
    end

    subgraph AuthZ["Authorization"]
        RBAC[RBAC Check]
        AgentAccess{Agent<br/>Access?}
        Allow[Allow]
        Deny[Deny 403]
    end

    subgraph Safety["Content Safety"]
        PIICheck[PII Detection]
        KeywordFilter[Keyword Filter]
        ContentMod[Content Moderation]
    end

    subgraph Audit["Audit Trail"]
        AuditLog[(Audit Log)]
        Compliance[Compliance Report]
    end

    Request --> JWT
    JWT --> EntraID
    EntraID --> UserContext
    UserContext --> RBAC
    RBAC --> AgentAccess
    AgentAccess -->|Yes| PIICheck
    AgentAccess -->|No| Deny
    PIICheck --> KeywordFilter
    KeywordFilter --> ContentMod
    ContentMod --> Allow
    
    Allow --> AuditLog
    Deny --> AuditLog
    AuditLog --> Compliance
```
