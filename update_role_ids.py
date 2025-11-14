"""
Script to update role_id for users
Changes all users with role_id=1 to role_id=2, except admin@prontivus.com
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

from app.models import User
from app.models.menu import UserRole as UserRoleModel
from config import settings

async def update_role_ids():
    """Update role_id for users with role_id=1, except admin@prontivus.com"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("=" * 80)
            print("UPDATING ROLE_ID FOR USERS")
            print("=" * 80)
            
            # First, check current state
            print("\n1. Current users with role_id=1:")
            print("-" * 80)
            result = await db.execute(
                select(User).where(User.role_id == 1)
            )
            users_with_role_1 = result.scalars().all()
            
            print(f"{'ID':<5} {'Username':<25} {'Email':<35} {'Current role_id':<15}")
            print("-" * 80)
            for user in users_with_role_1:
                print(f"{user.id:<5} {user.username[:25]:<25} {str(user.email)[:35]:<35} {user.role_id:<15}")
            
            # Verify admin@prontivus.com exists
            print("\n2. Checking admin@prontivus.com:")
            print("-" * 80)
            result = await db.execute(
                select(User).where(User.email == "admin@prontivus.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("❌ ERROR: User with email 'admin@prontivus.com' not found!")
                return
            
            print(f"✓ Found user: {admin_user.username} (ID: {admin_user.id})")
            print(f"  Current role_id: {admin_user.role_id}")
            
            # Verify role_id=2 exists (AdminClinica)
            print("\n3. Verifying role_id=2 exists:")
            print("-" * 80)
            result = await db.execute(
                select(UserRoleModel).where(UserRoleModel.id == 2)
            )
            role_2 = result.scalar_one_or_none()
            
            if not role_2:
                print("❌ ERROR: Role with ID=2 not found!")
                return
            
            print(f"✓ Role ID 2 exists: {role_2.name} ({role_2.description})")
            
            # Find users to update (role_id=1 but NOT admin@prontivus.com)
            print("\n4. Users to be updated (role_id=1 → role_id=2):")
            print("-" * 80)
            result = await db.execute(
                select(User).where(
                    User.role_id == 1,
                    User.email != "admin@prontivus.com"
                )
            )
            users_to_update = result.scalars().all()
            
            if not users_to_update:
                print("✓ No users to update. All users with role_id=1 are already correct.")
                return
            
            print(f"Found {len(users_to_update)} users to update:")
            print(f"{'ID':<5} {'Username':<25} {'Email':<35} {'Current role_id':<15} {'New role_id':<15}")
            print("-" * 80)
            for user in users_to_update:
                print(f"{user.id:<5} {user.username[:25]:<25} {str(user.email)[:35]:<35} {user.role_id:<15} 2")
            
            # Confirm update
            print("\n5. Summary:")
            print("-" * 80)
            print(f"✓ User to KEEP with role_id=1: {admin_user.username} ({admin_user.email})")
            print(f"✓ Users to UPDATE to role_id=2: {len(users_to_update)} users")
            print(f"  - New role: {role_2.name} ({role_2.description})")
            
            # Perform update
            print("\n6. Performing update...")
            print("-" * 80)
            
            updated_count = 0
            for user in users_to_update:
                user.role_id = 2
                updated_count += 1
                print(f"  ✓ Updated {user.username} (ID: {user.id}): role_id {1} → {2}")
            
            await db.commit()
            
            print(f"\n✅ Successfully updated {updated_count} users!")
            
            # Verify update
            print("\n7. Verification after update:")
            print("-" * 80)
            
            # Check users with role_id=1
            result = await db.execute(
                select(User).where(User.role_id == 1)
            )
            users_with_role_1_after = result.scalars().all()
            
            print(f"Users with role_id=1 (should be only admin@prontivus.com):")
            print(f"{'ID':<5} {'Username':<25} {'Email':<35} {'role_id':<10}")
            print("-" * 80)
            for user in users_with_role_1_after:
                print(f"{user.id:<5} {user.username[:25]:<25} {str(user.email)[:35]:<35} {user.role_id:<10}")
            
            if len(users_with_role_1_after) == 1 and users_with_role_1_after[0].email == "admin@prontivus.com":
                print("✅ Verification passed! Only admin@prontivus.com has role_id=1")
            else:
                print("⚠️  WARNING: Verification failed! Check the results above.")
            
            # Check users with role_id=2
            result = await db.execute(
                select(User).where(User.role_id == 2)
            )
            users_with_role_2_after = result.scalars().all()
            
            print(f"\nUsers with role_id=2 (AdminClinica):")
            print(f"{'ID':<5} {'Username':<25} {'Email':<35} {'role_id':<10}")
            print("-" * 80)
            for user in users_with_role_2_after:
                print(f"{user.id:<5} {user.username[:25]:<25} {str(user.email)[:35]:<35} {user.role_id:<10}")
            
            print(f"\n✅ Total users with role_id=2: {len(users_with_role_2_after)}")
            
            print("\n" + "=" * 80)
            print("UPDATE COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error updating role_ids: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_role_ids())

