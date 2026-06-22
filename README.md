# 产销预测智能工作台

## 项目简介

产销预测智能工作台是一个基于 FastAPI + 静态 HTML/Vite 的企业级预测管理系统，用于处理产销数据、计算风险评分、分配资源，并提供智能决策支持。

**版本**：v2.2.0  
**技术栈**：FastAPI, SQLAlchemy, MySQL, Python 3.11+, Vite 静态前端  
**部署说明**：详见 [docs/部署指南.md](docs/部署指南.md)

---

## 核心特性

### ✅ 已实现功能

1. **Excel 文件解析**
   - 支持 .xlsx, .xls, .csv 格式
   - 自动验证32个必需字段（含5个SAR渠道）
   - 数据规则校验（供应计算、SAR合计、缺口计算）

2. **智能计算引擎**
   - **分配算法**：5个渠道的可满足/未满足数量分配（供不应求时按比例分配）
   - **风险评分**：6级风险评估（CRITICAL, HIGH, MEDIUM, NORMAL, OVERSTOCK, SUFFICIENT）
   - **汇总统计**：总供应、总SAR、满足率、风险统计

3. **RESTful API**
   - 用户认证（登录/登出）
   - 文件上传与处理
   - 任务管理与查询
   - SKU 明细查询（支持分页、风险过滤）
   - 汇总数据查询

4. **数据持久化**
   - 9个核心数据表（MySQL 8.0+）
   - 37个字段的SKU明细表（v2.2规范）
   - 自动数据验证视图

---

## 快速开始

```powershell
python -m pip install -r requirements-dev.txt
npm install --prefix web
python -B -m uvicorn main:app --host 127.0.0.1 --port 8000
npm run dev --prefix web
```

访问：`http://127.0.0.1:4173/`

演示账号：`admin` / `admin123`、`planner` / `planner123`

## 测试与验收

```powershell
python -m pytest -q
npm run build --prefix web
npx --prefix web playwright test
```

## MVP 功能范围

- 登录：本地账号密码与 Cookie Session。
- 上传解析：支持 `.xlsx`、`.xls`、`.csv`，校验 `预测及排期明细表` 和 32 个核心字段。
- 汇总分析：计算总供应、合计 SAR、供需缺口、满足率与风险标签。
- AI 对话：绑定 `task_id`，读取 `task_summary` 和 `sku_forecast_detail`，对话历史写入数据库。
- 导出：基于 `docs/产销预测及供应表.xlsx` 第二个 sheet 生成 Excel，并新增 `SKU明细`。
- 日志：展示登录、上传、任务处理、导出、AI 对话等关键操作。

## 约束

- 上传大小默认按 50MB 执行。
- MVP 只支持单组织、单任务视角。
- 数据目录限定在项目目录内的 `data/uploads`、`data/exports`、`data/tmp`。
- 当前运行时数据库使用 `10.10.9.104:11123` 上的 MySQL，不允许为了本地运行切换 SQLite。
- 当前 AI 问答调用模型网关，配置见 `.env` 中 `AI_API_BASE`、`AI_API_KEY`、`AI_MODEL`。


### 环境要求

- Python 3.11+
- MySQL 8.0+
- pip

### 安装步骤

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**

编辑 `.env` 文件：
```env
DATABASE_URL=mysql+pymysql://<user>:<password>@10.10.9.104:11123/supply_demand_forecast?charset=utf8mb4
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=50
SECRET_KEY=your-secret-key-here
```

3. **初始化数据库**
```bash
mysql -h 10.10.9.104 -P 11123 -u <user> -p < scripts/init_db_v2.2.sql
```

4. **运行服务**
```bash
python -B -m uvicorn main:app --host 127.0.0.1 --port 8000
```

访问：`http://localhost:8000/docs`

---

## API 端点

- `GET /api/health` - 健康检查
- `POST /api/auth/login` - 用户登录
- `POST /api/tasks/upload` - 上传预测文件
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{task_id}/summary` - 获取汇总数据
- `GET /api/tasks/{task_id}/sku-details` - 获取SKU明细（支持分页）

---

## 测试

```bash
# 运行所有测试
python -m pytest tests/test_api_e2e.py tests/test_export_service.py tests/test_forecast_service.py tests/test_risk_service.py tests/test_ai_service.py -q
npm run test --prefix web
npm run build --prefix web

# 覆盖范围
# ✅ 后端 API、导出、预测计算、风险计算、AI 服务
# ✅ 静态前端登录、工作台、数据汇总、智能助手、日志、设置、处理页
# ✅ 前端构建
```

---

## 核心算法

### 分配算法

**供不应求时**：
```
可满足[渠道] = (渠道SAR / 总SAR) × 总供应
未满足[渠道] = 渠道SAR - 可满足[渠道]
```

**供应充足时**：
```
可满足[渠道] = 渠道SAR
未满足[渠道] = 0
```

### 风险评分

| 等级 | 条件 | 评分 |
|-----|------|-----|
| CRITICAL | 缺口 ≤ -30% 且 绝对值 ≥ 10000 | 160-200 |
| HIGH | -30% < 缺口 ≤ -15% 且 绝对值 ≥ 5000 | 120-150 |
| MEDIUM | -15% < 缺口 ≤ -5% | 85-115 |
| NORMAL | -5% ≤ 缺口 < 10% | 50 |

---

## 开发进度

- [x] 阶段0：环境准备
- [x] 阶段1：基础服务层（分配、风险、解析）
- [x] 阶段2：API路由开发
- [x] 阶段3：自动化测试与前端 smoke 验证
- [x] 阶段4：导出功能
- [x] 阶段5：AI对话
- [x] 阶段6：静态前端开发

---

**版本**：v2.2.0  
**完成日期**：2026-06-21  
**开发团队**：AI Assistant
