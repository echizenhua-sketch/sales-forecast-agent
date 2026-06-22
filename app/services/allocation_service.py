"""
产销预测智能工作台 - 可满足/未满足分配算法
==============================================

模块：app/services/allocation_service.py
功能：实现 5 个渠道的可满足/未满足数量分配
版本：v2.2（对齐技术评审报告 v2.2）
创建日期：2026-06-21

算法说明：
----------
1. 当缺口 < 0（供不应求）时：
   - 按各渠道 SAR 占总 SAR 的比例分配 total_supply
   - 可满足 = (渠道SAR / 总SAR) × 总供应
   - 未满足 = 渠道SAR - 可满足

2. 当缺口 >= 0（供应充足）时：
   - 所有渠道完全满足
   - 可满足 = 渠道SAR
   - 未满足 = 0

验证规则：
----------
- 可满足合计 = sum(5个渠道可满足)
- 未满足合计 = sum(5个渠道未满足)
- 可满足合计 + 未满足合计 = 合计SAR

参考文档：
----------
- PRD v2.1 第 493 行（数据验证规则）
- 技术评审报告 v2.2 第 3.1 节（数据模型）
"""

from typing import Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP


class AllocationService:
    """可满足/未满足分配服务"""

    def allocate_satisfied_unsatisfied(
        self,
        total_supply: Decimal,
        sar_province: Decimal,
        sar_dealer: Decimal,
        sar_ecommerce: Decimal,
        sar_ka: Decimal,
        sar_expansion: Decimal,
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        计算 5 个渠道的可满足/未满足数量分配

        Args:
            total_supply: 总供应量
            sar_province: 省大区SAR
            sar_dealer: 网络经销商SAR
            sar_ecommerce: 电商直营SAR
            sar_ka: KA部SAR
            sar_expansion: 拓展部SAR

        Returns:
            {
                'satisfied': {
                    'province': Decimal,
                    'dealer': Decimal,
                    'ecommerce': Decimal,
                    'ka': Decimal,
                    'expansion': Decimal,
                    'total': Decimal
                },
                'unsatisfied': {
                    'province': Decimal,
                    'dealer': Decimal,
                    'ecommerce': Decimal,
                    'ka': Decimal,
                    'expansion': Decimal,
                    'total': Decimal
                }
            }
        """
        # 计算合计 SAR
        sar_total = (
            sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion
        )

        # 边界条件：总需求为 0
        if sar_total == 0:
            return self._create_zero_allocation()

        # 计算缺口
        gap = total_supply - sar_total

        # 根据缺口判断分配策略
        if gap < 0:
            # 供不应求，按比例分配
            return self._allocate_by_ratio(
                total_supply=total_supply,
                sar_total=sar_total,
                sar_province=sar_province,
                sar_dealer=sar_dealer,
                sar_ecommerce=sar_ecommerce,
                sar_ka=sar_ka,
                sar_expansion=sar_expansion,
            )
        else:
            # 供应充足，完全满足
            return self._allocate_full_satisfied(
                sar_province=sar_province,
                sar_dealer=sar_dealer,
                sar_ecommerce=sar_ecommerce,
                sar_ka=sar_ka,
                sar_expansion=sar_expansion,
            )

    def _allocate_by_ratio(
        self,
        total_supply: Decimal,
        sar_total: Decimal,
        sar_province: Decimal,
        sar_dealer: Decimal,
        sar_ecommerce: Decimal,
        sar_ka: Decimal,
        sar_expansion: Decimal,
    ) -> Dict[str, Dict[str, Decimal]]:
        """按比例分配（供不应求场景）"""

        # 计算各渠道可满足数量（按占比分配总供应）
        satisfied_province = self._round_decimal(
            (sar_province / sar_total) * total_supply
        )
        satisfied_dealer = self._round_decimal(
            (sar_dealer / sar_total) * total_supply
        )
        satisfied_ecommerce = self._round_decimal(
            (sar_ecommerce / sar_total) * total_supply
        )
        satisfied_ka = self._round_decimal((sar_ka / sar_total) * total_supply)
        satisfied_expansion = self._round_decimal(
            (sar_expansion / sar_total) * total_supply
        )

        # 处理舍入误差：确保可满足合计 = total_supply
        satisfied_total_calculated = (
            satisfied_province
            + satisfied_dealer
            + satisfied_ecommerce
            + satisfied_ka
            + satisfied_expansion
        )
        rounding_diff = total_supply - satisfied_total_calculated

        # 将舍入误差分配给占比最大的渠道
        if rounding_diff != 0:
            max_sar_channel = max(
                [
                    ("province", sar_province),
                    ("dealer", sar_dealer),
                    ("ecommerce", sar_ecommerce),
                    ("ka", sar_ka),
                    ("expansion", sar_expansion),
                ],
                key=lambda x: x[1],
            )[0]

            if max_sar_channel == "province":
                satisfied_province += rounding_diff
            elif max_sar_channel == "dealer":
                satisfied_dealer += rounding_diff
            elif max_sar_channel == "ecommerce":
                satisfied_ecommerce += rounding_diff
            elif max_sar_channel == "ka":
                satisfied_ka += rounding_diff
            elif max_sar_channel == "expansion":
                satisfied_expansion += rounding_diff

        # 计算各渠道未满足数量
        unsatisfied_province = sar_province - satisfied_province
        unsatisfied_dealer = sar_dealer - satisfied_dealer
        unsatisfied_ecommerce = sar_ecommerce - satisfied_ecommerce
        unsatisfied_ka = sar_ka - satisfied_ka
        unsatisfied_expansion = sar_expansion - satisfied_expansion

        return {
            "satisfied": {
                "province": satisfied_province,
                "dealer": satisfied_dealer,
                "ecommerce": satisfied_ecommerce,
                "ka": satisfied_ka,
                "expansion": satisfied_expansion,
                "total": total_supply,  # 可满足合计 = 总供应
            },
            "unsatisfied": {
                "province": unsatisfied_province,
                "dealer": unsatisfied_dealer,
                "ecommerce": unsatisfied_ecommerce,
                "ka": unsatisfied_ka,
                "expansion": unsatisfied_expansion,
                "total": sar_total - total_supply,  # 未满足合计 = 总SAR - 总供应
            },
        }

    def _allocate_full_satisfied(
        self,
        sar_province: Decimal,
        sar_dealer: Decimal,
        sar_ecommerce: Decimal,
        sar_ka: Decimal,
        sar_expansion: Decimal,
    ) -> Dict[str, Dict[str, Decimal]]:
        """完全满足（供应充足场景）"""

        sar_total = (
            sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion
        )

        return {
            "satisfied": {
                "province": sar_province,
                "dealer": sar_dealer,
                "ecommerce": sar_ecommerce,
                "ka": sar_ka,
                "expansion": sar_expansion,
                "total": sar_total,
            },
            "unsatisfied": {
                "province": Decimal("0"),
                "dealer": Decimal("0"),
                "ecommerce": Decimal("0"),
                "ka": Decimal("0"),
                "expansion": Decimal("0"),
                "total": Decimal("0"),
            },
        }

    def _create_zero_allocation(self) -> Dict[str, Dict[str, Decimal]]:
        """创建零分配结果（边界条件：总SAR为0）"""
        zero = Decimal("0")
        return {
            "satisfied": {
                "province": zero,
                "dealer": zero,
                "ecommerce": zero,
                "ka": zero,
                "expansion": zero,
                "total": zero,
            },
            "unsatisfied": {
                "province": zero,
                "dealer": zero,
                "ecommerce": zero,
                "ka": zero,
                "expansion": zero,
                "total": zero,
            },
        }

    def _round_decimal(self, value: Decimal, places: int = 2) -> Decimal:
        """四舍五入到指定小数位"""
        quantize_str = "0." + "0" * places
        return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    def validate_allocation(
        self, allocation: Dict[str, Dict[str, Decimal]], sar_total: Decimal
    ) -> Tuple[bool, str]:
        """
        验证分配结果是否正确

        Args:
            allocation: 分配结果
            sar_total: 合计SAR

        Returns:
            (is_valid, error_message)
        """
        satisfied = allocation["satisfied"]
        unsatisfied = allocation["unsatisfied"]

        # 验证 1：可满足合计 = 5个渠道之和
        satisfied_sum = (
            satisfied["province"]
            + satisfied["dealer"]
            + satisfied["ecommerce"]
            + satisfied["ka"]
            + satisfied["expansion"]
        )
        if abs(satisfied_sum - satisfied["total"]) > Decimal("0.01"):
            return False, f"可满足合计不匹配：{satisfied_sum} != {satisfied['total']}"

        # 验证 2：未满足合计 = 5个渠道之和
        unsatisfied_sum = (
            unsatisfied["province"]
            + unsatisfied["dealer"]
            + unsatisfied["ecommerce"]
            + unsatisfied["ka"]
            + unsatisfied["expansion"]
        )
        if abs(unsatisfied_sum - unsatisfied["total"]) > Decimal("0.01"):
            return (
                False,
                f"未满足合计不匹配：{unsatisfied_sum} != {unsatisfied['total']}",
            )

        # 验证 3：可满足合计 + 未满足合计 = 合计SAR
        total_demand = satisfied["total"] + unsatisfied["total"]
        if abs(total_demand - sar_total) > Decimal("0.01"):
            return False, f"总需求不匹配：{total_demand} != {sar_total}"

        return True, "验证通过"


# ============================================================
# 使用示例
# ============================================================

def example_usage():
    """使用示例"""
    service = AllocationService()

    # 示例 1：供不应求场景
    print("=" * 60)
    print("示例 1：供不应求场景（缺口 < 0）")
    print("=" * 60)

    total_supply = Decimal("80000")
    sar_province = Decimal("30000")
    sar_dealer = Decimal("25000")
    sar_ecommerce = Decimal("20000")
    sar_ka = Decimal("15000")
    sar_expansion = Decimal("10000")
    sar_total = sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion

    print(f"总供应: {total_supply}")
    print(f"合计SAR: {sar_total}")
    print(f"缺口: {total_supply - sar_total}")
    print()

    allocation = service.allocate_satisfied_unsatisfied(
        total_supply=total_supply,
        sar_province=sar_province,
        sar_dealer=sar_dealer,
        sar_ecommerce=sar_ecommerce,
        sar_ka=sar_ka,
        sar_expansion=sar_expansion,
    )

    print("可满足明细:")
    for channel, value in allocation["satisfied"].items():
        if channel != "total":
            ratio = (value / total_supply * 100) if total_supply > 0 else 0
            print(f"  {channel}: {value} ({ratio:.1f}%)")
    print(f"  合计: {allocation['satisfied']['total']}")
    print()

    print("未满足明细:")
    for channel, value in allocation["unsatisfied"].items():
        if channel != "total":
            print(f"  {channel}: {value}")
    print(f"  合计: {allocation['unsatisfied']['total']}")
    print()

    # 验证
    is_valid, message = service.validate_allocation(allocation, sar_total)
    print(f"验证结果: {'✅ ' if is_valid else '❌ '}{message}")
    print()

    # 示例 2：供应充足场景
    print("=" * 60)
    print("示例 2：供应充足场景（缺口 >= 0）")
    print("=" * 60)

    total_supply = Decimal("120000")
    sar_total = sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion

    print(f"总供应: {total_supply}")
    print(f"合计SAR: {sar_total}")
    print(f"缺口: {total_supply - sar_total}")
    print()

    allocation = service.allocate_satisfied_unsatisfied(
        total_supply=total_supply,
        sar_province=sar_province,
        sar_dealer=sar_dealer,
        sar_ecommerce=sar_ecommerce,
        sar_ka=sar_ka,
        sar_expansion=sar_expansion,
    )

    print("可满足明细:")
    for channel, value in allocation["satisfied"].items():
        if channel != "total":
            print(f"  {channel}: {value}")
    print(f"  合计: {allocation['satisfied']['total']}")
    print()

    print("未满足明细:")
    for channel, value in allocation["unsatisfied"].items():
        if channel != "total":
            print(f"  {channel}: {value}")
    print(f"  合计: {allocation['unsatisfied']['total']}")
    print()

    # 验证
    is_valid, message = service.validate_allocation(allocation, sar_total)
    print(f"验证结果: {'✅ ' if is_valid else '❌ '}{message}")
    print()


if __name__ == "__main__":
    example_usage()
