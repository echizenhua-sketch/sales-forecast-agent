"""
数据库配置和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 连接池健康检查
    pool_recycle=3600,   # 连接回收时间（1小时）
    echo=settings.log_level == "DEBUG",  # 开发环境打印 SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Session:
    """
    获取数据库会话（依赖注入）

    用法：
        @app.get("/api/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构

    注意：仅用于开发测试，生产环境使用 SQL 迁移脚本
    """
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表结构初始化完成")


def check_db_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        bool: 连接成功返回 True，否则返回 False
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
