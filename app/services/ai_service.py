"""
AI对话服务
==========

集成MiniMax API，提供智能问答功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import requests

from app.core.config import get_settings


class AIService:
    """AI对话服务（基于MiniMax）"""

    def __init__(self):
        settings = get_settings()
        # AI模型配置。兼容旧环境变量，但不再内置任何密钥。
        self.api_base = (
            os.getenv("AI_API_BASE")
            or os.getenv("ANTHROPIC_BASE_URL")
            or settings.ai_api_base
            or settings.anthropic_base_url
            or ""
        ).rstrip("/")
        self.api_key = (
            os.getenv("AI_API_KEY")
            or os.getenv("ANTHROPIC_AUTH_TOKEN")
            or settings.ai_api_key
            or settings.anthropic_auth_token
            or ""
        )
        self.model = os.getenv("AI_MODEL") or settings.ai_model or "MiniMax-M3"
        self.conversation_history = {}

    def chat(
        self,
        session_id: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        AI对话

        Args:
            session_id: 会话ID
            user_message: 用户消息
            context: 上下文信息（任务数据、SKU信息等）

        Returns:
            AI回复
        """
        # 获取或创建会话历史
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        # 添加用户消息
        self.conversation_history[session_id].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        if not self.api_base or not self.api_key:
            ai_response = "AI模型未配置，请在 .env 中配置 AI_API_BASE 和 AI_API_KEY 后重试。"
            response_type = "llm_unconfigured"
            success = False
        else:
            # 构建系统提示
            system_prompt = self._build_system_prompt(context)

            try:
                ai_response = self._call_minimax_api(
                    session_id,
                    user_message,
                    system_prompt,
                    context
                )
                response_type = "llm_generate"
                success = True
            except Exception as e:
                ai_response = f"模型调用失败：{e}"
                response_type = "llm_error"
                success = False

        # 添加AI回复到历史
        self.conversation_history[session_id].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": success,
            "message": ai_response,
            "session_id": session_id,
            "type": response_type,
            "model": self.model,
            "timestamp": datetime.now().isoformat()
        }

    def _build_system_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """构建系统提示（专业产销预测助手）"""
        prompt = """# 角色定位
你是**产销预测智能分析助手**，专注于供需平衡分析、风险识别和优化建议。

# 核心能力
1. **数据分析** - 解读供需缺口、满足率、风险等级
2. **风险识别** - 识别高风险SKU，分析原因，提供应对措施
3. **优化建议** - 基于数据提供排产、库存、渠道优化方案
4. **专业解答** - 回答产销预测相关的专业问题

# 重要规则
1. **直接给结论** - 不要输出SQL查询过程，直接给出分析结果
2. **基于实际数据** - 使用context中提供的真实数据进行分析
3. **结构化呈现** - 使用标题、分点、数据表格
4. **可执行建议** - 建议要具体、可操作、分优先级

# 数据来源
所有数据来自MySQL数据库 `supply_demand_forecast`，通过context参数传入已汇总的数据。

**主要表结构**：
- `sku_forecast_detail` - SKU预测明细（核心字段：sku_code, product_name, total_supply, sar_total, gap, service_level, risk_level, risk_score）
- `task_summary` - 汇总结果（整体指标和风险统计）

**SAR渠道（5个）**：
- sar_province - 省大区SAR
- sar_dealer - 网络经销商SAR
- sar_ecommerce - 电商直营SAR
- sar_ka - KA部SAR
- sar_expansion - 拓展部SAR

# 分析方法论

## 风险评估标准
- **CRITICAL（极高风险）**: 缺口比例 < -30% 且绝对缺口 > 10000
- **HIGH（高风险）**: 缺口比例 -30% ~ -15% 且绝对缺口 > 5000
- **MEDIUM（中风险）**: 缺口比例 -15% ~ -5%

## 优化建议框架
1. **短期（本月）**: 紧急排产、库存调配
2. **中期（1-3月）**: 预测模型优化、安全库存建立
3. **长期**: 供应链机制优化、AI预测引入

## 渠道优先级
1. KA部 - 大客户，优先保障
2. 省大区 - 核心渠道
3. 网络经销商 - 规模渠道
4. 电商直营 - 增长渠道
5. 拓展部 - 新兴渠道

# 回答风格
- **直接高效** - 开门见山，先给核心结论
- **数据驱动** - 基于实际数据，给出具体数字
- **结构清晰** - 使用标题、分点、表格
- **可执行性** - 建议具体、分优先级

# 回答示例格式

**用户问**: "分析当前的风险情况"

**正确回答**:
```
## 风险分析

**整体概况:**
- 总供应: 1,000,000
- 总需求: 950,000
- 缺口: 50,000 (供应充足)
- 满足率: 95.5% (目标98%, 差距2.5%)

**风险分布:**
- 极高风险: 3个SKU
- 高风险: 8个SKU
- 中风险: 15个SKU

**关键问题:**
1. 满足率未达标 - 距离目标还差2.5个百分点
2. 极高风险SKU需立即处理
3. 高风险SKU有15个，需要重点关注

**应对措施:**
1. 紧急排产极高风险SKU
2. 优先保障KA部和省大区渠道
3. 监控中风险SKU，防止恶化

需要我深入分析某个具体方面吗?
```

**错误示例** (不要这样):
```
让我查询数据...

```sql
SELECT ... FROM sku_forecast_detail ...
```

执行查询后...
```
❌ 不要输出SQL过程，直接给结论!

# 当前数据上下文"""

        if context:
            if "task_summary" in context:
                summary = context["task_summary"]
                prompt += f"""

## 当前数据（已从数据库获取）

**整体指标：**
- 总供应：{summary.get('total_supply', 0):,.0f}
- 合计SAR：{summary.get('total_sar', 0):,.0f}
- SAR差异：{summary.get('total_gap', 0):,.0f}
- 满足率：{summary.get('service_level', 0):.1f}%
- 目标满足率：{summary.get('target_service_level', 98):.0f}%

**风险统计：**
- 极高风险SKU：{summary.get('critical_risk_count', 0)}个
- 高风险SKU：{summary.get('high_risk_count', 0)}个
- 中风险SKU：{summary.get('medium_risk_count', 0)}个

**重要**: 以上数据是最新的真实数据，请基于这些数据直接进行分析，不要再询问数据或SQL查询。"""

            if "sku_data" in context:
                prompt += "\n\n## SKU明细数据已加载，可进行具体分析"

            if "sku_details" in context and context["sku_details"]:
                prompt += "\n\n## 当前高风险 SKU 明细（已从数据库获取）\n"
                for index, sku in enumerate(context["sku_details"], start=1):
                    prompt += f"""
{index}. {sku.get('sku_code')}（{sku.get('product_name') or '未命名产品'}）
   - 月份：{sku.get('month')}
   - 总供应：{sku.get('total_supply', 0):,.0f}
   - 合计SAR：{sku.get('sar_total', 0):,.0f}
   - SAR差异：{sku.get('gap', 0):+,.0f}
   - 满足率：{sku.get('service_level', 0):.2f}%
   - 风险等级：{sku.get('risk_level') or '未知'}
   - 风险评分：{sku.get('risk_score', 0):.0f}
   - 未满足合计：{sku.get('unsatisfied_demand', 0):,.0f}
   - 风险原因：{sku.get('risk_reason') or '暂无'}
"""
                prompt += "\n回答具体 SKU、缺口、排产优先级问题时，必须优先引用以上 SKU 明细数据。"
        else:
            prompt += """

## 数据获取方式
当前没有提供context数据。如果用户询问具体数据分析：
1. 如果是汇总级别的问题，说明需要task_id来获取数据
2. 如果是通用咨询（如何使用、功能介绍等），可以直接回答"""

        return prompt

    def _call_minimax_api(
        self,
        session_id: str,
        user_message: str,
        system_prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        调用MiniMax API (通过Claude兼容接口)
        """
        # 构建消息历史（只包含用户和助手消息，不包括当前消息）
        messages = []

        # 添加系统提示作为第一条用户消息
        messages.append({
            "role": "user",
            "content": f"<system_context>\n{system_prompt}\n</system_context>"
        })
        messages.append({
            "role": "assistant",
            "content": "好的，我已了解我的角色和职责。我是产销预测智能分析助手，会基于数据库数据提供专业分析。请问有什么可以帮您？"
        })

        # 添加历史对话（优先使用数据库持久化历史，最多保留最近5轮）
        history = []
        if context and context.get("conversation_history"):
            history = context["conversation_history"]
        else:
            history = self.conversation_history.get(session_id, [])
        recent_history = history[-10:] if len(history) > 10 else history

        for msg in recent_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })

        # 调用API
        response = requests.post(
            f"{self.api_base}/v1/messages",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7,
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return self._extract_response_text(result)
        else:
            raise Exception(f"API调用失败: {response.status_code}, {response.text}")

    def _extract_response_text(self, result: Dict[str, Any]) -> str:
        """
        从模型网关响应中提取可展示文本。

        当前网关使用 Anthropic Messages 兼容格式，但 minimax-m3 会先返回
        `thinking` 块，再返回 `text` 块；不能固定读取 content[0].text。
        同时兼容 OpenAI Chat Completions 和 Responses API 的常见结构。
        """
        if not isinstance(result, dict):
            raise ValueError("模型响应格式错误：响应不是 JSON 对象")

        if result.get("error"):
            raise ValueError(f"模型返回错误：{result.get('error')}")

        output_text = result.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        content = result.get("content")
        text_parts = self._extract_text_parts(content)
        if text_parts:
            return "\n".join(text_parts).strip()

        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") or {}
                text_parts = self._extract_text_parts(message.get("content"))
                if text_parts:
                    return "\n".join(text_parts).strip()
                text = choice.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        output = result.get("output")
        if isinstance(output, list):
            output_parts = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                output_parts.extend(self._extract_text_parts(item.get("content")))
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    output_parts.append(text.strip())
            if output_parts:
                return "\n".join(output_parts).strip()

        raise ValueError(
            "模型响应中没有可展示文本，返回字段："
            + ", ".join(result.keys())
        )

    def _extract_text_parts(self, content: Any) -> List[str]:
        """从字符串或内容块列表中提取文本，自动跳过 thinking 等非展示块。"""
        if isinstance(content, str):
            return [content.strip()] if content.strip() else []

        if not isinstance(content, list):
            return []

        parts = []
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    parts.append(item.strip())
                continue

            if not isinstance(item, dict):
                continue

            item_type = item.get("type")
            if item_type in {"thinking", "reasoning"}:
                continue

            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
                continue

            nested_text = item.get("content")
            if isinstance(nested_text, str) and nested_text.strip():
                parts.append(nested_text.strip())

        return parts

    def _generate_fallback_response(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        生成降级响应（当API不可用时）
        """
        message_lower = user_message.lower()

        # 风险分析
        if "风险" in message_lower or "risk" in message_lower:
            if context and "task_summary" in context:
                summary = context["task_summary"]
                critical = summary.get('critical_risk_count', 0)
                high = summary.get('high_risk_count', 0)
                medium = summary.get('medium_risk_count', 0)

                return f"""[风险分析报告]

**当前风险分布：**
- [CRITICAL] 极高风险：{critical}个SKU
- [HIGH] 高风险：{high}个SKU
- [MEDIUM] 中风险：{medium}个SKU

**风险定义：**
- 极高风险：缺口比例 < -30% 且绝对缺口 > 10,000
- 高风险：缺口比例 -30% ~ -15% 且绝对缺口 > 5,000
- 中风险：缺口比例 -15% ~ -5%

**应对建议：**
1. **立即处理** - 极高风险SKU需紧急排产或调配
2. **优先关注** - 高风险SKU制定应急预案
3. **监控跟踪** - 中风险SKU密切观察需求变化

**建议查询SQL：**
```sql
-- 查看极高风险SKU详情
SELECT sku_code, product_name, gap, service_level
FROM sku_forecast_detail
WHERE risk_level = 'CRITICAL'
ORDER BY risk_score DESC;
```

需要查看具体SKU的风险详情吗？"""

        # 满足率分析
        elif "满足率" in message_lower or "service" in message_lower:
            if context and "task_summary" in context:
                summary = context["task_summary"]
                level = summary.get('service_level', 0)
                target = summary.get('target_service_level', 98)
                gap = target - level

                status = "[OK] 优秀" if level >= target else "[警告] 待改进"

                return f"""[图表] **满足率分析**

**当前表现：**
- 实际满足率：{level:.1f}%
- 目标满足率：{target:.0f}%
- 差距：{gap:.1f}个百分点
- 评价：{status}

**满足率公式：**
```
满足率 = (可满足需求 / 合计SAR) × 100%
```

**提升策略：**
{'[OK] 当前表现良好，继续保持！' if level >= target else f'''
1. **增加供应** - 提升关键SKU排产
2. **优化分配** - 按渠道优先级调配库存
3. **需求管理** - 与销售协调，优化预测准确度
4. **应急储备** - 建立安全库存缓冲

**建议查询SQL：**
```sql
-- 查询满足率最低的SKU
SELECT sku_code, product_name, service_level, gap
FROM sku_forecast_detail
WHERE service_level < {target}
ORDER BY service_level ASC
LIMIT 20;
```'''}

需要深入分析未满足需求的渠道分布吗？"""

        # 缺口分析
        elif "缺口" in message_lower or "差异" in message_lower or "gap" in message_lower:
            if context and "task_summary" in context:
                summary = context["task_summary"]
                supply = summary.get('total_supply', 0)
                demand = summary.get('total_sar', 0)
                gap = summary.get('total_gap', 0)

                if gap < 0:
                    return f"""[警告] **供应缺口分析**

**整体情况：**
- 总供应：{supply:,.0f}
- 合计需求（SAR）：{demand:,.0f}
- **缺口：{gap:,.0f}** （供不应求）
- 缺口比例：{(gap/demand*100):.1f}%

**影响评估：**
- [警告] 供应不足，可能影响订单交付
- 部分渠道需求无法满足
- 客户满意度可能下降

**应对措施：**

**短期（本月）：**
1. 紧急增加排产 - 针对高风险SKU
2. 跨渠道调配 - 从低优先级渠道调剂
3. 客户沟通 - 调整交付时间表

**中期（1-3月）：**
1. 提升产能 - 增加生产线或外协
2. 优化库存 - 建立安全库存
3. 改进预测 - 提高需求预测准确度

**建议查询SQL：**
```sql
-- 分析各渠道未满足需求
SELECT
    SUM(unsatisfied_province) as 省大区未满足,
    SUM(unsatisfied_dealer) as 网络经销商未满足,
    SUM(unsatisfied_ecommerce) as 电商未满足,
    SUM(unsatisfied_ka) as KA部未满足,
    SUM(unsatisfied_expansion) as 拓展部未满足
FROM sku_forecast_detail;
```

需要查看哪个渠道的缺口最大吗？"""
                else:
                    return f"""[OK] **供应充足分析**

**整体情况：**
- 总供应：{supply:,.0f}
- 合计需求（SAR）：{demand:,.0f}
- **盈余：{gap:,.0f}** （供大于求）
- 盈余比例：{(gap/demand*100):.1f}%

**机会点：**
- [OK] 供应充足，可以满足所有需求
- 可考虑市场推广，消化盈余
- 关注库存周转，避免积压

**优化建议：**
1. **市场拓展** - 加大销售力度
2. **促销活动** - 针对盈余产品
3. **库存管理** - 控制库存周转天数
4. **产能优化** - 适当调整生产计划

**建议查询SQL：**
```sql
-- 查询盈余最多的SKU
SELECT sku_code, product_name, gap, total_supply, sar_total
FROM sku_forecast_detail
WHERE gap > 0
ORDER BY gap DESC
LIMIT 20;
```

需要查看盈余产品的详细情况吗？"""

        # 渠道分析
        elif "渠道" in message_lower or "channel" in message_lower:
            return """[位置] **渠道需求分析**

**5大渠道体系：**

1. **省大区SAR** (sar_province)
   - 核心传统渠道
   - 通常占比最高
   - 优先级：⭐⭐⭐⭐

2. **网络经销商SAR** (sar_dealer)
   - 规模化分销渠道
   - 稳定需求来源
   - 优先级：⭐⭐⭐⭐

3. **电商直营SAR** (sar_ecommerce)
   - 增长型渠道
   - 灵活性高
   - 优先级：⭐⭐⭐

4. **KA部SAR** (sar_ka)
   - 大客户/战略客户
   - 优先保障
   - 优先级：⭐⭐⭐⭐⭐

5. **拓展部SAR** (sar_expansion)
   - 新兴渠道
   - 市场拓展
   - 优先级：⭐⭐

**渠道需求查询SQL：**
```sql
-- 各渠道需求汇总
SELECT
    SUM(sar_province) as 省大区,
    SUM(sar_dealer) as 网络经销商,
    SUM(sar_ecommerce) as 电商直营,
    SUM(sar_ka) as KA部,
    SUM(sar_expansion) as 拓展部,
    SUM(sar_total) as 合计
FROM sku_forecast_detail;

-- 各渠道满足情况
SELECT
    SUM(satisfied_province) / SUM(sar_province) * 100 as 省大区满足率,
    SUM(satisfied_dealer) / SUM(sar_dealer) * 100 as 经销商满足率,
    SUM(satisfied_ka) / SUM(sar_ka) * 100 as KA部满足率
FROM sku_forecast_detail;
```

需要查看某个具体渠道的数据吗？"""

        # 优化建议
        elif "建议" in message_lower or "优化" in message_lower or "怎么办" in message_lower:
            return """[建议] **产销优化建议方案**

**一、短期措施（本月内）**

1. **紧急排产**
   - 针对极高/高风险SKU增加排产
   - 优先保障KA部和核心渠道

2. **库存调配**
   - 跨渠道调剂：从低优先级渠道向高优先级调配
   - 跨区域调剂：从盈余区域支援缺口区域

3. **需求确认**
   - 与销售部门确认SAR准确性
   - 识别可压缩或延迟的需求

**二、中期措施（1-3个月）**

1. **预测模型优化**
   ```sql
   -- 分析历史预测准确度
   SELECT sku_code,
          AVG(ABS(actual - forecast) / forecast) as 误差率
   FROM forecast_history
   GROUP BY sku_code
   ORDER BY 误差率 DESC;
   ```

2. **安全库存建立**
   - 为高波动SKU建立缓冲
   - 公式：安全库存 = 日均需求 × 提前期 × 安全系数

3. **渠道协同**
   - 建立渠道间库存共享机制
   - 提升响应速度

**三、长期措施**

1. **供应链数字化**
   - 引入AI预测模型
   - 实时库存可见性
   - 自动化补货

2. **柔性生产能力**
   - 提升产能弹性
   - 缩短生产周期
   - 多品种小批量

3. **持续改进**
   - 定期回顾预测准确度
   - 优化分配算法
   - KPI监控与改进

**四、数据驱动决策**

**关键SQL查询：**
```sql
-- 1. 找出优化优先级最高的SKU
SELECT sku_code, product_name, risk_score, gap
FROM sku_forecast_detail
WHERE risk_level IN ('CRITICAL', 'HIGH')
ORDER BY risk_score DESC
LIMIT 10;

-- 2. 分析可调配的库存
SELECT sku_code,
       total_supply - sar_total as 可调配量
FROM sku_forecast_detail
WHERE gap > 0  -- 有盈余的SKU
ORDER BY gap DESC;

-- 3. 评估满足率改进空间
SELECT
    COUNT(*) as SKU总数,
    AVG(service_level) as 平均满足率,
    SUM(CASE WHEN service_level < 98 THEN 1 ELSE 0 END) as 待改进数量
FROM sku_forecast_detail;
```

需要针对哪个方面深入探讨吗？"""

        # 数据库查询帮助
        elif "sql" in message_lower or "查询" in message_lower or "数据库" in message_lower:
            return """[文档] **数据库查询指南**

**核心表：sku_forecast_detail**

**常用查询模板：**

**1. 风险SKU排查**
```sql
-- 按风险等级查询
SELECT sku_code, product_name, gap, service_level, risk_level
FROM sku_forecast_detail
WHERE risk_level = 'CRITICAL'  -- 或 'HIGH', 'MEDIUM'
ORDER BY risk_score DESC;

-- 自定义风险条件
SELECT sku_code, product_name, gap, service_level
FROM sku_forecast_detail
WHERE gap < -10000  -- 缺口超过1万
  AND service_level < 90  -- 满足率低于90%
ORDER BY gap ASC;
```

**2. 渠道分析**
```sql
-- 各渠道需求占比
SELECT
    SUM(sar_province) / SUM(sar_total) * 100 as 省大区占比,
    SUM(sar_dealer) / SUM(sar_total) * 100 as 经销商占比,
    SUM(sar_ecommerce) / SUM(sar_total) * 100 as 电商占比,
    SUM(sar_ka) / SUM(sar_total) * 100 as KA占比,
    SUM(sar_expansion) / SUM(sar_total) * 100 as 拓展占比
FROM sku_forecast_detail;

-- 渠道未满足需求
SELECT sku_code,
       unsatisfied_province as 省大区缺口,
       unsatisfied_dealer as 经销商缺口,
       unsatisfied_ka as KA缺口
FROM sku_forecast_detail
WHERE unsatisfied_province + unsatisfied_dealer + unsatisfied_ka > 0;
```

**3. 满足率分析**
```sql
-- 满足率分布
SELECT
    CASE
        WHEN service_level >= 100 THEN '完全满足'
        WHEN service_level >= 98 THEN '达标'
        WHEN service_level >= 95 THEN '接近达标'
        ELSE '待改进'
    END as 满足率分级,
    COUNT(*) as SKU数量
FROM sku_forecast_detail
GROUP BY 满足率分级;
```

**4. TOP/BOTTOM分析**
```sql
-- 缺口最大的10个SKU
SELECT sku_code, product_name, gap
FROM sku_forecast_detail
ORDER BY gap ASC
LIMIT 10;

-- 满足率最低的10个SKU
SELECT sku_code, product_name, service_level
FROM sku_forecast_detail
ORDER BY service_level ASC
LIMIT 10;
```

**5. 汇总统计**
```sql
-- 整体统计
SELECT
    COUNT(*) as SKU总数,
    SUM(total_supply) as 总供应,
    SUM(sar_total) as 总需求,
    SUM(gap) as 总缺口,
    AVG(service_level) as 平均满足率
FROM sku_forecast_detail;
```

需要其他查询示例吗？"""

        # 默认响应
        else:
            return f"""[您好] 收到您的问题：**"{user_message}"**

我是**产销预测智能助手**，基于数据库实时数据为您提供专业分析。

**我可以帮您：**

[数据] **数据分析**
- 供需缺口分析
- 满足率评估
- 风险识别与评级

[建议] **优化建议**
- 排产优化方案
- 库存调配策略
- 渠道优先级建议

[查询] **专业查询**
- 提供SQL查询示例
- 解读数据库字段
- 业务逻辑说明

**快速开始：**
- "有哪些高风险SKU？"
- "满足率如何？如何提升？"
- "各渠道的需求分布情况"
- "给我一些优化建议"
- "如何查询数据库？"

您想了解什么？"""

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        return self.conversation_history.get(session_id, [])

    def clear_conversation(self, session_id: str):
        """清除会话历史"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
