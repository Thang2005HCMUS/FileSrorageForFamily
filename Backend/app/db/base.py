from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Tạo engine kết nối bất đồng bộ
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Tạo Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class cho các Models kế thừa
class Base(DeclarativeBase):
    pass

# Dependency Injection để lấy DB session trong API
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session