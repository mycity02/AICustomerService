"""
消息服务
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
import uuid

from database.models import Message, MessageRole
from schemas import MessageResponse


class MessageService:
    """消息服务类"""
    
    def save_message(
        self,
        db: Session,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> MessageResponse:
        """保存消息"""
        from sqlalchemy.orm import selectinload

        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=MessageRole(role),
            content=content,
            meta=metadata
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # 重新查询以加载附件关系
        result = db.execute(
            select(Message)
            .options(selectinload(Message.attachments))
            .where(Message.id == message.id)
        )
        message = result.scalar_one()

        return MessageResponse.model_validate(message)
    
    def get_session_messages(
        self,
        db: Session,
        session_id: str,
        limit: int = 100
    ) -> List[MessageResponse]:
        """获取会话的所有消息"""
        from sqlalchemy.orm import selectinload

        result = db.execute(
            select(Message)
            .options(selectinload(Message.attachments))
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()

        return [MessageResponse.model_validate(m) for m in messages]
    
    def search_messages(
        self,
        db: Session,
        user_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[MessageResponse]:
        """搜索消息"""
        query = select(Message)
        
        conditions = []
        
        if keyword:
            conditions.append(Message.content.like(f"%{keyword}%"))
        
        if start_date:
            conditions.append(Message.created_at >= start_date)
        
        if end_date:
            conditions.append(Message.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(Message.created_at)).limit(limit)
        
        result = db.execute(query)
        messages = result.scalars().all()
        
        return [MessageResponse.model_validate(m) for m in messages]
