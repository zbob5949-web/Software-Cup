import os
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Iterator, Any
import hashlib

from openpyxl import load_workbook
from docx import Document as DocxDocument
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, Docx2txtLoader
from huggingface_hub import login
from datetime import datetime

# ============ 配置 ============
login(token="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")  # 请替换为您的实际令牌

CHROMA_PERSIST_DIR = "./linshan_chroma_db"
LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 文本分块参数
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# ✅ 嵌入批次大小（本地模型建议 1024~4096，根据显存调整）
EMBED_BATCH_SIZE = 2048

# 文件读取批次大小
FILE_READ_BATCH = 100

# ✅ Chroma 写入批次大小（越大越快，但需内存充裕；建议 5000~20000）
CHROMA_WRITE_BATCH = 10000

# 断点续传
ENABLE_RESUME = True

# 文件路径（保持不变）
FILE_PATHS = [
    "./data/lingshan/景点景区旅游数据行为分析数据.xlsx",
    "./data/lingshan/灵山胜境 景点结构化数据集.docx",
    "./data/lingshan/灵山胜境：历史、文化、景点特色与个性化游览指南.docx"
]
# ==============================

# ==================== 工具函数 ====================
def file_checksum(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def has_table_in_docx(file_path: str) -> bool:
    doc = DocxDocument(file_path)
    return len(doc.tables) > 0

def is_file_already_indexed(file_path: str, vector_store: Chroma) -> bool:
    if vector_store._collection.count() == 0:
        return False
    res = vector_store._collection.get(where={"source": file_path}, limit=1)
    return len(res["ids"]) > 0

# ✅ 将元数据清洗函数提取至全局（仅定义一次）
def clean_metadata(metadata: dict) -> dict:
    """将 datetime 等复杂类型转为可序列化的格式"""
    cleaned = {}
    for k, v in metadata.items():
        if isinstance(v, datetime):
            cleaned[k] = v.isoformat()
        elif isinstance(v, (list, dict, set)):
            cleaned[k] = str(v)
        else:
            cleaned[k] = v
    return cleaned
# =================================================

# ==================== 文档加载器（流式，保留原逻辑） ====================
def load_xlsx_stream(
    file_path: str,
    content_columns: List[str],
    metadata_columns: Optional[List[str]] = None,
    batch_size: int = FILE_READ_BATCH,
) -> Iterator[List[Document]]:
    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    batch = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        row_dict = {headers[i]: row[i] for i in range(len(headers)) if row[i] is not None}
        content_parts = []
        for col in content_columns:
            if col in row_dict and row_dict[col]:
                content_parts.append(str(row_dict[col]))
        content = " ".join(content_parts)
        if not content.strip():
            continue
        metadata = {"source": file_path, "file_type": "excel", "row": row_idx}
        if metadata_columns:
            for col in metadata_columns:
                if col in row_dict:
                    metadata[col] = row_dict[col]
        doc = Document(page_content=content, metadata=metadata)
        batch.append(doc)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
    wb.close()

def load_docx_table_stream(
    file_path: str,
    content_columns: Optional[List[str]] = None,
    metadata_columns: Optional[List[str]] = None,
    batch_size: int = FILE_READ_BATCH,
) -> Iterator[List[Document]]:
    doc = DocxDocument(file_path)
    batch = []
    for table in doc.tables:
        headers = [cell.text.strip() for cell in table.rows[0].cells]
        if content_columns is None:
            content_columns = headers
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            row_dict = dict(zip(headers, cells))
            parts = []
            for col in content_columns:
                if col in row_dict and row_dict[col]:
                    parts.append(f"{col}: {row_dict[col]}")
            content = "; ".join(parts)
            if not content:
                continue
            metadata = {"source": file_path, "file_type": "docx_table"}
            if metadata_columns:
                for col in metadata_columns:
                    if col in row_dict:
                        metadata[col] = row_dict[col]
            doc_obj = Document(page_content=content, metadata=metadata)
            batch.append(doc_obj)
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch

def load_text_or_docx_stream(file_path: str) -> Iterator[List[Document]]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()
    for d in docs:
        d.metadata["source"] = file_path
    yield docs
# ===================================================================

# ==================== 核心处理函数（性能优化版本） ====================
def process_documents_to_chroma(
    file_paths: List[str],
    persist_dir: str,
    local_model_name: str = LOCAL_MODEL_NAME,
    device: str = DEVICE,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    embed_batch_size: int = EMBED_BATCH_SIZE,
    chrome_write_batch: int = CHROMA_WRITE_BATCH,
    resume: bool = ENABLE_RESUME,
):
    # ✅ 初始化 Embedding 模型（提升 encode batch_size）
    embeddings = HuggingFaceEmbeddings(
        model_name=local_model_name,
        model_kwargs={"device": device},
        encode_kwargs={
            "batch_size": embed_batch_size,
            "normalize_embeddings": True
        }
    )

    vector_store = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="linshan_retrieval",
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        length_function=len,
    )

    # ---------- 断点续传 ----------
    files_to_process = []
    if resume:
        print("🔍 检查已索引文件...")
        for f in file_paths:
            if is_file_already_indexed(f, vector_store):
                print(f"⏭️  跳过已索引文件: {f}")
            else:
                files_to_process.append(f)
    else:
        files_to_process = file_paths

    if not files_to_process:
        print("✅ 所有文件均已索引，无需重复处理。")
        return vector_store

    # ---------- 并行加载文件 ----------
    all_doc_batches = []  # 元素为 List[Document]
    print(f"📂 开始加载 {len(files_to_process)} 个文件...")
    with ThreadPoolExecutor(max_workers=min(4, len(files_to_process))) as executor:
        future_to_file = {}
        for f in files_to_process:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".xlsx", ".xls"):
                future = executor.submit(
                    load_xlsx_stream,
                    f,
                    content_columns=["attraction_content", "attraction_name"],
                    metadata_columns=["tourist_id", "user_nickname", "age", "gender", "visit_date"],
                    batch_size=FILE_READ_BATCH,
                )
            elif ext == ".docx":
                if has_table_in_docx(f):
                    future = executor.submit(
                        load_docx_table_stream,
                        f,
                        content_columns=None,
                        metadata_columns=["景点ID", "景区名称", "景点名称"],
                        batch_size=FILE_READ_BATCH,
                    )
                else:
                    future = executor.submit(load_text_or_docx_stream, f)
            else:
                future = executor.submit(load_text_or_docx_stream, f)
            future_to_file[future] = f

        for future in tqdm(as_completed(future_to_file), total=len(files_to_process), desc="文件加载进度"):
            f = future_to_file[future]
            try:
                doc_generator = future.result()
                batches = list(doc_generator)  # 每个 batch 是一个 List[Document]
                all_doc_batches.extend(batches)
                print(f"✅ {f} 加载完成，共 {sum(len(b) for b in batches)} 条记录")
            except Exception as e:
                print(f"❌ 加载 {f} 时出错: {e}")

    if not all_doc_batches:
        print("❌ 未加载到任何文档，终止处理。")
        return vector_store

    # ---------- 文本分块（批量处理） ----------
    print("🔪 开始文本分块...")
    all_chunks = []  # 存储所有最终 chunk (Document 对象)
    pending_split_docs = []  # 临时存放待切割的长文档

    for batch_docs in tqdm(all_doc_batches, desc="整理文档"):
        for doc in batch_docs:
            if len(doc.page_content) < chunk_size * 0.8:
                all_chunks.append(doc)  # 足够短，直接作为 chunk
            else:
                pending_split_docs.append(doc)
                # ✅ 每积累一定数量的长文档就切割一次，提升效率
                if len(pending_split_docs) >= 500:
                    all_chunks.extend(splitter.split_documents(pending_split_docs))
                    pending_split_docs.clear()

    # 处理剩余的长文档
    if pending_split_docs:
        all_chunks.extend(splitter.split_documents(pending_split_docs))
        pending_split_docs.clear()

    print(f"📏 分块完成，共产生 {len(all_chunks)} 个文本块。")

    # ---------- 清洗元数据（统一处理，避免重复） ----------
    print("🧹 正在清洗元数据...")
    for doc in tqdm(all_chunks, desc="清洗元数据"):
        doc.metadata = clean_metadata(doc.metadata)

    # ---------- 一次性（大批次）写入 Chroma ----------
    print(f"💾 开始批量写入向量数据库（每批 {chrome_write_batch} 条）...")
    total_chunks = len(all_chunks)
    for start in tqdm(range(0, total_chunks, chrome_write_batch), desc="写入进度"):
        batch = all_chunks[start:start+chrome_write_batch]
        vector_store.add_documents(batch)
        # ✅ 仅在极少数情况下进行垃圾回收
        if start % (chrome_write_batch * 4) == 0 and start > 0:
            gc.collect()

    vector_store.persist()
    print(f"✨ 向量库构建完成！共嵌入 {total_chunks} 个文本块，存储路径: {persist_dir}")
    return vector_store
# ===============================================================

# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 运行前请确保文件路径存在，否则会报错
    vector_db = process_documents_to_chroma(
        file_paths=FILE_PATHS,
        persist_dir=CHROMA_PERSIST_DIR,
    )
    retriever = vector_db.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke("灵山大照壁的文化意义")
    for doc in docs:
        print(doc.page_content[:200] + "...")
# ================================================