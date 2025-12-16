"""
Script to configure OpenAI API key for a clinic
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_async_session, DATABASE_URL
from app.models import Clinic, AIConfig
from app.services.encryption_service import encrypt
from datetime import datetime, timezone


async def list_clinics(db: AsyncSession):
    """List all clinics"""
    result = await db.execute(select(Clinic).order_by(Clinic.id))
    clinics = result.scalars().all()
    return clinics


async def get_or_create_ai_config(db: AsyncSession, clinic_id: int) -> AIConfig:
    """Get or create AI config for a clinic"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.clinic_id == clinic_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Create new config with defaults
        config = AIConfig(
            clinic_id=clinic_id,
            enabled=False,
            provider="openai",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.7,
            features={
                "clinical_analysis": {"enabled": False, "description": "Análise automática de prontuários médicos"},
                "diagnosis_suggestions": {"enabled": False, "description": "Sugestões de diagnóstico baseadas em dados históricos"},
                "treatment_plan_generation": {"enabled": False, "description": "Geração de planos de tratamento personalizados"},
                "patient_education_materials": {"enabled": False, "description": "Criação de materiais educativos para pacientes"},
                "predictive_analytics": {"enabled": False, "description": "Análises preditivas para tendências de saúde e riscos"},
                "virtual_assistant": {"enabled": False, "description": "Assistente inteligente para médicos"},
            },
            usage_stats={
                "total_tokens": 0,
                "tokens_this_month": 0,
                "tokens_this_year": 0,
                "requests_count": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "last_reset_date": None,
                "last_request_date": None,
                "average_response_time_ms": 0,
                "documents_processed": 0,
                "suggestions_generated": 0,
                "approval_rate": 0.0,
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(config)
        await db.flush()
    
    return config


async def configure_openai_key(api_key: str, clinic_id: int = None):
    """Configure OpenAI API key for a clinic"""
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        try:
            # If clinic_id not provided, list clinics and let user choose
            if clinic_id is None:
                clinics = await list_clinics(db)
                if not clinics:
                    print("❌ No clinics found in the database.")
                    return
                
                print("\n" + "=" * 70)
                print("Available Clinics:")
                print("=" * 70)
                for clinic in clinics:
                    print(f"  ID: {clinic.id} - {clinic.name} ({clinic.tax_id})")
                print("=" * 70)
                
                # Use first clinic as default
                clinic_id = clinics[0].id
                print(f"\n✅ Using clinic ID {clinic_id} ({clinics[0].name})")
            
            # Verify clinic exists
            result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
            clinic = result.scalar_one_or_none()
            if not clinic:
                print(f"❌ Clinic with ID {clinic_id} not found.")
                return
            
            print(f"\n📋 Configuring OpenAI API key for clinic: {clinic.name} (ID: {clinic_id})")
            
            # Get or create AI config
            config = await get_or_create_ai_config(db, clinic_id)
            
            # Encrypt and set API key
            encrypted_key = encrypt(api_key)
            if not encrypted_key:
                print("❌ Failed to encrypt API key. Check ENCRYPTION_KEY environment variable.")
                return
            
            config.api_key_encrypted = encrypted_key
            config.provider = "openai"
            config.model = config.model or "gpt-4"
            config.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(config)
            
            print("✅ OpenAI API key configured successfully!")
            print(f"   Provider: {config.provider}")
            print(f"   Model: {config.model}")
            print(f"   Encrypted: Yes")
            print(f"   Enabled: {config.enabled}")
            print("\n💡 Note: You may need to enable AI in the clinic's license and set enabled=True via the API.")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error configuring OpenAI key: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python configure_openai_key.py <api_key> [clinic_id]")
        print("\nExample:")
        print("  python configure_openai_key.py sk-proj-...")
        print("  python configure_openai_key.py sk-proj-... 1")
        sys.exit(1)
    
    api_key = sys.argv[1]
    clinic_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    await configure_openai_key(api_key, clinic_id)


if __name__ == "__main__":
    asyncio.run(main())

