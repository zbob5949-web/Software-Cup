from typing import Optional

from pydantic import BaseModel, Field


class FAQForm(BaseModel):
    question: str = Field(..., min_length=1, max_length=255)
    answer: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    keywords: Optional[str] = Field(None, max_length=255)
    sort_order: int = 0
    is_active: bool = True


class FAQUpdateForm(BaseModel):
    question: Optional[str] = Field(None, min_length=1, max_length=255)
    answer: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    keywords: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class KnowledgeTextForm(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)
    indexing_technique: str = Field("high_quality", max_length=30)
    process_rule_mode: str = Field("automatic", max_length=30)


class KnowledgeRetrieveForm(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=10)


class DigitalHumanForm(BaseModel):
    model_key: str = Field("live2d_haru", max_length=80)
    name: str = Field(..., min_length=1, max_length=100)
    voice_name: str = Field("zh-CN-XiaoxiaoNeural", max_length=100)
    voice_style: Optional[str] = Field(None, max_length=100)
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    cultural_style: Optional[str] = None
    keywords: Optional[str] = None
    is_active: bool = False


class DigitalHumanUpdateForm(BaseModel):
    model_key: Optional[str] = Field(None, max_length=80)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    voice_name: Optional[str] = Field(None, max_length=100)
    voice_style: Optional[str] = Field(None, max_length=100)
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    cultural_style: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None
