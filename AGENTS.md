# 产销预测 Agent 开发规范

## 1. 项目概述

产销预测Agent是一个基于AI的智能数据分析和预测系统，主要功能包括：
- 用户认证与会话管理
- 数据文件上传与解析
- 产销数据预测与分析
- 数据报表生成与导出
- 智能对话问答
- 历史数据查询

## 2. 开发规范红线

- **禁止改变核心业务逻辑**：任何优化或重构不得改变原有业务计算规则和数据流程。
- **禁止硬编码敏感信息**：API Key、数据库密码、Token等敏感信息必须通过环境变量或配置文件管理。
- **禁止删除已有功能**：除非经过明确确认，不得删除任何已有功能、接口或配置。
- **禁止跳过数据校验**：所有外部输入（文件上传、API请求、用户输入）必须经过严格校验。
- **禁止在生产环境调试**：生产环境严禁输出调试信息、敏感数据或执行测试代码。

## 3. 代码规范

### 3.1 Python 代码规范

- 遵循 PEP 8 代码风格规范
- 使用 4 个空格缩进，禁止使用 Tab
- 类名使用大驼峰命名法：`SalesForecastAgent`
- 函数名和变量名使用小写+下划线：`calculate_forecast_data`
- 常量名使用全大写+下划线：`MAX_FILE_SIZE`
- 每个模块开头必须有模块说明文档字符串

### 3.2 项目结构规范

```
产销预测agent/
├── src/                    # 源代码目录
│   ├── agents/            # Agent 核心逻辑
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务层
│   ├── utils/             # 工具函数
│   └── api/               # API 接口
├── tests/                 # 测试代码
├── docs/                  # 项目文档
├── data/                  # 数据文件（不提交到Git）
├── logs/                  # 日志文件（不提交到Git）
├── config/                # 配置文件
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

### 3.3 依赖管理

- 使用 `requirements.txt` 管理依赖，固定版本号
- 新增依赖前必须说明原因和替代方案
- 定期更新依赖以修复安全漏洞
- 开发依赖和生产依赖分离：`requirements-dev.txt`

## 4. 注释规范

### 4.1 函数/方法注释

每个函数必须包含完整的文档字符串（Docstring），包括：功能说明、参数、返回值、异常、示例。

```python
def calculate_forecast(data: pd.DataFrame, forecast_period: int = 30) -> dict:
    """
    计算产销预测数据
    
    根据历史数据和预测周期，计算未来的产销预测结果。
    
    Args:
        data (pd.DataFrame): 历史产销数据，必须包含 date、sales、production 列
        forecast_period (int): 预测天数，默认30天
        
    Returns:
        dict: 预测结果字典，包含以下键：
            - forecast_dates: 预测日期列表
            - forecast_sales: 预测销量列表
            - forecast_production: 预测产量列表
            - confidence_interval: 置信区间
            
    Raises:
        ValueError: 当数据格式不正确或预测周期无效时
        
    Example:
        >>> data = pd.read_csv('sales_data.csv')
        >>> result = calculate_forecast(data, forecast_period=30)
        >>> print(result['forecast_sales'])
    """
    pass
```

### 4.2 类注释

```python
class SalesForecastAgent:
    """
    产销预测 Agent 核心类
    
    负责协调数据处理、模型预测、结果生成等核心业务流程。
    
    Attributes:
        model: 预测模型实例
        config: 配置信息
        logger: 日志记录器
        
    Example:
        >>> agent = SalesForecastAgent(config_path='config.yaml')
        >>> result = agent.forecast(data)
    """
    pass
```

### 4.3 关键业务逻辑注释

在复杂业务逻辑处添加注释，说明计算公式、业务规则、数据来源等。

```python
# 1. 计算5周可供应量
# 公式：4周30天可供应量 + 5周第5周合计
weeks_supply_5 = weeks_supply_4_30days + week5_total

# 2. 计算5周SAR结余
# 公式：5周可供应量 - 5周合计SAR
sar_balance_5weeks = weeks_supply_5 - total_sar_5weeks

# 3. 按业务规则确定最终合计
# 规则：若结余>0，使用已确认合计；否则使用已确认+未确认
if sar_balance_5weeks > 0:
    final_total = confirmed_total
else:
    final_total = confirmed_total + unconfirmed_total
```

## 5. 日志规范

### 5.1 日志级别

- **DEBUG**：详细的调试信息，仅在开发环境使用
- **INFO**：关键业务节点、正常流程记录
- **WARNING**：警告信息，不影响运行但需要关注
- **ERROR**：错误信息，影响功能但不导致崩溃
- **CRITICAL**：严重错误，导致系统崩溃

### 5.2 必记场景

- 用户登录/登出
- 文件上传开始/完成/失败
- 数据预测开始/完成/失败
- API 请求/响应（含请求ID、耗时）
- 数据库操作（增删改查）
- 外部服务调用（AI模型、第三方API）
- 异常和错误
- 关键业务参数变化

### 5.3 日志格式

```python
import logging

# 推荐使用结构化日志
logger.info(
    "开始计算预测数据",
    extra={
        "user_id": user_id,
        "file_name": file_name,
        "forecast_period": forecast_period,
        "timestamp": datetime.now().isoformat()
    }
)
```

### 5.4 敏感信息处理

- 禁止记录密码、Token、API Key
- 用户信息仅记录ID，不记录姓名、手机号等
- 数据内容仅记录摘要或统计信息

## 6. 数据处理规范

### 6.1 数据校验

- 文件上传前校验：文件类型、大小、格式
- 数据解析后校验：必填字段、数据类型、数值范围
- 业务规则校验：日期合理性、数量非负、关联数据完整性

### 6.2 数据清洗

- 去除空白字符
- 统一日期格式：`YYYY-MM-DD`
- 统一数值精度：金额保留2位小数，数量保留整数
- 处理缺失值：根据业务规则填充或标记

### 6.3 数据安全

- 用户上传文件隔离存储，使用用户ID + UUID命名
- 敏感数据加密存储
- 定期清理过期临时文件
- 导出数据添加水印或权限控制

## 7. API 接口规范

### 7.1 RESTful 风格

- **GET**：查询数据（幂等）
- **POST**：创建资源或执行操作
- **PUT**：全量更新资源
- **PATCH**：部分更新资源
- **DELETE**：删除资源

### 7.2 请求响应格式

统一使用 JSON 格式：

**成功响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "forecast_result": []
  },
  "timestamp": "2026-06-16T10:30:00Z",
  "request_id": "uuid-xxxx-xxxx"
}
```

**错误响应**：
```json
{
  "code": 400,
  "message": "参数校验失败",
  "error": {
    "field": "forecast_period",
    "reason": "预测周期必须在1-365之间"
  },
  "timestamp": "2026-06-16T10:30:00Z",
  "request_id": "uuid-xxxx-xxxx"
}
```

### 7.3 错误码规范

- **2xx**：成功
  - 200：请求成功
  - 201：创建成功
- **4xx**：客户端错误
  - 400：参数错误
  - 401：未认证
  - 403：无权限
  - 404：资源不存在
  - 429：请求过于频繁
- **5xx**：服务器错误
  - 500：服务器内部错误
  - 503：服务不可用

### 7.4 接口文档

- 使用 OpenAPI (Swagger) 规范
- 必须包含：接口路径、请求方法、参数说明、响应示例、错误码说明
- 接口变更必须更新文档并通知调用方

## 8. 测试规范

### 8.1 单元测试

- 使用 `pytest` 框架
- 测试覆盖率不低于 70%
- 关键业务逻辑测试覆盖率不低于 90%
- 测试文件命名：`test_<module_name>.py`
- 测试函数命名：`test_<function_name>_<scenario>`

### 8.2 集成测试

- 测试完整业务流程
- 测试外部依赖（数据库、AI模型、第三方API）
- 使用测试数据，禁止使用生产数据

### 8.3 性能测试

- 关键接口响应时间要求：
  - 查询接口：< 500ms
  - 预测计算：< 5s
  - 文件上传：< 10s
- 并发测试：模拟多用户同时访问

## 9. Git 工作流规范

### 9.1 分支管理

- **main**：主分支，保持稳定，禁止直接提交
- **develop**：开发分支，日常开发
- **feature/xxx**：功能分支，开发新功能
- **bugfix/xxx**：修复分支，修复bug
- **release/vx.x.x**：发布分支，准备发布

### 9.2 提交规范

提交信息格式：`<type>(<scope>): <subject>`

**type 类型：**
- **feat**：新功能
- **fix**：修复bug
- **docs**：文档更新
- **style**：代码格式调整（不影响功能）
- **refactor**：重构（不新增功能，不修复bug）
- **test**：测试相关
- **chore**：构建、配置、依赖更新

**示例：**
```bash
feat(forecast): 添加5周SAR预测计算功能
fix(api): 修复文件上传大小限制bug
docs(readme): 更新部署说明文档
```

### 9.3 代码审查

- 所有功能分支合并到 develop 前必须经过 Code Review
- 审查要点：
  - 代码规范
  - 业务逻辑正确性
  - 安全性
  - 性能
  - 测试覆盖

### 9.4 版本发布

- 遵循语义化版本规范：`主版本.次版本.修订号`
  - 主版本：不兼容的API修改
  - 次版本：向下兼容的功能新增
  - 修订号：向下兼容的bug修复
- 发布前必须：
  - 通过所有测试
  - 更新 CHANGELOG.md
  - 打标签：`git tag -a v1.0.0 -m "Release version 1.0.0"`
  - 推送标签：`git push origin v1.0.0`

## 10. 部署规范

### 10.1 环境划分

- **开发环境（dev）**：本地开发调试
- **测试环境（test）**：功能测试、集成测试
- **预发环境（staging）**：生产前验证
- **生产环境（prod）**：正式运行

### 10.2 配置管理

- 不同环境使用不同配置文件
- 敏感配置通过环境变量注入
- `.env.example` 文件提供配置模板
- 配置文件不提交到 Git（`.gitignore`）

### 10.3 部署检查清单

- [ ] 代码已通过所有测试
- [ ] 代码已合并到 main 分支
- [ ] 已创建版本标签
- [ ] 已更新 CHANGELOG.md
- [ ] 已备份生产数据库
- [ ] 已检查依赖版本兼容性
- [ ] 已准备回滚方案
- [ ] 已通知相关人员

### 10.4 监控与告警

- 应用性能监控（APM）
- 日志聚合与分析
- 关键指标告警：
  - 接口响应时间异常
  - 错误率超过阈值
  - 服务不可用
  - 资源使用率过高

## 11. AI Agent 开发规范

### 11.1 Prompt 工程

- Prompt 模板化管理，集中存放在 `prompts/` 目录
- 使用版本控制管理 Prompt 变更
- 记录 Prompt 调优历史和效果对比
- 敏感业务规则不直接暴露在 Prompt 中

### 11.2 模型调用

- 统一封装 AI 模型调用接口
- 实现重试机制和降级策略
- 记录每次调用的输入输出和耗时
- 实现请求限流和成本控制

### 11.3 对话管理

- 实现会话上下文管理
- 设置合理的上下文长度限制
- 敏感信息不保存在会话历史中
- 定期清理过期会话

## 12. 安全规范

- 所有用户输入必须校验和过滤（防止SQL注入、XSS）
- 使用参数化查询，禁止拼接SQL
- 文件上传检查文件类型和内容，防止恶意文件
- API 接口实现认证和授权
- 实现请求频率限制，防止滥用
- 定期进行安全审计和漏洞扫描

## 13. 文档规范

### 13.1 必备文档

- **README.md**：项目介绍、快速开始、部署说明
- **AGENTS.md**：开发规范（本文档）
- **CHANGELOG.md**：版本变更记录
- **API.md**：API 接口文档
- **ARCHITECTURE.md**：架构设计文档

### 13.2 代码注释

- 每个模块、类、函数必须有文档字符串
- 复杂业务逻辑必须有行内注释
- 重要算法和计算公式必须详细说明

### 13.3 文档更新

- 代码变更必须同步更新相关文档
- 接口变更必须提前通知并更新文档
- 定期检查文档与实际代码的一致性

---

**本规范优先级：** 本文档规范优先级高于个人编码习惯，所有开发人员必须严格遵守。如有疑问或改进建议，请提交 Issue 讨论。

**最后更新：** 2026-06-16
