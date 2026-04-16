# MAF 1.0 GA Architecture - Mermaid Diagrams

This document contains Mermaid diagrams for all three architecture versions.

---

## Version 1: Azure-Native Architecture

Full Azure ecosystem with Microsoft Foundry, APIM, Entra ID, and Key Vault.

```mermaid
flowchart TB
    subgraph Clients["🖥️ Client Layer"]
        direction LR
        WebUI["Web UI"]
        Teams["Teams Bot"]
        Mobile["Mobile App"]
        CLI["CLI"]
    end

    subgraph Security["🔐 Security & Identity"]
        direction TB
        subgraph EntraID["Microsoft Entra ID"]
            ManagedID["Managed Identity"]
            UserAuth["User Auth (B2C/B2B)"]
            RBAC["RBAC"]
        end
        subgraph KeyVault["Azure Key Vault"]
            Secrets["API Keys"]
            Certs["Certificates"]
            ConnStr["Connection Strings"]
        end
    end

    subgraph APIM["🌐 Azure API Management"]
        direction LR
        Traffic["Traffic Manager"]
        RateLimit["Rate Limiting"]
        Validation["Request Validation"]
        OAuth["OAuth2 Gateway"]
        Policy["Policy Engine"]
        ContentSafety1["Content Safety"]
        AIGateway["AI Gateway"]
    end

    subgraph MAF["🧠 MAF 1.0 GA - Orchestration Layer"]
        direction TB
        subgraph Orchestrator["Magentic Orchestrator"]
            SessionMgr["Session Manager"]
            LLMPlanner["LLM Planner"]
            Synthesizer["Result Synthesizer"]
            ContextBuilder["Context Builder"]
            AgentRouter["Agent Router"]
            Logger["Logger"]
        end
        subgraph HITL["Human-in-the-Loop"]
            PlanApproval["Plan Approval"]
            AsyncQueue["Async Queue"]
            Timeout["Timeout Handler"]
        end
        TrafficRouter["Traffic Router"]
        ParallelExec["Parallel Executor"]
        Middleware["Middleware Pipeline<br/>(RBAC | Content Safety | Audit)"]
        Checkpoint["Checkpoint Manager"]
        Memory["Memory Manager"]
    end

    subgraph Agents["🤖 MAF 1.0 GA - Agent Layer"]
        direction LR
        MerchAgent["MerchPlanner<br/>Agent"]
        SpaceAgent["SpacePlanner<br/>Agent"]
        LoyaltyAgent["Loyalty<br/>Agent"]
        ProductsAgent["ProductsFinder<br/>Agent"]
        CommercialAgent["CommercialSales<br/>Agent"]
        CampaignAgent["CampaignAnalyst<br/>Agent"]
    end

    subgraph Foundry["🤖 Microsoft Foundry"]
        direction LR
        AIStudio["AI Studio"]
        AzureOpenAI["Azure OpenAI<br/>(GPT-4o, GPT-4.1)"]
        PromptFlow["Prompt Flow"]
        AISearch["AI Search"]
        ContentSafety2["Content Safety"]
        ModelDeploy["Model Deployments"]
    end

    subgraph Knowledge["📚 Knowledge Layer"]
        direction LR
        CosmosDB["Cosmos DB<br/>(Chat History)"]
        Redis["Redis Cache<br/>(Semantic Cache)"]
        Blob["Blob Storage<br/>(Checkpoints)"]
        VectorDB["AI Search<br/>(Vector DB)"]
    end

    subgraph MCP["🔌 MCP / A2A Layer"]
        direction TB
        subgraph InternalMCP["Internal MCP"]
            SnowflakeMCP["Snowflake MCP"]
            SalesforceMCP["Salesforce MCP"]
            WeatherMCP["Weather MCP"]
            ItemsMCP["Items API MCP"]
        end
        subgraph ExternalA2A["External A2A"]
            PricingA2A["Pricing Agent"]
            InventoryA2A["Inventory Agent"]
            FulfilmentA2A["Fulfilment Agent"]
        end
    end

    subgraph Observability["📊 Observability"]
        direction TB
        Monitor["Azure Monitor"]
        AppInsights["Application Insights"]
        LogAnalytics["Log Analytics Workspace"]
        Alerts["Alerts"]
        Metrics["Metrics"]
        Dashboard["Dashboard"]
        Workbooks["Workbooks"]
        Langfuse["Langfuse<br/>(LLM Observability)"]
        OTel["OpenTelemetry"]
    end

    %% Connections
    Clients --> APIM
    Security --> APIM
    Security --> MAF
    APIM -->|JWT Token| MAF
    MAF --> Agents
    Agents -->|LLM Calls| Foundry
    Foundry --> Knowledge
    Agents --> MCP
    MAF -.->|Telemetry| Observability

    %% Styling
    classDef clientStyle fill:#FFF3E0,stroke:#E65100,stroke-width:2px
    classDef securityStyle fill:#FCE4EC,stroke:#AD1457,stroke-width:2px
    classDef apimStyle fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px
    classDef mafStyle fill:#E3F2FD,stroke:#1565C0,stroke-width:2px
    classDef agentStyle fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    classDef foundryStyle fill:#E8EAF6,stroke:#303F9F,stroke-width:2px
    classDef knowledgeStyle fill:#E0F2F1,stroke:#00695C,stroke-width:2px
    classDef mcpStyle fill:#ECEFF1,stroke:#455A64,stroke-width:2px
    classDef obsStyle fill:#FFF8E1,stroke:#FF6F00,stroke-width:2px

    class Clients clientStyle
    class Security securityStyle
    class APIM apimStyle
    class MAF mafStyle
    class Agents agentStyle
    class Foundry foundryStyle
    class Knowledge knowledgeStyle
    class MCP mcpStyle
    class Observability obsStyle
```

### V1 Component Flow Diagram

```mermaid
sequenceDiagram
    participant Client as 🖥️ Client
    participant APIM as 🌐 APIM
    participant Entra as 🔐 Entra ID
    participant MAF as 🧠 MAF Orchestrator
    participant Agent as 🤖 Agent
    participant Foundry as 🤖 Microsoft Foundry
    participant MCP as 🔌 MCP Server
    participant Obs as 📊 Observability

    Client->>APIM: HTTP Request
    APIM->>Entra: Validate Token
    Entra-->>APIM: Token Valid + Claims
    APIM->>APIM: Apply Policies (Rate Limit, Content Safety)
    APIM->>MAF: Forward Request (JWT)
    
    MAF->>MAF: Session Manager (Create/Resume)
    MAF->>Foundry: LLM Planning (GPT-4o)
    Foundry-->>MAF: Task Plan
    
    MAF->>Agent: Route to Specialist Agent
    Agent->>MCP: Tool Call (Snowflake/Salesforce)
    MCP-->>Agent: Tool Response
    Agent->>Foundry: LLM Reasoning
    Foundry-->>Agent: Agent Response
    
    Agent-->>MAF: Result
    MAF->>MAF: Synthesize Results
    MAF-->>APIM: Response
    APIM-->>Client: HTTP Response
    
    MAF-.>>Obs: Telemetry (OpenTelemetry)
    Agent-.>>Obs: Traces (Langfuse)
```

---

## Version 2: APIM-Centric Architecture

Azure API Management as the central hub handling all security, caching, and routing concerns.

```mermaid
flowchart TB
    subgraph Clients["🖥️ External Clients"]
        direction LR
        WebApps["Web Apps"]
        MobileApps["Mobile Apps"]
        TeamsBot["Teams Bot"]
        PartnerAPIs["Partner APIs"]
        CLIAgents["CLI / Agents"]
    end

    subgraph Identity["🔐 Identity & Secrets"]
        direction TB
        EntraID["Microsoft Entra ID<br/>(Token Issuance & Validation)"]
        KeyVault["Azure Key Vault<br/>(Secrets Management)"]
    end

    subgraph APIMHub["🌐 Azure API Management - Central Hub"]
        direction TB
        
        subgraph Inbound["Inbound Processing Pipeline"]
            direction LR
            RateLimit["Rate Limiting<br/>& Throttling"]
            OAuthValid["OAuth2 Token<br/>Validation"]
            JWTClaims["JWT Claims<br/>Extraction"]
            IPFilter["IP Filtering<br/>& Geo-Block"]
            ReqTransform["Request<br/>Transform"]
            ContentSafetyIn["Content Safety<br/>(Jailbreak Detect)"]
            SchemaValid["Schema<br/>Validation"]
            QuotaMgmt["Quota<br/>Management"]
            CacheLookup["Cache<br/>Lookup"]
        end

        subgraph Outbound["Outbound Processing Pipeline"]
            direction LR
            RespTransform["Response<br/>Transform"]
            RespValid["Response<br/>Validation"]
            OutputSafety["Output Content<br/>Safety"]
            PIIRedact["PII<br/>Redaction"]
            CORSHeaders["CORS<br/>Headers"]
            CacheStore["Cache Store<br/>(Response)"]
            Compression["Response<br/>Compression"]
            LoggingOut["Logging &<br/>Metrics"]
        end

        subgraph BackendPool["Backend Pool / Load Balancing"]
            direction LR
            PrimaryBackend["Primary Backend<br/>(MAF Service)"]
            AIGatewayBackend["AI Gateway<br/>Backend"]
            CircuitBreaker["Circuit<br/>Breaker"]
            RetryPolicy["Retry<br/>Policy"]
            TimeoutPolicy["Timeout<br/>Policy"]
            LBAlgo["Load Balancing<br/>(Round-Robin/Weighted)"]
            HealthProbe["Health<br/>Probes"]
            Failover["Failover<br/>Config"]
            TokenMetrics["Token Counting<br/>& Cost Tracking"]
            ModelRouter["Model Router<br/>(GPT-4o/4.1)"]
            SemanticCache["Semantic<br/>Caching"]
        end
    end

    subgraph MAFSimple["🧠 MAF 1.0 GA Service (Simplified)"]
        direction TB
        NoAuth["✓ No Auth Concerns - Handled by APIM"]
        
        subgraph OrchBox["Magentic Orchestrator"]
            SessionMgr2["Session<br/>Manager"]
            TaskLedger["Task<br/>Ledger"]
            ResultSynth["Result<br/>Synthesizer"]
            AgentRouter2["Agent<br/>Router"]
            ParallelExec2["Parallel<br/>Executor"]
            Handoff["Handoff"]
        end
        
        subgraph AgentsBox["Specialized Agents"]
            Merch["MerchPlanner"]
            Space["SpacePlanner"]
            Loyalty["LoyaltyAgent"]
            Products["ProductsFinder"]
            Commercial["CommercialSales"]
            Campaign["CampaignAnalyst"]
        end
        
        HITLBox["Human-in-the-Loop"]
        MiddlewareBox["Middleware (Audit Only)"]
        MemoryCheck["Memory & Checkpoint"]
        SkillsMCP["Skills & MCP Connectors"]
    end

    subgraph Foundry2["🤖 Microsoft Foundry"]
        direction LR
        AIStudio2["AI Studio"]
        OpenAI2["Azure OpenAI"]
        GPTModels["GPT-4o / GPT-4.1"]
        AISearch2["AI Search"]
        ContentSafety2["Content Safety"]
    end

    subgraph Data["💾 Data & Storage"]
        direction LR
        Cosmos2["Cosmos DB"]
        Redis2["Redis Cache"]
        Blob2["Blob Storage"]
        Search2["AI Search"]
        MCPConn["MCP Connectors"]
    end

    subgraph Obs2["📊 Observability"]
        direction TB
        Monitor2["Azure Monitor"]
        AppInsights2["App Insights"]
        LogAnalytics2["Log Analytics"]
        Alerts2["Alerts"]
        Workbooks2["Workbooks"]
        Langfuse2["Langfuse"]
        OTel2["OpenTelemetry"]
    end

    %% Connections
    Clients -->|HTTPS| APIMHub
    Identity --> APIMHub
    APIMHub -->|Internal| MAFSimple
    APIMHub -->|LLM Calls| Foundry2
    MAFSimple --> Foundry2
    MAFSimple --> Data
    APIMHub -.->|Telemetry| Obs2

    %% Styling
    classDef clientStyle fill:#FFF3E0,stroke:#E65100,stroke-width:2px
    classDef identityStyle fill:#FCE4EC,stroke:#AD1457,stroke-width:2px
    classDef apimStyle fill:#E8F5E9,stroke:#2E7D32,stroke-width:3px
    classDef mafStyle fill:#E3F2FD,stroke:#1565C0,stroke-width:2px
    classDef foundryStyle fill:#E8EAF6,stroke:#303F9F,stroke-width:2px
    classDef dataStyle fill:#E0F2F1,stroke:#00695C,stroke-width:2px
    classDef obsStyle fill:#FFF8E1,stroke:#FF6F00,stroke-width:2px

    class Clients clientStyle
    class Identity identityStyle
    class APIMHub apimStyle
    class MAFSimple mafStyle
    class Foundry2 foundryStyle
    class Data dataStyle
    class Obs2 obsStyle
```

### V2 Key Benefits

```mermaid
mindmap
  root((APIM-Centric<br/>Architecture))
    Security at Edge
      OAuth2/JWT Validation
      Content Safety
      PII Redaction
      IP Filtering
    Simplified MAF
      No Auth Logic
      Pure Business Logic
      Cleaner Codebase
    Caching
      Response Caching
      Semantic Caching
      Token Savings
    AI Gateway
      Model Routing
      Token Counting
      Cost Tracking
    Resilience
      Circuit Breaker
      Retry Policies
      Health Probes
      Failover
```

---

## Version 3: Cloud-Agnostic Architecture

Pluggable components for multi-cloud and hybrid deployments.

```mermaid
flowchart TB
    subgraph Clients3["🖥️ Client Applications"]
        direction LR
        WebApp3["Web Apps"]
        MobileApp3["Mobile Apps"]
        ChatBots3["Chat Bots"]
        PartnerAPI3["Partner APIs"]
    end

    subgraph Gateway["🌐 API Gateway Layer (Pluggable)"]
        direction TB
        GWInterface["IApiGateway Interface<br/>ValidateToken() | ApplyRateLimit() | RouteRequest()"]
        subgraph GWOptions["Gateway Options"]
            direction LR
            AzureAPIM["Azure APIM"]
            AWSAPIGW["AWS API Gateway"]
            Kong["Kong"]
            NGINX["NGINX"]
            Traefik["Traefik"]
        end
    end

    subgraph Identity3["🔐 Identity Provider (Pluggable)"]
        direction TB
        IDInterface["IIdentityProvider Interface<br/>Authenticate() | ValidateToken() | GetUserClaims()"]
        subgraph IDOptions["Identity Options"]
            direction LR
            EntraID3["Azure Entra ID"]
            Cognito["AWS Cognito"]
            Okta["Okta"]
            Auth0["Auth0"]
            Keycloak["Keycloak"]
        end
    end

    subgraph Secrets3["🔑 Secrets Management (Pluggable)"]
        direction TB
        SecretsInterface["ISecretsProvider Interface<br/>GetSecret() | SetSecret() | RotateSecret()"]
        subgraph SecretsOptions["Secrets Options"]
            direction LR
            AzureKV["Azure Key Vault"]
            AWSSecrets["AWS Secrets Manager"]
            HashiVault["HashiCorp Vault"]
            GCPSecrets["GCP Secret Manager"]
        end
    end

    subgraph MAFCore["🧠 MAF 1.0 GA Core (Cloud-Agnostic)"]
        direction TB
        CoreNote["Pure Business Logic - No Cloud Dependencies"]
        
        subgraph Orchestrator3["Magentic Orchestrator"]
            SessionMgr3["Session Manager"]
            TaskLedger3["Task Ledger"]
            Synthesizer3["Synthesizer"]
            AgentRouter3["Agent Router"]
            ParallelExec3["Parallel Executor"]
            Handoff3["Handoff"]
        end
        
        subgraph Agents3["Specialized Agents"]
            Merch3["MerchPlanner"]
            Space3["SpacePlanner"]
            Loyalty3["LoyaltyAgent"]
            Products3["ProductsFinder"]
            Commercial3["CommercialSales"]
            Campaign3["CampaignAnalyst"]
            Custom3["+ Custom Agents"]
        end
        
        HITL3["Human-in-the-Loop"]
        Middleware3["Middleware Pipeline"]
        MemCheck3["Memory & Checkpoint"]
        Skills3["Skills Registry (SKILL.md)"]
        MCPConn3["MCP Connectors (Pluggable)"]
        A2A3["A2A Protocol"]
        ChatInterface["IChatClient Interface (LLM Abstraction)"]
    end

    subgraph LLM["🤖 LLM Providers (Pluggable)"]
        direction TB
        ChatClientDef["IChatClient Interface<br/>SendMessage() | StreamResponse() | GetEmbeddings()"]
        subgraph LLMOptions["LLM Provider Options"]
            direction LR
            AzureOpenAI3["Azure OpenAI"]
            OpenAIDirect["OpenAI Direct"]
            Anthropic["Anthropic Claude"]
            GoogleGemini["Google Gemini"]
            AWSBedrock["AWS Bedrock"]
        end
        subgraph LocalLLM["Self-Hosted Options"]
            Ollama["Ollama"]
            LLaMA["LLaMA"]
            Mistral["Mistral AI"]
        end
        FoundryBox["Microsoft Foundry"]
    end

    subgraph Storage3["💾 Storage Layer (Pluggable)"]
        direction TB
        StorageInterface["IStorageProvider Interface<br/>Store() | Retrieve() | Delete()"]
        subgraph StorageOptions["Storage Options"]
            direction LR
            CosmosDB3["Cosmos DB"]
            DynamoDB["DynamoDB"]
            MongoDB["MongoDB"]
            PostgreSQL["PostgreSQL"]
            Redis3["Redis"]
        end
        subgraph FileStorage["File Storage"]
            BlobS3GCS["Blob / S3 / GCS"]
            VectorDB3["Vector DB (Pinecone/Weaviate)"]
        end
    end

    subgraph Obs3["📊 Observability (Pluggable)"]
        direction TB
        OTelCore["OpenTelemetry (Core)"]
        subgraph ObsAzure["Azure Stack"]
            Monitor3["Azure Monitor"]
            AppInsights3["App Insights"]
            LogAnalytics3["Log Analytics"]
        end
        subgraph ObsOther["Other Providers"]
            CloudWatch["CloudWatch"]
            Datadog["Datadog"]
            Grafana["Grafana"]
            Prometheus["Prometheus"]
            Jaeger["Jaeger"]
        end
        Langfuse3["Langfuse (LLM Observability)"]
    end

    subgraph Deploy["🚀 Deployment Targets"]
        direction TB
        subgraph Azure["Azure"]
            ACA["Container Apps"]
            AKS["AKS"]
            AppService["App Service"]
            Functions["Functions"]
        end
        subgraph AWS["AWS"]
            ECS["ECS / Fargate"]
            EKS["EKS"]
            Lambda["Lambda"]
        end
        subgraph GCP["GCP"]
            CloudRun["Cloud Run"]
            GKE["GKE"]
        end
        subgraph OnPrem["On-Premises"]
            K8s["Kubernetes"]
            Docker["Docker"]
        end
    end

    %% Connections
    Clients3 --> Gateway
    Gateway --> MAFCore
    Identity3 --> Gateway
    Identity3 --> MAFCore
    Secrets3 --> MAFCore
    MAFCore -->|IChatClient| LLM
    MAFCore --> Storage3
    MAFCore -.-> Obs3

    %% Styling
    classDef clientStyle fill:#FFF3E0,stroke:#E65100,stroke-width:2px
    classDef gatewayStyle fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px
    classDef identityStyle fill:#FCE4EC,stroke:#AD1457,stroke-width:2px
    classDef secretsStyle fill:#FFF8E1,stroke:#FF6F00,stroke-width:2px
    classDef coreStyle fill:#E3F2FD,stroke:#1565C0,stroke-width:3px
    classDef llmStyle fill:#E8EAF6,stroke:#303F9F,stroke-width:2px
    classDef storageStyle fill:#E0F2F1,stroke:#00695C,stroke-width:2px
    classDef obsStyle fill:#FFF8E1,stroke:#FF6F00,stroke-width:2px
    classDef deployStyle fill:#ECEFF1,stroke:#455A64,stroke-width:2px

    class Clients3 clientStyle
    class Gateway gatewayStyle
    class Identity3 identityStyle
    class Secrets3 secretsStyle
    class MAFCore coreStyle
    class LLM llmStyle
    class Storage3 storageStyle
    class Obs3 obsStyle
    class Deploy deployStyle
```

### V3 Pluggable Interface Architecture

```mermaid
classDiagram
    class IApiGateway {
        <<interface>>
        +ValidateToken(token) bool
        +ApplyRateLimit(request) bool
        +RouteRequest(request) Response
    }
    
    class IIdentityProvider {
        <<interface>>
        +Authenticate(credentials) Token
        +ValidateToken(token) Claims
        +GetUserClaims(token) UserClaims
    }
    
    class ISecretsProvider {
        <<interface>>
        +GetSecret(key) string
        +SetSecret(key, value) bool
        +RotateSecret(key) bool
    }
    
    class IChatClient {
        <<interface>>
        +SendMessage(messages) Response
        +StreamResponse(messages) Stream
        +GetEmbeddings(text) Vector
    }
    
    class IStorageProvider {
        <<interface>>
        +Store(key, data) bool
        +Retrieve(key) Data
        +Delete(key) bool
    }
    
    class IObservabilityProvider {
        <<interface>>
        +LogTrace(span) void
        +LogMetric(metric) void
        +LogEvent(event) void
    }

    %% Azure Implementations
    class AzureAPIM {
        +ValidateToken()
        +ApplyRateLimit()
        +RouteRequest()
    }
    
    class AzureEntraID {
        +Authenticate()
        +ValidateToken()
        +GetUserClaims()
    }
    
    class AzureKeyVault {
        +GetSecret()
        +SetSecret()
        +RotateSecret()
    }
    
    class AzureOpenAIClient {
        +SendMessage()
        +StreamResponse()
        +GetEmbeddings()
    }
    
    class CosmosDBProvider {
        +Store()
        +Retrieve()
        +Delete()
    }
    
    class AzureMonitorProvider {
        +LogTrace()
        +LogMetric()
        +LogEvent()
    }

    %% AWS Implementations
    class AWSAPIGateway {
        +ValidateToken()
        +ApplyRateLimit()
        +RouteRequest()
    }
    
    class AWSCognito {
        +Authenticate()
        +ValidateToken()
        +GetUserClaims()
    }
    
    class AWSSecretsManager {
        +GetSecret()
        +SetSecret()
        +RotateSecret()
    }
    
    class BedrockClient {
        +SendMessage()
        +StreamResponse()
        +GetEmbeddings()
    }
    
    class DynamoDBProvider {
        +Store()
        +Retrieve()
        +Delete()
    }

    %% Open Source Implementations
    class KongGateway {
        +ValidateToken()
        +ApplyRateLimit()
        +RouteRequest()
    }
    
    class KeycloakProvider {
        +Authenticate()
        +ValidateToken()
        +GetUserClaims()
    }
    
    class HashiCorpVault {
        +GetSecret()
        +SetSecret()
        +RotateSecret()
    }
    
    class OllamaClient {
        +SendMessage()
        +StreamResponse()
        +GetEmbeddings()
    }

    IApiGateway <|.. AzureAPIM
    IApiGateway <|.. AWSAPIGateway
    IApiGateway <|.. KongGateway
    
    IIdentityProvider <|.. AzureEntraID
    IIdentityProvider <|.. AWSCognito
    IIdentityProvider <|.. KeycloakProvider
    
    ISecretsProvider <|.. AzureKeyVault
    ISecretsProvider <|.. AWSSecretsManager
    ISecretsProvider <|.. HashiCorpVault
    
    IChatClient <|.. AzureOpenAIClient
    IChatClient <|.. BedrockClient
    IChatClient <|.. OllamaClient
    
    IStorageProvider <|.. CosmosDBProvider
    IStorageProvider <|.. DynamoDBProvider
```

### V3 Configuration-Driven Deployment

```mermaid
flowchart LR
    subgraph Config["⚙️ settings.py"]
        direction TB
        GW_TYPE["API_GATEWAY_TYPE"]
        ID_PROVIDER["IDENTITY_PROVIDER"]
        SECRETS_PROVIDER["SECRETS_PROVIDER"]
        LLM_PROVIDER["LLM_PROVIDER"]
        STORAGE_PROVIDER["STORAGE_PROVIDER"]
        OBS_BACKEND["OBSERVABILITY_BACKEND"]
    end

    subgraph Azure["Azure Deployment"]
        AzAPIM["Azure APIM"]
        AzEntra["Entra ID"]
        AzKV["Key Vault"]
        AzOpenAI["Azure OpenAI"]
        AzCosmos["Cosmos DB"]
        AzMon["Azure Monitor"]
    end

    subgraph AWS["AWS Deployment"]
        AWSAPI["API Gateway"]
        AWSCog["Cognito"]
        AWSSec["Secrets Manager"]
        AWSBed["Bedrock"]
        AWSDyn["DynamoDB"]
        AWSCloud["CloudWatch"]
    end

    subgraph Hybrid["Hybrid/On-Prem"]
        Kong2["Kong"]
        KC["Keycloak"]
        HV["HashiCorp Vault"]
        Ollama2["Ollama"]
        Mongo["MongoDB"]
        Prom["Prometheus"]
    end

    Config -->|"azure"| Azure
    Config -->|"aws"| AWS
    Config -->|"hybrid"| Hybrid

    style Config fill:#FFF9C4,stroke:#F9A825,stroke-width:2px
    style Azure fill:#E3F2FD,stroke:#1565C0,stroke-width:2px
    style AWS fill:#FFF3E0,stroke:#FF6F00,stroke-width:2px
    style Hybrid fill:#E0F2F1,stroke:#00695C,stroke-width:2px
```

---

## Architecture Comparison

```mermaid
graph TB
    subgraph V1["V1: Azure-Native"]
        V1A["Full Azure Integration"]
        V1B["Tight Coupling"]
        V1C["Maximum Azure Features"]
        V1D["Enterprise Ready"]
    end

    subgraph V2["V2: APIM-Centric"]
        V2A["APIM as Central Hub"]
        V2B["Simplified Backend"]
        V2C["Response Caching"]
        V2D["AI Gateway Features"]
    end

    subgraph V3["V3: Cloud-Agnostic"]
        V3A["Pluggable Components"]
        V3B["Multi-Cloud Support"]
        V3C["No Vendor Lock-in"]
        V3D["Interface-Based Design"]
    end

    V1 -->|"Add Caching &<br/>Centralize Security"| V2
    V2 -->|"Abstract to<br/>Interfaces"| V3

    style V1 fill:#E3F2FD,stroke:#1565C0,stroke-width:2px
    style V2 fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px
    style V3 fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
```

---

## Quick Reference

| Version | Best For | Key Feature | Trade-off |
|---------|----------|-------------|-----------|
| **V1** | Azure-first enterprises | Full Azure ecosystem | Azure lock-in |
| **V2** | High-traffic applications | Caching & AI Gateway | More APIM config |
| **V3** | Multi-cloud / Hybrid | Portability | More abstraction code |
