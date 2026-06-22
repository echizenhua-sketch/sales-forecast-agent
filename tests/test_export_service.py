"""
导出服务测试
"""

import pytest
from pathlib import Path
import os
from app.services.export_service import ExportService


class TestExportService:
    """导出服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return ExportService()

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return [
            {
                'sku_code': 'TEST-001',
                'product_name': '测试产品1',
                'total_supply': 10000,
                'sar_total': 12000,
                'gap': -2000,
                'risk_level': 'HIGH',
            },
            {
                'sku_code': 'TEST-002',
                'product_name': '测试产品2',
                'total_supply': 15000,
                'sar_total': 10000,
                'gap': 5000,
                'risk_level': 'NORMAL',
            },
        ]

    @pytest.fixture
    def summary_data(self):
        """汇总数据"""
        return {
            'total_supply': 25000,
            'total_sar': 22000,
            'total_gap': 3000,
            'service_level': 95.5,
            'target_service_level': 98.0,
            'critical_risk_count': 0,
            'high_risk_count': 1,
            'medium_risk_count': 0,
        }

    def test_export_to_excel(self, service, sample_data, summary_data, tmp_path):
        """测试Excel导出"""
        output_file = tmp_path / "test_export.xlsx"

        result = service.export_to_excel(
            sample_data,
            str(output_file),
            include_summary=True,
            summary_data=summary_data
        )

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0
        print(f"PASS: Excel导出成功，文件大小: {Path(result).stat().st_size} 字节")

    def test_export_to_csv(self, service, sample_data, tmp_path):
        """测试CSV导出"""
        output_file = tmp_path / "test_export.csv"

        result = service.export_to_csv(sample_data, str(output_file))

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

        # 验证内容
        with open(result, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            assert 'sku_code' in content
            assert 'TEST-001' in content

        print(f"PASS: CSV导出成功，文件大小: {Path(result).stat().st_size} 字节")

    def test_generate_export_filename(self, service):
        """测试文件名生成"""
        filename = service.generate_export_filename('SKU_DETAIL', 'XLSX', 123)

        assert 'export_sku_detail' in filename.lower()
        assert 'task123' in filename
        assert filename.endswith('.xlsx')
        print(f"PASS: 文件名生成: {filename}")

    def test_export_empty_data(self, service, tmp_path):
        """测试空数据导出"""
        output_file = tmp_path / "empty_export.csv"

        with pytest.raises(ValueError, match="数据为空"):
            service.export_to_csv([], str(output_file))

        print("PASS: 空数据导出正确抛出异常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
