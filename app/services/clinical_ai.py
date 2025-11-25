"""
Clinical AI Service
Provides AI-powered clinical decision support including:
- Symptom analysis and differential diagnosis
- ICD-10 code suggestions
- Drug interaction checking
"""

import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ClinicalAIService:
    """
    Clinical AI Service for diagnosis support and clinical decision assistance
    """
    
    def __init__(self):
        self.icd10_codes = self._load_icd10_codes()
        self.drug_interactions = self._load_drug_interactions()
        self.symptom_database = self._load_symptom_database()
    
    def _load_icd10_codes(self) -> Dict:
        """
        Load ICD-10 codes from local database or file
        In production, this should come from a database
        """
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
            # Add more codes as needed
        }
    
    def _load_drug_interactions(self) -> Dict:
        """
        Load drug interaction database
        In production, this should come from a comprehensive drug database
        """
        return {
            "warfarin": ["aspirin", "ibuprofen", "omeprazole", "fluconazole"],
            "simvastatin": ["clarithromycin", "itraconazole", "cyclosporine", "gemfibrozil"],
            "lisinopril": ["ibuprofen", "naproxen", "diclofenac", "indomethacin"],
            "digoxin": ["amiodarone", "verapamil", "quinidine", "spironolactone"],
            "metformin": ["alcohol", "furosemide", "cimetidine"],
            "aspirin": ["warfarin", "heparin", "ibuprofen", "naproxen"],
            "ibuprofen": ["aspirin", "warfarin", "lisinopril", "furosemide"],
            # Add more interactions
        }
    
    def _load_symptom_database(self) -> Dict:
        """
        Load symptom to condition mapping
        Maps symptoms to possible ICD-10 codes
        """
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
    
    async def analyze_symptoms(
        self, 
        symptoms: List[str], 
        patient_data: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze symptoms and suggest differential diagnoses
        
        Args:
            symptoms: List of symptoms reported by patient
            patient_data: Optional patient data (age, gender, medical history, etc.)
        
        Returns:
            Dictionary with differential diagnoses and recommendations
        """
        try:
            differential_diagnoses = []
            
            # Simple rule-based diagnosis (can be enhanced with ML)
            for symptom in symptoms:
                symptom_lower = symptom.lower().strip()
                possible_codes = self.symptom_database.get(symptom_lower, [])
                
                for code in possible_codes:
                    diagnosis = self.icd10_codes.get(code)
                    if diagnosis:
                        # Check if diagnosis already added
                        existing = next(
                            (d for d in differential_diagnoses if d["icd10_code"] == code),
                            None
                        )
                        
                        if existing:
                            # Add symptom to supporting symptoms if not already present
                            if symptom not in existing["supporting_symptoms"]:
                                existing["supporting_symptoms"].append(symptom)
                        else:
                            # Calculate confidence based on symptom match
                            confidence = 0.7
                            if patient_data:
                                # Adjust confidence based on patient data
                                # Example: age, gender, medical history
                                pass
                            
                            differential_diagnoses.append({
                                "icd10_code": diagnosis["code"],
                                "description": diagnosis["description"],
                                "confidence": confidence,
                                "supporting_symptoms": [symptom],
                                "recommended_tests": self._suggest_tests(diagnosis["code"])
                            })
            
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
                "patient_data_used": patient_data is not None
            }
            
        except Exception as e:
            logger.error(f"Symptom analysis error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "differential_diagnoses": [],
                "symptoms_analyzed": symptoms
            }
    
    async def suggest_icd10_codes(self, clinical_findings: str) -> List[Dict]:
        """
        Suggest ICD-10 codes based on clinical findings
        
        Args:
            clinical_findings: Text describing clinical findings, symptoms, or assessment
        
        Returns:
            List of suggested ICD-10 codes with match scores
        """
        try:
            suggested_codes = []
            findings_lower = clinical_findings.lower()
            
            # Extract keywords from findings
            findings_words = set(findings_lower.split())
            
            for code, info in self.icd10_codes.items():
                description_lower = info["description"].lower()
                description_words = set(description_lower.split())
                
                # Calculate match score based on word overlap
                common_words = findings_words.intersection(description_words)
                if common_words:
                    match_score = len(common_words) / max(len(description_words), 1)
                    
                    # Also check symptom database
                    for symptom, codes in self.symptom_database.items():
                        if symptom in findings_lower and code in codes:
                            match_score += 0.2
                    
                    if match_score > 0.1:  # Threshold for relevance
                        suggested_codes.append({
                            "code": code,
                            "description": info["description"],
                            "match_score": min(match_score, 1.0),
                            "category": self._get_code_category(code)
                        })
            
            # Sort by match score and return top 10
            suggested_codes.sort(key=lambda x: x["match_score"], reverse=True)
            return suggested_codes[:10]
            
        except Exception as e:
            logger.error(f"ICD-10 suggestion error: {str(e)}")
            return []
    
    async def check_drug_interactions(self, medications: List[str]) -> List[Dict]:
        """
        Check for potential drug interactions
        
        Args:
            medications: List of medication names
        
        Returns:
            List of potential drug interactions with severity and recommendations
        """
        try:
            interactions = []
            medications_lower = [med.lower().strip() for med in medications]
            
            for i, med1 in enumerate(medications_lower):
                for j, med2 in enumerate(medications_lower):
                    if i < j:  # Avoid duplicate pairs
                        # Check both directions
                        interaction_found = False
                        severity = "moderate"
                        description = ""
                        
                        if med1 in self.drug_interactions:
                            if med2 in self.drug_interactions[med1]:
                                interaction_found = True
                                severity = self._get_interaction_severity(med1, med2)
                                description = (
                                    f"Interação potencial entre {medications[i]} e {medications[j]}. "
                                    f"Pode resultar em aumento ou diminuição da eficácia, "
                                    f"ou aumento do risco de efeitos adversos."
                                )
                        
                        if med2 in self.drug_interactions:
                            if med1 in self.drug_interactions[med2]:
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
        
        Args:
            icd10_code: ICD-10 code
        
        Returns:
            List of recommended diagnostic tests
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
        
        Args:
            code: ICD-10 code
        
        Returns:
            Category description
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
        
        Args:
            drug1: First drug name
            drug2: Second drug name
        
        Returns:
            Severity level (mild, moderate, severe)
        """
        # High-risk combinations
        high_risk = [
            ("warfarin", "aspirin"),
            ("warfarin", "ibuprofen"),
            ("digoxin", "amiodarone"),
        ]
        
        pair = tuple(sorted([drug1.lower(), drug2.lower()]))
        if pair in high_risk:
            return "severe"
        
        # Moderate risk for most known interactions
        return "moderate"
    
    def _get_interaction_recommendation(self, severity: str) -> str:
        """
        Get recommendation based on interaction severity
        
        Args:
            severity: Interaction severity level
        
        Returns:
            Recommendation text
        """
        recommendations = {
            "mild": "Monitorar paciente. Interação de baixo risco.",
            "moderate": "Monitorar paciente cuidadosamente. Considere ajuste de dose ou monitoramento adicional.",
            "severe": "ATENÇÃO: Interação de alto risco. Revisar prescrição. Considerar alternativas ou monitoramento intensivo."
        }
        return recommendations.get(severity, "Monitorar paciente e revisar prescrição.")


# Singleton instance
clinical_ai = ClinicalAIService()

