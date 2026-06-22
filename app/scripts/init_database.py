"""
数据库初始化脚本

用途：
1. 检查数据库连接
2. 创建所有表结构（仅用于开发测试）
3. 生产环境请使用 scripts/init_db_v2.2.sql

运行：
    python -m app.scripts.init_database
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db import engine, check_db_connection, init_db
from app.models import Base


def main():
    """主函数"""
    print("=" * 60)
    print("产销预测智能工作台 - 数据库初始化")
    print("=" * 60)
    print()

    # 1. 检查数据库连接
    print("🔍 检查数据库连接...")
    if not check_db_connection():
        print("❌ 数据库连接失败，请检查配置")
        sys.exit(1)
    print("✅ 数据库连接成功")
    print()

    # 2. 显示将要创建的表
    print("📋 将要创建的表:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
    print()

    # 3. 确认创建
    response = input("⚠️  是否继续创建表？(y/N): ")
    if response.lower() != "y":
        print("❌ 已取消")
        sys.exit(0)
    print()

    # 4. 创建表
    print("🚀 开始创建表...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 所有表创建成功")
        print()

        # 5. 验证表创建
        print("🔍 验证表结构...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        print(f"✅ 共创建 {len(created_tables)} 个表:")
        for table in created_tables:
            print(f"  - {table}")
        print()

        print("=" * 60)
        print("✅ 数据库初始化完成")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
