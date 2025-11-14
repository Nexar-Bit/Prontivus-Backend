"""
Script to update existing users with role_id based on their enum role
Run this after seeding menu data to link existing users to the new role system
"""
import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import User
from app.models.menu import UserRole as UserRoleModel
from database import get_async_session, DATABASE_URL

async def update_user_roles():
    """Update all users to have role_id based on their enum role"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Get all roles
            roles_result = await db.execute(select(UserRoleModel))
            roles = roles_result.scalars().all()
            role_map = {role.name: role.id for role in roles}
            
            print(f"Found {len(roles)} roles: {list(role_map.keys())}")
            
            # Map enum roles to role names
            enum_to_role_name = {
                "admin": "SuperAdmin",
                "secretary": "Secretaria",
                "doctor": "Medico",
                "patient": "Paciente"
            }
            
            # Get all users without role_id
            users_result = await db.execute(
                select(User).where(User.role_id == None)
            )
            users = users_result.scalars().all()
            
            print(f"\nFound {len(users)} users without role_id")
            
            updated_count = 0
            for user in users:
                role_name = enum_to_role_name.get(user.role.value)
                if role_name and role_name in role_map:
                    user.role_id = role_map[role_name]
                    updated_count += 1
                    print(f"  ✓ Updated {user.username} ({user.role.value}) -> role_id: {role_map[role_name]}")
                else:
                    print(f"  ⚠️  Skipped {user.username} ({user.role.value}) - role not found in mapping")
            
            if updated_count > 0:
                await db.commit()
                print(f"\n✅ Successfully updated {updated_count} users with role_id")
            else:
                print("\n⚠️  No users were updated")
                
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error updating user roles: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_user_roles())

