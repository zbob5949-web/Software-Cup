"""管理后台 - Dify 知识库管理接口。

接口编号：ADMIN-KB-01 ~ ADMIN-KB-10
用途：把前端管理后台的上传、更新、删除、检索操作封装为 Dify Dataset API 调用。
这段代码实现了Dify知识库的管理接口，封装了Dify平台的API调用，让管理员可以通过后台界面管理知识库文档。
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from core.config import DIFY_DATASET_ID
from dependencies import get_current_admin_user
from routers.admin.common import ok
from routers.admin.schemas import KnowledgeRetrieveForm, KnowledgeTextForm
from services import dify_service
from utils.response import Result

router = APIRouter()


# ADMIN-KB-01：知识库配置查询接口，用于确认Dify配置是否可用。
@router.get("/api/admin/knowledge/config")
@router.get("/admin/knowledge/config")
def knowledge_config(_: dict = Depends(get_current_admin_user)):
    """返回当前 Dify 知识库 ID 和 API Key 配置状态。"""
    masked = DIFY_DATASET_ID[:8] + "..." if DIFY_DATASET_ID else ""
    return ok({"dataset_id": DIFY_DATASET_ID, "dataset_id_masked": masked, "api_key_configured": bool(dify_service.DIFY_API_KEY)})


# ADMIN-KB-02：知识库文档列表接口，用于分页查看Dify中的文档。
@router.get("/api/admin/knowledge/documents")
@router.get("/admin/knowledge/documents")
def knowledge_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, max_length=100),
    _: dict = Depends(get_current_admin_user),
):
    """分页查询 Dify 知识库文档，支持关键词搜索。"""
    try:
        return ok(dify_service.list_documents(page, limit, keyword))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-03：知识库文档详情接口，用于编辑前查看Dify中的单个文档。
@router.get("/api/admin/knowledge/documents/{document_id}")
@router.get("/admin/knowledge/documents/{document_id}")
def knowledge_document_detail(document_id: str, _: dict = Depends(get_current_admin_user)):
    """按 Dify 文档 ID 查询文档详情，补齐知识库 CRUD 的 Read 能力。"""
    try:
        return ok(dify_service.get_document(document_id))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-04：文本文档上传接口，用于直接把讲解词/资料文本写入Dify。
@router.post("/api/admin/knowledge/documents/text")
@router.post("/admin/knowledge/documents/text")
def knowledge_create_text(form: KnowledgeTextForm, _: dict = Depends(get_current_admin_user)):
    """创建文本型知识库文档，并交给 Dify 自动切分和向量化。"""
    try:
        return ok(dify_service.create_document_by_text(
            form.name, form.text, form.indexing_technique, form.process_rule_mode
        ), "文本文档已提交至Dify解析入库")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-05：文件文档上传接口，用于上传docx/pdf/txt等资料到Dify。
@router.post("/api/admin/knowledge/documents/file")
@router.post("/admin/knowledge/documents/file")
async def knowledge_create_file(
    file: UploadFile = File(...),
    indexing_technique: str = "high_quality",
    process_rule_mode: str = "automatic",
    _: dict = Depends(get_current_admin_user),
):
    """上传文件到 Dify 知识库，并触发解析、切分和向量入库。"""
    content = await file.read()
    if not content:
        return Result(400, "文件不能为空")
    try:
        return ok(dify_service.create_document_by_file(
            file.filename or "upload.txt", content, file.content_type, indexing_technique, process_rule_mode
        ), "文件已提交至Dify解析入库")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-06：文本文档更新接口，用于用新文本替换Dify已有文档内容。
@router.put("/api/admin/knowledge/documents/{document_id}/text")
@router.put("/admin/knowledge/documents/{document_id}/text")
def knowledge_update_text(document_id: str, form: KnowledgeTextForm, _: dict = Depends(get_current_admin_user)):
    """按 Dify 文档 ID 更新文本内容并重新索引。"""
    try:
        return ok(dify_service.update_document_by_text(
            document_id, form.name, form.text, form.process_rule_mode
        ), "文本文档已更新并重新解析")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-07：文件文档更新接口，用于重新上传文件替换已有Dify文档。
@router.put("/api/admin/knowledge/documents/{document_id}/file")
@router.put("/admin/knowledge/documents/{document_id}/file")
async def knowledge_update_file(
    document_id: str,
    file: UploadFile = File(...),
    process_rule_mode: str = "automatic",
    _: dict = Depends(get_current_admin_user),
):
    """按 Dify 文档 ID 更新文件内容并重新解析索引。"""
    content = await file.read()
    if not content:
        return Result(400, "文件不能为空")
    try:
        return ok(dify_service.update_document_by_file(
            document_id, file.filename or "upload.txt", content, file.content_type, process_rule_mode
        ), "文件文档已更新并重新解析")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-08：知识库文档删除接口，用于从Dify中删除无效资料。
@router.delete("/api/admin/knowledge/documents/{document_id}")
@router.delete("/admin/knowledge/documents/{document_id}")
def knowledge_delete_document(document_id: str, _: dict = Depends(get_current_admin_user)):
    """按 Dify 文档 ID 删除知识库文档。"""
    try:
        return ok(dify_service.delete_document(document_id), "Dify文档删除成功")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-09：索引进度查询接口，用于上传后轮询Dify解析/向量化状态。
@router.get("/api/admin/knowledge/indexing-status/{batch}")
@router.get("/admin/knowledge/indexing-status/{batch}")
def knowledge_indexing_status(batch: str, _: dict = Depends(get_current_admin_user)):
    """根据 Dify 返回的 batch 查询文档索引进度。"""
    try:
        return ok(dify_service.indexing_status(batch))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


# ADMIN-KB-10：知识库检索测试接口，用于管理后台验证RAG召回效果。
@router.post("/api/admin/knowledge/retrieve")
@router.post("/admin/knowledge/retrieve")
def knowledge_retrieve(form: KnowledgeRetrieveForm, _: dict = Depends(get_current_admin_user)):
    """用指定问题测试 Dify 知识库召回结果。"""
    try:
        return ok(dify_service.retrieve(form.query, form.top_k))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))
