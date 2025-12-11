"""
Script to create the initial SuperAdmin user for MySQL database
Run this after migrations are complete
"""
import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from app.models import User, UserRole as UserRoleEnum, Clinic
from app.models.menu import UserRole as UserRoleModel
from app.core.security import hash_password

async def create_initial_admin():
    """Create initial SuperAdmin user"""
    
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
                    (User.role_id == 1) | (User.username == "superadmin")
                )
            )
            if existing_user.scalar_one_or_none():
                print("⚠️  SuperAdmin user already exists!")
                print("   You can use the existing SuperAdmin account to log in.")
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
                    email="admin@prontivus.com",
                    is_active=True,
                    max_users=1000
                )
                db.add(default_clinic)
                await db.commit()
                await db.refresh(default_clinic)
                clinic = default_clinic
                print(f"✅ Created default clinic: {default_clinic.name} (ID: {default_clinic.id})")
            
            # Create SuperAdmin user
            print("\n" + "=" * 60)
            print("Creating Initial SuperAdmin User")
            print("=" * 60)
            
            # Get user input for credentials
            print("\nEnter SuperAdmin credentials:")
            username = input("Username [superadmin]: ").strip() or "superadmin"
            email = input("Email [admin@prontivus.com]: ").strip() or "admin@prontivus.com"
            password = input("Password (min 8 chars): ").strip()
            
            if len(password) < 8:
                print("❌ Error: Password must be at least 8 characters!")
                return False
            
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
            print(f"  Password: [the password you entered]")
            print(f"\n⚠️  IMPORTANT: Save these credentials securely!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error creating SuperAdmin: {e}")
            await db.rollback()
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Prontivus - Create Initial SuperAdmin")
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
        sys.exit(1)

