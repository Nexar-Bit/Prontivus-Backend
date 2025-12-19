from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure SQLAlchemy logging to reduce verbosity
# Only show WARNING and above in production, INFO in development
sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
if os.getenv("ENVIRONMENT", "development") == "production":
    sqlalchemy_logger.setLevel(logging.WARNING)
else:
    sqlalchemy_logger.setLevel(logging.WARNING)  # Even in dev, reduce noise

# Get database URL from environment variable
# CRITICAL: Never hardcode production credentials. Always use environment variables.
# Default now targets PostgreSQL with asyncpg for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/prontivus_clinic"  # Default for local development only
)

# Create async engine
# Determine if we should echo SQL queries (only in development)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ECHO_SQL = (ENVIRONMENT == "development" and DEBUG)

# Connection pool configuration to prevent connection exhaustion
# These settings help prevent intermittent connection failures for both PostgreSQL and MySQL
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "25"))  # Number of connections to maintain
MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "35"))  # Additional connections beyond pool_size
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "5"))  # Seconds to wait for a connection (increased for PostgreSQL RDS)
# Recycle connections periodically to avoid stale connections (works for Postgres and MySQL/RDS)
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "7200"))  # Recycle connections after 2 hours
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"  # Test connections before using

logger = logging.getLogger(__name__)

try:
    # Configure connect_args based on database type
    connect_args = {}
    if "postgresql" in DATABASE_URL.lower():
        # PostgreSQL (asyncpg) SSL configuration for AWS RDS
        # RDS requires SSL connections
        connect_args["ssl"] = "require"
    elif "mysql" in DATABASE_URL.lower():
        # MySQL (aiomysql) configuration
        connect_args["charset"] = "utf8mb4"  # Support full UTF-8 including emojis
        connect_args["init_command"] = "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=ECHO_SQL,  # Only echo SQL in development
        future=True,
        pool_pre_ping=POOL_PRE_PING,  # Test connections before using them
        pool_size=POOL_SIZE,  # Number of connections to maintain
        max_overflow=MAX_OVERFLOW,  # Additional connections beyond pool_size
        pool_timeout=POOL_TIMEOUT,  # Seconds to wait for a connection
        pool_recycle=POOL_RECYCLE,  # Recycle connections after this many seconds
        connect_args=connect_args if connect_args else None,
    )
    logger.info(f"Database engine created with pool_size={POOL_SIZE}, max_overflow={MAX_OVERFLOW}")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}", exc_info=True)
    raise

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
async def get_db():
    """
    Dependency function to get database session
    Usage in FastAPI routes:
        async def my_route(db: AsyncSession = Depends(get_db)):
    
    Note: Session is automatically closed in the finally block to ensure
    connections are returned to the pool.
    """
    session = None
    try:
        session = AsyncSessionLocal()
        yield session
        await session.commit()
    except Exception as e:
        if session:
            await session.rollback()
        # Log database errors for debugging
        logger.error(f"Database error in session: {str(e)}", exc_info=True)
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as close_error:
                logger.warning(f"Error closing session: {close_error}")

# Alias for consistency
get_async_session = get_db

