"""
补齐现有 MySQL 表结构。

初始化脚本已经创建过库时，本脚本只做向后兼容增列，不删除数据。
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.db import engine


SKU_COLUMNS = {
    "business_unit": "VARCHAR(100) NULL COMMENT '事业部'",
    "product_series": "VARCHAR(100) NULL COMMENT '产品系列'",
    "factory": "VARCHAR(100) NULL COMMENT '生产工厂'",
    "product_attribute": "VARCHAR(100) NULL COMMENT '属性'",
    "product_category": "VARCHAR(100) NULL COMMENT '产品类别'",
    "ex_factory_price": "DECIMAL(18, 2) NULL COMMENT '出厂价'",
    "launch_date": "DATETIME NULL COMMENT '上市日期'",
    "satisfied_ka_before_25": "DECIMAL(18, 2) NULL COMMENT 'KA-5月25日前可满足（含25日）'",
}


def ensure_schema() -> list[str]:
    """补齐缺失列，返回执行过的 ALTER 语句。"""
    if engine.dialect.name != "mysql":
        return []

    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("sku_forecast_detail")}
    statements = []
    with engine.begin() as conn:
        for column_name, ddl in SKU_COLUMNS.items():
            if column_name not in existing:
                statement = f"ALTER TABLE sku_forecast_detail ADD COLUMN {column_name} {ddl}"
                conn.execute(text(statement))
                statements.append(statement)
    return statements


if __name__ == "__main__":
    for sql in ensure_schema():
        print(sql)
