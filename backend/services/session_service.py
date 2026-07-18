"""
会话管理服务
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import uuid

from database.models import Session
from schemas import SessionCreate, SessionResponse


class SessionService:
    """会话管理服务类"""
    
    def create_session(self, db: Session, user_id: str, session_data: SessionCreate) -> SessionResponse:
        """创建新会话"""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=session_data.title or "新对话",
            is_active=True,
            message_count=0
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return SessionResponse.model_validate(session)
    
    def get_session(self, db: Session, session_id: str, user_id: str) -> Optional[SessionResponse]:
        """获取会话详情"""
        result = db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        return SessionResponse.model_validate(session)
    
    def list_user_sessions(
        self,
        db: Session,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[SessionResponse]:
        """列出用户的所有会话"""
        result = db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.updated_at))
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()
        
        return [SessionResponse.model_validate(s) for s in sessions]
    
    def update_session_activity(self, db: Session, session_id: str):
        """更新会话活动时间"""
        result = db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if session:
            session.last_message_at = datetime.utcnow()
            session.message_count += 1
            db.commit()
    
    def delete_session(self, db: Session, session_id: str, user_id: str) -> bool:
        """删除会话及其所有消息"""
        result = db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        return True

    def update_session_title(self, db: Session, session_id: str, title: str):
        """更新会话标题"""
        result = db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if session:
            session.title = title
            db.commit()

    def delete_session(self, db: Session, session_id: str, user_id: str) -> bool:
        """删除会话及其所有消息"""
        result = db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return False

        db.delete(session)
        db.commit()
        return True

    
    def generate_session_title(self, first_message: str, max_length: int = 20) -> str:
        """根据第一条消息生成会话标题"""
        if not first_message:
            return "新对话"
        
        # 清理消息内容
        title = first_message.strip()
        
        # 去除 Markdown 标记
        import re
        title = re.sub(r'[#*_`\[\]()]', '', title)
        
        # 去除多余空白
        title = re.sub(r'\s+', ' ', title)
        
        # 截取前 max_length 个字符
        if len(title) > max_length:
            title = title[:max_length] + "..."
        
        # 如果标题为空，返回默认标题
        if not title.strip():
            return "新对话"
        
        return title.strip()
    
    def check_session_timeout(self, session: SessionResponse, timeout_minutes: int = 60) -> bool:
        """检查会话是否超时"""
        if not session.last_message_at:
            return False
        
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return session.last_message_at < timeout_threshold
