from pathlib import Path
from zipfile import ZipFile
import re
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent
DOCX_FILES = [
    BASE_DIR / "灵山胜境 景点结构化数据集.docx",
    BASE_DIR / "灵山胜境：历史、文化、景点特色与个性化游览指南.docx",
]
OUTPUT_FILE = BASE_DIR / "dify_knowledge_chunks.md"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def paragraph_text(node: ET.Element) -> str:
    parts = []
    for child in node.iter():
        if child.tag == f"{{{NS['w']}}}t":
            parts.append(child.text or "")
        elif child.tag == f"{{{NS['w']}}}tab":
            parts.append(" ")
        elif child.tag == f"{{{NS['w']}}}br":
            parts.append("\n")
    return clean_text("".join(parts))


def table_rows(table: ET.Element) -> list[list[str]]:
    rows = []
    for row in table.findall("w:tr", NS):
        cells = []
        for cell in row.findall("w:tc", NS):
            texts = [paragraph_text(p) for p in cell.findall(".//w:p", NS)]
            cells.append(clean_text("；".join(t for t in texts if t)))
        if any(cells):
            rows.append(cells)
    return rows


def extract_blocks(docx_path: Path) -> list[tuple[str, str | list[list[str]]]]:
    with ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find("w:body", NS)
    if body is None:
        return []

    blocks: list[tuple[str, str | list[list[str]]]] = []
    for child in body:
        if child.tag == f"{{{NS['w']}}}p":
            text = paragraph_text(child)
            if text:
                blocks.append(("p", text))
        elif child.tag == f"{{{NS['w']}}}tbl":
            rows = table_rows(child)
            if rows:
                blocks.append(("table", rows))
    return blocks


def is_heading(text: str) -> bool:
    if len(text) > 64:
        return False
    landmark_prefixes = (
        "灵山大佛",
        "灵山梵宫",
        "九龙灌浴",
        "五印坛城",
        "祥符禅寺",
        "个性化游览路线推荐",
        "门票与实用信息",
    )
    if len(text) <= 36 and text.startswith(landmark_prefixes) and "：" in text:
        return True
    if len(text) > 48:
        return False
    if re.match(r"^(第[一二三四五六七八九十\d]+[章节部分]|[一二三四五六七八九十]+[、.．]|[0-9]+[、.．])", text):
        return True
    if text.endswith(("概述", "介绍", "指南", "特色", "传说", "历史", "文化", "路线", "建议", "服务", "信息")):
        return True
    return False


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？；])", text)
    return [p.strip() for p in pieces if p.strip()]


def chunk_text(title: str, source: str, body: str, max_len: int = 620) -> list[str]:
    body = clean_text(body)
    if not body:
        return []
    sentences = split_sentences(body)
    chunks = []
    current = []
    current_len = 0
    for sentence in sentences:
        projected = current_len + len(sentence)
        if current and projected > max_len:
            chunks.append(format_chunk(title, source, "".join(current)))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len = projected
    if current:
        chunks.append(format_chunk(title, source, "".join(current)))
    return chunks


def format_chunk(title: str, source: str, content: str) -> str:
    keywords = extract_keywords(f"{title} {content}")
    lines = [
        f"## {title}",
        "",
        f"来源：{source}",
        f"关键词：{keywords}",
        "",
        clean_text(content),
    ]
    return "\n".join(lines).strip()


def format_table_row(row: list[str], header: list[str] | None) -> tuple[str, str]:
    if header and len(header) == len(row):
        pairs = [(h.strip(), v.strip()) for h, v in zip(header, row) if v.strip()]
        title = table_title_from_pairs(pairs)
        body = "\n".join(f"{key}：{value}" for key, value in pairs if key.strip())
        return title, body.rstrip("，,；;、：:")

    title = row[0].strip() if row else "表格信息"
    body = "\n".join(cell.strip() for cell in row if cell.strip())
    return title, body.rstrip("，,；;、：:")


def table_title_from_pairs(pairs: list[tuple[str, str]]) -> str:
    preferred = ["景点名称", "类型", "项目", "票种", "路线名称", "名称"]
    for key in preferred:
        for pair_key, value in pairs:
            if key in pair_key and value:
                return value
    for pair_key, value in pairs:
        if value and pair_key not in {"景区名称", "备注", "详细信息"}:
            return value
    return pairs[0][1] if pairs else "表格信息"


def looks_like_header(row: list[str]) -> bool:
    header_markers = {"景区名称", "景点ID", "景点名称", "具体位置", "项目", "详细信息", "票种", "价格", "适用人群"}
    return sum(1 for cell in row if cell in header_markers) >= 2


def extract_keywords(text: str) -> str:
    candidates = [
        "灵山胜境",
        "灵山大佛",
        "九龙灌浴",
        "梵宫",
        "五印坛城",
        "祥符禅寺",
        "天下第一掌",
        "百子戏弥勒",
        "阿育王柱",
        "佛教文化",
        "无锡",
        "太湖",
        "游览路线",
        "亲子",
        "摄影",
        "祈福",
        "素食",
        "交通",
    ]
    found = [kw for kw in candidates if kw in text]
    return "、".join(found[:8]) if found else "灵山胜境"


def build_chunks(docx_path: Path) -> list[str]:
    blocks = extract_blocks(docx_path)
    source = docx_path.name
    chunks = []
    current_title = docx_path.stem
    current_body = []

    for block_type, block in blocks:
        if block_type == "table":
            if current_body:
                chunks.extend(chunk_text(current_title, source, "\n".join(current_body)))
                current_body = []
            rows = block
            if not isinstance(rows, list):
                continue
            header = rows[0] if rows and looks_like_header(rows[0]) else None
            data_rows = rows[1:] if header else rows
            for row in data_rows:
                title, body = format_table_row(row, header)
                if title in {"基本数据", "建造工艺", "佛教意义", "最佳体验", "建筑规模", "核心艺术", "特色体验", "文化地位", "表演内容", "建筑风格", "内部艺术", "历史遗存", "佛教活动"}:
                    title = f"{current_title} - {title}"
                chunks.extend(chunk_text(title, source, body, max_len=760))
            continue

        if not isinstance(block, str):
            continue

        if is_heading(block):
            if current_body:
                chunks.extend(chunk_text(current_title, source, "\n".join(current_body)))
                current_body = []
            current_title = block
        else:
            current_body.append(block)

    if current_body:
        chunks.extend(chunk_text(current_title, source, "\n".join(current_body)))
    return chunks


def main() -> None:
    all_chunks = []
    for docx_path in DOCX_FILES:
        all_chunks.extend(build_chunks(docx_path))

    content = [
        "# 灵山胜境 Dify 知识库分块",
        "",
        "说明：每个二级标题下为一个可独立检索的知识块，保留来源和关键词，适合上传 Dify 后按 Markdown 标题或分隔符切分。",
        "",
    ]
    for index, chunk in enumerate(all_chunks, 1):
        content.append(f"<!-- chunk:{index:03d} -->")
        content.append(chunk)
        content.append("")
        content.append("---")
        content.append("")

    OUTPUT_FILE.write_text("\n".join(content).strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(all_chunks)} chunks to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
