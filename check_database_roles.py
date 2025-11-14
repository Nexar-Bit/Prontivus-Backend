"""
Script to check database roles and user assignments
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

from app.models import User
from app.models.menu import UserRole as UserRoleModel
from config import settings

async def check_database():
    """Check database roles and user assignments"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("=" * 60)
            print("DATABASE ROLES CHECK")
            print("=" * 60)
            
            # Check user_roles table
            print("\n1. Checking user_roles table...")
            result = await db.execute(select(UserRoleModel).order_by(UserRoleModel.id))
            roles = result.scalars().all()
            
            if not roles:
                print("   ❌ No roles found in user_roles table!")
                print("   → Run: python seed_menu_data.py")
            else:
                print(f"   ✓ Found {len(roles)} roles:")
                for role in roles:
                    print(f"      - ID: {role.id}, Name: '{role.name}', Description: {role.description}")
            
            # Check users with role_id
            print("\n2. Checking users with role_id...")
            result = await db.execute(
                select(User).where(User.role_id.isnot(None))
            )
            users_with_role = result.scalars().all()
            
            if not users_with_role:
                print("   ❌ No users found with role_id!")
            else:
                print(f"   ✓ Found {len(users_with_role)} users with role_id:")
                for user in users_with_role:
                    role_name = "N/A"
                    if user.role_id:
                        role_result = await db.execute(
                            select(UserRoleModel).where(UserRoleModel.id == user.role_id)
                        )
                        role = role_result.scalar_one_or_none()
                        if role:
                            role_name = role.name
                    
                    print(f"      - Username: '{user.username}', Role ID: {user.role_id}, Role Name: '{role_name}', Enum Role: {user.role}")
            
            # Check superadmin user specifically
            print("\n3. Checking 'superadmin' user...")
            result = await db.execute(
                select(User).where(User.username == "superadmin")
            )
            superadmin_user = result.scalar_one_or_none()
            
            if not superadmin_user:
                print("   ❌ User 'superadmin' not found!")
                print("   → Run: python seed_menu_data.py")
            else:
                print(f"   ✓ Found user 'superadmin':")
                print(f"      - ID: {superadmin_user.id}")
                print(f"      - Email: {superadmin_user.email}")
                print(f"      - Enum Role: {superadmin_user.role}")
                print(f"      - Role ID: {superadmin_user.role_id}")
                
                if superadmin_user.role_id:
                    role_result = await db.execute(
                        select(UserRoleModel).where(UserRoleModel.id == superadmin_user.role_id)
                    )
                    role = role_result.scalar_one_or_none()
                    if role:
                        print(f"      - Role Name: '{role.name}'")
                    else:
                        print(f"      - ⚠️  Role ID {superadmin_user.role_id} not found in user_roles table!")
                else:
                    print(f"      - ❌ No role_id assigned!")
                    print(f"      - → Need to update user with role_id")
            
            # Check all users
            print("\n4. Checking all users...")
            result = await db.execute(select(User))
            all_users = result.scalars().all()
            print(f"   ✓ Found {len(all_users)} total users:")
            for user in all_users:
                role_info = f"role_id={user.role_id}" if user.role_id else "role_id=NULL"
                print(f"      - Username: '{user.username}', Enum: {user.role}, {role_info}")
            
            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            
            if not roles:
                print("❌ CRITICAL: user_roles table is empty!")
                print("   → Run: python seed_menu_data.py")
            elif not superadmin_user:
                print("❌ CRITICAL: 'superadmin' user not found!")
                print("   → Run: python seed_menu_data.py")
            elif not superadmin_user.role_id:
                print("⚠️  WARNING: 'superadmin' user exists but has no role_id!")
                print("   → Need to update user with SuperAdmin role_id")
            else:
                # Check if role_id points to SuperAdmin
                role_result = await db.execute(
                    select(UserRoleModel).where(UserRoleModel.id == superadmin_user.role_id)
                )
                role = role_result.scalar_one_or_none()
                if role and role.name == "SuperAdmin":
                    print("✅ Everything looks good!")
                elif role:
                    print(f"⚠️  WARNING: 'superadmin' user has role_id={superadmin_user.role_id} which points to '{role.name}', not 'SuperAdmin'!")
                else:
                    print(f"❌ ERROR: 'superadmin' user has role_id={superadmin_user.role_id} but this role doesn't exist!")
            
        except Exception as e:
            print(f"\n❌ Error checking database: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_database())

