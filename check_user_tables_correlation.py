"""
Script to check correlation between all user-related tables
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text, inspect

from app.models import User, Clinic
from app.models.menu import UserRole as UserRoleModel
from config import settings

async def check_user_tables_correlation():
    """Check correlation between all user-related tables"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("=" * 80)
            print("USER-RELATED TABLES CORRELATION CHECK")
            print("=" * 80)
            
            # 1. Check user_roles table structure
            print("\n1. USER_ROLES TABLE")
            print("-" * 80)
            result = await db.execute(select(UserRoleModel).order_by(UserRoleModel.id))
            roles = result.scalars().all()
            
            print(f"Total roles: {len(roles)}")
            print(f"\n{'ID':<5} {'Name':<20} {'Description':<40} {'is_system':<10}")
            print("-" * 80)
            for role in roles:
                print(f"{role.id:<5} {role.name:<20} {role.description[:40]:<40} {str(role.is_system):<10}")
            
            # 2. Check users table structure and relationships
            print("\n\n2. USERS TABLE")
            print("-" * 80)
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            print(f"Total users: {len(users)}")
            print(f"\n{'ID':<5} {'Username':<25} {'Email':<30} {'Enum Role':<15} {'role_id':<10} {'clinic_id':<10}")
            print("-" * 80)
            
            users_without_role_id = []
            users_with_invalid_role_id = []
            users_without_clinic = []
            
            for user in users:
                # Check role_id correlation
                role_name = "NULL"
                role_valid = True
                if user.role_id:
                    role_result = await db.execute(
                        select(UserRoleModel).where(UserRoleModel.id == user.role_id)
                    )
                    role = role_result.scalar_one_or_none()
                    if role:
                        role_name = role.name
                    else:
                        role_name = f"INVALID (ID {user.role_id})"
                        role_valid = False
                        users_with_invalid_role_id.append(user)
                else:
                    users_without_role_id.append(user)
                
                # Check clinic_id correlation
                clinic_name = "NULL"
                if user.clinic_id:
                    clinic_result = await db.execute(
                        select(Clinic).where(Clinic.id == user.clinic_id)
                    )
                    clinic = clinic_result.scalar_one_or_none()
                    if clinic:
                        clinic_name = clinic.name[:20]
                    else:
                        clinic_name = f"INVALID (ID {user.clinic_id})"
                        users_without_clinic.append(user)
                else:
                    users_without_clinic.append(user)
                
                print(f"{user.id:<5} {user.username[:25]:<25} {str(user.email)[:30]:<30} {str(user.role):<15} {str(user.role_id) if user.role_id else 'NULL':<10} {str(user.clinic_id) if user.clinic_id else 'NULL':<10}")
                if not role_valid:
                    print(f"      ⚠️  Role ID {user.role_id} does not exist in user_roles table!")
            
            # 3. Check enum role to role_id mapping
            print("\n\n3. ENUM ROLE TO ROLE_ID MAPPING")
            print("-" * 80)
            
            enum_to_role_map = {
                "admin": "SuperAdmin",
                "secretary": "Secretaria",
                "doctor": "Medico",
                "patient": "Paciente"
            }
            
            print(f"\n{'Enum Role':<20} {'Expected Role Name':<20} {'Users Count':<15} {'Mismatches':<15}")
            print("-" * 80)
            
            for enum_role, expected_role_name in enum_to_role_map.items():
                # Get expected role_id
                role_result = await db.execute(
                    select(UserRoleModel).where(UserRoleModel.name == expected_role_name)
                )
                expected_role = role_result.scalar_one_or_none()
                expected_role_id = expected_role.id if expected_role else None
                
                # Count users with this enum role
                users_with_enum = [u for u in users if u.role.value == enum_role]
                mismatches = []
                
                for user in users_with_enum:
                    if user.role_id != expected_role_id:
                        mismatches.append(user)
                
                mismatch_count = len(mismatches)
                print(f"{enum_role:<20} {expected_role_name:<20} {len(users_with_enum):<15} {mismatch_count:<15}")
                
                if mismatches:
                    print(f"      ⚠️  Mismatches found:")
                    for user in mismatches:
                        actual_role_name = "NULL"
                        if user.role_id:
                            role_result = await db.execute(
                                select(UserRoleModel).where(UserRoleModel.id == user.role_id)
                            )
                            role = role_result.scalar_one_or_none()
                            if role:
                                actual_role_name = role.name
                        print(f"         - {user.username}: enum={enum_role}, role_id={user.role_id} ({actual_role_name})")
            
            # 4. Check specific superadmin user
            print("\n\n4. SUPERADMIN USER DETAILED CHECK")
            print("-" * 80)
            
            result = await db.execute(
                select(User).where(User.username == "superadmin")
            )
            superadmin_user = result.scalar_one_or_none()
            
            if superadmin_user:
                print(f"✓ User 'superadmin' found:")
                print(f"  - ID: {superadmin_user.id}")
                print(f"  - Email: {superadmin_user.email}")
                print(f"  - Enum Role: {superadmin_user.role.value}")
                print(f"  - Role ID: {superadmin_user.role_id}")
                print(f"  - Clinic ID: {superadmin_user.clinic_id}")
                
                if superadmin_user.role_id:
                    role_result = await db.execute(
                        select(UserRoleModel).where(UserRoleModel.id == superadmin_user.role_id)
                    )
                    role = role_result.scalar_one_or_none()
                    if role:
                        print(f"  - Role Name: {role.name}")
                        print(f"  - Role Description: {role.description}")
                        
                        if role.name != "SuperAdmin":
                            print(f"  ⚠️  WARNING: User has role_id={superadmin_user.role_id} but role name is '{role.name}', not 'SuperAdmin'!")
                    else:
                        print(f"  ❌ ERROR: Role ID {superadmin_user.role_id} not found in user_roles table!")
                else:
                    print(f"  ❌ ERROR: User has no role_id assigned!")
            else:
                print("❌ User 'superadmin' not found!")
            
            # 5. Check all users with admin enum role
            print("\n\n5. ALL USERS WITH ADMIN ENUM ROLE")
            print("-" * 80)
            
            admin_users = [u for u in users if u.role.value == "admin"]
            print(f"Found {len(admin_users)} users with enum role 'admin':")
            
            for user in admin_users:
                role_name = "NULL"
                if user.role_id:
                    role_result = await db.execute(
                        select(UserRoleModel).where(UserRoleModel.id == user.role_id)
                    )
                    role = role_result.scalar_one_or_none()
                    if role:
                        role_name = role.name
                
                print(f"  - {user.username}: role_id={user.role_id}, role_name='{role_name}'")
            
            # 6. Check foreign key constraints
            print("\n\n6. FOREIGN KEY CONSTRAINTS CHECK")
            print("-" * 80)
            
            # Check users.role_id -> user_roles.id
            invalid_role_ids = []
            for user in users:
                if user.role_id:
                    role_result = await db.execute(
                        select(UserRoleModel).where(UserRoleModel.id == user.role_id)
                    )
                    role = role_result.scalar_one_or_none()
                    if not role:
                        invalid_role_ids.append((user.username, user.role_id))
            
            if invalid_role_ids:
                print(f"❌ Found {len(invalid_role_ids)} users with invalid role_id:")
                for username, role_id in invalid_role_ids:
                    print(f"  - {username}: role_id={role_id} (does not exist)")
            else:
                print("✓ All role_id foreign keys are valid")
            
            # Check users.clinic_id -> clinics.id
            invalid_clinic_ids = []
            for user in users:
                if user.clinic_id:
                    clinic_result = await db.execute(
                        select(Clinic).where(Clinic.id == user.clinic_id)
                    )
                    clinic = clinic_result.scalar_one_or_none()
                    if not clinic:
                        invalid_clinic_ids.append((user.username, user.clinic_id))
            
            if invalid_clinic_ids:
                print(f"❌ Found {len(invalid_clinic_ids)} users with invalid clinic_id:")
                for username, clinic_id in invalid_clinic_ids:
                    print(f"  - {username}: clinic_id={clinic_id} (does not exist)")
            else:
                print("✓ All clinic_id foreign keys are valid")
            
            # 7. Summary
            print("\n\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            
            issues = []
            
            if users_without_role_id:
                issues.append(f"❌ {len(users_without_role_id)} users without role_id")
            
            if users_with_invalid_role_id:
                issues.append(f"❌ {len(users_with_invalid_role_id)} users with invalid role_id")
            
            if users_without_clinic:
                issues.append(f"⚠️  {len(users_without_clinic)} users without clinic_id")
            
            if not superadmin_user:
                issues.append("❌ 'superadmin' user not found")
            elif superadmin_user.role_id:
                role_result = await db.execute(
                    select(UserRoleModel).where(UserRoleModel.id == superadmin_user.role_id)
                )
                role = role_result.scalar_one_or_none()
                if role and role.name != "SuperAdmin":
                    issues.append(f"⚠️  'superadmin' user has role '{role.name}' instead of 'SuperAdmin'")
            
            if issues:
                print("\nIssues found:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n✅ All correlations are correct!")
            
            print("\n" + "=" * 80)
            
        except Exception as e:
            print(f"\n❌ Error checking database: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_user_tables_correlation())

