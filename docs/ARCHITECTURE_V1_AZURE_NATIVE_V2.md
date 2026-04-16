# Architecture V1: Azure-Native with Microsoft Foundry (2026)

> **Version 2.0** - Updated April 2026 for Microsoft Foundry GA and MAF 1.0 GA
> 
> This document describes the complete Azure-native architecture for the Multi-Agent Framework (MAF) 1.0 GA, integrated with Microsoft Foundry's latest capabilities including Model Catalog, Tool Catalog, Workflow orchestration, and comprehensive Observability features.

---

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        DEPLOYMENT TARGETS                                                    │
│  ┌─────────────────────────────────────────────┐  ┌─────────────────────────────────────────────┐           │
│  │              AZURE CLOUD                    │  │              ON-PREMISES                    │           │
│  │  ┌─────────────┐ ┌─────────────┐           │  │  ┌─────────────┐ ┌─────────────┐           │           │
│  │  │ Container   │ │ Azure       │           │  │  │ Docker      │ │ Kubernetes  │           │           │
│  │  │ Apps        │ │ Functions   │           │  │  │ Containers  │ │ (K8s)       │           │           │
│  │  └─────────────┘ └─────────────┘           │  │  └─────────────┘ └─────────────┘           │           │
│  │  ┌─────────────┐ ┌─────────────┐           │  │  ┌─────────────┐ ┌─────────────┐           │           │
│  │  │ Azure       │ │ App         │           │  │  │ VM / Bare   │ │ Azure Arc   │           │           │
│  │  │ Kubernetes  │ │ Service     │           │  │  │ Metal       │ │ (Hybrid)    │           │           │
│  │  └─────────────┘ └─────────────┘           │  │  └─────────────┘ └─────────────┘           │           │
│  └─────────────────────────────────────────────┘  └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ External Client Applications                                                              │           │
│     │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │           │
│     │ │ Web Apps    │ │ Mobile Apps │ │ CLI Tools   │ │ Power Apps  │ │ Teams Bots  │          │           │
│     │ │ (React/Vue) │ │ (iOS/And)   │ │ (Python)    │ │ (Low-code)  │ │ (Copilot)   │          │           │
│     │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        │ HTTPS/TLS 1.3
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ Azure API Management (APIM) - AI Gateway                                                  │           │
│     │ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐ ┌──────────────────┐│           │
│     │ │ 2a. Traffic Manager│ │ 2b. Rate Limiting  │ │ 2c. Request Valid. │ │ 2d. AI Gateway   ││           │
│     │ │ • Load balancing   │ │ • Per-user quotas  │ │ • Schema validation│ │ • Token limits   ││           │
│     │ │ • URL routing      │ │ • Throttling       │ │ • Input sanitize   │ │ • Semantic cache ││           │
│     │ │ • Health checks    │ │ • Burst protection │ │ • Size limits      │ │ • Content safety ││           │
│     │ └────────────────────┘ └────────────────────┘ └────────────────────┘ └──────────────────┘│           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                          ┌─────────────────────────────┼─────────────────────────────┐
                          │                             │                             │
                          ▼                             ▼                             ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────────────┐
│  3. ┌─────────────────────────────┐ │ │  4. ┌─────────────────────┐ │ │  5. ┌─────────────────────────────┐ │
│     │ Azure Entra ID              │ │ │     │ Azure Key Vault     │ │ │     │ Azure App Configuration    │ │
│     │ ┌─────────────────────────┐ │ │ │     │ ┌─────────────────┐ │ │ │     │ ┌─────────────────────────┐ │ │
│     │ │ • OAuth2 / OIDC         │ │ │ │     │ │ • API Keys      │ │ │ │     │ │ • Feature Flags         │ │ │
│     │ │ • JWT Token Validation  │ │ │ │     │ │ • Connection Str│ │ │ │     │ │ • Agent Configuration   │ │ │
│     │ │ • RBAC Role Assignment  │ │ │ │     │ │ • Certificates  │ │ │ │     │ │ • Model Routing Rules   │ │ │
│     │ │ • Managed Identity      │ │ │ │     │ │ • Managed Access│ │ │ │     │ │ • Dynamic Settings      │ │ │
│     │ │ • Conditional Access    │ │ │ │     │ └─────────────────┘ │ │ │     │ └─────────────────────────┘ │ │
│     │ │ • Workload Identity     │ │ │ │     └─────────────────────┘ │ │     └─────────────────────────────┘ │
│     │ └─────────────────────────┘ │ │ └─────────────────────────────┘ └─────────────────────────────────────┘
│     └─────────────────────────────┘ │
└─────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  6. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ MAF 1.0 GA - Orchestration Layer (Magentic-One)                                           │           │
│     │ ┌────────────────────────────┐ ┌──────────────────────────┐ ┌────────────────────────────┐│           │
│     │ │ 6a. Session Manager        │ │ 6b. LLM Planner          │ │ 6c. Context Builder        ││           │
│     │ │ • Conversation tracking    │ │ • Task-Ledger creation   │ │ • Memory retrieval         ││           │
│     │ │ • State persistence        │ │ • Multi-step planning    │ │ • RAG integration          ││           │
│     │ │ • User context binding     │ │ • Dependency resolution  │ │ • Skills loading           ││           │
│     │ └────────────────────────────┘ └──────────────────────────┘ └────────────────────────────┘│           │
│     │ ┌────────────────────────────┐ ┌──────────────────────────┐ ┌────────────────────────────┐│           │
│     │ │ 6d. Agent Router           │ │ 6e. Parallel Executor    │ │ 6f. Human Approval         ││           │
│     │ │ • Task distribution        │ │ • Concurrent execution   │ │ • HITL workflow            ││           │
│     │ │ • Agent selection          │ │ • Result aggregation     │ │ • Approval queues          ││           │
│     │ │ • Load balancing           │ │ • Error handling         │ │ • Notification (Teams)     ││           │
│     │ └────────────────────────────┘ └──────────────────────────┘ └────────────────────────────┘│           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  7. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ MAF Agent Layer                                                                           │           │
│     │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │           │
│     │ │ MerchPlanner     │ │ SpacePlanner     │ │ CampaignAnalyst  │ │ ProductsFinder   │      │           │
│     │ │ • Inventory      │ │ • Store layout   │ │ • Marketing      │ │ • Product search │      │           │
│     │ │ • Sales forecast │ │ • Planograms     │ │ • Weather impact │ │ • Recommendations│      │           │
│     │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘      │           │
│     │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │           │
│     │ │ LoyaltyAgent     │ │ CommercialSales  │ │ CustomAgent      │ │ A2A RemoteAgent  │      │           │
│     │ │ • Customer data  │ │ • B2B sales      │ │ • User-defined   │ │ • External agents│      │           │
│     │ │ • Rewards        │ │ • Contracts      │ │ • Plugin support │ │ • Cross-org call │      │           │
│     │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘      │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  8. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ Microsoft Foundry (2026) - AI Platform                                                    │           │
│     │                                                                                           │           │
│     │ ┌─────────────────────────────────────────────────────────────────────────────────────┐  │           │
│     │ │                        MODEL CATALOG (1,900+ Models)                                 │  │           │
│     │ │ ┌─────────────────────────────────────────────────────────────────────────────────┐ │  │           │
│     │ │ │ AZURE DIRECT MODELS (Microsoft Hosted with SLA)                                 │ │  │           │
│     │ │ │ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐          │ │  │           │
│     │ │ │ │Azure OpenAI│ │ DeepSeek  │ │ Meta Llama│ │ Mistral   │ │ Cohere    │          │ │  │           │
│     │ │ │ │• GPT-4o    │ │• R1       │ │• Llama 3.x│ │• Large    │ │• Command  │          │ │  │           │
│     │ │ │ │• GPT-4.1   │ │• V3       │ │• Llama 4  │ │• Medium   │ │• Embed    │          │ │  │           │
│     │ │ │ │• o1/o3     │ │           │ │           │ │• Nemo     │ │• Rerank   │          │ │  │           │
│     │ │ │ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘          │ │  │           │
│     │ │ └─────────────────────────────────────────────────────────────────────────────────┘ │  │           │
│     │ │ ┌─────────────────────────────────────────────────────────────────────────────────┐ │  │           │
│     │ │ │ PARTNER & COMMUNITY MODELS (Third-Party via Marketplace)                        │ │  │           │
│     │ │ │ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐          │ │  │           │
│     │ │ │ │ Anthropic │ │HuggingFace│ │ NVIDIA    │ │ Custom    │ │ Fine-tuned│          │ │  │           │
│     │ │ │ │• Claude 3.5│ │• 100s of  │ │• NeMo     │ │• BYOM     │ │• LoRA     │          │ │  │           │
│     │ │ │ │• Claude 4  │ │  models   │ │• Megatron │ │• Import   │ │• QLoRA    │          │ │  │           │
│     │ │ │ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘          │ │  │           │
│     │ │ └─────────────────────────────────────────────────────────────────────────────────┘ │  │           │
│     │ └─────────────────────────────────────────────────────────────────────────────────────┘  │           │
│     │                                                                                           │           │
│     │ ┌───────────────────────────────────┐ ┌───────────────────────────────────┐              │           │
│     │ │ TOOL CATALOG (1,400+ Tools)       │ │ WORKFLOW ORCHESTRATION            │              │           │
│     │ │ ┌─────────────────────────────┐   │ │ ┌─────────────────────────────┐   │              │           │
│     │ │ │ Built-in Tools:             │   │ │ │ • Responses API (Agents v2) │   │              │           │
│     │ │ │ • Web Search (Bing)         │   │ │ │ • Multi-agent Workflows     │   │              │           │
│     │ │ │ • Code Interpreter          │   │ │ │ • Sequential/Parallel Exec  │   │              │           │
│     │ │ │ • File Search               │   │ │ │ • Human-in-the-Loop         │   │              │           │
│     │ │ │ • Azure AI Search           │   │ │ │ • Conditional Branching     │   │              │           │
│     │ │ │ • Azure Functions           │   │ │ │ • Error Recovery            │   │              │           │
│     │ │ │ • SharePoint                │   │ │ └─────────────────────────────┘   │              │           │
│     │ │ │ • Microsoft Fabric          │   │ └───────────────────────────────────┘              │           │
│     │ │ │ • Browser Automation        │   │                                                    │           │
│     │ │ │ • Image Generation          │   │ ┌───────────────────────────────────┐              │           │
│     │ │ │ • Computer Use (preview)    │   │ │ FOUNDRY IQ & MEMORY               │              │           │
│     │ │ └─────────────────────────────┘   │ │ ┌─────────────────────────────┐   │              │           │
│     │ │ ┌─────────────────────────────┐   │ │ │ • Intelligent Model Routing │   │              │           │
│     │ │ │ Custom Tools:               │   │ │ │ • Cost Optimization         │   │              │           │
│     │ │ │ • MCP Servers (Protocol)    │   │ │ │ • Query Analysis            │   │              │           │
│     │ │ │ • OpenAPI (REST Spec)       │   │ │ │ • Auto-Scaling              │   │              │           │
│     │ │ │ • A2A (Agent-to-Agent)      │   │ │ │ • Context Management        │   │              │           │
│     │ │ │ • Function Calling          │   │ │ │ • Session State (Redis)     │   │              │           │
│     │ │ └─────────────────────────────┘   │ │ │ • RAG (AI Search)           │   │              │           │
│     │ └───────────────────────────────────┘ │ └─────────────────────────────┘   │              │           │
│     │                                       └───────────────────────────────────┘              │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  9. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ TOOLS LAYER (Extensibility)                                                               │           │
│     │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │           │
│     │ │ Azure Logic Apps │ │ Azure Functions  │ │ API Endpoints    │ │ MCP Servers      │      │           │
│     │ │ • Workflow       │ │ • Serverless     │ │ • REST APIs      │ │ • Snowflake      │      │           │
│     │ │   orchestration  │ │ • Event-driven   │ │ • GraphQL        │ │ • Salesforce     │      │           │
│     │ │ • 1000+ connectors│ │ • Custom code   │ │ • gRPC           │ │ • Weather        │      │           │
│     │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘      │           │
│     │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │           │
│     │ │ APIM Callbacks   │ │ A2A Remote Agents│ │ OpenAPI Tools    │ │ Private Catalog  │      │           │
│     │ │ • Gateway trigger│ │ • Cross-org call │ │ • Spec-based     │ │ • Org-specific   │      │           │
│     │ │ • Webhooks       │ │ • Federated      │ │ • Auto-discovery │ │ • Curated tools  │      │           │
│     │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘      │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 10. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ Knowledge Layer                                                                           │           │
│     │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │           │
│     │ │ Azure AI Search  │ │ Azure Cosmos DB  │ │ Azure Redis Cache│ │ Azure Blob       │      │           │
│     │ │ • Vector search  │ │ • Session state  │ │ • Memory cache   │ │ • Document store │      │           │
│     │ │ • Semantic rank  │ │ • Conversation   │ │ • Hot data       │ │ • File storage   │      │           │
│     │ │ • Hybrid search  │ │ • User profiles  │ │ • Fast retrieval │ │ • Skill files    │      │           │
│     │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘      │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 11. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ EXTERNAL AI PLATFORM INTEGRATIONS                                                         │           │
│     │                                                                                           │           │
│     │ ┌───────────────────────────────────────────────────────────────────────────────────────┐ │           │
│     │ │                           CONNECTION METHODS                                           │ │           │
│     │ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │ │           │
│     │ │ │ MCP Protocol    │ │ OpenAPI Tool    │ │ A2A Protocol    │ │ Direct API/SDK  │      │ │           │
│     │ │ │ (Standardized)  │ │ (REST Spec)     │ │ (Agent-to-Agent)│ │ (Custom)        │      │ │           │
│     │ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘      │ │           │
│     │ └───────────────────────────────────────────────────────────────────────────────────────┘ │           │
│     │                                           │                                               │           │
│     │                                           ▼                                               │           │
│     │ ┌───────────────────────────────────────────────────────────────────────────────────────┐ │           │
│     │ │                           EXTERNAL PLATFORMS                                           │ │           │
│     │ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │ │           │
│     │ │ │ Google Vertex AI│ │ AWS Bedrock     │ │ Custom LLMs     │ │ On-Prem Models  │      │ │           │
│     │ │ │ • Gemini Pro    │ │ • Claude (AWS)  │ │ • Self-hosted   │ │ • Ollama        │      │ │           │
│     │ │ │ • Gemini Ultra  │ │ • Titan         │ │ • vLLM          │ │ • LM Studio     │      │ │           │
│     │ │ │ • PaLM          │ │ • Llama (AWS)   │ │ • TGI           │ │ • LocalAI       │      │ │           │
│     │ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘      │ │           │
│     │ └───────────────────────────────────────────────────────────────────────────────────────┘ │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 12. ┌───────────────────────────────────────────────────────────────────────────────────────────┐           │
│     │ OBSERVABILITY & COMPLIANCE LAYER (Microsoft Foundry)                                      │           │
│     │                                                                                           │           │
│     │ ┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐      │           │
│     │ │         EVALUATION                    │ │         MONITORING                    │      │           │
│     │ │ • Built-in Evaluators:                │ │ • Azure Monitor Integration           │      │           │
│     │ │   - Quality (coherence, fluency)      │ │ • Application Insights                │      │           │
│     │ │   - RAG (groundedness, relevance)     │ │ • Real-time Dashboards                │      │           │
│     │ │   - Safety (hate, violence)           │ │ • Token Consumption Metrics           │      │           │
│     │ │   - Agent (tool accuracy, completion) │ │ • Latency & Error Rates               │      │           │
│     │ │ • Custom Evaluators (Python SDK)      │ │ • Quality Score Tracking              │      │           │
│     │ │ • Model Benchmarking & Comparison     │ │ • Cost Analytics                      │      │           │
│     │ │ • A/B Testing Support                 │ │ • Alerts & Notifications              │      │           │
│     │ └───────────────────────────────────────┘ └───────────────────────────────────────┘      │           │
│     │                                                                                           │           │
│     │ ┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐      │           │
│     │ │         TRACING                       │ │         RED TEAMING & SAFETY          │      │           │
│     │ │ • OpenTelemetry Standard              │ │ • AI Red Teaming Agent (PyRIT)        │      │           │
│     │ │ • Distributed Trace Capture           │ │ • Jailbreak Detection                 │      │           │
│     │ │ • LLM Call Visualization              │ │ • Prompt Injection Testing            │      │           │
│     │ │ • Tool Invocation Tracking            │ │ • Content Safety Filters              │      │           │
│     │ │ • Agent Decision Paths                │ │ • Protected Materials Detection       │      │           │
│     │ │ • Multi-step Reasoning Chains         │ │ • Adversarial Testing                 │      │           │
│     │ │ • Framework Support:                  │ │ • Scheduled Security Probes           │      │           │
│     │ │   - LangChain, Semantic Kernel        │ │ • Compliance Reporting                │      │           │
│     │ │   - OpenAI Agents SDK, AutoGen        │ │   (SOC 2, ISO 27001, HIPAA)           │      │           │
│     │ └───────────────────────────────────────┘ └───────────────────────────────────────┘      │           │
│     │                                                                                           │           │
│     │ ┌─────────────────────────────────────────────────────────────────────────────────────┐  │           │
│     │ │         LOG ANALYTICS & AUDIT                                                        │  │           │
│     │ │ • Log Analytics Workspace              • KQL Query Support                           │  │           │
│     │ │ • Audit Trail (all operations)         • Workbooks & Dashboards                      │  │           │
│     │ │ • Data Retention Policies              • Export to SIEM                              │  │           │
│     │ └─────────────────────────────────────────────────────────────────────────────────────┘  │           │
│     └───────────────────────────────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Summary

| # | Component | Purpose | Key Features |
|---|-----------|---------|--------------|
| **0** | Deployment Targets | Runtime environments | Azure (Container Apps, Functions, AKS) + On-prem (Docker, K8s) |
| **1** | External Clients | User interfaces | Web, Mobile, CLI, Power Apps, Teams |
| **2** | Azure APIM | API Gateway + AI Gateway | Rate limiting, validation, AI features |
| **3** | Azure Entra ID | Authentication | OAuth2, OIDC, RBAC, Managed Identity |
| **4** | Azure Key Vault | Secrets management | API keys, connection strings, certificates |
| **5** | App Configuration | Dynamic config | Feature flags, model routing, settings |
| **6** | MAF Orchestration | Agent coordination | Magentic-One, planning, routing |
| **7** | MAF Agent Layer | Specialized agents | Retail domain agents, custom agents |
| **8** | Microsoft Foundry | AI Platform | Model Catalog, Tool Catalog, Workflow, IQ |
| **9** | Tools Layer | Extensibility | Logic Apps, Functions, MCP, APIs |
| **10** | Knowledge Layer | Data persistence | AI Search, Cosmos DB, Redis, Blob |
| **11** | External AI | Multi-cloud | Vertex AI, Bedrock, Custom LLMs |
| **12** | Observability | Monitoring & Compliance | Evaluation, Tracing, Red Teaming |

---

## Detailed Request Flow

### Step 1: External Client Request
**Component:** Client Applications

A user initiates a request from any client application (web app, mobile, CLI, Teams bot):

```json
POST https://api.company.com/maf/v1/agents/invoke
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Content-Type: application/json

{
  "agent_name": "MerchPlanner",
  "input": "Analyze paint category sell-through rate for Q4",
  "conversation_id": "conv-abc123",
  "goal": "Analyze paint category sell-through rate for Q4",
  "orchestration_type": "magentic",
  "require_approval": false,
  "model_preference": "auto"  // or "gpt-4o", "claude-3.5", "deepseek-r1"
}
```

---

### Step 2: API Management - Traffic Processing
**Component:** Azure API Management (APIM) with AI Gateway

**What Happens:**
1. **2a. Traffic Manager** receives the inbound request
   - Routes to correct backend based on URL path
   - Load balances across multiple instances if configured

2. **2b. Rate Limiting** checks quota
   - Per-user rate limits (e.g., 100 requests/minute)
   - Per-subscription quotas (e.g., 10,000 requests/day)
   - Token-based limits for AI requests
   - Returns `429 Too Many Requests` if exceeded

3. **2c. Request Validation** ensures schema compliance
   - Validates JSON structure against OpenAPI schema
   - Checks required fields are present
   - Returns `400 Bad Request` if invalid

4. **2d. AI Gateway Features** (New in 2026)
   - Token limit enforcement
   - Semantic caching for repeated queries
   - Content safety pre-screening
   - Load balancing across model endpoints

---

### Step 3: OAuth2 Token Extraction
**Component:** Azure API Management (APIM)

**What Happens:**
1. APIM extracts the `Authorization: Bearer <token>` header
2. Validates token format (must be valid JWT)
3. Passes token to Entra ID for validation

**APIM Policy (Inbound):**
```xml
<inbound>
    <validate-jwt header-name="Authorization" 
                  failed-validation-httpcode="401"
                  failed-validation-error-message="Unauthorized">
        <openid-config url="https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration"/>
        <audiences>
            <audience>api://mafga-multiagent</audience>
        </audiences>
        <required-claims>
            <claim name="roles" match="any">
                <value>Agent.Invoke</value>
            </claim>
        </required-claims>
    </validate-jwt>
</inbound>
```

---

### Step 4: Authentication & Authorization
**Component:** Azure Entra ID

**What Happens:**
1. **4a. JWT Token Validation**
   - Verifies token signature using Entra ID public keys
   - Checks token expiration (`exp` claim)
   - Validates issuer (`iss` claim matches tenant)
   - Validates audience (`aud` claim matches app registration)

2. **4b. Claims Extraction**
   - Extracts user identity (`sub`, `oid`, `upn` claims)
   - Extracts roles (`roles` claim)
   - Extracts groups (`groups` claim)

3. **4c. RBAC Permission Check**
   - Matches user roles against required permissions
   - Agent-level access control:
     ```
     User Role: "Retail.Analyst" → Can access: MerchPlanner, SpacePlanner
     User Role: "Sales.Manager" → Can access: CommercialSales, CampaignAnalyst
     User Role: "Admin" → Can access: All agents
     ```

**UserContext Created:**
```python
@dataclass
class UserContext:
    user_id: str = "user-12345"
    email: str = "analyst@company.com"
    name: str = "John Doe"
    roles: list[str] = ["Retail.Analyst", "Agent.Invoke"]
    groups: list[str] = ["Retail-Team", "AU-Region"]
```

---

### Step 5: Session Manager
**Component:** MAF 1.0 GA Orchestration Layer

**What Happens:**
1. Checks if `conversation_id` exists in request
2. If exists: Loads existing session from Azure Cosmos DB
3. If not: Creates new session with unique ID
4. Initializes session state:
   ```python
   session = {
       "session_id": "sess-xyz789",
       "conversation_id": "conv-abc123",
       "user_context": user_context,
       "created_at": "2026-04-16T10:30:00Z",
       "messages": [],
       "plan": None,
       "status": "active"
   }
   ```

---

### Step 6: LLM Planner (Task-Ledger Creation)
**Component:** Magentic Orchestrator

**What Happens:**
1. Retrieves conversation history from Cosmos DB
2. Loads relevant context from Azure AI Search (RAG)
3. Calls Model Catalog (multi-model selection) with planning prompt:

**Model Selection (via Foundry IQ):**
```python
# Foundry IQ automatically selects optimal model based on:
# - Task complexity
# - Cost constraints
# - Latency requirements
# - User preference

model = foundry_iq.select_model(
    task_type="planning",
    preference=request.model_preference,  # "auto", "gpt-4o", etc.
    constraints={"max_cost": 0.10, "max_latency_ms": 5000}
)
# Returns: "gpt-4o" for complex planning, "gpt-4.1-mini" for simple tasks
```

**Prompt Sent to Selected Model:**
```
You are a planning agent. Create an execution plan for this goal:
"Analyze paint category sell-through rate for Q4"

Available agents:
- MerchPlanner: Merchandise planning, inventory analysis, sales forecasting
- SpacePlanner: Store layout, planogram optimization
- CampaignAnalyst: Marketing campaigns, weather impact analysis

Output JSON plan with steps, agent assignments, and dependencies.
```

**LLM Response:**
```json
{
  "plan_id": "plan-001",
  "goal": "Analyze paint category sell-through rate for Q4",
  "steps": [
    {
      "step_id": "step_1",
      "agent_name": "MerchPlanner",
      "task": "Query Q4 paint category sales and inventory data",
      "dependencies": []
    },
    {
      "step_id": "step_2",
      "agent_name": "CampaignAnalyst", 
      "task": "Analyze promotional impact on paint sales",
      "dependencies": ["step_1"]
    }
  ]
}
```

---

### Step 7: Context Builder
**Component:** Magentic Orchestrator

**What Happens:**
1. **Load Memory**: Retrieves relevant past conversations from Redis cache
2. **Load Skills**: Reads SKILL.md files for selected agents
3. **Load Tools**: Binds Tool Catalog tools to each agent
4. **Build Context Window**:
   ```python
   context = {
       "conversation_history": [...last 10 messages...],
       "retrieved_documents": [...RAG results from AI Search...],
       "agent_skills": "# Retail Analysis Skill\n...",
       "available_tools": ["query_sales", "get_inventory", "get_weather", "web_search", "code_interpreter"]
   }
   ```

---

### Step 8: Agent Router
**Component:** Magentic Orchestrator

**What Happens:**
1. Reads the plan's first ready step
2. Selects appropriate agent based on `agent_name`
3. Routes task to selected agent
4. For parallel execution: Uses `asyncio.gather()` to run independent steps concurrently

**Routing Logic:**
```python
# Get steps with no pending dependencies
ready_steps = plan.get_ready_steps()

# Route to agents
for step in ready_steps:
    agent = agent_registry.get(step.agent_name)
    task_queue.add(agent.invoke(step.task, context))
```

---

### Step 9: Human-in-the-Loop (HITL) Approval
**Component:** Human Approval Manager (Optional)

**When Triggered:**
- `require_approval: true` in request
- Plan involves sensitive operations (e.g., price changes)
- Plan cost exceeds threshold

**What Happens:**
1. Plan is serialized and stored in Azure Service Bus queue
2. Notification sent to approver (Teams/Email)
3. System waits for approval (with timeout)
4. Approver reviews plan and approves/rejects

**Approval Workflow:**
```
┌──────────┐     ┌───────────────┐     ┌──────────────┐     ┌──────────────┐
│ Plan     │────►│ Service Bus   │────►│ Teams        │────►│ Approver     │
│ Created  │     │ Queue         │     │ Notification │     │ Reviews      │
└──────────┘     └───────────────┘     └──────────────┘     └──────────────┘
                                                                   │
     ┌─────────────────────────────────────────────────────────────┘
     ▼
┌──────────────┐     ┌───────────────┐     ┌──────────────────────────────┐
│ Approved/    │────►│ Queue         │────►│ Orchestrator Resumes         │
│ Rejected     │     │ Response      │     │ Execution                    │
└──────────────┘     └───────────────┘     └──────────────────────────────┘
```

---

### Step 10: Agent Execution
**Component:** MAF Agent Layer

**What Happens:**
1. Selected agent (e.g., MerchPlanner) receives task
2. Agent constructs prompt with system instructions + task
3. Agent invokes tools as needed via Tool Catalog (MCP, Functions, etc.)
4. Agent processes LLM response

**Example Agent Execution:**
```python
# MerchPlanner Agent
class MerchPlannerAgent(BaseRetailAgent):
    async def invoke(self, task: str, context: dict) -> AgentResponse:
        # 1. Build prompt
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": task}
        ]
        
        # 2. Call LLM via Model Catalog
        response = await self.chat_client.chat_completion(
            messages,
            model=context.get("model", "gpt-4o"),  # Multi-model support
            tools=self.available_tools
        )
        
        # 3. If LLM wants to use tool
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # Call via Tool Catalog (MCP, Functions, OpenAPI, etc.)
                tool_result = await self.tool_catalog.call_tool(
                    tool_type=tool_call.type,  # "mcp", "function", "openapi"
                    server=tool_call.server,    # "snowflake_mcp"
                    tool=tool_call.name,        # "query_sales"
                    arguments=tool_call.arguments
                )
                # Continue conversation with tool result
                messages.append({"role": "tool", "content": tool_result})
        
        # 4. Get final response
        final_response = await self.chat_client.chat_completion(messages)
        return AgentResponse(content=final_response.content)
```

---

### Step 11: LLM Inference (Model Catalog)
**Component:** Microsoft Foundry Model Catalog

**What Happens:**
1. Request routed to selected model from catalog
2. Content Safety filters check input
3. Model generates response
4. Content Safety filters check output
5. Response returned with usage metrics

**Multi-Model Configuration:**
```python
# Microsoft Foundry Model Catalog supports 1,900+ models
from azure.ai.foundry import FoundryClient

client = FoundryClient(
    endpoint="https://your-foundry.azure.com",
    credential=DefaultAzureCredential()
)

# Choose from multiple providers
response = await client.chat.completions.create(
    model="gpt-4o",              # Azure OpenAI
    # model="claude-3.5-sonnet", # Anthropic
    # model="deepseek-r1",       # DeepSeek
    # model="llama-3.1-70b",     # Meta Llama
    # model="mistral-large",     # Mistral
    messages=messages,
    tools=tool_definitions,
    temperature=0.3
)
```

---

### Step 12: Tool Execution (Tool Catalog)
**Component:** Microsoft Foundry Tool Catalog (1,400+ tools)

**What Happens:**
1. Agent requests tool execution via Tool Catalog
2. Tool Catalog routes to appropriate backend (MCP, Function, API)
3. Tool executes and returns results
4. Results returned to agent

**Built-in Tools Example:**
```python
# Web Search (Bing)
web_result = await tool_catalog.call(
    tool="web_search",
    query="paint market trends Q4 2026"
)

# Code Interpreter
code_result = await tool_catalog.call(
    tool="code_interpreter",
    code="import pandas as pd\ndf = pd.read_csv('sales.csv')\nprint(df.describe())"
)

# Azure AI Search
search_result = await tool_catalog.call(
    tool="azure_ai_search",
    query="paint category inventory levels",
    index="retail-documents"
)
```

**Custom MCP Tool Example:**
```json
// Request to MCP Server
{
  "method": "tools/call",
  "params": {
    "name": "query_sales",
    "arguments": {
      "query": "SELECT category, SUM(sales) FROM sales_data WHERE category='paint' AND quarter='Q4' GROUP BY category"
    }
  }
}

// Response
{
  "result": {
    "content": [
      {"type": "text", "text": "Paint category Q4 sales: $2.4M, Units: 45,230, Sell-through: 72%"}
    ]
  }
}
```

---

### Step 13: Result Synthesis
**Component:** Result Synthesizer

**What Happens:**
1. Collects results from all executed agent steps
2. Calls LLM to synthesize into coherent response
3. Formats final response for user

**Synthesis Prompt:**
```
You are a synthesis agent. Combine these agent results into a coherent response:

Original Goal: "Analyze paint category sell-through rate for Q4"

Agent Results:
1. [MerchPlanner]: "Paint category Q4 sales: $2.4M, 45,230 units, 72% sell-through..."
2. [CampaignAnalyst]: "Holiday promotions drove 15% increase in paint sales..."

Synthesize into a comprehensive response addressing the original goal.
```

---

### Step 14: Response to User
**Component:** API Gateway → Client

**What Happens:**
1. Final response packaged as JSON
2. Sent through APIM (outbound policies apply)
3. Response logged to Application Insights
4. Tracing data sent to OpenTelemetry
5. Evaluation metrics recorded
6. Delivered to client application

**Final Response:**
```json
{
  "status": "completed",
  "result": "**Paint Category Q4 Analysis**\n\nThe paint category achieved a 72% sell-through rate in Q4, with total sales of $2.4M across 45,230 units.\n\n**Key Findings:**\n- Holiday promotions drove a 15% increase vs Q3\n- Premium paint lines outperformed (+23% YoY)\n- Inventory levels are optimal at 4.2 weeks of supply\n\n**Recommendations:**\n- Maintain promotional cadence for Q1\n- Increase allocation for premium SKUs",
  "plan": {
    "plan_id": "plan-001",
    "steps": [...]
  },
  "conversation_id": "conv-abc123",
  "metadata": {
    "tokens_used": 1847,
    "latency_ms": 3421,
    "agents_invoked": ["MerchPlanner", "CampaignAnalyst"],
    "model_used": "gpt-4o",
    "cost_usd": 0.0147,
    "trace_id": "trace-abc123"
  }
}
```

---

## Authentication Flow Detail

```mermaid
sequenceDiagram
    participant User
    participant Client as Client App
    participant APIM as Azure APIM
    participant Entra as Azure Entra ID
    participant MAF as MAF Service
    participant KV as Key Vault
    participant Foundry as Microsoft Foundry

    User->>Client: 1. Login Request
    Client->>Entra: 2. Redirect to Entra Login
    Entra->>User: 3. Login Page
    User->>Entra: 4. Credentials
    Entra->>Entra: 5. Validate & Generate Tokens
    Entra->>Client: 6. Access Token + Refresh Token
    
    Note over Client,APIM: User makes API request
    
    Client->>APIM: 7. API Request + Bearer Token
    APIM->>APIM: 8. Rate Limit Check
    APIM->>Entra: 9. Validate JWT Token
    Entra->>APIM: 10. Token Valid + Claims
    APIM->>MAF: 11. Forward Request + User Context
    MAF->>KV: 12. Get Secrets (API Keys)
    KV->>MAF: 13. Return Secrets
    MAF->>Foundry: 14. Call Model Catalog
    Foundry->>MAF: 15. Model Response
    MAF->>APIM: 16. Response
    APIM->>Client: 17. Response
    Client->>User: 18. Display Result
```

---

## Multi-Model Architecture Flow

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Request[User Request]
    end
    
    subgraph Gateway["API Gateway"]
        APIM[Azure APIM]
    end
    
    subgraph MAF["MAF Orchestration"]
        Router[Agent Router]
        IQ[Foundry IQ]
    end
    
    subgraph Foundry["Microsoft Foundry Model Catalog"]
        direction TB
        subgraph Azure["Azure Direct Models"]
            GPT4[Azure OpenAI GPT-4o]
            DeepSeek[DeepSeek R1]
            Llama[Meta Llama 3.x]
            Mistral[Mistral Large]
        end
        subgraph Partner["Partner Models"]
            Claude[Anthropic Claude]
            Cohere[Cohere Command]
            HF[Hugging Face Models]
        end
        subgraph Custom["Custom Models"]
            BYOM[Bring Your Own Model]
            FineTuned[Fine-tuned Models]
        end
    end
    
    subgraph External["External AI Platforms"]
        Vertex[Google Vertex AI]
        Bedrock[AWS Bedrock]
        OnPrem[On-Prem LLMs]
    end
    
    Request --> APIM
    APIM --> Router
    Router --> IQ
    IQ -->|Cost Optimized| GPT4
    IQ -->|Reasoning Tasks| DeepSeek
    IQ -->|Code Generation| Claude
    IQ -->|Embeddings| Cohere
    IQ -->|Custom Domain| BYOM
    
    Router -.->|Via MCP/API| Vertex
    Router -.->|Via MCP/API| Bedrock
    Router -.->|Via MCP/API| OnPrem
    
    GPT4 --> Response[Unified Response]
    DeepSeek --> Response
    Claude --> Response
    Cohere --> Response
    BYOM --> Response
    Vertex -.-> Response
    Bedrock -.-> Response
    OnPrem -.-> Response
```

---

## Observability & Evaluation Flow

```mermaid
flowchart TB
    subgraph Runtime["Agent Runtime"]
        Agent[Agent Execution]
        Tools[Tool Calls]
        LLM[LLM Inference]
    end
    
    subgraph Tracing["Distributed Tracing"]
        OTel[OpenTelemetry SDK]
        AppInsights[Application Insights]
    end
    
    subgraph Evaluation["Evaluation Pipeline"]
        Quality[Quality Evaluators<br/>coherence, fluency]
        RAG[RAG Evaluators<br/>groundedness, relevance]
        Safety[Safety Evaluators<br/>hate, violence, PII]
        Custom[Custom Evaluators<br/>domain-specific]
    end
    
    subgraph RedTeam["Security Testing"]
        PyRIT[PyRIT Framework]
        Jailbreak[Jailbreak Detection]
        Injection[Prompt Injection Test]
    end
    
    subgraph Monitoring["Production Monitoring"]
        Dashboard[Azure Monitor Dashboard]
        Alerts[Alert Rules]
        Logs[Log Analytics]
    end
    
    Agent --> OTel
    Tools --> OTel
    LLM --> OTel
    OTel --> AppInsights
    
    Agent --> Quality
    Agent --> RAG
    Agent --> Safety
    Agent --> Custom
    
    Agent -.->|Scheduled| PyRIT
    PyRIT --> Jailbreak
    PyRIT --> Injection
    
    AppInsights --> Dashboard
    Quality --> Dashboard
    Safety --> Alerts
    Jailbreak --> Alerts
    AppInsights --> Logs
```

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Azure["Azure Cloud Deployment"]
        subgraph Compute["Compute Options"]
            ACA[Azure Container Apps<br/>Recommended for serverless]
            AKS[Azure Kubernetes Service<br/>For complex workloads]
            Functions[Azure Functions<br/>For event-driven]
            AppService[Azure App Service<br/>For web apps]
        end
        
        subgraph Data["Data Layer"]
            CosmosDB[(Cosmos DB)]
            Redis[(Redis Cache)]
            AISearch[(AI Search)]
            Blob[(Blob Storage)]
        end
        
        subgraph Security["Security"]
            EntraID[Entra ID]
            KeyVault[Key Vault]
            APIM[API Management]
        end
    end
    
    subgraph OnPrem["On-Premises Deployment"]
        Docker[Docker Containers]
        K8s[Kubernetes Cluster]
        VM[Virtual Machines]
        Arc[Azure Arc<br/>Hybrid Management]
    end
    
    subgraph Foundry["Microsoft Foundry"]
        ModelCatalog[Model Catalog]
        ToolCatalog[Tool Catalog]
        Observability[Observability]
    end
    
    ACA --> Foundry
    AKS --> Foundry
    Functions --> Foundry
    AppService --> Foundry
    
    Docker -.->|Via Arc| Foundry
    K8s -.->|Via Arc| Foundry
    Arc --> Foundry
    
    Compute --> Data
    Compute --> Security
```

---

## Security Considerations

| Layer | Security Control | Implementation |
|-------|------------------|----------------|
| **Network** | TLS 1.3 | APIM enforces HTTPS |
| **API Gateway** | Rate Limiting | APIM policies + AI Gateway token limits |
| **Authentication** | OAuth2 / OIDC | Azure Entra ID |
| **Authorization** | RBAC | Entra ID roles + Custom claims |
| **Secrets** | Managed Access | Azure Key Vault + Managed Identity |
| **Data** | Encryption at rest | Azure Storage encryption |
| **LLM Input** | Content Safety | Azure AI Content Safety (pre-screen) |
| **LLM Output** | Content Safety | Azure AI Content Safety (post-screen) |
| **Red Teaming** | Adversarial Testing | PyRIT framework, scheduled probes |
| **Audit** | Logging | Application Insights + Log Analytics |
| **Compliance** | Standards | SOC 2, ISO 27001, HIPAA, GDPR |

---

## Key Benefits of Azure-Native Architecture with Microsoft Foundry

### Enterprise Capabilities
1. **Enterprise Security**: Full Entra ID integration with MFA, Conditional Access, Managed Identity
2. **Compliance**: Azure compliance certifications (SOC 2, ISO 27001, HIPAA, GDPR)
3. **Audit Trail**: Complete logging and tracing with Application Insights and Log Analytics

### AI Platform Benefits
4. **Multi-Model Freedom**: Access to 1,900+ models from Azure OpenAI, Anthropic, Meta, Mistral, DeepSeek, and more
5. **Tool Ecosystem**: 1,400+ pre-built tools including Web Search, Code Interpreter, File Search, and custom MCP tools
6. **Intelligent Routing**: Foundry IQ automatically selects optimal model based on task, cost, and latency

### Operational Excellence
7. **Observability**: Comprehensive evaluation, monitoring, tracing, and red teaming capabilities
8. **Scalability**: Auto-scaling with Azure Container Apps, Functions, or AKS
9. **Cost Management**: Token-based billing, cost analytics, and optimization recommendations

### Flexibility
10. **Deployment Options**: Azure cloud, on-premises (Docker/K8s), or hybrid (Azure Arc)
11. **External Integration**: Connect to Vertex AI, AWS Bedrock, or custom LLMs via MCP/OpenAPI
12. **Workflow Orchestration**: Multi-agent workflows with parallel execution and human-in-the-loop

---

## Migration from V1 to V2

If you're upgrading from the original V1 architecture, here are the key changes:

| V1 (Original) | V2 (Microsoft Foundry 2026) |
|---------------|----------------------------|
| Azure OpenAI only | Model Catalog (1,900+ models) |
| Prompt Flow orchestration | Workflow (Multi-agent, Responses API) |
| Basic MCP tools | Tool Catalog (1,400+ tools) |
| Application Insights only | Full Observability (Eval, Trace, Monitor, Red Team) |
| Azure-only deployment | Azure + On-prem + Hybrid |
| Single model routing | Foundry IQ (intelligent routing) |
| Manual content safety | Integrated Content Safety + Red Teaming |

---

## References

- [Microsoft Foundry Documentation](https://learn.microsoft.com/en-us/azure/foundry/)
- [Microsoft Foundry Model Catalog](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/foundry-models-overview)
- [Foundry Agent Service Tool Catalog](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog)
- [Foundry Observability](https://learn.microsoft.com/en-us/azure/foundry/concepts/observability)
- [Microsoft Agent Framework (MAF)](https://github.com/microsoft/agent-framework)
- [Azure API Management AI Gateway](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-overview)
