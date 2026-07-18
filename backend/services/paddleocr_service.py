"""
视觉LLM 服务
用于多模态文档理解（图片中的文字识别、视觉推理）
基于硅基流动 API
支持模型: PaddleOCR-VL, Qwen3-VL 等
"""
import base64
import logging
from typing import Optional, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)


class VisionLLMService:
    """视觉LLM 服务类"""
    
    def __init__(self):
        self.enabled = settings.VISION_LLM_ENABLED
        self.api_key = settings.VISION_LLM_API_KEY
        self.base_url = settings.VISION_LLM_BASE_URL
        self.model = settings.VISION_LLM_MODEL
        self.client = None
        
        if self.enabled and self.api_key:
            self.client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
            logger.info(f"视觉LLM 服务已初始化，模型: {self.model}")
        else:
            logger.info("视觉LLM 服务未启用（缺少配置）")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.enabled and self.api_key and self.client is not None
    
    def extract_text_from_image(
        self, 
        image_data: bytes,
        prompt: str = "请识别图片中的所有文字内容，保持原有格式。"
    ) -> Optional[str]:
        """
        从图片中提取文字
        
        Args:
            image_data: 图片二进制数据
            prompt: 提示词
            
        Returns:
            识别出的文字内容，失败返回 None
        """
        if not self.is_available():
            logger.warning("PaddleOCR-VL 服务不可用")
            return None
        
        try:
            # 将图片转为 base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # 构建请求
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            # 发送请求
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            result = response.json()
            extracted_text = result["choices"][0]["message"]["content"]
            
            logger.info(f"PaddleOCR-VL 成功提取文字，长度: {len(extracted_text)}")
            return extracted_text
            
        except Exception as e:
            logger.error(f"PaddleOCR-VL 文字提取失败: {e}")
            return None
    
    def extract_text_from_image_file(
        self, 
        file_path: str,
        prompt: str = "请识别图片中的所有文字内容，保持原有格式。"
    ) -> Optional[str]:
        """
        从图片文件中提取文字
        
        Args:
            file_path: 图片文件路径
            prompt: 提示词
            
        Returns:
            识别出的文字内容，失败返回 None
        """
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
            return self.extract_text_from_image(image_data, prompt)
        except Exception as e:
            logger.error(f"读取图片文件失败: {e}")
            return None
    
    def analyze_document_image(
        self,
        image_data: bytes,
        analysis_type: str = "text"
    ) -> Dict[str, Any]:
        """
        分析文档图片
        
        Args:
            image_data: 图片二进制数据
            analysis_type: 分析类型 (text: 仅文字, structure: 结构化分析)
            
        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {"success": False, "error": "服务不可用"}
        
        prompts = {
            "text": "请识别图片中的所有文字内容，保持原有格式。",
            "structure": """请分析这张文档图片，提取以下信息：
1. 文档标题（如果有）
2. 所有文字内容
3. 表格数据（如果有表格）
4. 关键信息摘要

请以结构化格式输出。"""
        }
        
        prompt = prompts.get(analysis_type, prompts["text"])
        
        try:
            text = self.extract_text_from_image(image_data, prompt)
            if text:
                return {
                    "success": True,
                    "text": text,
                    "analysis_type": analysis_type
                }
            else:
                return {
                    "success": False,
                    "error": "文字提取失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


    def analyze_image_intent(
        self,
        image_data: bytes
    ) -> Dict[str, Any]:
        """
        分析图片意图，识别图片类型和内容
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            {
                "intent": "商品咨询|订单查询|售后服务|工单|文档分析|其他",
                "description": "图片描述",
                "extracted_text": "提取的文字",
                "confidence": 0.95
            }
        """
        if not self.is_available():
            return {"intent": "其他", "description": "", "extracted_text": "", "confidence": 0}
        
        prompt = """请分析这张图片，识别图片类型和内容。

请按以下JSON格式输出：
{
    "intent": "商品咨询|订单查询|售后服务|工单|文档分析|其他",
    "description": "简要描述图片内容",
    "extracted_text": "图片中的文字内容",
    "reasoning": "判断理由"
}

意图类型说明：
- 商品咨询：商品截图、商品列表、商品详情页、商品图片
- 订单查询：订单详情、订单列表、支付页面、物流信息
- 售后服务：退款申请、退货页面、售后凭证、质量问题截图
- 工单：错误提示、系统故障、bug截图、报错页面
- 文档分析：文档截图、文字材料、PDF截图、合同文件
- 其他：无法归类的图片

请确保输出是有效的JSON格式。"""
        
        try:
            result_text = self.extract_text_from_image(image_data, prompt)
            if result_text:
                # 尝试解析JSON
                import json
                try:
                    # 清理可能的markdown代码块
                    cleaned = result_text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    
                    result = json.loads(cleaned.strip())
                    return {
                        "intent": result.get("intent", "其他"),
                        "description": result.get("description", ""),
                        "extracted_text": result.get("extracted_text", ""),
                        "reasoning": result.get("reasoning", ""),
                        "confidence": 0.9
                    }
                except json.JSONDecodeError:
                    # 如果解析失败，返回原始文本
                    return {
                        "intent": "其他",
                        "description": "图片分析结果",
                        "extracted_text": result_text,
                        "confidence": 0.5
                    }
            else:
                return {"intent": "其他", "description": "", "extracted_text": "", "confidence": 0}
        except Exception as e:
            logger.error(f"图片意图分析失败: {e}")
            return {"intent": "其他", "description": "", "extracted_text": "", "confidence": 0}


# 全局服务实例
vision_llm_service = VisionLLMService()

# 保持向后兼容
paddleocr_service = vision_llm_service
