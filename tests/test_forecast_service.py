"""
业务计算服务 - 单元测试
"""

import pytest
from decimal import Decimal
from app.services.forecast_service import ForecastCalculationService


class TestForecastCalculationService:
    """业务计算服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return ForecastCalculationService()

    def test_calculate_sku_detail(self, service):
        """测试单个 SKU 计算"""
        import pandas as pd

        # 模拟一行数据
        row = pd.Series({
            "sku_code": "TEST-001",
            "product_name": "测试产品",
            "material_code": "MAT-001",
            "initial_inventory": 5000,
            "production_plan": 15000,
            "safety_stock": 0,
            "total_supply": 20000,
            "sar_province": 8000,
            "sar_dealer": 6000,
            "sar_ecommerce": 4000,
            "sar_ka": 3000,
            "sar_expansion": 2000,
        })

        sku_detail = service._calculate_sku_detail(row)

        # 验证基础字段
        assert sku_detail["sku_code"] == "TEST-001"
        assert sku_detail["total_supply"] == 20000
        assert sku_detail["sar_total"] == 23000  # 8000+6000+4000+3000+2000

        # 验证缺口
        assert sku_detail["gap"] == -3000  # 20000-23000

        # 验证分配（供不应求，按比例分配）
        assert sku_detail["satisfied_demand"] == 20000
        assert sku_detail["unsatisfied_demand"] == 3000

        # 验证风险
        assert sku_detail["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM", "NORMAL"]
        assert sku_detail["risk_score"] >= 0

        # print 输出（去掉 emoji 避免编码问题）
        # print(f"SKU计算测试通过:")
        # print(f"  - SKU: {sku_detail['sku_code']}")
        # print(f"  - 总供应: {sku_detail['total_supply']}")
        # print(f"  - 合计SAR: {sku_detail['sar_total']}")
        # print(f"  - 缺口: {sku_detail['gap']}")
        # print(f"  - 可满足: {sku_detail['satisfied_demand']}")
        # print(f"  - 未满足: {sku_detail['unsatisfied_demand']}")
        # print(f"  - 风险等级: {sku_detail['risk_level']}")
        # print(f"  - 风险评分: {sku_detail['risk_score']}")

    def test_calculate_summary(self, service):
        """测试汇总计算"""
        sku_details = [
            {
                "total_supply": 20000,
                "sar_total": 23000,
                "satisfied_demand": 20000,
                "unsatisfied_demand": 3000,
                "risk_level": "MEDIUM",
            },
            {
                "total_supply": 50000,
                "sar_total": 40000,
                "satisfied_demand": 40000,
                "unsatisfied_demand": 0,
                "risk_level": "NORMAL",
            },
            {
                "total_supply": 30000,
                "sar_total": 50000,
                "satisfied_demand": 30000,
                "unsatisfied_demand": 20000,
                "risk_level": "CRITICAL",
            },
        ]

        metadata = {}
        summary = service._calculate_summary(sku_details, metadata)

        # 验证汇总
        assert summary["total_supply"] == 100000  # 20000+50000+30000
        assert summary["total_sar"] == 113000  # 23000+40000+50000
        assert summary["total_gap"] == -13000  # 100000-113000
        assert summary["service_level"] > 0

        # 验证风险统计
        assert summary["critical_risk_count"] == 1
        assert summary["high_risk_count"] == 0
        assert summary["medium_risk_count"] == 1

        # print 输出（去掉 emoji 避免编码问题）
        # print(f"汇总计算测试通过:")
        # print(f"  - 总供应: {summary['total_supply']}")
        # print(f"  - 合计SAR: {summary['total_sar']}")
        # print(f"  - 总缺口: {summary['total_gap']}")
        # print(f"  - 满足率: {summary['service_level']:.2f}%")
        # print(f"  - 极高风险数量: {summary['critical_risk_count']}")
        # print(f"  - 高风险数量: {summary['high_risk_count']}")
        # print(f"  - 中风险数量: {summary['medium_risk_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
