import json
from typing import Any

import requests

from app.core.config import DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID


class DifyError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _ensure_config(dataset_id: str | None = None) -> str:
    target_dataset_id = dataset_id or DIFY_DATASET_ID
    if not DIFY_API_KEY:
        raise DifyError("未配置 DIFY_API_KEY")
    if not target_dataset_id:
        raise DifyError("未配置 DIFY_DATASET_ID")
    return target_dataset_id


def _headers(json_content: bool = True) -> dict:
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def _request(method: str, path: str, **kwargs) -> Any:
    url = f"{DIFY_API_BASE_URL}{path}"
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
    last_error: DifyError | None = None
    for path in paths:
        try:
            return _request(method, path, **kwargs)
        except DifyError as exc:
            last_error = exc
            if exc.status_code not in {404, 405}:
                raise
    raise last_error or DifyError("Dify 请求失败")


def list_documents(page: int = 1, limit: int = 20, keyword: str | None = None, dataset_id: str | None = None) -> Any:
    dataset_id = _ensure_config(dataset_id)
    params = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    return _request("GET", f"/datasets/{dataset_id}/documents", headers=_headers(), params=params)


def create_document_by_text(name: str, text: str, indexing_technique: str = "high_quality", process_rule_mode: str = "automatic", dataset_id: str | None = None) -> Any:
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


def create_document_by_file(filename: str, content: bytes, mime_type: str | None = None, indexing_technique: str = "high_quality", process_rule_mode: str = "automatic", dataset_id: str | None = None) -> Any:
    dataset_id = _ensure_config(dataset_id)
    data = {
        "indexing_technique": indexing_technique,
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    files = {"file": (filename, content, mime_type or "application/octet-stream")}
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


def update_document_by_text(document_id: str, name: str, text: str, process_rule_mode: str = "automatic", dataset_id: str | None = None) -> Any:
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


def update_document_by_file(document_id: str, filename: str, content: bytes, mime_type: str | None = None, process_rule_mode: str = "automatic", dataset_id: str | None = None) -> Any:
    dataset_id = _ensure_config(dataset_id)
    data = {
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "process_rule": {"mode": process_rule_mode},
    }
    files = {"file": (filename, content, mime_type or "application/octet-stream")}
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
    dataset_id = _ensure_config(dataset_id)
    return _request("GET", f"/datasets/{dataset_id}/documents/{document_id}", headers=_headers())


def delete_document(document_id: str, dataset_id: str | None = None) -> Any:
    dataset_id = _ensure_config(dataset_id)
    return _request("DELETE", f"/datasets/{dataset_id}/documents/{document_id}", headers=_headers())


def indexing_status(batch: str, dataset_id: str | None = None) -> Any:
    dataset_id = _ensure_config(dataset_id)
    return _request("GET", f"/datasets/{dataset_id}/documents/{batch}/indexing-status", headers=_headers())


def retrieve(query: str, top_k: int = 5, dataset_id: str | None = None) -> Any:
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
