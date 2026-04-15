# ─────────────────────────────────────────────────────────────────────────────
# Salesforce MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation for CRM and sales data access.
# ─────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime, timedelta

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class SalesforceMCPServer(BaseMCPServer):
    """Mock Salesforce MCP server for CRM data access."""
    
    def __init__(self):
        super().__init__(
            name="salesforce-mcp",
            version="1.0.0",
            description="Access CRM, leads, opportunities, and sales pipeline data"
        )
    
    def _register_tools(self) -> None:
        self.register_tool(MCPTool(
            name="get_opportunities",
            description="Get sales opportunities by stage, owner, or account.",
            input_schema=create_json_schema(
                properties={
                    "stage": {"type": "string", "description": "Opportunity stage filter"},
                    "owner_id": {"type": "string", "description": "Sales rep ID"},
                    "account_id": {"type": "string", "description": "Account/customer ID"},
                    "min_value": {"type": "number", "description": "Minimum opportunity value"},
                },
                required=[]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_leads",
            description="Get sales leads by status or source.",
            input_schema=create_json_schema(
                properties={
                    "status": {"type": "string", "description": "Lead status", "enum": ["New", "Contacted", "Qualified", "Unqualified"]},
                    "source": {"type": "string", "description": "Lead source"},
                },
                required=[]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_account",
            description="Get account details and contact information.",
            input_schema=create_json_schema(
                properties={
                    "account_id": {"type": "string", "description": "Account ID"},
                },
                required=["account_id"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_pipeline_summary",
            description="Get sales pipeline summary with forecasts.",
            input_schema=create_json_schema(
                properties={
                    "period": {"type": "string", "description": "Forecast period", "default": "quarter"},
                },
                required=[]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        if call.name == "get_opportunities":
            return await self._get_opportunities(call.arguments)
        elif call.name == "get_leads":
            return await self._get_leads(call.arguments)
        elif call.name == "get_account":
            return await self._get_account(call.arguments)
        elif call.name == "get_pipeline_summary":
            return await self._get_pipeline_summary(call.arguments)
        return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _get_opportunities(self, args: dict) -> MCPToolResult:
        stages = ["Prospecting", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
        stage_filter = args.get("stage")
        min_value = args.get("min_value", 0)
        
        opportunities = []
        for i in range(10):
            stage = random.choice(stages)
            if stage_filter and stage != stage_filter:
                continue
            value = round(random.uniform(10000, 500000), 2)
            if value < min_value:
                continue
            opportunities.append({
                "opportunity_id": f"OPP-{i+1:06d}",
                "name": f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} {i+1}",
                "account_name": f"Customer Corp {random.randint(1, 50)}",
                "stage": stage,
                "value": value,
                "probability_pct": random.randint(10, 90),
                "close_date": (datetime.now() + timedelta(days=random.randint(7, 90))).strftime("%Y-%m-%d"),
                "owner": f"Sales Rep {random.randint(1, 5)}",
            })
        
        return MCPToolResult.json_result({
            "opportunity_count": len(opportunities),
            "total_value": sum(o["value"] for o in opportunities),
            "opportunities": opportunities,
        })
    
    async def _get_leads(self, args: dict) -> MCPToolResult:
        status_filter = args.get("status")
        statuses = ["New", "Contacted", "Qualified", "Unqualified"]
        sources = ["Website", "Trade Show", "Referral", "Cold Call", "Marketing Campaign"]
        
        leads = []
        for i in range(8):
            status = random.choice(statuses)
            if status_filter and status != status_filter:
                continue
            leads.append({
                "lead_id": f"LEAD-{i+1:06d}",
                "company": f"Prospect Company {i+1}",
                "contact_name": f"Contact {i+1}",
                "email": f"contact{i+1}@prospect.com",
                "status": status,
                "source": random.choice(sources),
                "created_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                "score": random.randint(1, 100),
            })
        
        return MCPToolResult.json_result({
            "lead_count": len(leads),
            "leads": leads,
        })
    
    async def _get_account(self, args: dict) -> MCPToolResult:
        account_id = args.get("account_id", "ACC-001")
        
        return MCPToolResult.json_result({
            "account_id": account_id,
            "name": f"Customer Corp {account_id[-3:]}",
            "type": random.choice(["Trade", "Retail", "Commercial", "Government"]),
            "industry": random.choice(["Construction", "Manufacturing", "Retail", "Services"]),
            "annual_revenue": round(random.uniform(1000000, 50000000), 2),
            "employees": random.randint(50, 1000),
            "billing_address": "456 Business Road, Sydney NSW 2000",
            "primary_contact": {
                "name": "John Smith",
                "title": "Procurement Manager",
                "email": "john.smith@customercorp.com",
                "phone": "+61 2 8888 7777",
            },
            "account_owner": f"Account Manager {random.randint(1, 3)}",
            "lifetime_value": round(random.uniform(100000, 2000000), 2),
        })
    
    async def _get_pipeline_summary(self, args: dict) -> MCPToolResult:
        period = args.get("period", "quarter")
        
        return MCPToolResult.json_result({
            "period": period,
            "pipeline": {
                "total_value": round(random.uniform(5000000, 20000000), 2),
                "weighted_value": round(random.uniform(2000000, 8000000), 2),
                "opportunity_count": random.randint(50, 200),
                "avg_deal_size": round(random.uniform(50000, 150000), 2),
            },
            "by_stage": [
                {"stage": "Prospecting", "count": random.randint(20, 50), "value": round(random.uniform(500000, 2000000), 2)},
                {"stage": "Qualification", "count": random.randint(15, 30), "value": round(random.uniform(800000, 3000000), 2)},
                {"stage": "Proposal", "count": random.randint(10, 25), "value": round(random.uniform(1000000, 4000000), 2)},
                {"stage": "Negotiation", "count": random.randint(5, 15), "value": round(random.uniform(1500000, 5000000), 2)},
            ],
            "forecast": {
                "best_case": round(random.uniform(3000000, 8000000), 2),
                "commit": round(random.uniform(2000000, 5000000), 2),
                "closed": round(random.uniform(500000, 2000000), 2),
            },
        })
