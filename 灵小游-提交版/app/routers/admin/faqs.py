from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.routers.admin.schemas import FAQForm, FAQUpdateForm
from app.utils.response import Result

router = APIRouter()


def faq_row(row):
    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "category": row.get("category"),
        "keywords": row.get("keywords"),
        "sort_order": row.get("sort_order", 0),
        "is_active": bool(row.get("is_active")),
        "created_at": str(row.get("created_at")) if row.get("created_at") else None,
    }


@router.get("/api/admin/faqs")
@router.get("/admin/faqs")
def admin_list_faqs(
    category: Optional[str] = Query(None, max_length=50),
    keyword: Optional[str] = Query(None, max_length=100),
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    where = []
    params = []
    if not include_inactive:
        where.append("is_active = TRUE")
    if category:
        where.append("category = %s")
        params.append(category)
    if keyword:
        where.append("(question LIKE %s OR answer LIKE %s OR keywords LIKE %s)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    offset = (page - 1) * page_size
    with db.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM faqs {where_sql}", params)
        total = cursor.fetchone()["cnt"]
        cursor.execute(
            f"""
            SELECT id, question, answer, category, keywords, sort_order, is_active, created_at
            FROM faqs {where_sql}
            ORDER BY sort_order ASC, id DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()
    return ok({"total": total, "page": page, "page_size": page_size, "faqs": [faq_row(r) for r in rows]})


@router.get("/api/admin/faqs/{faq_id}")
@router.get("/admin/faqs/{faq_id}")
def admin_get_faq(faq_id: int, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT id, question, answer, category, keywords, sort_order, is_active, created_at FROM faqs WHERE id = %s",
            (faq_id,),
        )
        row = cursor.fetchone()
    if not row:
        return Result(404, "FAQ不存在")
    return ok(faq_row(row))


@router.post("/api/admin/faqs")
@router.post("/admin/faqs")
def admin_create_faq(form: FAQForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO faqs (question, answer, category, keywords, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (form.question.strip(), form.answer.strip(), form.category, form.keywords, form.sort_order, form.is_active),
            )
            faq_id = cursor.lastrowid
        db.commit()
        return ok({"id": faq_id}, "FAQ创建成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"FAQ创建失败：{exc}")


@router.put("/api/admin/faqs/{faq_id}")
@router.put("/admin/faqs/{faq_id}")
def admin_update_faq(faq_id: int, form: FAQUpdateForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    fields = []
    params = []
    for name in ["question", "answer", "category", "keywords", "sort_order", "is_active"]:
        value = getattr(form, name)
        if value is not None:
            fields.append(f"{name} = %s")
            params.append(value.strip() if isinstance(value, str) else value)
    if not fields:
        return Result(400, "没有需要更新的字段")
    try:
        with db.cursor() as cursor:
            cursor.execute(f"UPDATE faqs SET {', '.join(fields)} WHERE id = %s", params + [faq_id])
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "FAQ不存在")
        db.commit()
        return ok({"id": faq_id}, "FAQ更新成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"FAQ更新失败：{exc}")


@router.delete("/api/admin/faqs/{faq_id}")
@router.delete("/admin/faqs/{faq_id}")
def admin_delete_faq(
    faq_id: int,
    hard: bool = False,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        with db.cursor() as cursor:
            if hard:
                cursor.execute("DELETE FROM faqs WHERE id = %s", (faq_id,))
            else:
                cursor.execute("UPDATE faqs SET is_active = FALSE WHERE id = %s", (faq_id,))
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "FAQ不存在")
        db.commit()
        return ok({"id": faq_id, "hard": hard}, "FAQ删除成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"FAQ删除失败：{exc}")
