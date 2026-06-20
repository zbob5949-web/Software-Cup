"""管理后台请求体模型。

这段代码是一个Pydantic请求体模型集合文件，集中定义了管理后台所有接口的数据验证模型。
"""
from typing import Optional

from pydantic import BaseModel, Field


#FAQ管理模型（2个）
#FAQForm - 新增FAQ
class FAQForm(BaseModel):
    """ADMIN-FAQ-03 新增FAQ请求体。"""
    question: str = Field(..., min_length=1, max_length=255)
    answer: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    keywords: Optional[str] = Field(None, max_length=255)
    sort_order: int = 0
    is_active: bool = True

#FAQUpdateForm - 更新FAQ
class FAQUpdateForm(BaseModel):
    """ADMIN-FAQ-04 更新FAQ请求体，所有字段均可选。"""
    question: Optional[str] = Field(None, min_length=1, max_length=255)
    answer: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    keywords: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


#知识库管理模型（2个）
#KnowledgeTextForm - 文本上传/更新
class KnowledgeTextForm(BaseModel):
    """ADMIN-KB-03/05 文本文档创建或更新请求体。"""
    name: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)
    indexing_technique: str = Field("high_quality", max_length=30)
    process_rule_mode: str = Field("automatic", max_length=30)

#KnowledgeRetrieveForm - 检索测试
class KnowledgeRetrieveForm(BaseModel):
    """ADMIN-KB-09 知识库检索测试请求体。"""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=10)

#数字人形象管理模型（2个）
#DigitalHumanForm - 新增形象
class DigitalHumanForm(BaseModel):
    """ADMIN-DH-02 新增数字人形象请求体。"""
    name: str = Field(..., min_length=1, max_length=100)
    voice_name: str = Field("zh-CN-XiaoxiaoNeural", max_length=100)
    voice_style: Optional[str] = Field(None, max_length=100)
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    cultural_style: Optional[str] = None
    keywords: Optional[str] = None
    is_active: bool = False

#DigitalHumanUpdateForm - 更新形象
class DigitalHumanUpdateForm(BaseModel):
    """ADMIN-DH-03 更新数字人形象请求体，所有字段均可选。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    voice_name: Optional[str] = Field(None, max_length=100)
    voice_style: Optional[str] = Field(None, max_length=100)
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    cultural_style: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None
