from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.routers.admin.schemas import DigitalHumanForm, DigitalHumanUpdateForm
from app.utils.response import Result

router = APIRouter()


def digital_row(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "voice_name": row.get("voice_name"),
        "voice_style": row.get("voice_style"),
        "appearance": row.get("appearance"),
        "clothing": row.get("clothing"),
        "cultural_style": row.get("cultural_style"),
        "keywords": row.get("keywords"),
        "is_active": bool(row.get("is_active")),
        "created_at": str(row.get("created_at")) if row.get("created_at") else None,
        "updated_at": str(row.get("updated_at")) if row.get("updated_at") else None,
    }


@router.get("/api/admin/digital-humans")
@router.get("/admin/digital-humans")
def list_digital_humans(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM digital_human_configs ORDER BY is_active DESC, id DESC")
        rows = cursor.fetchall()
    return ok({"items": [digital_row(r) for r in rows]})


@router.get("/api/digital-human/current")
def current_digital_human(db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM digital_human_configs WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    if not row:
        return Result(404, "未配置数字人形象")
    return ok(digital_row(row))


@router.post("/api/admin/digital-humans")
@router.post("/admin/digital-humans")
def create_digital_human(form: DigitalHumanForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            if form.is_active:
                cursor.execute("UPDATE digital_human_configs SET is_active = FALSE")
            cursor.execute(
                """
                INSERT INTO digital_human_configs
                (name, voice_name, voice_style, appearance, clothing, cultural_style, keywords, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (form.name, form.voice_name, form.voice_style, form.appearance, form.clothing, form.cultural_style, form.keywords, form.is_active),
            )
            item_id = cursor.lastrowid
        db.commit()
        return ok({"id": item_id}, "数字人形象创建成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"数字人形象创建失败：{exc}")


@router.put("/api/admin/digital-humans/{item_id}")
@router.put("/admin/digital-humans/{item_id}")
def update_digital_human(item_id: int, form: DigitalHumanUpdateForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    fields = []
    params = []
    for name in ["name", "voice_name", "voice_style", "appearance", "clothing", "cultural_style", "keywords", "is_active"]:
        value = getattr(form, name)
        if value is not None:
            fields.append(f"{name} = %s")
            params.append(value)
    if not fields:
        return Result(400, "没有需要更新的字段")
    try:
        with db.cursor() as cursor:
            if form.is_active is True:
                cursor.execute("UPDATE digital_human_configs SET is_active = FALSE WHERE id <> %s", (item_id,))
            cursor.execute(f"UPDATE digital_human_configs SET {', '.join(fields)} WHERE id = %s", params + [item_id])
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "数字人形象不存在")
        db.commit()
        return ok({"id": item_id}, "数字人形象更新成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"数字人形象更新失败：{exc}")


@router.delete("/api/admin/digital-humans/{item_id}")
@router.delete("/admin/digital-humans/{item_id}")
def delete_digital_human(item_id: int, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM digital_human_configs WHERE id = %s", (item_id,))
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "数字人形象不存在")
        db.commit()
        return ok({"id": item_id}, "数字人形象删除成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"数字人形象删除失败：{exc}")
