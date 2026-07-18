"""
认证服务
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

from config import settings
from database.models import User
from schemas import UserCreate, UserLogin, AuthToken, UserResponse


class AuthService:
    """认证服务类"""
    
    @staticmethod
    def _password_bytes(password: str) -> bytes:
        """按 bcrypt 的 72 字节上限规范化密码。"""
        return password.encode("utf-8")[:72]

    def hash_password(self, password: str) -> str:
        """使用 bcrypt 原生接口生成可持久化的密码哈希。"""
        hashed = bcrypt.hashpw(self._password_bytes(password), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证 bcrypt 密码，并安全处理损坏或非 bcrypt 哈希。"""
        try:
            return bcrypt.checkpw(
                self._password_bytes(plain_password),
                hashed_password.encode("utf-8"),
            )
        except (AttributeError, TypeError, ValueError):
            return False
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def register(self, db: Session, user_data: UserCreate) -> UserResponse:
        """注册新用户"""
        # 检查用户名是否已存在
        result = db.execute(select(User).where(User.username == user_data.username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("用户名已存在")
        
        # 创建新用户
        user = User(
            id=str(uuid.uuid4()),
            username=user_data.username,
            password_hash=self.hash_password(user_data.password),
            email=user_data.email,
            role=user_data.role,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return UserResponse.model_validate(user)
    
    def login(self, db: Session, login_data: UserLogin) -> AuthToken:
        """用户登录"""
        # 查找用户
        result = db.execute(select(User).where(User.username == login_data.username))
        user = result.scalar_one_or_none()
        
        if not user or not self.verify_password(login_data.password, user.password_hash):
            raise ValueError("用户名或密码错误")
        
        if not user.is_active:
            raise ValueError("用户已被禁用")
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        # 生成令牌
        token_data = {"sub": user.id, "username": user.username, "role": user.role.value}
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def refresh_access_token(self, refresh_token: str) -> AuthToken:
        """刷新访问令牌"""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("无效的刷新令牌")
        
        # 生成新的访问令牌
        token_data = {
            "sub": payload["sub"],
            "username": payload["username"],
            "role": payload["role"]
        }
        access_token = self.create_access_token(token_data)
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def get_current_user(self, db: Session, token: str) -> UserResponse:
        """获取当前用户"""
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "access":
            raise ValueError("无效的访问令牌")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("令牌中缺少用户ID")
        
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在")
        
        if not user.is_active:
            raise ValueError("用户已被禁用")
        
        return UserResponse.model_validate(user)
