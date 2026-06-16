# ==================== FAQ知识库模块 ====================
# 接口16-17：FAQ列表 / FAQ智能匹配
from fastapi import APIRouter, Depends, Query
from dependencies import get_db
from utils.faq_matcher import match_faq as _match_faq_smart
from utils.response import Result

router = APIRouter()

# ===== 接口16：FAQ分类列表 =====
# 分类：开放时间/票价/演出/路线推荐/景点介绍/文化背景/餐饮/住宿/交通/实用贴士/其他
@router.get("/api/faqs")
def get_faqs(category: str = Query(None, max_length=30), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            if category:
                cursor.execute(
                    "SELECT id, question, answer, category FROM faqs "
                    "WHERE is_active = TRUE AND category = %s ORDER BY sort_order ASC", (category,)
                )
            else:
                cursor.execute(
                    "SELECT id, question, answer, category FROM faqs "
                    "WHERE is_active = TRUE ORDER BY sort_order ASC"
                )
            rows = cursor.fetchall()
            faqs = [{"id": r["id"], "question": r["question"],
                     "answer": r["answer"], "category": r["category"]} for r in rows]
        return Result(200, "success", {"faqs": faqs})
    except Exception as e:
        print(f"[faq 错误] {e}")
        return Result(50001, "获取FAQ失败")

# ===== 接口17：FAQ智能匹配 =====
# 说明：三级匹配（精确→模糊→关键词），score越高越准。未匹配时 matched=false
@router.get("/api/faqs/match")
def match_faq(q: str = Query("", max_length=100), db=Depends(get_db)):
    if not q.strip():
        return Result(40001, "请输入问题")
    try:
        with db.cursor() as cursor:
            results = _match_faq_smart(cursor, q.strip())
            if results:
                best = results[0]
                return Result(200, "success", {
                    "matched": True,
                    "score": best["score"],
                    "faq": {"id": best["id"], "question": best["question"],
                            "answer": best["answer"], "category": best["category"]}
                })
            return Result(200, "success", {"matched": False, "score": 0, "faq": None})
    except Exception as e:
        print(f"[faq match 错误] {e}")
        return Result(50001, "匹配失败")
