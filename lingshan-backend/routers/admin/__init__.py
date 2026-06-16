"""管理后台路由聚合包。这段代码是一个 FastAPI 路由聚合模块，用于统一管理和组织所有管理后台的子路由。

文件组织：
- faqs.py：FAQ 管理
- knowledge.py：Dify 知识库管理
- digital_human.py：数字人形象管理
- dashboard.py：数据大屏
- reports.py：游客感受度报告

main.py 只需要 include_router(admin.router)，这里负责汇总全部管理后台子路由。
"""
from fastapi import APIRouter

from routers.admin import dashboard, digital_human, faqs, knowledge, reports

#本文件创建主路由器
router = APIRouter()

#依次挂载各个子模块的路由器
router.include_router(faqs.router)
router.include_router(knowledge.router)
router.include_router(digital_human.router)
router.include_router(dashboard.router)
router.include_router(reports.router)
