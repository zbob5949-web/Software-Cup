"""Dify Dataset API 封装服务。
这段代码是Dify知识库API的封装服务层，为管理后台提供统一的接口来操作Dify平台的知识库文档。
该文件不直接提供 HTTP 接口，而是供 routers/admin/knowledge.py 调用，
统一处理 Dify 鉴权、错误转换、文档上传/更新/删除/检索等操作。
"""
import json
from typing import Any

import requests

from core.config import DIFY_API_KEY, DIFY_BASE_URL, DIFY_DATASET_ID

#错误处理
class DifyError(Exception):
    """Dify 调用失败时抛出的业务异常，路由层会转换成 502 响应。"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

#配置管理
def _ensure_config(dataset_id: str | None = None) -> str:
    """检查 Dify API Key 和知识库 ID 是否已配置，并返回最终 dataset_id。"""
    target_dataset_id = dataset_id or DIFY_DATASET_ID
    if not DIFY_API_KEY:
        raise DifyError("未配置 DIFY_API_KEY")
    if not target_dataset_id:
        raise DifyError("未配置 DIFY_DATASET_ID")
    return target_dataset_id


def _headers(json_content: bool = True) -> dict:
    """生成 Dify API 请求头；文件上传时不手动指定 JSON Content-Type。"""
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def _request(method: str, path: str, **kwargs) -> Any:
    """统一发送 Dify HTTP 请求，并把非 2xx 响应转换为 DifyError。"""
    url = f"{DIFY_BASE_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=60, **kwargs)
    except requests.RequestException as exc:
        raise DifyError(f"Dify 请求失败：{exc}") from exc

    if not (200 <= resp.status_code < 300):
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:500]
        raise DifyError(f"Dify 返回错误 {resp.status_code}: {detail}", resp.status_code)

    if not resp.content:
        return {"ok": True}
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}


def _request_with_path_fallback(method: str, paths: list[str], **kwargs) -> Any:
    """兼容 Dify 不同版本的 Dataset API 路径命名。

    Dify 文档接口在不同部署版本中存在 create-by-file/create_by_file
    这类连字符/下划线差异。优先使用当前官方连字符路径；若服务返回
    404/405，再回退到旧路径，避免管理后台因 Dify 版本不同而不可用。
    """
    last_error: DifyError | None = None
    for path in paths:
        try:
            return _request(method, path, **kwargs)
        except DifyError as exc:
            last_error = exc
            if exc.status_code not in {404, 405}:
                raise
    raise last_error or DifyError("Dify 请求失败")


def list_documents(page: int = 1, limit: int = 20, keyword: str | None = None,
                   dataset_id: str | None = None) -> Any:
    """查询 Dify 知识库文档列表，供 ADMIN-KB-02 调用。"""
    dataset_id = _ensure_config(dataset_id)
    params = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    return _request("GET", f"/datasets/{dataset_id}/documents", headers=_headers(), params=params)


def create_document_by_text(name: str, text: str, indexing_technique: str = "high_quality",
                            process_rule_mode: str = "automatic", dataset_id: str | None = None) -> Any:
    """用纯文本创建 Dify 文档，供 ADMIN-KB-03 调用。"""
    dataset_id = _ensure_config(dataset_id)
    payload = {
        "name": name,
        "text": text,
        "indexing_technique": indexing_technique,
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    return _request_with_path_fallback(
        "POST",
        [
            f"/datasets/{dataset_id}/document/create-by-text",
            f"/datasets/{dataset_id}/document/create_by_text",
        ],
        headers=_headers(),
        json=payload,
    )


def create_document_by_file(filename: str, content: bytes, mime_type: str | None = None,
                            indexing_technique: str = "high_quality",
                            process_rule_mode: str = "automatic",
                            dataset_id: str | None = None) -> Any:
    """用上传文件创建 Dify 文档，供 ADMIN-KB-04 调用。"""
    dataset_id = _ensure_config(dataset_id)
    data = {
        "indexing_technique": indexing_technique,
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    files = {
        "file": (filename, content, mime_type or "application/octet-stream"),
    }
    return _request_with_path_fallback(
        "POST",
        [
            f"/datasets/{dataset_id}/document/create-by-file",
            f"/datasets/{dataset_id}/document/create_by_file",
        ],
        headers=_headers(json_content=False),
        data={"data": json.dumps(data, ensure_ascii=False)},
        files=files,
    )


def update_document_by_text(document_id: str, name: str, text: str,
                            process_rule_mode: str = "automatic",
                            dataset_id: str | None = None) -> Any:
    """用纯文本更新 Dify 文档，供 ADMIN-KB-05 调用。"""
    dataset_id = _ensure_config(dataset_id)
    payload = {
        "name": name,
        "text": text,
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    return _request_with_path_fallback(
        "POST",
        [
            f"/datasets/{dataset_id}/documents/{document_id}/update-by-text",
            f"/datasets/{dataset_id}/documents/{document_id}/update_by_text",
        ],
        headers=_headers(),
        json=payload,
    )


def update_document_by_file(document_id: str, filename: str, content: bytes,
                            mime_type: str | None = None,
                            process_rule_mode: str = "automatic",
                            dataset_id: str | None = None) -> Any:
    """用上传文件更新 Dify 文档，供 ADMIN-KB-06 调用。"""
    dataset_id = _ensure_config(dataset_id)
    data = {
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    files = {
        "file": (filename, content, mime_type or "application/octet-stream"),
    }
    return _request_with_path_fallback(
        "POST",
        [
            f"/datasets/{dataset_id}/documents/{document_id}/update-by-file",
            f"/datasets/{dataset_id}/documents/{document_id}/update_by_file",
        ],
        headers=_headers(json_content=False),
        data={"data": json.dumps(data, ensure_ascii=False)},
        files=files,
    )


def get_document(document_id: str, dataset_id: str | None = None) -> Any:
    """查询单个 Dify 文档详情，补齐知识库管理的 Read 能力。"""
    dataset_id = _ensure_config(dataset_id)
    return _request(
        "GET",
        f"/datasets/{dataset_id}/documents/{document_id}",
        headers=_headers(),
    )


def delete_document(document_id: str, dataset_id: str | None = None) -> Any:
    """删除指定 Dify 文档，供 ADMIN-KB-07 调用。"""
    dataset_id = _ensure_config(dataset_id)
    return _request(
        "DELETE",
        f"/datasets/{dataset_id}/documents/{document_id}",
        headers=_headers(),
    )


def indexing_status(batch: str, dataset_id: str | None = None) -> Any:
    """查询 Dify 文档索引进度，供 ADMIN-KB-08 调用。"""
    dataset_id = _ensure_config(dataset_id)
    return _request(
        "GET",
        f"/datasets/{dataset_id}/documents/{batch}/indexing-status",
        headers=_headers(),
    )


def retrieve(query: str, top_k: int = 5, dataset_id: str | None = None) -> Any:
    """测试 Dify 知识库召回效果，供 ADMIN-KB-09 调用。"""
    dataset_id = _ensure_config(dataset_id)
    payload = {
        "query": query,
        "retrieval_model": {
            "search_method": "hybrid_search",
            "reranking_enable": False,
            "top_k": top_k,
            "score_threshold_enabled": False,
        },
    }
    return _request("POST", f"/datasets/{dataset_id}/retrieve", headers=_headers(), json=payload)
