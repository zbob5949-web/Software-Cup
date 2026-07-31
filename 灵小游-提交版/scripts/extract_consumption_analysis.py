"""Extract the small, aggregate subset used by the admin consumption report."""

from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree.ElementTree import iterparse, fromstring


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\却绫\Desktop\比赛\软件杯\示范景区公开资料包\景点景区旅游数据行为分析数据.xlsx"
)
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/consumption_analysis.json")


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall(f"{NS}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{NS}t")))
    return values


def excel_date(value: str) -> str:
    try:
        return (date(1899, 12, 30) + timedelta(days=float(value))).isoformat()
    except (TypeError, ValueError):
        return "未知"


def number(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def main() -> None:
    with zipfile.ZipFile(SOURCE) as zf:
        strings = shared_strings(zf)
        columns: list[str] = []
        totals = Counter()
        genders = Counter()
        age_groups = Counter()
        attraction_types = Counter()
        months = defaultdict(lambda: {"visitors": 0, "revenue": 0.0})
        satisfaction_sum = 0.0
        satisfaction_count = 0
        total_group_size = 0.0
        rows = 0

        stream = zf.open("xl/worksheets/sheet1.xml")
        for _, element in iterparse(stream, events=("end",)):
            if element.tag != f"{NS}row":
                continue
            values: dict[str, str] = {}
            for cell in element.findall(f"{NS}c"):
                value = cell.find(f"{NS}v")
                if value is None:
                    continue
                raw = value.text or ""
                if cell.attrib.get("t") == "s":
                    raw = strings[int(raw)] if raw else ""
                values[cell.attrib["r"].rstrip("0123456789")] = raw
            if not columns:
                columns = [values.get(chr(ord("A") + index), "") for index in range(17)]
                element.clear()
                continue
            rows += 1
            costs = {
                "ticket": number(values.get("J")),
                "food": number(values.get("K")),
                "shopping": number(values.get("L")),
                "transport": number(values.get("M")),
                "entertainment": number(values.get("N")),
                "total": number(values.get("O")),
            }
            totals.update(costs)
            gender = values.get("D") or "未知"
            genders[gender] += 1
            age = number(values.get("C"))
            age_groups[
                "18岁以下" if age < 18 else "18-30岁" if age <= 30 else "31-45岁" if age <= 45 else "46-60岁" if age <= 60 else "60岁以上"
            ] += 1
            attraction_types[values.get("G") or "未知"] += 1
            visit_date = excel_date(values.get("H", ""))
            month = visit_date[:7] if visit_date != "未知" else "未知"
            months[month]["visitors"] += 1
            months[month]["revenue"] += costs["total"]
            satisfaction = number(values.get("Q"))
            if satisfaction:
                satisfaction_sum += satisfaction
                satisfaction_count += 1
            total_group_size += number(values.get("P"))
            element.clear()

    revenue = totals["total"]
    result = {
        "source": SOURCE.name,
        "basis_columns": columns,
        "record_count": rows,
        "financial": {
            "total_revenue": round(revenue, 2),
            "average_spend": round(revenue / rows, 2) if rows else 0,
            "average_group_size": round(total_group_size / rows, 2) if rows else 0,
            "average_satisfaction": round(satisfaction_sum / satisfaction_count, 2) if satisfaction_count else 0,
            "cost_breakdown": [
                {"key": key, "name": name, "amount": round(totals[key], 2), "ratio": round(totals[key] / revenue * 100, 2) if revenue else 0}
                for key, name in (("ticket", "门票消费"), ("food", "餐饮消费"), ("shopping", "购物消费"), ("transport", "交通消费"), ("entertainment", "娱乐消费"))
            ],
        },
        "segments": {
            "gender": [{"name": key, "count": value} for key, value in genders.most_common()],
            "age_groups": [{"name": key, "count": age_groups[key]} for key in ("18岁以下", "18-30岁", "31-45岁", "46-60岁", "60岁以上")],
            "attraction_types": [{"name": key, "count": value} for key, value in attraction_types.most_common(8)],
        },
        "monthly": [{"month": key, **value} for key, value in sorted(months.items()) if key != "未知"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": rows, "output": str(OUTPUT), "columns": columns}, ensure_ascii=False))


if __name__ == "__main__":
    main()
