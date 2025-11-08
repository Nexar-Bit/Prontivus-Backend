"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import os

from database import Base, get_db
from app.models import User
from app.core.auth import create_access_token


# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
        poolclass=StaticPool if "sqlite" in TEST_DATABASE_URL else None,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user
    """
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("testpassword123"),
        full_name="Test User",
        role="admin",
        is_active=True,
        clinic_id=1
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def test_token(test_user: User) -> str:
    """
    Create a test JWT token
    """
    return create_access_token(data={"sub": test_user.email, "role": test_user.role})


@pytest.fixture
def auth_headers(test_token: str) -> dict:
    """
    Create authorization headers for testing
    """
    return {"Authorization": f"Bearer {test_token}"}

