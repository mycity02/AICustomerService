"""
工单服务
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
import uuid

from database.models import Ticket, TicketHistory, TicketStatus, TicketPriority
from schemas import TicketCreate, TicketUpdate, TicketResponse, TicketHistoryResponse


class TicketService:
    """工单服务类"""
    
    def create_ticket(
        self,
        db: Session,
        user_id: str,
        ticket_data: TicketCreate,
        session_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> TicketResponse:
        """创建工单"""
        ticket = Ticket(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            title=ticket_data.title,
            description=ticket_data.description,
            priority=TicketPriority(ticket_data.priority),
            category=ticket_data.category,
            status=TicketStatus.PENDING,
            context=context
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        return TicketResponse.model_validate(ticket)
    
    def get_ticket(
        self,
        db: Session,
        ticket_id: str,
        user_id: Optional[str] = None
    ) -> Optional[TicketResponse]:
        """获取工单详情"""
        query = select(Ticket).where(Ticket.id == ticket_id)
        
        if user_id:
            query = query.where(Ticket.user_id == user_id)
        
        result = db.execute(query)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return None
        
        return TicketResponse.model_validate(ticket)
    
    def update_ticket_status(
        self,
        db: Session,
        ticket_id: str,
        status: str,
        operator_id: str,
        comment: Optional[str] = None
    ) -> TicketResponse:
        """更新工单状态"""
        result = db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError("工单不存在")
        
        old_status = ticket.status.value
        ticket.status = TicketStatus(status)
        
        if status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        
        # 记录历史
        history = TicketHistory(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            operator_id=operator_id,
            action="status_change",
            old_value=old_status,
            new_value=status,
            comment=comment
        )
        
        db.add(history)
        db.commit()
        db.refresh(ticket)
        
        return TicketResponse.model_validate(ticket)
    
    def list_user_tickets(
        self,
        db: Session,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[TicketResponse]:
        """列出用户的工单"""
        query = select(Ticket).where(Ticket.user_id == user_id)
        
        if status:
            query = query.where(Ticket.status == TicketStatus(status))
        
        query = query.order_by(desc(Ticket.created_at)).limit(limit).offset(offset)
        
        result = db.execute(query)
        tickets = result.scalars().all()
        
        return [TicketResponse.model_validate(t) for t in tickets]
    
    def get_ticket_history(
        self,
        db: Session,
        ticket_id: str
    ) -> List[TicketHistoryResponse]:
        """获取工单历史"""
        result = db.execute(
            select(TicketHistory)
            .where(TicketHistory.ticket_id == ticket_id)
            .order_by(TicketHistory.created_at)
        )
        history = result.scalars().all()
        
        return [TicketHistoryResponse.model_validate(h) for h in history]
