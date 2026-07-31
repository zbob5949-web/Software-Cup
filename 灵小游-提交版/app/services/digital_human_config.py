from __future__ import annotations

from typing import Any

from app.database import get_db_connection


MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "live2d_haru": {
        "key": "live2d_haru", "label": "Haru 灵小游", "model_dir": "Haru", "display_mode": "live2d",
        "default_voice": "zh-CN-XiaoyiNeural", "keywords": "Haru,少女,亲和,轻快,互动",
        "appearance": "当前主形象，表情和口型驱动完整", "clothing": "樱色景区导览制服", "cultural_style": "亲和、轻盈、适合景区讲解",
    },
    "live2d_hiyori": {
        "key": "live2d_hiyori", "label": "Hiyori 灵小游", "model_dir": "Hiyori", "display_mode": "live2d",
        "default_voice": "zh-CN-XiaoxiaoNeural", "keywords": "Hiyori,清新,温柔,自然,亲子",
        "appearance": "Hiyori Live2D 形象，适合轻松导览", "clothing": "青绿色自然风导览服", "cultural_style": "清新、温柔、适合亲子与自然路线",
    },
    "live2d_mao": {
        "key": "live2d_mao", "label": "Mao 灵小游", "model_dir": "Mao", "display_mode": "live2d",
        "default_voice": "zh-CN-XiaoyiNeural", "keywords": "Mao,活泼,元气,年轻,互动",
        "appearance": "Mao Live2D 形象，适合互动问答", "clothing": "明快活泼的景区导览服", "cultural_style": "元气、活泼、强调互动体验",
    },
}

DEFAULT_MODEL_KEY = "live2d_haru"


def get_model_profile(model_key: str | None = None) -> dict[str, Any]:
    return dict(MODEL_CATALOG.get(model_key or DEFAULT_MODEL_KEY, MODEL_CATALOG[DEFAULT_MODEL_KEY]))


def get_active_profile() -> dict[str, Any]:
    profile = get_model_profile()
    conn = get_db_connection()
    if not conn:
        return profile
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM digital_human_configs WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
        if not row:
            return profile
        catalog = get_model_profile(row.get("model_key"))
        profile.update({
            "id": row.get("id"), "model_key": catalog["key"], "model_dir": catalog["model_dir"],
            "name": row.get("name") or catalog["label"], "voice_name": row.get("voice_name") or catalog["default_voice"],
            "voice_style": row.get("voice_style"), "appearance": row.get("appearance") or catalog["appearance"],
            "clothing": row.get("clothing") or catalog["clothing"], "cultural_style": row.get("cultural_style") or catalog["cultural_style"],
            "keywords": row.get("keywords") or catalog["keywords"], "is_active": True,
            "speed": float(row.get("speed") or 1.0), "volume": float(row.get("volume") or 0.8),
        })
        return profile
    except Exception:
        return profile
    finally:
        conn.close()


def get_active_voice() -> str:
    return str(get_active_profile().get("voice_name") or MODEL_CATALOG[DEFAULT_MODEL_KEY]["default_voice"])