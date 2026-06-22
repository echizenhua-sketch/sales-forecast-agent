"""
风险评分计算服务
==================

根据技术评审报告 v2.2 第 3.3 节实现风险评分逻辑

风险等级：
- CRITICAL: 极高风险
- HIGH: 高风险
- MEDIUM: 中风险
- NORMAL: 正常
- OVERSTOCK: 超储
- SUFFICIENT: 充足

风险评分范围：0-200，数值越大风险越高
"""

from decimal import Decimal
from typing import Tuple


class RiskCalculationService:
    """风险评分计算服务"""

    # 风险阈值配置
    CRITICAL_GAP_RATIO = Decimal("-0.30")  # 极高风险缺口比例
    CRITICAL_GAP_ABSOLUTE = Decimal("10000")  # 极高风险缺口绝对值
    HIGH_GAP_RATIO_MIN = Decimal("-0.30")  # 高风险缺口比例最小值
    HIGH_GAP_RATIO_MAX = Decimal("-0.15")  # 高风险缺口比例最大值
    HIGH_GAP_ABSOLUTE = Decimal("5000")  # 高风险缺口绝对值
    MEDIUM_GAP_RATIO_MIN = Decimal("-0.15")  # 中风险缺口比例最小值
    MEDIUM_GAP_RATIO_MAX = Decimal("-0.05")  # 中风险缺口比例最大值

    def calculate_risk(
        self,
        total_supply: Decimal,
        sar_total: Decimal,
        gap: Decimal,
    ) -> Tuple[str, str, Decimal]:
        """
        计算风险等级、风险原因和风险评分

        Args:
            total_supply: 总供应
            sar_total: 合计SAR
            gap: 缺口 (= 总供应 - 合计SAR)

        Returns:
            (risk_level, risk_reason, risk_score)
            - risk_level: 风险等级
            - risk_reason: 风险原因
            - risk_score: 风险评分（0-200）
        """
        # 边界条件：总SAR为0
        if sar_total == 0:
            return "NORMAL", "合计SAR为0，无需求", Decimal("0")

        # 计算缺口比例
        gap_ratio = gap / sar_total

        # 1. 极高风险 (CRITICAL)
        # 条件：缺口比例 <= -30% 且 缺口绝对值 >= 10000
        if gap_ratio <= self.CRITICAL_GAP_RATIO and abs(gap) >= self.CRITICAL_GAP_ABSOLUTE:
            risk_level = "CRITICAL"
            risk_reason = f"缺口比例 {gap_ratio*100:.2f}%，缺口绝对值 {abs(gap):.0f}，严重缺货"
            risk_score = Decimal("200") + gap_ratio * Decimal("100")  # 200-230
            return risk_level, risk_reason, min(risk_score, Decimal("200"))

        # 2. 高风险 (HIGH)
        # 条件：-30% < 缺口比例 <= -15% 且 缺口绝对值 >= 5000
        if self.CRITICAL_GAP_RATIO < gap_ratio <= self.HIGH_GAP_RATIO_MAX and abs(gap) >= self.HIGH_GAP_ABSOLUTE:
            risk_level = "HIGH"
            risk_reason = f"缺口比例 {gap_ratio*100:.2f}%，缺口绝对值 {abs(gap):.0f}，供应紧张"
            risk_score = Decimal("150") + gap_ratio * Decimal("100")  # 135-165
            return risk_level, risk_reason, risk_score

        # 3. 中风险 (MEDIUM)
        # 条件：-15% < 缺口比例 <= -5%
        if self.HIGH_GAP_RATIO_MAX < gap_ratio <= self.MEDIUM_GAP_RATIO_MAX:
            risk_level = "MEDIUM"
            risk_reason = f"缺口比例 {gap_ratio*100:.2f}%，需关注供应"
            risk_score = Decimal("100") + gap_ratio * Decimal("100")  # 85-115
            return risk_level, risk_reason, risk_score

        # 4. 正常 (NORMAL)
        if Decimal("-0.05") <= gap_ratio < Decimal("0.10"):
            risk_level = "NORMAL"
            risk_reason = "供需平衡"
            risk_score = Decimal("50")
            return risk_level, risk_reason, risk_score

        # 5. 超储 (OVERSTOCK)
        if Decimal("0.10") <= gap_ratio < Decimal("0.30"):
            risk_level = "OVERSTOCK"
            risk_reason = f"库存过剩 {gap_ratio*100:.2f}%，注意周转"
            risk_score = Decimal("30")
            return risk_level, risk_reason, risk_score

        # 6. 充足 (SUFFICIENT)
        if gap_ratio >= Decimal("0.30"):
            risk_level = "SUFFICIENT"
            risk_reason = f"供应充足，富余 {gap_ratio*100:.2f}%"
            risk_score = Decimal("10")
            return risk_level, risk_reason, risk_score

        # 默认：正常
        return "NORMAL", "供需平衡", Decimal("50")


# ============================================================
# 使用示例
# ============================================================

def example_usage():
    """使用示例"""
    service = RiskCalculationService()

    test_cases = [
        # (total_supply, sar_total, gap, 预期等级)
        (Decimal("60000"), Decimal("100000"), Decimal("-40000"), "CRITICAL"),  # -40%
        (Decimal("80000"), Decimal("100000"), Decimal("-20000"), "HIGH"),      # -20%
        (Decimal("90000"), Decimal("100000"), Decimal("-10000"), "MEDIUM"),    # -10%
        (Decimal("100000"), Decimal("100000"), Decimal("0"), "NORMAL"),        # 0%
        (Decimal("115000"), Decimal("100000"), Decimal("15000"), "OVERSTOCK"), # +15%
        (Decimal("140000"), Decimal("100000"), Decimal("40000"), "SUFFICIENT"),# +40%
    ]

    print("=" * 80)
    print("风险评分计算测试")
    print("=" * 80)

    for total_supply, sar_total, gap, expected_level in test_cases:
        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)
        gap_ratio = (gap / sar_total * 100) if sar_total > 0 else 0

        print(f"\n总供应: {total_supply}, 合计SAR: {sar_total}, 缺口: {gap} ({gap_ratio:.1f}%)")
        print(f"  风险等级: {level} (预期: {expected_level})")
        print(f"  风险原因: {reason}")
        print(f"  风险评分: {score}")
        print(f"  {'✅ 通过' if level == expected_level else '❌ 失败'}")


if __name__ == "__main__":
    example_usage()
