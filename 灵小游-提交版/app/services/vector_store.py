"""
vector_store.py
本地向量知识库 — ChromaDB + 通义（DashScope）Embedding API 替代 Dify。
无需下载模型，调用阿里百炼 API 生成向量。
"""
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

# 确保 .env 已加载
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

# ---- 常量 ----
COLLECTION_NAME = "lingshan_knowledge"
DB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chroma_db"
TOP_K_DEFAULT = 5
SIMILARITY_THRESHOLD = 0.35
EMBED_BATCH_SIZE = 10  # DashScope 单次最多 10 条

# ---- 单例 ----
_chroma_client = None
_collection = None


def _call_embedding(texts: list[str]) -> list[list[float]]:
    """调用通义 DashScope TextEmbedding API，单次最多 10 条文本。"""
    import dashscope
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")
    from dashscope import TextEmbedding

    if not dashscope.api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，请在 .env 中设置阿里百炼 API Key")

    resp = TextEmbedding.call(
        model=TextEmbedding.Models.text_embedding_v1,
        input=texts,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DashScope embedding 失败: {resp.code} {resp.message}")

    return [e["embedding"] for e in resp.output["embeddings"]]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """分批调用 embedding API，处理任意数量的文本。"""
    all_embeddings = []
    total = len(texts)
    for i in range(0, total, EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        logger.info("  embedding 批次 %d-%d / %d", i + 1, min(i + len(batch), total), total)
        all_embeddings.extend(_call_embedding(batch))
        if i + EMBED_BATCH_SIZE < total:
            time.sleep(0.1)  # 避免限流
    return all_embeddings


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(DB_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection():
    global _collection
    if _collection is not None:
        return _collection
    try:
        _collection = get_chroma_client().get_collection(COLLECTION_NAME)
        logger.info("ChromaDB 集合 '%s' 已加载: %d 条文档", COLLECTION_NAME, _collection.count())
        return _collection
    except Exception:
        logger.warning("ChromaDB 集合 '%s' 未找到 —— 请先运行 build_kb_index.py 构建索引", COLLECTION_NAME)
        return None


def collection_exists() -> bool:
    try:
        get_chroma_client().get_collection(COLLECTION_NAME)
        return True
    except Exception:
        return False


def _sanitize_metadata(meta: dict) -> dict:
    """将 metadata 中的 None 转为空字符串，确保 ChromaDB 兼容。"""
    return {k: (v if v is not None else "") for k, v in meta.items()}


def build_index(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    """构建（重建）知识库索引。"""
    global _collection
    client = get_chroma_client()

    metadatas = [_sanitize_metadata(m) for m in metadatas]

    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("已删除旧的 ChromaDB 集合，准备重建")
    except Exception:
        pass

    _collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # 通过通义 API 批量生成向量
    logger.info("通过通义 DashScope API 生成向量（%d 条文本）...", len(documents))
    embeddings = _embed_batch(documents)

    # 写入 ChromaDB
    for i in range(0, len(documents), EMBED_BATCH_SIZE):
        end = min(i + EMBED_BATCH_SIZE, len(documents))
        _collection.add(
            documents=documents[i:end],
            embeddings=embeddings[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end],
        )
        logger.info("  写入批次 %d-%d / %d", i + 1, end, len(documents))

    logger.info("索引构建完成: %d 条文档已存入 '%s'", len(documents), COLLECTION_NAME)


def retrieve(query: str, top_k: int = TOP_K_DEFAULT) -> list[dict]:
    """语义检索。返回: [{"id", "content", "metadata", "score"}, ...]"""
    collection = get_collection()
    if collection is None:
        return []

    query_embedding = _call_embedding([query])

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    formatted = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = 1.0 - (distance / 2.0)
            if similarity < SIMILARITY_THRESHOLD:
                continue
            formatted.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": round(similarity, 4),
            })
    return formatted


def retrieve_formatted(query: str, top_k: int = 3) -> str:
    """格式化检索结果（兼容旧 Dify 格式）。"""
    results = retrieve(query, top_k=top_k)
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(f"[LocalKB score={r['score']:.4f}]\n{r['content'].strip()}")
    return "\n\n".join(parts)
