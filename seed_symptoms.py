"""
Seed script for populating symptoms and symptom-ICD10 mappings
Run this after creating the symptom tables
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import os
from dotenv import load_dotenv

from app.models.symptom import Symptom, SymptomICD10Mapping
from database import DATABASE_URL

load_dotenv()

# Common symptoms with their ICD-10 mappings
SYMPTOMS_DATA = [
    {
        "name": "febre",
        "description": "Aumento da temperatura corporal acima do normal",
        "category": "geral",
        "icd10_codes": [
            {"code": "R50", "relevance": 100, "notes": "Febre de origem desconhecida"},
            {"code": "J06", "relevance": 90, "notes": "Infecções respiratórias"},
            {"code": "A09", "relevance": 85, "notes": "Gastroenterite"},
            {"code": "A02", "relevance": 80, "notes": "Infecções por salmonelas"},
        ]
    },
    {
        "name": "cefaleia",
        "description": "Dor de cabeça",
        "category": "neurológico",
        "icd10_codes": [
            {"code": "R51", "relevance": 100, "notes": "Cefaleia"},
            {"code": "G43", "relevance": 90, "notes": "Enxaqueca"},
            {"code": "G44", "relevance": 85, "notes": "Outras síndromes de cefaleia"},
            {"code": "I10", "relevance": 70, "notes": "Hipertensão"},
        ]
    },
    {
        "name": "dor abdominal",
        "description": "Dor na região do abdome",
        "category": "gastrointestinal",
        "icd10_codes": [
            {"code": "R10", "relevance": 100, "notes": "Dor abdominal e pélvica"},
            {"code": "K35", "relevance": 90, "notes": "Apendicite aguda"},
            {"code": "K57", "relevance": 85, "notes": "Doença diverticular"},
            {"code": "A09", "relevance": 80, "notes": "Gastroenterite"},
        ]
    },
    {
        "name": "náusea",
        "description": "Sensação de vontade de vomitar",
        "category": "gastrointestinal",
        "icd10_codes": [
            {"code": "R11", "relevance": 100, "notes": "Náusea e vômito"},
            {"code": "A09", "relevance": 90, "notes": "Gastroenterite"},
            {"code": "K29", "relevance": 85, "notes": "Gastrite"},
            {"code": "R10", "relevance": 75, "notes": "Dor abdominal"},
        ]
    },
    {
        "name": "vômito",
        "description": "Expulsão do conteúdo gástrico",
        "category": "gastrointestinal",
        "icd10_codes": [
            {"code": "R11", "relevance": 100, "notes": "Náusea e vômito"},
            {"code": "A09", "relevance": 90, "notes": "Gastroenterite"},
            {"code": "K29", "relevance": 85, "notes": "Gastrite"},
            {"code": "K35", "relevance": 80, "notes": "Apendicite aguda"},
        ]
    },
    {
        "name": "tosse",
        "description": "Expulsão brusca de ar dos pulmões",
        "category": "respiratório",
        "icd10_codes": [
            {"code": "R05", "relevance": 100, "notes": "Tosse"},
            {"code": "J06", "relevance": 90, "notes": "Infecções respiratórias"},
            {"code": "J20", "relevance": 85, "notes": "Bronquite aguda"},
            {"code": "J40", "relevance": 80, "notes": "Bronquite não especificada"},
            {"code": "J44", "relevance": 75, "notes": "Doença pulmonar obstrutiva crônica"},
        ]
    },
    {
        "name": "dispneia",
        "description": "Dificuldade para respirar",
        "category": "respiratório",
        "icd10_codes": [
            {"code": "R06", "relevance": 100, "notes": "Anormalidades da respiração"},
            {"code": "J44", "relevance": 90, "notes": "DPOC"},
            {"code": "I50", "relevance": 85, "notes": "Insuficiência cardíaca"},
            {"code": "J96", "relevance": 80, "notes": "Insuficiência respiratória"},
        ]
    },
    {
        "name": "dor no peito",
        "description": "Dor na região torácica",
        "category": "cardiovascular",
        "icd10_codes": [
            {"code": "R07", "relevance": 100, "notes": "Dor no peito"},
            {"code": "I20", "relevance": 90, "notes": "Angina pectoris"},
            {"code": "I21", "relevance": 85, "notes": "Infarto do miocárdio"},
            {"code": "J18", "relevance": 75, "notes": "Pneumonia"},
        ]
    },
    {
        "name": "tontura",
        "description": "Sensação de desequilíbrio ou vertigem",
        "category": "neurológico",
        "icd10_codes": [
            {"code": "R42", "relevance": 100, "notes": "Tontura e desmaio"},
            {"code": "I10", "relevance": 80, "notes": "Hipertensão"},
            {"code": "E11", "relevance": 75, "notes": "Diabetes"},
            {"code": "G93", "relevance": 70, "notes": "Transtornos do encéfalo"},
        ]
    },
    {
        "name": "fadiga",
        "description": "Cansaço ou falta de energia",
        "category": "geral",
        "icd10_codes": [
            {"code": "R53", "relevance": 100, "notes": "Mal-estar, fadiga"},
            {"code": "E11", "relevance": 80, "notes": "Diabetes"},
            {"code": "D64", "relevance": 75, "notes": "Anemias"},
            {"code": "F32", "relevance": 70, "notes": "Episódios depressivos"},
        ]
    },
    {
        "name": "hipertensão",
        "description": "Pressão arterial elevada",
        "category": "cardiovascular",
        "icd10_codes": [
            {"code": "I10", "relevance": 100, "notes": "Hipertensão essencial"},
            {"code": "I15", "relevance": 90, "notes": "Hipertensão secundária"},
            {"code": "I16", "relevance": 85, "notes": "Crise hipertensiva"},
        ]
    },
    {
        "name": "diabetes",
        "description": "Distúrbio do metabolismo da glicose",
        "category": "endócrino",
        "icd10_codes": [
            {"code": "E11", "relevance": 100, "notes": "Diabetes tipo 2"},
            {"code": "E10", "relevance": 90, "notes": "Diabetes tipo 1"},
            {"code": "E13", "relevance": 85, "notes": "Outros tipos de diabetes"},
        ]
    },
]


async def seed_symptoms():
    """Seed symptoms and mappings into database"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("🌱 Seeding symptoms database...")
            
            for symptom_data in SYMPTOMS_DATA:
                # Check if symptom already exists
                result = await session.execute(
                    select(Symptom).where(Symptom.name_normalized == symptom_data["name"].lower())
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"  ⏭️  Symptom '{symptom_data['name']}' already exists, skipping...")
                    symptom = existing
                else:
                    # Create symptom
                    symptom = Symptom(
                        name=symptom_data["name"],
                        name_normalized=symptom_data["name"].lower(),
                        description=symptom_data.get("description"),
                        category=symptom_data.get("category"),
                        is_active=True
                    )
                    session.add(symptom)
                    await session.flush()  # Get the ID
                    print(f"  ✅ Created symptom: {symptom_data['name']}")
                
                # Add ICD-10 mappings
                for mapping_data in symptom_data.get("icd10_codes", []):
                    # Check if mapping already exists
                    result = await session.execute(
                        select(SymptomICD10Mapping).where(
                            SymptomICD10Mapping.symptom_id == symptom.id,
                            SymptomICD10Mapping.icd10_code == mapping_data["code"]
                        )
                    )
                    existing_mapping = result.scalar_one_or_none()
                    
                    if not existing_mapping:
                        mapping = SymptomICD10Mapping(
                            symptom_id=symptom.id,
                            icd10_code=mapping_data["code"],
                            relevance_score=mapping_data.get("relevance", 100),
                            notes=mapping_data.get("notes")
                        )
                        session.add(mapping)
            
            await session.commit()
            print("✅ Symptoms database seeded successfully!")
            print(f"   Total symptoms: {len(SYMPTOMS_DATA)}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding symptoms: {str(e)}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_symptoms())

