"""
Script to create the initial SuperAdmin user automatically
Uses default credentials (can be overridden via environment variables)
"""
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from app.models import User, UserRole as UserRoleEnum, Clinic
from app.models.menu import UserRole as UserRoleModel
from app.core.security import hash_password

async def create_initial_admin():
    """Create initial SuperAdmin user with default or environment credentials"""
    
    # Get credentials from environment or use defaults
    username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    email = os.getenv("SUPERADMIN_EMAIL", "admin@prontivus.com")
    password = os.getenv("SUPERADMIN_PASSWORD", "Admin@123456")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if SuperAdmin role exists (role_id = 1)
            role_query = await db.execute(
                select(UserRoleModel).where(UserRoleModel.id == 1)
            )
            superadmin_role = role_query.scalar_one_or_none()
            
            if not superadmin_role:
                print("❌ Error: SuperAdmin role (role_id=1) not found!")
                print("   Please ensure migrations have been run: alembic upgrade head")
                return False
            
            # Check if SuperAdmin user already exists
            existing_user = await db.execute(
                select(User).where(
                    (User.role_id == 1) | (User.username == username)
                )
            )
            existing = existing_user.scalar_one_or_none()
            if existing:
                print("⚠️  SuperAdmin user already exists!")
                print(f"   Username: {existing.username}")
                print(f"   Email: {existing.email}")
                print("   You can use this account to log in.")
                return True
            
            # Check if any clinic exists (SuperAdmin needs a clinic_id)
            clinic_query = await db.execute(select(Clinic))
            clinic = clinic_query.scalar_one_or_none()
            
            if not clinic:
                print("⚠️  No clinic found. Creating a default clinic first...")
                # Create a default clinic for SuperAdmin
                default_clinic = Clinic(
                    name="Sistema Principal",
                    legal_name="Sistema Principal",
                    tax_id="00000000000000",
                    email=email,
                    is_active=True,
                    max_users=1000
                )
                db.add(default_clinic)
                await db.commit()
                await db.refresh(default_clinic)
                clinic = default_clinic
                print(f"✅ Created default clinic: {default_clinic.name} (ID: {default_clinic.id})")
            
            # Check if username/email already exists
            existing_username = await db.execute(
                select(User).where(User.username == username)
            )
            if existing_username.scalar_one_or_none():
                print(f"❌ Error: Username '{username}' already exists!")
                return False
            
            existing_email = await db.execute(
                select(User).where(User.email == email)
            )
            if existing_email.scalar_one_or_none():
                print(f"❌ Error: Email '{email}' already exists!")
                return False
            
            # Create SuperAdmin user
            print("\n" + "=" * 60)
            print("Creating Initial SuperAdmin User")
            print("=" * 60)
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Password: {'*' * len(password)}")
            
            superadmin_user = User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                first_name="Super",
                last_name="Admin",
                role=UserRoleEnum.ADMIN,  # Legacy enum
                role_id=1,  # SuperAdmin role_id
                clinic_id=clinic.id,
                is_active=True,
                is_verified=True
            )
            
            db.add(superadmin_user)
            await db.commit()
            await db.refresh(superadmin_user)
            
            print("\n" + "=" * 60)
            print("✅ SuperAdmin user created successfully!")
            print("=" * 60)
            print(f"\nLogin Credentials:")
            print(f"  Username: {username}")
            print(f"  Email: {email}")
            print(f"  Password: {password}")
            print(f"\n⚠️  IMPORTANT: Save these credentials securely!")
            print("   Change the password after first login for security.")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error creating SuperAdmin: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Prontivus - Create Initial SuperAdmin (Auto)")
    print("=" * 60)
    print("\nUsing default credentials:")
    print("  Username: superadmin")
    print("  Email: admin@prontivus.com")
    print("  Password: Admin@123456")
    print("\nTo customize, set environment variables:")
    print("  SUPERADMIN_USERNAME=your_username")
    print("  SUPERADMIN_EMAIL=your_email")
    print("  SUPERADMIN_PASSWORD=your_password")
    print("=" * 60)
    
    try:
        success = asyncio.run(create_initial_admin())
        if success:
            print("\n✅ Setup complete! You can now log in with the SuperAdmin account.")
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

