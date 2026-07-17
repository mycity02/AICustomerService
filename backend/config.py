"""
应用配置模块
"""
import logging
import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "AI客服系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEFAULT_BUSINESS_ID: str = "graduation-marketplace"
    
    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "ai_customer_service"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_REQUIRED: bool = False
    CONTEXT_CACHE_TTL_SECONDS: int = 86400
    
    # FAISS配置
    FAISS_PERSIST_DIRECTORY: str = str(DATA_DIR / "faiss")
    
    # JWT配置
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # LLM 配置（支持 OpenAI 和 DeepSeek）
    LLM_PROVIDER: str = "deepseek"  # 可选: openai, deepseek
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # 意图识别模型配置（可独立配置，不填则复用主模型）
    INTENT_MODEL: str = ""
    INTENT_MODEL_PROVIDER: str = ""
    INTENT_API_KEY: str = ""
    INTENT_TEMPERATURE: float = 0.1
    INTENT_MAX_TOKENS: int = 200
    
    # 硅基流动配置（用于 Embeddings）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    
    # 视觉LLM 配置（多模态文档理解）
    # 可选模型: PaddlePaddle/PaddleOCR-VL (免费, 文档OCR专用)
    #          Qwen/Qwen3-VL-8B-Thinking (通用视觉推理, 支持工具调用)
    VISION_LLM_ENABLED: bool = True  # 是否启用视觉LLM
    VISION_LLM_API_KEY: str = ""
    VISION_LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VISION_LLM_MODEL: str = "Qwen/Qwen3-VL-8B-Thinking"  # 模型名称
    
    # 文件上传配置
    UPLOAD_DIR: str = str(DATA_DIR / "uploads")
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = "pdf,doc,docx,txt,png,jpg,jpeg"
    
    # 系统配置
    MAX_CONCURRENT_SESSIONS: int = 50
    CONTEXT_MAX_HISTORY: int = 20
    RETRIEVAL_TOP_K: int = 3
    REQUEST_TIMEOUT: int = 30
    
    # 意图追踪配置
    INTENT_HISTORY_SIZE: int = 5  # 提供给 LLM 的意图历史条数
    INTENT_FALLBACK_THRESHOLD: float = 0.6  # 回退到历史意图的置信度阈值
    
    # 对话摘要配置
    SUMMARY_TRIGGER_THRESHOLD: int = 10  # 触发摘要的对话轮数阈值
    CONTEXT_MAX_TOKENS: int = 3000  # 上下文最大 token 数
    
    # 高级RAG配置
    RAG_USE_HYBRID_SEARCH: bool = True  # 是否使用混合检索(向量+BM25)
    RAG_USE_RERANK: bool = True  # 是否使用LLM重排序
    RAG_USE_QUERY_REWRITE: bool = True  # 是否使用查询改写
    RAG_RERANK_TOP_K: int = 10  # 重排序前保留的候选文档数
    RAG_SIMILARITY_THRESHOLD: float = 0.7  # 相似度阈值
    
    # CORS配置
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """Allow environment values such as 'release' and 'production'."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "on", "yes"}:
                return True
        return value

    @field_validator("FAISS_PERSIST_DIRECTORY", "UPLOAD_DIR", mode="before")
    @classmethod
    def resolve_data_paths(cls, value):
        """Resolve relative storage paths against the backend directory."""
        if not value:
            return value

        path = Path(str(value))
        if path.is_absolute():
            return str(path)
        return str((BACKEND_DIR / path).resolve())
    
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
    
    @property
    def LLM_MODEL(self) -> str:
        """根据provider返回对应的模型"""
        if self.LLM_PROVIDER == "deepseek":
            return self.DEEPSEEK_MODEL
        return self.OPENAI_MODEL
    
    @property
    def LLM_API_KEY(self) -> str:
        """根据provider返回对应的API Key"""
        if self.LLM_PROVIDER == "deepseek":
            return self.DEEPSEEK_API_KEY
        return self.OPENAI_API_KEY
    
    @property
    def LLM_BASE_URL(self) -> str:
        """根据provider返回对应的Base URL"""
        if self.LLM_PROVIDER == "deepseek":
            return self.DEEPSEEK_BASE_URL
        return self.OPENAI_BASE_URL
    
    @property
    def redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    def validate_runtime_configuration(self) -> None:
        """Fail fast on unsafe runtime configuration."""
        errors: List[str] = []

        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "your-secret-key-change-this":
            errors.append("JWT_SECRET_KEY must be set to a non-default secret")

        provider = (self.LLM_PROVIDER or "").strip().lower()
        if provider == "deepseek" and not self.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY must be set when LLM_PROVIDER=deepseek")
        if provider == "openai" and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY must be set when LLM_PROVIDER=openai")

        if self.VISION_LLM_ENABLED and not self.VISION_LLM_API_KEY:
            logger.warning(
                "VISION_LLM_ENABLED=true but VISION_LLM_API_KEY is empty; vision analysis will be disabled"
            )

        if errors:
            raise RuntimeError("Invalid runtime configuration: " + "; ".join(errors))

    class Config:
        # 尝试多个可能的 .env 文件位置
        env_file = ".env" if os.path.exists(".env") else "backend/.env"
        case_sensitive = True


# 全局配置实例
settings = Settings()


def init_intent_model():
    """初始化意图识别专用LLM"""
    from langchain.chat_models import init_chat_model as _init_chat_model
    model = settings.INTENT_MODEL or settings.DEEPSEEK_MODEL
    provider = settings.INTENT_MODEL_PROVIDER or "deepseek"
    api_key = settings.INTENT_API_KEY or settings.DEEPSEEK_API_KEY
    return _init_chat_model(
        model=model,
        model_provider=provider,
        temperature=settings.INTENT_TEMPERATURE,
        max_tokens=settings.INTENT_MAX_TOKENS,
        api_key=api_key,
    )
