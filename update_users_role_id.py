"""
Update Existing Users with role_id
Maps existing enum roles to new role_id foreign keys
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

from app.models import User, UserRole as UserRoleEnum
from app.models.menu import UserRole as UserRoleModel
from config import settings


async def update_users_role_id():
    """Update existing users to have role_id based on their enum role"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Map enum roles to role names
            role_mapping = {
                UserRoleEnum.ADMIN: "SuperAdmin",
                UserRoleEnum.SECRETARY: "Secretaria",
                UserRoleEnum.DOCTOR: "Medico",
                UserRoleEnum.PATIENT: "Paciente"
            }
            
            # Get all roles
            result = await db.execute(select(UserRoleModel))
            roles = result.scalars().all()
            role_dict = {role.name: role.id for role in roles}
            
            # Update users without role_id
            result = await db.execute(
                select(User).where(User.role_id.is_(None))
            )
            users = result.scalars().all()
            
            updated_count = 0
            for user in users:
                role_name = role_mapping.get(user.role)
                if role_name and role_name in role_dict:
                    user.role_id = role_dict[role_name]
                    updated_count += 1
                    print(f"  ✓ Updated user {user.username} ({user.email}) with role_id: {role_dict[role_name]} ({role_name})")
            
            await db.commit()
            print(f"\n✅ Updated {updated_count} users with role_id")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error updating users: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_users_role_id())

