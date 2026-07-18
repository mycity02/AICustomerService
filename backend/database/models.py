"""
SQLAlchemy数据模型
"""
from pathlib import Path

from sqlalchemy import Column, String, Integer, Text, Boolean, Enum, TIMESTAMP, BigInteger, ForeignKey, JSON, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .connection import Base
import enum


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    USER = "user"
    ADMIN = "admin"


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TicketStatus(str, enum.Enum):
    """工单状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """工单优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ProductDifficulty(str, enum.Enum):
    """商品口感浓度枚举（字段名保持兼容）"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProductStatus(str, enum.Enum):
    """商品状态枚举"""
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    SOLD_OUT = "sold_out"


class OrderStatus(str, enum.Enum):
    """订单状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionStatus(str, enum.Enum):
    """交易状态枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), index=True)
    role = Column(Enum(UserRole), default=UserRole.USER, index=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # 关系
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    tickets = relationship("Ticket", foreign_keys="Ticket.user_id", back_populates="user", cascade="all, delete-orphan")
    created_documents = relationship("KnowledgeDocument", back_populates="creator")
    products = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="buyer")
    seller_order_items = relationship("OrderItem", foreign_keys="OrderItem.seller_id", back_populates="seller")
    reviews_given = relationship("Review", foreign_keys="Review.buyer_id", back_populates="buyer")
    reviews_received = relationship("Review", foreign_keys="Review.seller_id", back_populates="seller")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    browse_history = relationship("UserBrowseHistory", back_populates="user", cascade="all, delete-orphan")
    user_coupons = relationship("UserCoupon", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")



class Session(Base):
    """会话模型"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_message_at = Column(TIMESTAMP, nullable=True)
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    
    # 关系
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="session")


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False, index=True)
    content = Column(Text, nullable=False)
    meta = Column("metadata", JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    
    # 关系
    session = relationship("Session", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    """附件模型"""
    __tablename__ = "attachments"
    
    id = Column(String(36), primary_key=True)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    file_size = Column(BigInteger, nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    message = relationship("Message", back_populates="attachments")

    @property
    def file_id(self):
        try:
            return Path(self.file_path).stem
        except Exception:
            return None


class Ticket(Base):
    """工单模型"""
    __tablename__ = "tickets"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.PENDING, index=True)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, index=True)
    category = Column(String(50))
    assigned_to = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    context = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    resolved_at = Column(TIMESTAMP, nullable=True)
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")
    session = relationship("Session", back_populates="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to])
    history = relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan")


class TicketHistory(Base):
    """工单历史模型"""
    __tablename__ = "ticket_history"
    
    id = Column(String(36), primary_key=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    operator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    old_value = Column(String(100))
    new_value = Column(String(100))
    comment = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    
    # 关系
    ticket = relationship("Ticket", back_populates="history")
    operator = relationship("User")


class KnowledgeDocument(Base):
    """知识库文档模型"""
    __tablename__ = "knowledge_documents"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), index=True)
    tags = Column(JSON)
    source = Column(String(200))
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    creator = relationship("User", back_populates="created_documents")
    
    # 全文索引
    __table_args__ = (
        Index('idx_content', 'title', 'content', mysql_prefix='FULLTEXT'),
    )


class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = "system_config"
    
    id = Column(String(36), primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(String(500))
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    updater = relationship("User")


class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(String(36))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    
    # 关系
    user = relationship("User")
    
    # 复合索引
    __table_args__ = (
        Index('idx_resource', 'resource_type', 'resource_id'),
    )


# ==================== 电商扩展模型 ====================

class ProductDifficulty(str, enum.Enum):
    """商品口感浓度枚举（字段名保持兼容）"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProductStatus(str, enum.Enum):
    """商品状态枚举"""
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    SOLD_OUT = "sold_out"


class OrderStatus(str, enum.Enum):
    """订单状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionStatus(str, enum.Enum):
    """交易状态枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class RefundType(str, enum.Enum):
    """售后类型枚举"""
    REFUND_ONLY = "refund_only"       # 仅退款
    RETURN_REFUND = "return_refund"   # 退货退款
    EXCHANGE = "exchange"             # 换货


class RefundStatus(str, enum.Enum):
    """售后状态枚举"""
    PENDING = "pending"               # 待审核
    APPROVED = "approved"             # 已同意
    REJECTED = "rejected"             # 已拒绝
    RETURNING = "returning"           # 退货中
    REFUNDING = "refunding"           # 退款中
    COMPLETED = "completed"           # 已完成
    CANCELLED = "cancelled"           # 已取消


class RefundReason(str, enum.Enum):
    """退款原因枚举"""
    QUALITY_ISSUE = "quality_issue"           # 质量问题
    NOT_AS_DESCRIBED = "not_as_described"     # 与描述不符
    WRONG_ITEM = "wrong_item"                 # 发错商品
    MISSING_PARTS = "missing_parts"           # 缺少部件
    NO_LONGER_NEEDED = "no_longer_needed"     # 不想要了
    OTHER = "other"                           # 其他原因


class Category(Base):
    """商品分类模型"""
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    description = Column(Text)
    icon = Column(String(200))
    sort_order = Column(Integer, default=0, index=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="category")


class Product(Base):
    """商品模型"""
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True)
    seller_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False, index=True)  # 存储为分（cents）
    original_price = Column(Integer, nullable=True)  # 存储为分（cents）
    cover_image = Column(String(500))
    demo_video = Column(String(500))
    tech_stack = Column(JSON)
    difficulty = Column(Enum(ProductDifficulty), default=ProductDifficulty.MEDIUM)
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT, index=True)
    view_count = Column(Integer, default=0)
    sales_count = Column(Integer, default=0, index=True)
    rating = Column(Integer, default=0)  # 存储为 rating * 100
    review_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    seller = relationship("User", foreign_keys=[seller_id])
    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    files = relationship("ProductFile", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    """商品图片模型"""
    __tablename__ = "product_images"
    
    id = Column(String(36), primary_key=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0, index=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    product = relationship("Product", back_populates="images")


class ProductFile(Base):
    """商品文件模型"""
    __tablename__ = "product_files"
    
    id = Column(String(36), primary_key=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    product = relationship("Product", back_populates="files")



# ==================== 电商扩展模型 ====================
# Category, Product, ProductImage, ProductFile 已在上面定义

class CartItem(Base):
    """购物车模型"""
    __tablename__ = "cart_items"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # 关系
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")

    # 唯一约束
    __table_args__ = (
        Index('uk_user_product', 'user_id', 'product_id', unique=True),
    )


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    total_amount = Column(Integer, nullable=False)  # 存储为分（cents）
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    payment_method = Column(String(50))
    payment_time = Column(TIMESTAMP, nullable=True)
    delivery_time = Column(TIMESTAMP, nullable=True)
    completion_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    buyer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="order", cascade="all, delete-orphan")
    used_coupons = relationship("UserCoupon", back_populates="order")


class OrderItem(Base):
    """订单明细模型"""
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    seller_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_title = Column(String(200), nullable=False)
    product_cover = Column(String(500))
    price = Column(Integer, nullable=False)  # 存储为分（cents）
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="seller_order_items")
    reviews = relationship("Review", back_populates="order_item", cascade="all, delete-orphan")


class Transaction(Base):
    """交易记录模型"""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    transaction_no = Column(String(100), unique=True, nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)  # 存储为分（cents）
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    payment_time = Column(TIMESTAMP, nullable=True)
    refund_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    order = relationship("Order", back_populates="transactions")


class Coupon(Base):
    """优惠券模型"""
    __tablename__ = "coupons"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    discount_type = Column(String(20), default="amount")  # amount: 固定金额, percent: 百分比
    discount_amount = Column(Float, nullable=False)  # 优惠金额或百分比
    min_amount = Column(Float, default=0)  # 最低消费金额
    max_discount_amount = Column(Float)  # 最高优惠金额（百分比类型用）
    total_count = Column(Integer, default=0)  # 发放总量
    remain_count = Column(Integer, default=0)  # 剩余数量
    expire_date = Column(TIMESTAMP, nullable=False)  # 过期时间
    status = Column(String(20), default="active")  # active: 生效, inactive: 未生效, expired: 已过期
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    user_coupons = relationship("UserCoupon", back_populates="coupon")


class UserCoupon(Base):
    """用户优惠券模型"""
    __tablename__ = "user_coupons"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="unused")  # unused: 未使用, used: 已使用, expired: 已过期
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    user = relationship("User", back_populates="user_coupons")
    coupon = relationship("Coupon", back_populates="user_coupons")
    order = relationship("Order")


class Address(Base):
    """收货地址模型"""
    __tablename__ = "addresses"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact = Column(String(50), nullable=False)  # 联系人姓名
    phone = Column(String(20), nullable=False)  # 联系电话
    province = Column(String(50), nullable=False)  # 省份
    city = Column(String(50), nullable=False)  # 城市
    district = Column(String(50), nullable=False)  # 区县
    detail = Column(String(200), nullable=False)  # 详细地址
    is_default = Column(Boolean, default=False)  # 是否默认地址
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    user = relationship("User", back_populates="addresses")


class Review(Base):
    """评价模型"""
    __tablename__ = "reviews"
    
    id = Column(String(36), primary_key=True)
    order_item_id = Column(String(36), ForeignKey("order_items.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    seller_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False, index=True)  # 1-5
    content = Column(Text)
    images = Column(JSON)
    reply = Column(Text)
    reply_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    
    # 关系
    order_item = relationship("OrderItem", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="reviews_given")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="reviews_received")


class Favorite(Base):
    """收藏模型"""
    __tablename__ = "favorites"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # 关系
    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorites")
    
    # 唯一约束
    __table_args__ = (
        Index('uk_user_product_fav', 'user_id', 'product_id', unique=True),
    )


class UserBrowseHistory(Base):
    """用户浏览历史模型"""
    __tablename__ = "user_browse_history"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    view_duration = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    
    # 关系
    user = relationship("User", back_populates="browse_history")
    product = relationship("Product")
    
    # 唯一约束：同一用户对同一商品只记录一条
    __table_args__ = (
        Index('uk_user_product_browse', 'user_id', 'product_id', unique=True),
    )


class RefundRequest(Base):
    """售后退款申请模型"""
    __tablename__ = "refund_requests"

    id = Column(String(36), primary_key=True)
    refund_no = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id = Column(String(36), ForeignKey("order_items.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    refund_type = Column(Enum(RefundType), nullable=False)
    reason = Column(Enum(RefundReason), nullable=False)
    description = Column(Text, nullable=True)
    evidence_images = Column(JSON, nullable=True)

    refund_amount = Column(Integer, nullable=False)  # 存储为分
    status = Column(Enum(RefundStatus), default=RefundStatus.PENDING, index=True)

    review_note = Column(Text, nullable=True)
    reviewed_at = Column(TIMESTAMP, nullable=True)

    return_tracking_no = Column(String(100), nullable=True)
    return_carrier = Column(String(50), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    completed_at = Column(TIMESTAMP, nullable=True)

    # 关系
    order = relationship("Order", backref="refund_requests")
    order_item = relationship("OrderItem")
    user = relationship("User")
