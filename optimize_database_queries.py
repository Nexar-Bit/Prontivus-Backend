"""
Database Query Optimization Script
Identifies missing indexes and slow queries to improve performance
"""
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL, POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT, POOL_RECYCLE, POOL_PRE_PING

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_table_indexes(session: AsyncSession, table_name: str):
    """Check indexes for a specific table"""
    try:
        result = await session.execute(text(f"""
            SHOW INDEXES FROM {table_name}
        """))
        indexes = result.fetchall()
        return [idx[2] for idx in indexes]  # Return index names
    except Exception as e:
        logger.warning(f"Could not check indexes for {table_name}: {e}")
        return []


async def analyze_slow_queries(session: AsyncSession):
    """Analyze slow queries from MySQL slow query log"""
    try:
        # Check if slow query log is enabled
        result = await session.execute(text("SHOW VARIABLES LIKE 'slow_query_log'"))
        slow_log_enabled = result.fetchone()
        
        if slow_log_enabled and slow_log_enabled[1] == 'ON':
            logger.info("Slow query log is enabled - checking for slow queries...")
            # Note: Accessing slow query log requires file system access
            # This is a placeholder for the analysis
            return True
        else:
            logger.info("Slow query log is not enabled")
            return False
    except Exception as e:
        logger.warning(f"Could not check slow query log: {e}")
        return False


async def check_missing_indexes(session: AsyncSession):
    """Check for common missing indexes on frequently queried columns"""
    logger.info("\n" + "=" * 70)
    logger.info("Checking for Missing Indexes")
    logger.info("=" * 70)
    
    # Common columns that should be indexed for performance
    tables_to_check = {
        "users": ["clinic_id", "email", "username", "role_id", "is_active"],
        "patients": ["clinic_id", "is_active", "created_at"],
        "appointments": ["clinic_id", "scheduled_datetime", "status", "patient_id"],
        "clinical_records": ["clinic_id", "patient_id", "appointment_id", "created_at"],
        "invoices": ["clinic_id", "issue_date", "status", "patient_id", "appointment_id"],
        "payments": ["invoice_id", "payment_date", "status"],
        "notifications": ["user_id", "is_read", "created_at"],
        "user_settings": ["user_id"],
        "stock_movements": ["product_id", "clinic_id", "movement_date"],
        "products": ["clinic_id", "is_active"],
    }
    
    missing_indexes = []
    
    for table_name, columns in tables_to_check.items():
        try:
            # Check if table exists
            result = await session.execute(text(f"""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table_name}'
            """))
            table_exists = result.scalar() > 0
            
            if not table_exists:
                logger.debug(f"Table {table_name} does not exist, skipping...")
                continue
            
            # Get existing indexes
            existing_indexes = await check_table_indexes(session, table_name)
            
            # Check each column
            for column in columns:
                # Check if there's an index on this column
                result = await session.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                    AND table_name = '{table_name}'
                    AND column_name = '{column}'
                """))
                has_index = result.scalar() > 0
                
                if not has_index:
                    missing_indexes.append({
                        "table": table_name,
                        "column": column,
                        "recommendation": f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column});"
                    })
                    logger.warning(f"  ❌ Missing index on {table_name}.{column}")
                else:
                    logger.info(f"  ✅ Index exists on {table_name}.{column}")
        except Exception as e:
            logger.warning(f"Could not check indexes for {table_name}: {e}")
    
    return missing_indexes


async def check_query_performance(session: AsyncSession):
    """Check performance of common queries"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Query Performance")
    logger.info("=" * 70)
    
    test_queries = [
        ("Users by clinic", "SELECT COUNT(*) FROM users WHERE clinic_id = 1"),
        ("Active patients", "SELECT COUNT(*) FROM patients WHERE clinic_id = 1 AND is_active = 1"),
        ("Appointments this month", """
            SELECT COUNT(*) FROM appointments 
            WHERE clinic_id = 1 
            AND scheduled_datetime >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
        """),
        ("User settings", "SELECT * FROM user_settings WHERE user_id = 1 LIMIT 1"),
    ]
    
    results = []
    for query_name, query_sql in test_queries:
        try:
            import time
            start_time = time.time()
            result = await session.execute(text(query_sql))
            elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            row_count = result.scalar() if hasattr(result, 'scalar') else 0
            
            status = "✅" if elapsed < 100 else "⚠️" if elapsed < 500 else "❌"
            logger.info(f"{status} {query_name}: {elapsed:.2f}ms (rows: {row_count})")
            
            results.append({
                "query": query_name,
                "time_ms": elapsed,
                "status": "fast" if elapsed < 100 else "slow" if elapsed < 500 else "very_slow"
            })
        except Exception as e:
            logger.warning(f"  ❌ {query_name} failed: {e}")
            results.append({
                "query": query_name,
                "time_ms": None,
                "status": "error",
                "error": str(e)
            })
    
    return results


async def generate_optimization_suggestions(missing_indexes, query_results):
    """Generate optimization suggestions"""
    logger.info("\n" + "=" * 70)
    logger.info("Optimization Suggestions")
    logger.info("=" * 70)
    
    if missing_indexes:
        logger.info("\n📋 Missing Indexes to Create:")
        logger.info("-" * 70)
        for idx in missing_indexes:
            logger.info(f"\n-- Table: {idx['table']}, Column: {idx['column']}")
            logger.info(idx['recommendation'])
    
    slow_queries = [q for q in query_results if q.get('status') in ['slow', 'very_slow']]
    if slow_queries:
        logger.info("\n⚠️  Slow Queries Detected:")
        logger.info("-" * 70)
        for q in slow_queries:
            logger.info(f"  - {q['query']}: {q.get('time_ms', 'N/A')}ms")
            logger.info("    Consider adding indexes or optimizing the query")
    
    if not missing_indexes and not slow_queries:
        logger.info("\n✅ No obvious optimization issues found!")
        logger.info("   Database queries appear to be performing well.")
    
    # General recommendations
    logger.info("\n💡 General Recommendations:")
    logger.info("-" * 70)
    logger.info("1. Ensure MySQL query cache is enabled (if using MySQL < 8.0)")
    logger.info("2. Monitor slow query log for queries taking > 1 second")
    logger.info("3. Consider increasing connection pool size if pool exhaustion occurs")
    logger.info("4. Use EXPLAIN to analyze query execution plans")
    logger.info("5. Consider partitioning large tables if they grow significantly")


async def main():
    """Main function"""
    print("=" * 70)
    print("Database Query Optimization Analysis")
    print("=" * 70)
    
    # Create engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=POOL_PRE_PING,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check missing indexes
            missing_indexes = await check_missing_indexes(session)
            
            # Check query performance
            query_results = await check_query_performance(session)
            
            # Generate suggestions
            await generate_optimization_suggestions(missing_indexes, query_results)
            
            # Save recommendations to file
            if missing_indexes:
                with open("database_optimization_indexes.sql", "w") as f:
                    f.write("-- Database Index Optimization Script\n")
                    f.write("-- Generated by optimize_database_queries.py\n\n")
                    for idx in missing_indexes:
                        f.write(f"-- Index for {idx['table']}.{idx['column']}\n")
                        f.write(f"{idx['recommendation']}\n\n")
                logger.info(f"\n💾 Index creation SQL saved to: database_optimization_indexes.sql")
            
        except Exception as e:
            logger.error(f"Error during optimization analysis: {e}", exc_info=True)
        finally:
            await engine.dispose()
    
    print("\n" + "=" * 70)
    print("Analysis Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

