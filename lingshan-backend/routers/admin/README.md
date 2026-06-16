# 管理后台后端包说明

本目录专门存放管理后台相关路由与模型，`main.py` 只需引入 `routers.admin.router`。

## 文件组织

| 文件 | 职责 |
| --- | --- |
| `__init__.py` | 汇总并注册所有管理后台子路由 |
| `faqs.py` | FAQ 增删改查 |
| `knowledge.py` | Dify 知识库文档列表、详情、上传、更新、删除、检索 |
| `digital_human.py` | 数字人形象声音、外观、服装、关键词配置 |
| `dashboard.py` | 数据大屏指标聚合 |
| `reports.py` | 游客感受度/情绪趋势报告 |
| `schemas.py` | 管理后台请求体模型 |
| `common.py` | 管理后台公共响应、日期、关键词工具 |

## 接口编号

### FAQ 管理

- `ADMIN-FAQ-01`：`GET /api/admin/faqs`
- `ADMIN-FAQ-02`：`GET /api/admin/faqs/{faq_id}`
- `ADMIN-FAQ-03`：`POST /api/admin/faqs`
- `ADMIN-FAQ-04`：`PUT /api/admin/faqs/{faq_id}`
- `ADMIN-FAQ-05`：`DELETE /api/admin/faqs/{faq_id}`

### Dify 知识库管理

- `ADMIN-KB-01`：`GET /api/admin/knowledge/config`
- `ADMIN-KB-02`：`GET /api/admin/knowledge/documents`
- `ADMIN-KB-03`：`GET /api/admin/knowledge/documents/{document_id}`
- `ADMIN-KB-04`：`POST /api/admin/knowledge/documents/text`
- `ADMIN-KB-05`：`POST /api/admin/knowledge/documents/file`
- `ADMIN-KB-06`：`PUT /api/admin/knowledge/documents/{document_id}/text`
- `ADMIN-KB-07`：`PUT /api/admin/knowledge/documents/{document_id}/file`
- `ADMIN-KB-08`：`DELETE /api/admin/knowledge/documents/{document_id}`
- `ADMIN-KB-09`：`GET /api/admin/knowledge/indexing-status/{batch}`
- `ADMIN-KB-10`：`POST /api/admin/knowledge/retrieve`

### 数字人形象管理

- `ADMIN-DH-01`：`GET /api/admin/digital-humans`
- `ADMIN-DH-02`：`POST /api/admin/digital-humans`
- `ADMIN-DH-03`：`PUT /api/admin/digital-humans/{item_id}`
- `ADMIN-DH-04`：`DELETE /api/admin/digital-humans/{item_id}`
- `PUBLIC-DH-01`：`GET /api/digital-human/current`

### 数据大屏

- `ADMIN-DASH-01`：`GET /api/admin/dashboard/overview`

### 游客感受度报告

- `ADMIN-REPORT-01`：`GET /api/admin/reports/sentiment`

说明：所有 `/api/admin/**` 和 `/admin/**` 接口均需要管理员 Token，`PUBLIC-DH-01` 面向游客端读取当前启用形象，不需要管理员权限。
