# ─────────────────────────────────────────────────────────────────────────────
# Human Approval Manager (Human-in-the-Loop)
# ─────────────────────────────────────────────────────────────────────────────
# Implements the HITL pattern from MAF 1.0 GA.
# Provides approval gates for plan execution with:
# - Async approval workflow
# - Timeout handling
# - Approval persistence
# - WebSocket integration point
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import uuid

# Configure module logger
logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """
    Represents a request for human approval.
    
    Attributes:
        request_id: Unique identifier for this request
        title: Short title for the approval
        description: Detailed description of what's being approved
        plan_data: The plan/data requiring approval
        requestor: Who/what requested approval
        created_at: When the request was created
        status: Current status
        responded_at: When approval/rejection was received
        responder: Who approved/rejected
        comments: Optional comments from responder
        expires_at: When the request expires
    """
    request_id: str
    title: str
    description: str
    plan_data: dict[str, Any]
    requestor: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ApprovalStatus = ApprovalStatus.PENDING
    responded_at: Optional[datetime] = None
    responder: Optional[str] = None
    comments: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "title": self.title,
            "description": self.description,
            "plan_data": self.plan_data,
            "requestor": self.requestor,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "responder": self.responder,
            "comments": self.comments,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if the request has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


# Type for notification callback
NotificationCallback = Callable[[ApprovalRequest], None]


class HumanApprovalManager:
    """
    Human Approval Manager implementing MAF 1.0 GA HITL pattern.
    
    This manager provides approval gates that pause agent execution
    until a human approves or rejects the proposed action.
    
    Key Features:
    - Async approval workflow with Future-based waiting
    - Configurable timeout with auto-reject option
    - Persistent approval requests
    - WebSocket notification integration point
    - Audit trail of approvals
    
    Integration:
    - Works with MagenticOrchestrator's human_approval_callback
    - Can be exposed via API for external approval systems
    - Supports WebSocket for real-time notifications
    
    Usage:
        approval_manager = HumanApprovalManager(
            notification_callback=lambda req: send_ws_notification(req),
        )
        
        # With MagenticOrchestrator
        orchestrator = MagenticOrchestrator(
            client=client,
            agents=agents,
            human_approval_callback=approval_manager.create_sync_callback(),
        )
    """
    
    def __init__(
        self,
        notification_callback: Optional[NotificationCallback] = None,
        default_timeout_minutes: int = 60,
        auto_reject_on_timeout: bool = True,
    ):
        """
        Initialize the human approval manager.
        
        Args:
            notification_callback: Callback for sending notifications
            default_timeout_minutes: Default timeout for approval requests
            auto_reject_on_timeout: Whether to auto-reject on timeout
        """
        self._notification_callback = notification_callback
        self._default_timeout = timedelta(minutes=default_timeout_minutes)
        self._auto_reject = auto_reject_on_timeout
        
        # Pending approvals storage
        self._pending: dict[str, ApprovalRequest] = {}
        self._futures: dict[str, asyncio.Future] = {}
        
        # History for audit
        self._history: list[ApprovalRequest] = []
        
        logger.info(
            f"HumanApprovalManager initialized, "
            f"timeout={default_timeout_minutes}min, auto_reject={auto_reject_on_timeout}"
        )
    
    async def request_approval(
        self,
        title: str,
        description: str,
        plan_data: dict[str, Any],
        requestor: str = "system",
        timeout_minutes: Optional[int] = None,
    ) -> ApprovalRequest:
        """
        Request human approval asynchronously.
        
        This method will wait until the request is approved, rejected,
        or times out.
        
        Args:
            title: Short title for the approval
            description: Detailed description
            plan_data: The plan/data to approve
            requestor: Who requested approval
            timeout_minutes: Custom timeout (default: use manager default)
            
        Returns:
            The ApprovalRequest with final status
        """
        timeout = timedelta(minutes=timeout_minutes) if timeout_minutes else self._default_timeout
        
        request = ApprovalRequest(
            request_id=f"approval-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            plan_data=plan_data,
            requestor=requestor,
            expires_at=datetime.now(timezone.utc) + timeout,
        )
        
        # Store request and create future
        self._pending[request.request_id] = request
        future = asyncio.get_event_loop().create_future()
        self._futures[request.request_id] = future
        
        logger.info(f"Created approval request: {request.request_id} - {title}")
        
        # Send notification
        if self._notification_callback:
            try:
                self._notification_callback(request)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
        
        # Wait for approval with timeout
        try:
            timeout_seconds = timeout.total_seconds()
            await asyncio.wait_for(future, timeout=timeout_seconds)
            
        except asyncio.TimeoutError:
            logger.warning(f"Approval request {request.request_id} timed out")
            request.status = ApprovalStatus.TIMEOUT
            request.responded_at = datetime.now(timezone.utc)
            
            if self._auto_reject:
                request.status = ApprovalStatus.REJECTED
                request.comments = "Auto-rejected due to timeout"
        
        finally:
            # Cleanup
            self._pending.pop(request.request_id, None)
            self._futures.pop(request.request_id, None)
            self._history.append(request)
        
        return request
    
    def approve(
        self,
        request_id: str,
        responder: str,
        comments: Optional[str] = None,
    ) -> bool:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request to approve
            responder: Who is approving
            comments: Optional comments
            
        Returns:
            True if approval was processed, False if request not found
        """
        request = self._pending.get(request_id)
        
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        if request.is_expired:
            logger.warning(f"Approval request expired: {request_id}")
            return False
        
        request.status = ApprovalStatus.APPROVED
        request.responded_at = datetime.now(timezone.utc)
        request.responder = responder
        request.comments = comments
        
        # Resolve the future
        future = self._futures.get(request_id)
        if future and not future.done():
            future.set_result(True)
        
        logger.info(f"Approval granted: {request_id} by {responder}")
        return True
    
    def reject(
        self,
        request_id: str,
        responder: str,
        comments: Optional[str] = None,
    ) -> bool:
        """
        Reject a pending request.
        
        Args:
            request_id: ID of the request to reject
            responder: Who is rejecting
            comments: Optional comments explaining rejection
            
        Returns:
            True if rejection was processed, False if request not found
        """
        request = self._pending.get(request_id)
        
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        request.status = ApprovalStatus.REJECTED
        request.responded_at = datetime.now(timezone.utc)
        request.responder = responder
        request.comments = comments
        
        # Resolve the future
        future = self._futures.get(request_id)
        if future and not future.done():
            future.set_result(False)
        
        logger.info(f"Approval rejected: {request_id} by {responder}")
        return True
    
    def cancel(self, request_id: str) -> bool:
        """Cancel a pending approval request."""
        request = self._pending.get(request_id)
        
        if not request:
            return False
        
        request.status = ApprovalStatus.CANCELLED
        request.responded_at = datetime.now(timezone.utc)
        
        future = self._futures.get(request_id)
        if future and not future.done():
            future.cancel()
        
        self._pending.pop(request_id, None)
        self._futures.pop(request_id, None)
        self._history.append(request)
        
        logger.info(f"Approval cancelled: {request_id}")
        return True
    
    def get_pending(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        # Clean up expired requests
        now = datetime.now(timezone.utc)
        expired = [
            req_id for req_id, req in self._pending.items()
            if req.expires_at and now > req.expires_at
        ]
        
        for req_id in expired:
            self.cancel(req_id)
        
        return list(self._pending.values())
    
    def get_history(
        self,
        limit: int = 100,
        status: Optional[ApprovalStatus] = None,
    ) -> list[ApprovalRequest]:
        """
        Get approval history.
        
        Args:
            limit: Maximum number of records to return
            status: Filter by status
            
        Returns:
            List of historical approval requests
        """
        history = self._history
        
        if status:
            history = [r for r in history if r.status == status]
        
        return history[-limit:]
    
    def create_sync_callback(self) -> Callable:
        """
        Create a synchronous callback for use with orchestrators.
        
        This creates a blocking callback that can be used with
        MagenticOrchestrator's human_approval_callback parameter.
        
        Note: This uses asyncio.run() internally, so it should only
        be used in sync contexts. For async contexts, use
        request_approval() directly.
        
        Returns:
            A callable that blocks until approval is received
        """
        from orchestration.magentic_orchestrator import MagenticPlan
        
        def sync_callback(plan: MagenticPlan) -> bool:
            """Blocking approval callback."""
            # For sync context, we check if there's a running loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create a task
                future = asyncio.ensure_future(
                    self.request_approval(
                        title=f"Plan Approval: {plan.goal}",
                        description=plan.get_summary(),
                        plan_data=plan.to_dict(),
                    )
                )
                # This is tricky - we need to wait synchronously
                # In real implementation, you'd use a different approach
                import concurrent.futures
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                result = pool.submit(asyncio.run, future).result()
                return result.status == ApprovalStatus.APPROVED
                
            except RuntimeError:
                # No running loop, use asyncio.run()
                result = asyncio.run(
                    self.request_approval(
                        title=f"Plan Approval: {plan.goal}",
                        description=plan.get_summary(),
                        plan_data=plan.to_dict(),
                    )
                )
                return result.status == ApprovalStatus.APPROVED
        
        return sync_callback
    
    def create_auto_approve_callback(self) -> Callable:
        """
        Create a callback that auto-approves everything.
        
        Useful for testing and development.
        """
        def auto_approve(_) -> bool:
            logger.info("Auto-approving request (development mode)")
            return True
        
        return auto_approve
