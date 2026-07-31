from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.routers.admin.schemas import DigitalHumanForm, DigitalHumanUpdateForm
from app.services.digital_human_config import MODEL_CATALOG, get_active_profile, get_model_profile
from app.utils.response import Result

router = APIRouter()


def profile_for_row(row):
    profile = get_model_profile(row.get("model_key"))
    return {
        "id": row.get("id"),
        "model_key": row.get("model_key") or profile["key"],
        "model_label": profile["label"],
        "display_mode": profile["display_mode"],
        "model_dir": profile["model_dir"],
        "asset_url": "/live2d/index.html?embed=1&model=" + profile["model_dir"] + "&api=http%3A%2F%2F127.0.0.1%3A8000",
        "name": row.get("name") or profile["label"],
        "voice_name": row.get("voice_name") or profile["default_voice"],
        "voice_style": row.get("voice_style"),
        "appearance": row.get("appearance") or profile["appearance"],
        "clothing": row.get("clothing") or profile["clothing"],
        "cultural_style": row.get("cultural_style") or profile["cultural_style"],
        "keywords": row.get("keywords") or profile["keywords"],
        "is_active": bool(row.get("is_active")),
        "created_at": str(row.get("created_at")) if row.get("created_at") else None,
        "updated_at": str(row.get("updated_at")) if row.get("updated_at") else None,
    }


def digital_row(row):
    return profile_for_row(row)


@router.get("/api/digital-human/catalog")
@router.get("/api/admin/digital-human/catalog")
def digital_human_catalog():
    return ok({
        "items": [
            {
                **profile,
                "model_key": profile["key"],
                "model_label": profile["label"],
                "voice_name": profile["default_voice"],
            }
            for profile in MODEL_CATALOG.values()
        ]
    })


@router.get("/api/admin/digital-humans")
@router.get("/admin/digital-humans")
def list_digital_humans(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM digital_human_configs ORDER BY is_active DESC, id DESC")
        rows = cursor.fetchall()
    return ok({"items": [digital_row(r) for r in rows]})


@router.get("/api/digital-human/current")
def current_digital_human():
    return ok(get_active_profile())


@router.post("/api/admin/digital-humans")
@router.post("/admin/digital-humans")
def create_digital_human(form: DigitalHumanForm, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    if form.model_key not in MODEL_CATALOG:
        return Result(400, "模型不在可选目录中")
    try:
        with db.cursor() as cursor:
            if form.is_active:
                cursor.execute("UPDATE digital_human_configs SET is_active = FALSE")
            cursor.execute(
                """
                INSERT INTO digital_human_configs
                (model_key, name, voice_name, voice_style, appearance, clothing, cultural_style, keywords, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (form.model_key, form.name, form.voice_name, form.voice_style, form.appearance, form.clothing, form.cultural_style, form.keywords, form.is_active),
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
    for name in ["model_key", "name", "voice_name", "voice_style", "appearance", "clothing", "cultural_style", "keywords", "is_active"]:
        value = getattr(form, name)
        if value is not None:
            if name == "model_key" and value not in MODEL_CATALOG:
                return Result(400, "模型不在可选目录中")
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