"""
产销预测智能工作台 - Excel 解析服务
===================================

模块：app/services/parser_service.py
功能：解析产销预测 Excel 文件，验证格式和数据
版本：v2.2（对齐技术评审报告 v2.2 和 PRD v2.1）
创建日期：2026-06-21

支持格式：
---------
- .xlsx (Office 2016+)
- .xls (Office 2003)
- .csv (UTF-8 编码)

必需字段：
---------
32 个核心字段（参考 PRD v2.1 第 5.3 节）

特别注意：
---------
5 个 SAR 字段（v2.2 修正）：
1. 省大区SAR
2. 网络经销商SAR
3. 电商直营SAR（不是"海外出口SAR"）
4. KA部SAR（不是"内部调拨需求"）
5. 拓展部SAR（新增）

数据验证规则：
-------------
1. 5月总供应 = 4.30日库存 + 5月排产
2. 5月SAR合计 = 省大区SAR + 网络经销商SAR + 电商直营SAR + KA部SAR + 拓展部SAR
3. 5月SAR差异 = 5月总供应 - 5月SAR合计

参考文档：
---------
- PRD v2.1 第 5.3 节（Excel 字段清单）
- 技术评审报告 v2.2 第 3.1 节（数据模型）
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ExcelParserError(Exception):
    """Excel 解析错误"""
    pass


class ExcelParserService:
    """Excel 解析服务"""

    # ============================================================
    # 必需字段定义（v2.2 修正版，32 个核心字段）
    # ============================================================
    REQUIRED_SHEET_NAME = "预测及排期明细表"

    # 基础信息字段
    BASIC_FIELDS = [
        "事业部",
        "产品系列",
        "生产工厂",
        "属性",
        "型号",  # SKU编码
        "产品描述",
        "产品类别",
        "出厂价",
        "上市日期",
    ]

    # 库存与排产字段
    INVENTORY_FIELDS = [
        "4.30日库存",  # 期初库存
        "5月排产（4.30-5.29）",  # 排产计划
        "5月总供应",
    ]

    # SAR 需求字段（v2.2 修正：5个独立渠道）
    SAR_FIELDS = [
        "省大区SAR",
        "网络经销商SAR",
        "电商直营SAR",  # v2.2 修正
        "KA部SAR",  # v2.2 修正
        "拓展部SAR",  # v2.2 新增
        "5月SAR合计",
        "5月SAR差异",
    ]

    # 可满足明细字段
    SATISFIED_FIELDS = [
        "可满足合计",
        "省大区（可满足）",
        "网络经销商（可满足）",
        "电商直营（可满足）",
        "KA部（可满足）",
        "拓展部（可满足）",
        "KA-5月25日前可满足（含25日）",
    ]

    # 未满足明细字段
    UNSATISFIED_FIELDS = [
        "未满足合计",
        "省大区（未满足）",
        "网络经销商（未满足）",
        "电商直营（未满足）",
        "KA部（未满足）",
        "拓展部（未满足）",
    ]

    # 所有必需字段
    ALL_REQUIRED_FIELDS = (
        BASIC_FIELDS
        + INVENTORY_FIELDS
        + SAR_FIELDS
        + SATISFIED_FIELDS
        + UNSATISFIED_FIELDS
    )

    # 字段映射（Excel 列名 -> 数据库字段名）
    FIELD_MAPPING = {
        "事业部": "business_unit",
        "产品系列": "product_series",
        "生产工厂": "factory",
        "属性": "product_attribute",
        "型号": "sku_code",
        "产品描述": "product_name",
        "产品类别": "product_category",
        "出厂价": "ex_factory_price",
        "上市日期": "launch_date",
        "物料编码": "material_code",
        "4.30日库存": "initial_inventory",
        "5月排产（4.30-5.29）": "production_plan",
        "5月总供应": "total_supply",
        "省大区SAR": "sar_province",
        "网络经销商SAR": "sar_dealer",
        "电商直营SAR": "sar_ecommerce",  # v2.2 修正
        "KA部SAR": "sar_ka",  # v2.2 修正
        "拓展部SAR": "sar_expansion",  # v2.2 新增
        "5月SAR合计": "sar_total",
        "5月SAR差异": "gap",
        "可满足合计": "satisfied_demand",
        "未满足合计": "unsatisfied_demand",
        "省大区（可满足）": "satisfied_province",
        "网络经销商（可满足）": "satisfied_dealer",
        "电商直营（可满足）": "satisfied_ecommerce",
        "KA部（可满足）": "satisfied_ka",
        "拓展部（可满足）": "satisfied_expansion",
        "KA-5月25日前可满足（含25日）": "satisfied_ka_before_25",
        "省大区（未满足）": "unsatisfied_province",
        "网络经销商（未满足）": "unsatisfied_dealer",
        "电商直营（未满足）": "unsatisfied_ecommerce",
        "KA部（未满足）": "unsatisfied_ka",
        "拓展部（未满足）": "unsatisfied_expansion",
    }

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_excel(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        解析 Excel 文件

        Args:
            file_path: Excel 文件路径

        Returns:
            (parsed_data, metadata)
            - parsed_data: 解析后的 DataFrame
            - metadata: 元数据（文件名、行数、列数等）

        Raises:
            ExcelParserError: 解析失败
        """
        self.errors = []
        self.warnings = []

        try:
            # 1. 读取 Excel 文件
            logger.info(f"开始解析文件: {file_path}")
            df = self._read_excel(file_path)

            # 2. 验证 Sheet 名称
            self._validate_sheet_name(file_path)

            # 3. 验证必需字段
            self._validate_required_fields(df)

            # 4. 验证数据类型
            df = self._validate_data_types(df)

            # 5. 验证数据规则
            self._validate_data_rules(df)

            # 6. 数据清洗
            df = self._clean_data(df)

            # 7. 字段映射
            df = self._map_fields(df)

            # 8. 生成元数据
            metadata = self._generate_metadata(file_path, df)

            if self.errors:
                error_msg = "\n".join(self.errors)
                raise ExcelParserError(f"Excel 解析失败:\n{error_msg}")

            logger.info(f"文件解析成功，共 {len(df)} 行数据")
            if self.warnings:
                logger.warning(f"警告信息:\n" + "\n".join(self.warnings))

            return df, metadata

        except ExcelParserError:
            raise
        except Exception as e:
            logger.error(f"解析文件时发生异常: {str(e)}", exc_info=True)
            raise ExcelParserError(f"文件解析失败: {str(e)}")

    def _read_excel(self, file_path: str) -> pd.DataFrame:
        """读取 Excel 文件"""
        file_ext = Path(file_path).suffix.lower()

        try:
            if file_ext == ".csv":
                df = pd.read_csv(file_path, encoding="utf-8")
            elif file_ext in [".xlsx", ".xls"]:
                # 尝试读取指定的 Sheet
                try:
                    df = pd.read_excel(
                        file_path,
                        sheet_name=self.REQUIRED_SHEET_NAME,
                        engine="openpyxl" if file_ext == ".xlsx" else None,
                    )
                except ValueError:
                    # Sheet 不存在，尝试读取第一个 Sheet
                    df = pd.read_excel(file_path)
                    self.errors.append(
                        f"未找到名为《{self.REQUIRED_SHEET_NAME}》的 Sheet，"
                        f"已自动读取第一个 Sheet"
                    )
            else:
                raise ExcelParserError(f"不支持的文件格式: {file_ext}")

            # 清理列名：移除换行符、多余空格
            df.columns = df.columns.str.replace('\n', '').str.replace('\r', '').str.strip()

            return df

        except Exception as e:
            raise ExcelParserError(f"读取文件失败: {str(e)}")

    def _validate_sheet_name(self, file_path: str):
        """验证 Sheet 名称"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext in [".xlsx", ".xls"]:
            try:
                xl_file = pd.ExcelFile(file_path)
                sheet_names = xl_file.sheet_names

                if self.REQUIRED_SHEET_NAME not in sheet_names:
                    self.errors.append(
                        f"未能在工作簿中找到名为《{self.REQUIRED_SHEET_NAME}》的 Sheet，"
                        f"请检查文件格式后重新上传。\n"
                        f"当前 Sheet 列表: {', '.join(sheet_names)}"
                    )
            except Exception as e:
                self.warnings.append(f"无法验证 Sheet 名称: {str(e)}")

    def _validate_required_fields(self, df: pd.DataFrame):
        """验证必需字段"""
        df_columns = df.columns.tolist()
        missing_fields = []

        for field in self.ALL_REQUIRED_FIELDS:
            if field not in df_columns:
                missing_fields.append(field)

        if missing_fields:
            self.errors.append(
                f"缺少必需字段（共 {len(missing_fields)} 个）:\n"
                + "\n".join(f"  - {field}" for field in missing_fields[:10])
                + (
                    f"\n  ... 还有 {len(missing_fields) - 10} 个字段"
                    if len(missing_fields) > 10
                    else ""
                )
            )

        # 特别检查 5 个 SAR 字段（v2.2 重点）
        sar_fields_check = {
            "省大区SAR": "省大区SAR" in df_columns,
            "网络经销商SAR": "网络经销商SAR" in df_columns,
            "电商直营SAR": "电商直营SAR" in df_columns,
            "KA部SAR": "KA部SAR" in df_columns,
            "拓展部SAR": "拓展部SAR" in df_columns,
        }

        missing_sar = [k for k, v in sar_fields_check.items() if not v]
        if missing_sar:
            self.errors.append(
                "缺少 SAR 字段（v2.2 要求 5 个）:\n"
                + "\n".join(f"  - {field}" for field in missing_sar)
            )

        # 检查是否使用了旧字段名
        old_field_names = ["海外出口SAR", "内部调拨需求"]
        found_old_fields = [f for f in old_field_names if f in df_columns]
        if found_old_fields:
            self.errors.append(
                "检测到旧版本字段名（已废弃）:\n"
                + "\n".join(f"  - {field}" for field in found_old_fields)
                + "\n\n请使用 v2.2 版本的字段名：\n"
                + "  - 电商直营SAR（替代 海外出口SAR）\n"
                + "  - KA部SAR（替代 内部调拨需求）\n"
                + "  - 拓展部SAR（新增）"
            )

    def _validate_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据类型"""
        # 数值型字段
        numeric_fields = (
            self.INVENTORY_FIELDS + self.SAR_FIELDS[:-1]  # 排除 "5月SAR差异"
            + self.SATISFIED_FIELDS
            + self.UNSATISFIED_FIELDS
        )

        for field in numeric_fields:
            if field in df.columns:
                # 尝试转换为数值类型
                df[field] = pd.to_numeric(df[field], errors="coerce")

                # 检查空值
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    self.warnings.append(
                        f"字段 [{field}] 有 {null_count} 个空值，已填充为 0"
                    )
                    df[field] = df[field].fillna(0)

        return df

    def _validate_data_rules(self, df: pd.DataFrame):
        """验证数据规则（PRD v2.1 第 493-494 行）"""
        validation_errors = []

        for idx, row in df.iterrows():
            row_errors = []

            # 规则 1: 5月总供应 = 4.30日库存 + 5月排产
            if all(
                f in df.columns
                for f in ["4.30日库存", "5月排产（4.30-5.29）", "5月总供应"]
            ):
                expected_supply = row["4.30日库存"] + row["5月排产（4.30-5.29）"]
                actual_supply = row["5月总供应"]
                if abs(expected_supply - actual_supply) > 0.01:
                    row_errors.append(
                        f"总供应计算错误: 期望 {expected_supply}, 实际 {actual_supply}"
                    )

            # 规则 2: 5月SAR合计 = 省大区SAR + 网络经销商SAR + 电商直营SAR + KA部SAR + 拓展部SAR
            sar_fields = ["省大区SAR", "网络经销商SAR", "电商直营SAR", "KA部SAR", "拓展部SAR"]
            if all(f in df.columns for f in sar_fields + ["5月SAR合计"]):
                expected_sar_total = sum(row[f] for f in sar_fields)
                actual_sar_total = row["5月SAR合计"]
                if abs(expected_sar_total - actual_sar_total) > 0.01:
                    row_errors.append(
                        f"SAR合计计算错误: 期望 {expected_sar_total}, 实际 {actual_sar_total}"
                    )

            # 规则 3: 5月SAR差异 = 5月总供应 - 5月SAR合计
            if all(f in df.columns for f in ["5月总供应", "5月SAR合计", "5月SAR差异"]):
                expected_gap = row["5月总供应"] - row["5月SAR合计"]
                actual_gap = row["5月SAR差异"]
                if abs(expected_gap - actual_gap) > 0.01:
                    row_errors.append(
                        f"SAR差异计算错误: 期望 {expected_gap}, 实际 {actual_gap}"
                    )

            if row_errors:
                sku_code = row.get("型号", f"第{idx+2}行")
                validation_errors.append(f"SKU [{sku_code}]:\n  " + "\n  ".join(row_errors))

        if validation_errors:
            # 只显示前 5 个错误
            error_msg = "\n\n".join(validation_errors[:5])
            if len(validation_errors) > 5:
                error_msg += f"\n\n... 还有 {len(validation_errors) - 5} 个验证错误"

            self.errors.append(f"数据验证失败:\n{error_msg}")

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 删除全空行
        df = df.dropna(how="all")

        # 删除 SKU 编码为空的行
        if "型号" in df.columns:
            df = df[df["型号"].notna()]

        # 重置索引
        df = df.reset_index(drop=True)

        return df

    def _map_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """字段映射（Excel 列名 -> 数据库字段名）"""
        # 只保留映射的字段
        mapped_df = pd.DataFrame()

        for excel_col, db_col in self.FIELD_MAPPING.items():
            if excel_col in df.columns:
                mapped_df[db_col] = df[excel_col]

        return mapped_df

    def _generate_metadata(self, file_path: str, df: pd.DataFrame) -> Dict:
        """生成元数据"""
        return {
            "file_name": Path(file_path).name,
            "file_size": Path(file_path).stat().st_size,
            "row_count": len(df),
            "column_count": len(df.columns),
            "sar_fields_count": 5,  # v2.2: 5 个 SAR 字段
            "warnings": self.warnings,
        }


# ============================================================
# 使用示例
# ============================================================

def example_usage():
    """使用示例"""
    parser = ExcelParserService()

    # 解析文件
    try:
        df, metadata = parser.parse_excel("example.xlsx")

        print("=" * 60)
        print("解析成功")
        print("=" * 60)
        print(f"文件名: {metadata['file_name']}")
        print(f"文件大小: {metadata['file_size']} 字节")
        print(f"数据行数: {metadata['row_count']}")
        print(f"数据列数: {metadata['column_count']}")
        print(f"SAR 字段数: {metadata['sar_fields_count']}")
        print()

        print("前 5 行数据:")
        print(df.head())
        print()

        if metadata['warnings']:
            print("警告信息:")
            for warning in metadata['warnings']:
                print(f"  {warning}")

    except ExcelParserError as e:
        print("=" * 60)
        print("解析失败")
        print("=" * 60)
        print(str(e))


if __name__ == "__main__":
    example_usage()
