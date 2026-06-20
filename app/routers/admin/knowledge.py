from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.config import DIFY_DATASET_ID
from app.dependencies import get_current_admin_user
from app.routers.admin.common import ok
from app.routers.admin.schemas import KnowledgeRetrieveForm, KnowledgeTextForm
from app.services import dify_service
from app.utils.response import Result

router = APIRouter()


@router.get("/api/admin/knowledge/config")
@router.get("/admin/knowledge/config")
def knowledge_config(_: dict = Depends(get_current_admin_user)):
    masked = DIFY_DATASET_ID[:8] + "..." if DIFY_DATASET_ID else ""
    return ok({"dataset_id": DIFY_DATASET_ID, "dataset_id_masked": masked, "api_key_configured": bool(dify_service.DIFY_API_KEY)})


@router.get("/api/admin/knowledge/documents")
@router.get("/admin/knowledge/documents")
def knowledge_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, max_length=100),
    _: dict = Depends(get_current_admin_user),
):
    try:
        return ok(dify_service.list_documents(page, limit, keyword))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.get("/api/admin/knowledge/documents/{document_id}")
@router.get("/admin/knowledge/documents/{document_id}")
def knowledge_document_detail(document_id: str, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.get_document(document_id))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.post("/api/admin/knowledge/documents/text")
@router.post("/admin/knowledge/documents/text")
def knowledge_create_text(form: KnowledgeTextForm, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.create_document_by_text(form.name, form.text, form.indexing_technique, form.process_rule_mode), "文本文档已提交至Dify解析入库")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.post("/api/admin/knowledge/documents/file")
@router.post("/admin/knowledge/documents/file")
async def knowledge_create_file(
    file: UploadFile = File(...),
    indexing_technique: str = "high_quality",
    process_rule_mode: str = "automatic",
    _: dict = Depends(get_current_admin_user),
):
    content = await file.read()
    if not content:
        return Result(400, "文件不能为空")
    try:
        return ok(dify_service.create_document_by_file(file.filename or "upload.txt", content, file.content_type, indexing_technique, process_rule_mode), "文件已提交至Dify解析入库")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.put("/api/admin/knowledge/documents/{document_id}/text")
@router.put("/admin/knowledge/documents/{document_id}/text")
def knowledge_update_text(document_id: str, form: KnowledgeTextForm, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.update_document_by_text(document_id, form.name, form.text, form.process_rule_mode), "文本文档已更新并重新解析")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.put("/api/admin/knowledge/documents/{document_id}/file")
@router.put("/admin/knowledge/documents/{document_id}/file")
async def knowledge_update_file(
    document_id: str,
    file: UploadFile = File(...),
    process_rule_mode: str = "automatic",
    _: dict = Depends(get_current_admin_user),
):
    content = await file.read()
    if not content:
        return Result(400, "文件不能为空")
    try:
        return ok(dify_service.update_document_by_file(document_id, file.filename or "upload.txt", content, file.content_type, process_rule_mode), "文件文档已更新并重新解析")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.delete("/api/admin/knowledge/documents/{document_id}")
@router.delete("/admin/knowledge/documents/{document_id}")
def knowledge_delete_document(document_id: str, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.delete_document(document_id), "Dify文档删除成功")
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.get("/api/admin/knowledge/indexing-status/{batch}")
@router.get("/admin/knowledge/indexing-status/{batch}")
def knowledge_indexing_status(batch: str, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.indexing_status(batch))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))


@router.post("/api/admin/knowledge/retrieve")
@router.post("/admin/knowledge/retrieve")
def knowledge_retrieve(form: KnowledgeRetrieveForm, _: dict = Depends(get_current_admin_user)):
    try:
        return ok(dify_service.retrieve(form.query, form.top_k))
    except dify_service.DifyError as exc:
        return Result(502, str(exc))
