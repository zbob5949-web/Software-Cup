"""
build_kb_index.py
一次性脚本：解析 RAG 知识库源文件 → 分块 → embedding → 存入 ChromaDB。
运行：
    python app/scripts/build_kb_index.py
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.vector_store import build_index

# ---- RAG 源文件 ----
RAG_DIR = Path("C:/Users/却绫/Desktop/rag知识库")

KEYWORD_POOL = [
    "灵山大佛", "灵山梵宫", "九龙灌浴", "五印坛城", "祥符禅寺",
    "天下第一掌", "百子戏弥勒", "阿育王柱", "降魔浮雕",
    "灵山大照壁", "五明桥", "佛足坛", "五智门", "菩提大道",
    "曼飞龙塔", "无尽意斋", "佛教文化博览馆",
    "拈花湾", "拈花广场", "梵天花海", "香月花街", "拈花堂", "五灯湖", "鹿鸣谷",
    "门票", "票价", "开放时间", "演出", "路线", "游览",
    "祈福", "文化", "历史", "禅意", "素斋", "交通",
]

def extract_keywords(text: str) -> str:
    found = [kw for kw in KEYWORD_POOL if kw in text]
    return ",".join(found[:10]) if found else "灵山胜境"

def safe_id(text: str) -> str:
    return re.sub(r"[^\w一-鿿]", "_", text)[:60]


# ============================================================
# Parser 1: 景区结构化数据集（按 ====SPLIT==== 分隔）
# ============================================================
def parse_structured_dataset(text: str) -> list[dict]:
    blocks = re.split(r"====SPLIT====", text)
    chunks = []

    for idx, block in enumerate(blocks):
        block = block.strip()
        if not block or block.startswith("# "):
            continue

        fields = {}
        current_key = None
        current_lines = []

        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^([^\s：:]+)[：:]\s*(.*)", line)
            if m:
                if current_key:
                    fields[current_key] = "\n".join(current_lines).strip()
                current_key = m.group(1)
                current_lines = [m.group(2)]
            else:
                if current_key:
                    current_lines.append(line)
        if current_key:
            fields[current_key] = "\n".join(current_lines).strip()
        if not fields:
            continue

        aid = fields.get("景点ID", f"UNK-{idx}")
        name = fields.get("景点名称", "未知景点")
        area = fields.get("所属景区", "灵山胜境")

        parts = [f"景点名称：{name}", f"所属景区：{area}"]
        for k in ["位置", "参数", "功能", "文化内涵", "详细介绍", "游玩亮点", "开放信息", "备注"]:
            v = fields.get(k, "").strip()
            if v:
                parts.append(f"{k}：{v}")
        full_text = "\n".join(parts)

        meta = {
            "source_file": "structured_dataset",
            "attraction_id": aid,
            "attraction_name": name,
            "scenic_area": area,
            "chunk_type": "attraction_full",
            "keywords": extract_keywords(full_text),
            "char_length": len(full_text),
        }
        chunks.append({"id": f"struct_{aid}", "text": full_text, "metadata": meta})

        # 详细介绍 >500 字拆子 chunk
        detail = fields.get("详细介绍", "")
        if len(detail) > 500:
            sentences = re.split(r"(?<=[。！？])", detail)
            buf, seg = "", 0
            for s in sentences:
                if len(buf) + len(s) > 400 and buf:
                    chunks.append({
                        "id": f"struct_{aid}_d{seg}",
                        "text": f"景点名称：{name}\n\n{buf.strip()}",
                        "metadata": {**meta, "chunk_type": "detail_segment"},
                    })
                    buf = s
                    seg += 1
                else:
                    buf += s
            if buf.strip():
                chunks.append({
                    "id": f"struct_{aid}_d{seg}",
                    "text": f"景点名称：{name}\n\n{buf.strip()}",
                    "metadata": {**meta, "chunk_type": "detail_segment"},
                })

    return chunks


# ============================================================
# Parser 2: 表格内容（按项目列合并多行）
# ============================================================
def parse_table_data(text: str) -> list[dict]:
    rows = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("|") and line.endswith("|") and "---" not in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2 and cells[0] and cells[1]:
                rows.append(cells)
    if rows and rows[0][0] in ("项目", "景点"):
        rows = rows[1:]

    groups = {}
    for row in rows:
        topic = row[0].strip()
        detail = row[1].strip() if len(row) > 1 else ""
        groups.setdefault(topic, []).append(detail)

    chunks = []
    for topic, details in groups.items():
        cleaned = []
        for d in details:
            m = re.match(r"^([^：:]+)[：:]\s*(.*)", d)
            cleaned.append(f"{m.group(1)}：{m.group(2)}" if m else d)
        text = f"## {topic}\n\n" + "\n".join(cleaned)
        chunks.append({
            "id": f"table_{safe_id(topic)}",
            "text": text,
            "metadata": {
                "source_file": "table_data",
                "attraction_id": None, "attraction_name": topic,
                "scenic_area": "灵山胜境", "chunk_type": "table_topic",
                "keywords": extract_keywords(text), "char_length": len(text),
            },
        })
    return chunks


# ============================================================
# Parser 3: 叙述性 Markdown（按 ## 标题切分）
# ============================================================
def parse_narrative_guide(text: str) -> list[dict]:
    sections = re.split(r"\n(?=## )", text)
    chunks = []

    for idx, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        first_line = section.split("\n")[0]
        hm = re.match(r"^#{1,2}\s+(.+?)(?:\s*⚠️.*)?$", first_line)
        heading = hm.group(1) if hm else f"section_{idx}"

        cleaned = re.sub(r"⚠️\s*此处原有详细数据表格.*?(\n|$)", "", section).strip()
        if not cleaned or len(cleaned) < 30:
            continue

        if any(w in heading for w in ["历史", "渊源", "兴衰", "缘起", "小灵山"]):
            stype = "history"
        elif any(w in heading for w in ["文化", "内涵", "艺术", "祈福", "融合", "传承"]):
            stype = "culture"
        elif any(w in heading for w in ["路线", "游览"]):
            stype = "route"
        elif any(w in heading for w in ["贴士", "门票", "餐饮", "住宿", "交通", "建议"]):
            stype = "tips"
        elif any(w in heading for w in ["景点", "大佛", "梵宫", "灌浴", "坛城", "禅寺"]):
            stype = "attraction_detail"
        else:
            stype = "general"

        chunks.append({
            "id": f"narr_{safe_id(heading)}",
            "text": cleaned,
            "metadata": {
                "source_file": "narrative_guide",
                "attraction_id": None, "attraction_name": heading,
                "scenic_area": "灵山胜境", "chunk_type": "narrative_section",
                "keywords": extract_keywords(cleaned), "char_length": len(cleaned),
                "section_type": stype,
            },
        })
    return chunks


# ============================================================
def main():
    sources = {
        "structured_dataset": RAG_DIR / "景区结构化数据集",
        "table_data": RAG_DIR / "灵山胜境：历史、文化、景点特色与个性化游览指南 表格内容",
        "narrative_guide": RAG_DIR / "灵山胜境：历史、文化、景点特色与个性化游览指南文字",
    }

    all_chunks = []
    for key, path in sources.items():
        if not path.exists():
            print(f"WARNING: 文件不存在: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if key == "structured_dataset":
            chunks = parse_structured_dataset(text)
        elif key == "table_data":
            chunks = parse_table_data(text)
        else:
            chunks = parse_narrative_guide(text)
        print(f"  {key}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"\nTotal: {len(all_chunks)} chunks, building index...\n")
    docs = [c["text"] for c in all_chunks]
    metas = [c["metadata"] for c in all_chunks]
    ids = [c["id"] for c in all_chunks]
    build_index(docs, metas, ids)
    print(f"\nDone! Index stored at data/chroma_db/")


if __name__ == "__main__":
    main()
