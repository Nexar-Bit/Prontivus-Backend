"""Quick verification script for symptoms database"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from app.models.symptom import Symptom, SymptomICD10Mapping
from database import DATABASE_URL

async def verify():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Count symptoms
        symptom_count = await session.scalar(select(func.count(Symptom.id)))
        
        # Count mappings
        mapping_count = await session.scalar(select(func.count(SymptomICD10Mapping.id)))
        
        # Get sample symptoms
        result = await session.execute(
            select(Symptom).limit(5)
        )
        sample_symptoms = result.scalars().all()
        
        print("=" * 50)
        print("✅ Symptoms Database Verification")
        print("=" * 50)
        print(f"Total Symptoms: {symptom_count}")
        print(f"Total Mappings: {mapping_count}")
        print("\nSample Symptoms:")
        for symptom in sample_symptoms:
            print(f"  - {symptom.name} ({symptom.category})")
        print("=" * 50)
        
        if symptom_count >= 12:
            print("✅ Database is properly seeded!")
        else:
            print("⚠️  Warning: Expected at least 12 symptoms")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())

