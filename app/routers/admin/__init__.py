from fastapi import APIRouter

from app.routers.admin import dashboard, digital_human, faqs, knowledge, reports

router = APIRouter()
router.include_router(faqs.router)
router.include_router(knowledge.router)
router.include_router(digital_human.router)
router.include_router(dashboard.router)
router.include_router(reports.router)
