"""
Clinical AI Service
Provides AI-powered clinical decision support including:
- Symptom analysis and differential diagnosis
- ICD-10 code suggestions
- Drug interaction checking

Now uses real database for ICD-10 codes and symptoms
"""

import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.models.icd10 import ICD10Category, ICD10Subcategory, ICD10SearchIndex
from app.models.symptom import Symptom, SymptomICD10Mapping

logger = logging.getLogger(__name__)


class ClinicalAIService:
    """
    Clinical AI Service for diagnosis support and clinical decision assistance
    Now uses database for ICD-10 codes and symptoms
    """
    
    def __init__(self):
        # Keep fallback data for when database is not available
        self.fallback_icd10_codes = self._load_fallback_icd10_codes()
        self.fallback_drug_interactions = self._load_fallback_drug_interactions()
        self.fallback_symptom_database = self._load_fallback_symptom_database()
    
    def _load_fallback_icd10_codes(self) -> Dict:
        """Fallback ICD-10 codes if database is unavailable"""
        return {
            "I10": {"code": "I10", "description": "Hipertensão essencial (primária)"},
            "E11": {"code": "E11", "description": "Diabetes mellitus tipo 2"},
            "J06": {"code": "J06", "description": "Infeções agudas das vias respiratórias superiores"},
            "R51": {"code": "R51", "description": "Cefaleia"},
            "R10": {"code": "R10", "description": "Dor abdominal e pélvica"},
            "G43": {"code": "G43", "description": "Enxaqueca"},
            "G44": {"code": "G44", "description": "Outras síndromes de cefaleia"},
            "K35": {"code": "K35", "description": "Apendicite aguda"},
            "K57": {"code": "K57", "description": "Doença diverticular do intestino"},
            "R11": {"code": "R11", "description": "Náusea e vômito"},
            "A09": {"code": "A09", "description": "Gastroenterite e colite de origem infecciosa"},
            "A02": {"code": "A02", "description": "Outras infecções por salmonelas"},
            "K29": {"code": "K29", "description": "Gastrite e duodenite"},
        }
    
    def _load_fallback_drug_interactions(self) -> Dict:
        """Fallback drug interactions if database is unavailable"""
        return {
            "warfarin": ["aspirin", "ibuprofen", "omeprazole", "fluconazole"],
            "simvastatin": ["clarithromycin", "itraconazole", "cyclosporine", "gemfibrozil"],
            "lisinopril": ["ibuprofen", "naproxen", "diclofenac", "indomethacin"],
            "digoxin": ["amiodarone", "verapamil", "quinidine", "spironolactone"],
            "metformin": ["alcohol", "furosemide", "cimetidine"],
            "aspirin": ["warfarin", "heparin", "ibuprofen", "naproxen"],
            "ibuprofen": ["aspirin", "warfarin", "lisinopril", "furosemide"],
        }
    
    def _load_fallback_symptom_database(self) -> Dict:
        """Fallback symptom database if database is unavailable"""
        return {
            "febre": ["J06", "A09", "A02", "R50"],
            "cefaleia": ["R51", "G43", "G44", "I10"],
            "dor abdominal": ["R10", "K35", "K57", "A09"],
            "náusea": ["R11", "A09", "K29", "R10"],
            "vômito": ["R11", "A09", "K29", "K35"],
            "hipertensão": ["I10", "I15", "I16"],
            "diabetes": ["E11", "E10", "E13"],
            "tosse": ["J06", "J20", "J40", "J44"],
            "dispneia": ["J44", "I50", "J96", "R06"],
            "dor no peito": ["I20", "I21", "R07", "J18"],
            "tontura": ["R42", "I10", "E11", "G93"],
            "fadiga": ["R53", "E11", "D64", "F32"],
        }
    
    async def get_icd10_code_from_db(
        self, 
        db: AsyncSession, 
        code: str
    ) -> Optional[Dict]:
        """
        Get ICD-10 code from database
        Tries subcategory first, then category
        """
        try:
            # Try subcategory first (most specific)
            result = await db.execute(
                select(ICD10Subcategory)
                .where(ICD10Subcategory.code == code.upper())
            )
            subcategory = result.scalar_one_or_none()
            if subcategory:
                return {
                    "code": subcategory.code,
                    "description": subcategory.description,
                    "description_short": subcategory.description_short,
                    "level": "subcategory"
                }
            
            # Try category
            result = await db.execute(
                select(ICD10Category)
                .where(ICD10Category.code == code.upper())
            )
            category = result.scalar_one_or_none()
            if category:
                return {
                    "code": category.code,
                    "description": category.description,
                    "description_short": category.description_short,
                    "level": "category"
                }
            
            return None
        except Exception as e:
            logger.error(f"Error getting ICD-10 code from database: {str(e)}")
            return None
    
    async def get_symptoms_from_db(
        self, 
        db: AsyncSession
    ) -> Dict[str, List[str]]:
        """
        Get all symptoms and their ICD-10 mappings from database
        Returns: {symptom_name: [icd10_codes]}
        """
        try:
            result = await db.execute(
                select(Symptom, SymptomICD10Mapping)
                .join(SymptomICD10Mapping, Symptom.id == SymptomICD10Mapping.symptom_id)
                .where(Symptom.is_active == True)
                .order_by(SymptomICD10Mapping.relevance_score.desc())
            )
            
            symptom_map = {}
            for symptom, mapping in result.all():
                symptom_name = symptom.name_normalized
                if symptom_name not in symptom_map:
                    symptom_map[symptom_name] = []
                symptom_map[symptom_name].append(mapping.icd10_code)
            
            return symptom_map
        except Exception as e:
            logger.error(f"Error getting symptoms from database: {str(e)}")
            return {}
    
    async def search_icd10_codes_from_db(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search ICD-10 codes from database using search index
        """
        try:
            # Normalize query
            query_normalized = query.lower().strip()
            
            result = await db.execute(
                select(ICD10SearchIndex)
                .where(ICD10SearchIndex.search_text.ilike(f"%{query_normalized}%"))
                .limit(limit)
            )
            
            codes = []
            for item in result.scalars().all():
                codes.append({
                    "code": item.code,
                    "description": item.description,
                    "level": item.level,
                    "parent_code": item.parent_code
                })
            
            return codes
        except Exception as e:
            logger.error(f"Error searching ICD-10 codes from database: {str(e)}")
            return []
    
    async def analyze_symptoms(
        self, 
        db: AsyncSession,
        symptoms: List[str], 
        patient_data: Optional[Dict] = None,
        use_ai: bool = False,
        ai_service = None
    ) -> Dict:
        """
        Analyze symptoms and suggest differential diagnoses
        Now uses database for symptom and ICD-10 lookups
        
        Args:
            db: Database session
            symptoms: List of symptoms reported by patient
            patient_data: Optional patient data (age, gender, medical history, etc.)
            use_ai: Whether to use AI service for enhanced diagnosis
            ai_service: Optional AI service instance
        
        Returns:
            Dictionary with differential diagnoses and recommendations
        """
        try:
            differential_diagnoses = []
            
            # Get symptoms from database
            symptom_db = await self.get_symptoms_from_db(db)
            if not symptom_db:
                # Fallback to hardcoded data
                logger.warning("Using fallback symptom database")
                symptom_db = self.fallback_symptom_database
            
            # Analyze each symptom
            for symptom in symptoms:
                symptom_lower = symptom.lower().strip()
                possible_codes = symptom_db.get(symptom_lower, [])
                
                # If not found, try fuzzy matching
                if not possible_codes:
                    for db_symptom in symptom_db.keys():
                        if symptom_lower in db_symptom or db_symptom in symptom_lower:
                            possible_codes = symptom_db[db_symptom]
                            break
                
                for code in possible_codes:
                    # Get ICD-10 code from database
                    diagnosis = await self.get_icd10_code_from_db(db, code)
                    if not diagnosis:
                        # Fallback to hardcoded data
                        diagnosis = self.fallback_icd10_codes.get(code)
                        if diagnosis:
                            diagnosis = {**diagnosis, "level": "fallback"}
                    
                    if diagnosis:
                        # Check if diagnosis already added
                        existing = next(
                            (d for d in differential_diagnoses if d["icd10_code"] == diagnosis["code"]),
                            None
                        )
                        
                        if existing:
                            # Add symptom to supporting symptoms if not already present
                            if symptom not in existing["supporting_symptoms"]:
                                existing["supporting_symptoms"].append(symptom)
                                # Increase confidence with more symptoms
                                existing["confidence"] = min(0.95, existing["confidence"] + 0.1)
                        else:
                            # Calculate confidence based on symptom match
                            confidence = 0.7
                            if patient_data:
                                # Adjust confidence based on patient data
                                age = patient_data.get("age")
                                if age:
                                    # Some conditions are age-specific
                                    pass
                            
                            differential_diagnoses.append({
                                "icd10_code": diagnosis["code"],
                                "description": diagnosis.get("description", diagnosis.get("description_short", "")),
                                "confidence": confidence,
                                "supporting_symptoms": [symptom],
                                "recommended_tests": self._suggest_tests(diagnosis["code"]),
                                "level": diagnosis.get("level", "unknown")
                            })
            
            # If AI is enabled and available, enhance the diagnosis
            if use_ai and ai_service:
                try:
                    ai_suggestions, _ = await ai_service.suggest_diagnosis(
                        symptoms,
                        patient_data
                    )
                    # Merge AI suggestions with database results
                    # AI suggestions can add new diagnoses or adjust confidence
                    for ai_diag in ai_suggestions:
                        existing = next(
                            (d for d in differential_diagnoses if d.get("icd10_code") == ai_diag.get("diagnosis", {}).get("code")),
                            None
                        )
                        if existing:
                            # Boost confidence if AI also suggests it
                            existing["confidence"] = min(0.95, existing["confidence"] + 0.15)
                            existing["ai_enhanced"] = True
                except Exception as e:
                    logger.warning(f"AI enhancement failed, using database results only: {str(e)}")
            
            # Sort by confidence and number of supporting symptoms
            differential_diagnoses.sort(
                key=lambda x: (x["confidence"], len(x["supporting_symptoms"])),
                reverse=True
            )
            
            return {
                "success": True,
                "symptoms_analyzed": symptoms,
                "differential_diagnoses": differential_diagnoses,
                "primary_suspicion": differential_diagnoses[0] if differential_diagnoses else None,
                "patient_data_used": patient_data is not None,
                "ai_enhanced": use_ai and ai_service is not None
            }
            
        except Exception as e:
            logger.error(f"Symptom analysis error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "differential_diagnoses": [],
                "symptoms_analyzed": symptoms
            }
    
    async def suggest_icd10_codes(
        self,
        db: AsyncSession,
        clinical_findings: str
    ) -> List[Dict]:
        """
        Suggest ICD-10 codes based on clinical findings
        Now uses database search
        
        Args:
            db: Database session
            clinical_findings: Text describing clinical findings, symptoms, or assessment
        
        Returns:
            List of suggested ICD-10 codes with match scores
        """
        try:
            # Use database search index
            suggested_codes = await self.search_icd10_codes_from_db(db, clinical_findings, limit=20)
            
            # Calculate match scores based on text similarity
            findings_lower = clinical_findings.lower()
            findings_words = set(findings_lower.split())
            
            scored_codes = []
            for code_info in suggested_codes:
                description_lower = code_info["description"].lower()
                description_words = set(description_lower.split())
                
                # Calculate match score
                common_words = findings_words.intersection(description_words)
                match_score = len(common_words) / max(len(description_words), 1)
                
                # Boost score if symptom database matches
                symptom_db = await self.get_symptoms_from_db(db)
                for symptom, codes in symptom_db.items():
                    if symptom in findings_lower and code_info["code"] in codes:
                        match_score += 0.2
                
                if match_score > 0.1:  # Threshold for relevance
                    scored_codes.append({
                        "code": code_info["code"],
                        "description": code_info["description"],
                        "match_score": min(match_score, 1.0),
                        "category": self._get_code_category(code_info["code"]),
                        "level": code_info.get("level", "unknown")
                    })
            
            # Sort by match score and return top 10
            scored_codes.sort(key=lambda x: x["match_score"], reverse=True)
            return scored_codes[:10]
            
        except Exception as e:
            logger.error(f"ICD-10 suggestion error: {str(e)}", exc_info=True)
            return []
    
    async def check_drug_interactions(self, medications: List[str]) -> List[Dict]:
        """
        Check for potential drug interactions
        TODO: Integrate with real drug interaction database
        
        Args:
            medications: List of medication names
        
        Returns:
            List of potential drug interactions with severity and recommendations
        """
        try:
            interactions = []
            medications_lower = [med.lower().strip() for med in medications]
            
            # Use fallback database for now
            drug_interactions = self.fallback_drug_interactions
            
            for i, med1 in enumerate(medications_lower):
                for j, med2 in enumerate(medications_lower):
                    if i < j:  # Avoid duplicate pairs
                        # Check both directions
                        interaction_found = False
                        severity = "moderate"
                        description = ""
                        
                        if med1 in drug_interactions:
                            if med2 in drug_interactions[med1]:
                                interaction_found = True
                                severity = self._get_interaction_severity(med1, med2)
                                description = (
                                    f"Interação potencial entre {medications[i]} e {medications[j]}. "
                                    f"Pode resultar em aumento ou diminuição da eficácia, "
                                    f"ou aumento do risco de efeitos adversos."
                                )
                        
                        if med2 in drug_interactions:
                            if med1 in drug_interactions[med2]:
                                interaction_found = True
                                severity = self._get_interaction_severity(med2, med1)
                                description = (
                                    f"Interação potencial entre {medications[j]} e {medications[i]}. "
                                    f"Pode resultar em aumento ou diminuição da eficácia, "
                                    f"ou aumento do risco de efeitos adversos."
                                )
                        
                        if interaction_found:
                            interactions.append({
                                "drug1": medications[i],
                                "drug2": medications[j],
                                "severity": severity,
                                "description": description,
                                "recommendation": self._get_interaction_recommendation(severity)
                            })
            
            return interactions
            
        except Exception as e:
            logger.error(f"Drug interaction check error: {str(e)}")
            return []
    
    def _suggest_tests(self, icd10_code: str) -> List[str]:
        """
        Suggest diagnostic tests based on ICD-10 code
        TODO: Move to database table
        """
        test_suggestions = {
            "I10": ["Pressão arterial", "Eletrocardiograma", "Hemograma completo", "Perfil lipídico"],
            "E11": ["Glicemia em jejum", "Hemoglobina glicada", "Perfil lipídico", "Creatinina"],
            "J06": ["Hemograma", "Raio-X de tórax", "Teste rápido para influenza", "Teste para COVID-19"],
            "R51": ["Pressão arterial", "Exame neurológico", "Ressonância magnética (se necessário)", "Tomografia computadorizada (se necessário)"],
            "R10": ["Hemograma", "Ultrassonografia abdominal", "Exame de urina", "Radiografia abdominal"],
            "G43": ["Exame neurológico", "Ressonância magnética (se necessário)", "Análise de líquido cefalorraquidiano (se necessário)"],
            "K35": ["Hemograma", "Ultrassonografia abdominal", "Tomografia computadorizada", "Exame físico completo"],
            "R11": ["Hemograma", "Exame de urina", "Testes de função hepática", "Eletrólitos"],
        }
        return test_suggestions.get(icd10_code, ["Avaliação clínica completa", "Exames complementares conforme necessário"])
    
    def _get_code_category(self, code: str) -> str:
        """
        Get category from ICD-10 code
        """
        if not code:
            return "Outras condições"
            
        first_char = code[0]
        categories = {
            "A": "Doenças infecciosas e parasitárias",
            "B": "Doenças infecciosas e parasitárias",
            "C": "Neoplasias (tumores)",
            "D": "Doenças do sangue e órgãos hematopoéticos",
            "E": "Doenças endócrinas, nutricionais e metabólicas",
            "F": "Transtornos mentais e comportamentais",
            "G": "Doenças do sistema nervoso",
            "H": "Doenças do olho e anexos",
            "I": "Doenças do aparelho circulatório",
            "J": "Doenças do aparelho respiratório",
            "K": "Doenças do aparelho digestivo",
            "L": "Doenças da pele e tecido subcutâneo",
            "M": "Doenças do sistema osteomuscular",
            "N": "Doenças do aparelho geniturinário",
            "O": "Gravidez, parto e puerpério",
            "P": "Algumas afecções originadas no período perinatal",
            "Q": "Malformações congênitas",
            "R": "Sintomas, sinais e achados anormais",
            "S": "Traumatismos, envenenamentos e algumas outras consequências de causas externas",
            "T": "Traumatismos, envenenamentos e algumas outras consequências de causas externas",
            "U": "Códigos para situações especiais",
            "V": "Causas externas de morbidade",
            "W": "Causas externas de morbidade",
            "X": "Causas externas de morbidade",
            "Y": "Causas externas de morbidade",
            "Z": "Fatores que influenciam o estado de saúde"
        }
        return categories.get(first_char, "Outras condições")
    
    def _get_interaction_severity(self, drug1: str, drug2: str) -> str:
        """
        Determine interaction severity
        """
        high_risk = [
            ("warfarin", "aspirin"),
            ("warfarin", "ibuprofen"),
            ("digoxin", "amiodarone"),
        ]
        
        pair = tuple(sorted([drug1.lower(), drug2.lower()]))
        if pair in high_risk:
            return "severe"
        
        return "moderate"
    
    def _get_interaction_recommendation(self, severity: str) -> str:
        """
        Get recommendation based on interaction severity
        """
        recommendations = {
            "mild": "Monitorar paciente. Interação de baixo risco.",
            "moderate": "Monitorar paciente cuidadosamente. Considere ajuste de dose ou monitoramento adicional.",
            "severe": "ATENÇÃO: Interação de alto risco. Revisar prescrição. Considerar alternativas ou monitoramento intensivo."
        }
        return recommendations.get(severity, "Monitorar paciente e revisar prescrição.")


# Singleton instance (but now requires db session for most operations)
clinical_ai = ClinicalAIService()
