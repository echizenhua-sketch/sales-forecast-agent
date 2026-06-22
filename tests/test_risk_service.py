"""
风险评分计算服务 - 单元测试
"""

import pytest
from decimal import Decimal
from app.services.risk_service import RiskCalculationService


class TestRiskCalculationService:
    """风险评分计算服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RiskCalculationService()

    def test_critical_risk(self, service):
        """测试极高风险"""
        total_supply = Decimal("60000")
        sar_total = Decimal("100000")
        gap = Decimal("-40000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "CRITICAL"
        assert "严重缺货" in reason
        assert score <= Decimal("200")
        print(f"✓ 极高风险测试通过: {level}, {reason}, {score}")

    def test_high_risk(self, service):
        """测试高风险"""
        total_supply = Decimal("80000")
        sar_total = Decimal("100000")
        gap = Decimal("-20000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "HIGH"
        assert "供应紧张" in reason
        # gap_ratio = -0.2, score = 150 + (-0.2)*100 = 130
        assert Decimal("120") <= score <= Decimal("150")
        print(f"✓ 高风险测试通过: {level}, {reason}, {score}")

    def test_medium_risk(self, service):
        """测试中风险"""
        total_supply = Decimal("90000")
        sar_total = Decimal("100000")
        gap = Decimal("-10000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "MEDIUM"
        assert "需关注" in reason
        assert Decimal("85") <= score <= Decimal("115")
        print(f"✓ 中风险测试通过: {level}, {reason}, {score}")

    def test_normal_risk(self, service):
        """测试正常"""
        total_supply = Decimal("100000")
        sar_total = Decimal("100000")
        gap = Decimal("0")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "NORMAL"
        assert "平衡" in reason
        assert score == Decimal("50")
        print(f"✓ 正常测试通过: {level}, {reason}, {score}")

    def test_overstock_risk(self, service):
        """测试超储"""
        total_supply = Decimal("115000")
        sar_total = Decimal("100000")
        gap = Decimal("15000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "OVERSTOCK"
        assert "库存过剩" in reason or "周转" in reason
        assert score == Decimal("30")
        print(f"✓ 超储测试通过: {level}, {reason}, {score}")

    def test_sufficient_risk(self, service):
        """测试充足"""
        total_supply = Decimal("140000")
        sar_total = Decimal("100000")
        gap = Decimal("40000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "SUFFICIENT"
        assert "充足" in reason
        assert score == Decimal("10")
        print(f"✓ 充足测试通过: {level}, {reason}, {score}")

    def test_zero_sar(self, service):
        """测试边界条件：总SAR为0"""
        total_supply = Decimal("10000")
        sar_total = Decimal("0")
        gap = Decimal("10000")

        level, reason, score = service.calculate_risk(total_supply, sar_total, gap)

        assert level == "NORMAL"
        assert "无需求" in reason
        assert score == Decimal("0")
        print(f"✓ 零SAR测试通过: {level}, {reason}, {score}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
