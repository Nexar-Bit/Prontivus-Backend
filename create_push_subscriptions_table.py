"""
Create push_subscriptions table directly
Use this if Alembic migration has conflicts
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def create_push_subscriptions_table():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file.")
        return

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # Check if table already exists
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='push_subscriptions');"
            ))
            if result.scalar():
                print("ℹ️  Table 'push_subscriptions' already exists. Skipping creation.")
                return

            # Create push_subscriptions table
            await conn.execute(text("""
                CREATE TABLE push_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    endpoint VARCHAR(500) NOT NULL,
                    p256dh VARCHAR(200) NOT NULL,
                    auth VARCHAR(100) NOT NULL,
                    user_agent VARCHAR(500),
                    device_info JSON,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT fk_push_subscriptions_user_id 
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """))
            
            # Create indexes
            await conn.execute(text(
                "CREATE INDEX ix_push_subscriptions_user_id ON push_subscriptions(user_id);"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_push_subscriptions_endpoint ON push_subscriptions(endpoint);"
            ))
            
            print("✅ Table 'push_subscriptions' created successfully!")
            print("✅ Indexes created successfully!")
        print("\n✅ Push subscriptions table setup completed successfully!")
        print("   You can now use the push notification feature.")
    except Exception as e:
        print(f"❌ Error creating push_subscriptions table: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_push_subscriptions_table())

