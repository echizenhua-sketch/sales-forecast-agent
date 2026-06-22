"""
产销预测智能工作台 - 单元测试
==============================

模块：tests/test_allocation_service.py
功能：测试可满足/未满足分配算法
版本：v2.2
创建日期：2026-06-21

测试覆盖：
---------
1. 供不应求场景（缺口 < 0）
2. 供应充足场景（缺口 >= 0）
3. 边界条件（总SAR = 0）
4. 数据验证（验证公式正确性）
5. 舍入误差处理
"""

import pytest
from decimal import Decimal
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.allocation_service import AllocationService


class TestAllocationService:
    """可满足/未满足分配服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return AllocationService()

    @pytest.fixture
    def sample_sar_data(self):
        """示例 SAR 数据"""
        return {
            "sar_province": Decimal("30000"),
            "sar_dealer": Decimal("25000"),
            "sar_ecommerce": Decimal("20000"),
            "sar_ka": Decimal("15000"),
            "sar_expansion": Decimal("10000"),
            "sar_total": Decimal("100000"),
        }

    # ============================================================
    # 场景 1：供不应求（缺口 < 0）
    # ============================================================

    def test_allocate_insufficient_supply(self, service, sample_sar_data):
        """测试供不应求场景"""
        total_supply = Decimal("80000")  # 缺口 = -20000

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证可满足合计 = 总供应
        assert result["satisfied"]["total"] == total_supply

        # 验证未满足合计 = 总SAR - 总供应
        expected_unsatisfied_total = sample_sar_data["sar_total"] - total_supply
        assert result["unsatisfied"]["total"] == expected_unsatisfied_total

        # 验证可满足 + 未满足 = 总SAR
        total_demand = result["satisfied"]["total"] + result["unsatisfied"]["total"]
        assert total_demand == sample_sar_data["sar_total"]

        # 验证每个渠道的可满足数量 > 0
        assert result["satisfied"]["province"] > 0
        assert result["satisfied"]["dealer"] > 0
        assert result["satisfied"]["ecommerce"] > 0
        assert result["satisfied"]["ka"] > 0
        assert result["satisfied"]["expansion"] > 0

        # 验证每个渠道的未满足数量 > 0
        assert result["unsatisfied"]["province"] > 0
        assert result["unsatisfied"]["dealer"] > 0
        assert result["unsatisfied"]["ecommerce"] > 0
        assert result["unsatisfied"]["ka"] > 0
        assert result["unsatisfied"]["expansion"] > 0

    def test_allocate_by_ratio_accuracy(self, service, sample_sar_data):
        """测试按比例分配的准确性"""
        total_supply = Decimal("80000")

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证省大区的可满足数量（占比 30%）
        expected_province = Decimal("24000")  # 30% * 80000
        assert abs(result["satisfied"]["province"] - expected_province) < Decimal("1")

        # 验证网络经销商的可满足数量（占比 25%）
        expected_dealer = Decimal("20000")  # 25% * 80000
        assert abs(result["satisfied"]["dealer"] - expected_dealer) < Decimal("1")

        # 验证电商直营的可满足数量（占比 20%）
        expected_ecommerce = Decimal("16000")  # 20% * 80000
        assert abs(result["satisfied"]["ecommerce"] - expected_ecommerce) < Decimal("1")

    # ============================================================
    # 场景 2：供应充足（缺口 >= 0）
    # ============================================================

    def test_allocate_sufficient_supply(self, service, sample_sar_data):
        """测试供应充足场景"""
        total_supply = Decimal("120000")  # 缺口 = +20000

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证可满足合计 = 总SAR
        assert result["satisfied"]["total"] == sample_sar_data["sar_total"]

        # 验证未满足合计 = 0
        assert result["unsatisfied"]["total"] == Decimal("0")

        # 验证每个渠道完全满足
        assert result["satisfied"]["province"] == sample_sar_data["sar_province"]
        assert result["satisfied"]["dealer"] == sample_sar_data["sar_dealer"]
        assert result["satisfied"]["ecommerce"] == sample_sar_data["sar_ecommerce"]
        assert result["satisfied"]["ka"] == sample_sar_data["sar_ka"]
        assert result["satisfied"]["expansion"] == sample_sar_data["sar_expansion"]

        # 验证每个渠道未满足 = 0
        assert result["unsatisfied"]["province"] == Decimal("0")
        assert result["unsatisfied"]["dealer"] == Decimal("0")
        assert result["unsatisfied"]["ecommerce"] == Decimal("0")
        assert result["unsatisfied"]["ka"] == Decimal("0")
        assert result["unsatisfied"]["expansion"] == Decimal("0")

    def test_allocate_exact_match(self, service, sample_sar_data):
        """测试供需完全匹配场景"""
        total_supply = sample_sar_data["sar_total"]  # 缺口 = 0

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证完全满足
        assert result["satisfied"]["total"] == sample_sar_data["sar_total"]
        assert result["unsatisfied"]["total"] == Decimal("0")

    # ============================================================
    # 场景 3：边界条件
    # ============================================================

    def test_allocate_zero_sar(self, service):
        """测试总SAR为0的边界条件"""
        total_supply = Decimal("10000")

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=Decimal("0"),
            sar_dealer=Decimal("0"),
            sar_ecommerce=Decimal("0"),
            sar_ka=Decimal("0"),
            sar_expansion=Decimal("0"),
        )

        # 验证所有字段为 0
        assert result["satisfied"]["total"] == Decimal("0")
        assert result["unsatisfied"]["total"] == Decimal("0")
        assert result["satisfied"]["province"] == Decimal("0")
        assert result["unsatisfied"]["province"] == Decimal("0")

    def test_allocate_zero_supply(self, service, sample_sar_data):
        """测试总供应为0的边界条件"""
        total_supply = Decimal("0")

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证可满足合计 = 0
        assert result["satisfied"]["total"] == Decimal("0")

        # 验证未满足合计 = 总SAR
        assert result["unsatisfied"]["total"] == sample_sar_data["sar_total"]

    def test_allocate_single_channel_only(self, service):
        """测试只有一个渠道有需求的场景"""
        total_supply = Decimal("50000")
        sar_province = Decimal("100000")

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sar_province,
            sar_dealer=Decimal("0"),
            sar_ecommerce=Decimal("0"),
            sar_ka=Decimal("0"),
            sar_expansion=Decimal("0"),
        )

        # 验证只有省大区有分配
        assert result["satisfied"]["province"] == total_supply
        assert result["unsatisfied"]["province"] == sar_province - total_supply

        # 验证其他渠道为 0
        assert result["satisfied"]["dealer"] == Decimal("0")
        assert result["satisfied"]["ecommerce"] == Decimal("0")
        assert result["satisfied"]["ka"] == Decimal("0")
        assert result["satisfied"]["expansion"] == Decimal("0")

    # ============================================================
    # 场景 4：数据验证
    # ============================================================

    def test_validate_allocation_success(self, service, sample_sar_data):
        """测试验证成功场景"""
        total_supply = Decimal("80000")

        allocation = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        is_valid, message = service.validate_allocation(
            allocation, sample_sar_data["sar_total"]
        )

        assert is_valid is True
        assert "验证通过" in message

    def test_validate_allocation_satisfied_sum_mismatch(self, service, sample_sar_data):
        """测试可满足合计不匹配的场景"""
        # 构造错误的分配结果
        allocation = {
            "satisfied": {
                "province": Decimal("20000"),
                "dealer": Decimal("15000"),
                "ecommerce": Decimal("10000"),
                "ka": Decimal("8000"),
                "expansion": Decimal("5000"),
                "total": Decimal("99999"),  # 故意错误
            },
            "unsatisfied": {
                "province": Decimal("10000"),
                "dealer": Decimal("10000"),
                "ecommerce": Decimal("10000"),
                "ka": Decimal("7000"),
                "expansion": Decimal("5000"),
                "total": Decimal("42000"),
            },
        }

        is_valid, message = service.validate_allocation(
            allocation, sample_sar_data["sar_total"]
        )

        assert is_valid is False
        assert "可满足合计不匹配" in message

    # ============================================================
    # 场景 5：5 个 SAR 字段完整性（v2.2 重点）
    # ============================================================

    def test_all_five_sar_fields_allocated(self, service, sample_sar_data):
        """测试 5 个 SAR 字段都参与分配（v2.2 重点）"""
        total_supply = Decimal("80000")

        result = service.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sample_sar_data["sar_province"],
            sar_dealer=sample_sar_data["sar_dealer"],
            sar_ecommerce=sample_sar_data["sar_ecommerce"],
            sar_ka=sample_sar_data["sar_ka"],
            sar_expansion=sample_sar_data["sar_expansion"],
        )

        # 验证 5 个字段都存在且有值
        assert "province" in result["satisfied"]
        assert "dealer" in result["satisfied"]
        assert "ecommerce" in result["satisfied"]  # v2.2 修正
        assert "ka" in result["satisfied"]  # v2.2 修正
        assert "expansion" in result["satisfied"]  # v2.2 新增

        # 验证 5 个渠道可满足之和 = 总供应
        satisfied_sum = (
            result["satisfied"]["province"]
            + result["satisfied"]["dealer"]
            + result["satisfied"]["ecommerce"]
            + result["satisfied"]["ka"]
            + result["satisfied"]["expansion"]
        )
        assert satisfied_sum == total_supply

        # 验证 5 个渠道未满足之和 = 总SAR - 总供应
        unsatisfied_sum = (
            result["unsatisfied"]["province"]
            + result["unsatisfied"]["dealer"]
            + result["unsatisfied"]["ecommerce"]
            + result["unsatisfied"]["ka"]
            + result["unsatisfied"]["expansion"]
        )
        expected_unsatisfied = sample_sar_data["sar_total"] - total_supply
        assert unsatisfied_sum == expected_unsatisfied


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
