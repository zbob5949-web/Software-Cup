"""管理后台 - 数字人形象管理接口。

接口编号：ADMIN-DH-01 ~ ADMIN-DH-04，外加游客端 PUBLIC-DH-01
用途：配置数字人的声音、外观、服装、文化关键词等形象参数。
"""
from fastapi import APIRouter, Depends

from dependencies import get_current_admin_user, get_db
from routers.admin.common import ok
from routers.admin.schemas import DigitalHumanForm, DigitalHumanUpdateForm
from utils.response import Result

router = APIRouter()


def digital_row(row):
    """把数字人配置数据库行转换成前端统一 JSON 结构。"""
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


# ADMIN-DH-01：数字人形象列表接口，用于管理后台查看所有形象配置。
@router.get("/api/admin/digital-humans")
@router.get("/admin/digital-humans")
def list_digital_humans(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    """查询全部数字人形象配置，启用项优先显示。"""
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM digital_human_configs ORDER BY is_active DESC, id DESC")
        rows = cursor.fetchall()
    return ok({"items": [digital_row(r) for r in rows]})


# PUBLIC-DH-01：当前数字人形象接口，游客端可读取正在启用的形象。
@router.get("/api/digital-human/current")
def current_digital_human(db=Depends(get_db)):
    """查询当前启用的数字人形象，供游客端渲染和TTS配置使用。"""
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM digital_human_configs WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    if not row:
        return Result(404, "未配置数字人形象")
    return ok(digital_row(row))


# ADMIN-DH-02：数字人形象新增接口，用于创建新的声音/外观/服装方案。
@router.post("/api/admin/digital-humans")
@router.post("/admin/digital-humans")
def create_digital_human(form: DigitalHumanForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    """新增数字人形象；若设置为启用，会自动停用其他形象。"""
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
                (form.name, form.voice_name, form.voice_style, form.appearance, form.clothing,
                 form.cultural_style, form.keywords, form.is_active),
            )
            item_id = cursor.lastrowid
        db.commit()
        return ok({"id": item_id}, "数字人形象创建成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"数字人形象创建失败：{exc}")


# ADMIN-DH-03：数字人形象更新接口，用于修改形象参数或切换启用状态。
@router.put("/api/admin/digital-humans/{item_id}")
@router.put("/admin/digital-humans/{item_id}")
def update_digital_human(item_id: int, form: DigitalHumanUpdateForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    """按 ID 局部更新数字人形象配置。"""
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


# ADMIN-DH-04：数字人形象删除接口，用于移除不再使用的形象方案。
@router.delete("/api/admin/digital-humans/{item_id}")
@router.delete("/admin/digital-humans/{item_id}")
def delete_digital_human(item_id: int, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    """按 ID 删除数字人形象配置。"""
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
