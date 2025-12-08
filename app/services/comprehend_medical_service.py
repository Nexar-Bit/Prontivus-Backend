"""
AWS Comprehend Medical Service
Extracts medical entities, relationships, and insights from clinical text
Supports Portuguese (pt-BR) and English (en-US)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# AWS Comprehend Medical imports
try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    COMPREHEND_MEDICAL_AVAILABLE = True
except ImportError:
    COMPREHEND_MEDICAL_AVAILABLE = False
    logging.warning("boto3 not installed. AWS Comprehend Medical will be disabled.")

logger = logging.getLogger(__name__)


class ComprehendMedicalService:
    """
    AWS Comprehend Medical Service
    Extracts structured medical information from unstructured clinical text
    """
    
    def __init__(self):
        """Initialize AWS Comprehend Medical client"""
        self.enabled = False
        self.client = None
        
        if not COMPREHEND_MEDICAL_AVAILABLE:
            logger.warning("AWS Comprehend Medical not available. Install boto3: pip install boto3")
            return
        
        # Get AWS credentials from environment
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        if aws_access_key and aws_secret_key:
            try:
                self.client = boto3.client(
                    'comprehendmedical',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=aws_region
                )
                self.enabled = True
                logger.info(f"AWS Comprehend Medical initialized for region: {aws_region}")
            except Exception as e:
                logger.error(f"Failed to initialize AWS Comprehend Medical: {str(e)}")
                self.enabled = False
        else:
            logger.warning("AWS credentials not configured. Comprehend Medical disabled.")
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return self.enabled and self.client is not None
    
    async def detect_entities(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Detect medical entities in text
        
        Entity types:
        - MEDICATION: Medications, dosages, routes
        - MEDICAL_CONDITION: Diagnoses, symptoms, conditions
        - TEST_TREATMENT_PROCEDURE: Tests, treatments, procedures
        - ANATOMY: Body parts, organs
        - PROTECTED_HEALTH_INFORMATION: PHI (names, dates, etc.)
        - TIME_EXPRESSION: Temporal expressions
        
        Args:
            text: Clinical text to analyze
            language: Language code (pt-BR or en-US)
        
        Returns:
            Dictionary with detected entities and metadata
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "AWS Comprehend Medical not enabled",
                "entities": []
            }
        
        if not text or len(text.strip()) == 0:
            return {
                "success": False,
                "error": "Empty text provided",
                "entities": []
            }
        
        try:
            # AWS Comprehend Medical uses different language codes
            # pt-BR -> pt, en-US -> en
            aws_language = "pt" if language.startswith("pt") else "en"
            
            # Call AWS Comprehend Medical API
            response = self.client.detect_entities_v2(
                Text=text,
                LanguageCode=aws_language
            )
            
            # Process entities
            entities = []
            for entity in response.get('Entities', []):
                entities.append({
                    "id": entity.get('Id'),
                    "text": entity.get('Text'),
                    "category": entity.get('Category'),
                    "type": entity.get('Type'),
                    "score": entity.get('Score', 0.0),
                    "begin_offset": entity.get('BeginOffset'),
                    "end_offset": entity.get('EndOffset'),
                    "traits": entity.get('Traits', []),
                    "attributes": entity.get('Attributes', [])
                })
            
            return {
                "success": True,
                "entities": entities,
                "model_version": response.get('ModelVersion'),
                "pagination_token": response.get('PaginationToken'),
                "unmapped_attributes": response.get('UnmappedAttributes', [])
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"AWS Comprehend Medical error ({error_code}): {error_message}")
            return {
                "success": False,
                "error": f"AWS error: {error_message}",
                "error_code": error_code,
                "entities": []
            }
        except Exception as e:
            logger.error(f"Error detecting entities: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "entities": []
            }
    
    async def detect_phi(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Detect Protected Health Information (PHI) in text
        
        PHI types:
        - NAME: Patient names, doctor names
        - DATE: Dates of birth, visit dates
        - AGE: Patient age
        - PHONE_OR_FAX: Phone numbers
        - EMAIL: Email addresses
        - ID: Medical record numbers, IDs
        - URL: URLs
        - ADDRESS: Physical addresses
        - PROFESSION: Professional titles
        
        Args:
            text: Clinical text to analyze
            language: Language code (pt-BR or en-US)
        
        Returns:
            Dictionary with detected PHI entities
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "AWS Comprehend Medical not enabled",
                "phi_entities": []
            }
        
        try:
            # Use detect_entities which includes PHI
            result = await self.detect_entities(text, language)
            
            if not result["success"]:
                return result
            
            # Filter for PHI entities
            phi_entities = [
                entity for entity in result["entities"]
                if entity.get("category") == "PROTECTED_HEALTH_INFORMATION"
            ]
            
            return {
                "success": True,
                "phi_entities": phi_entities,
                "count": len(phi_entities)
            }
            
        except Exception as e:
            logger.error(f"Error detecting PHI: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "phi_entities": []
            }
    
    async def extract_medications(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Extract medication information from clinical text
        
        Returns:
            Dictionary with medications, dosages, frequencies, routes
        """
        result = await self.detect_entities(text, language)
        
        if not result["success"]:
            return result
        
        medications = []
        for entity in result["entities"]:
            if entity.get("category") == "MEDICATION":
                medication = {
                    "name": entity.get("text"),
                    "confidence": entity.get("score", 0.0),
                    "attributes": {}
                }
                
                # Extract medication attributes
                for attr in entity.get("attributes", []):
                    attr_type = attr.get("Type")
                    attr_text = attr.get("Text")
                    medication["attributes"][attr_type.lower()] = attr_text
                
                # Extract traits (e.g., NEGATION, SIGN, SYMPTOM)
                traits = [trait.get("Name") for trait in entity.get("traits", [])]
                medication["traits"] = traits
                
                medications.append(medication)
        
        return {
            "success": True,
            "medications": medications,
            "count": len(medications)
        }
    
    async def extract_conditions(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Extract medical conditions/diagnoses from clinical text
        
        Returns:
            Dictionary with conditions, diagnoses, symptoms
        """
        result = await self.detect_entities(text, language)
        
        if not result["success"]:
            return result
        
        conditions = []
        for entity in result["entities"]:
            if entity.get("category") == "MEDICAL_CONDITION":
                condition = {
                    "text": entity.get("text"),
                    "type": entity.get("type"),
                    "confidence": entity.get("score", 0.0),
                    "attributes": {}
                }
                
                # Extract condition attributes
                for attr in entity.get("attributes", []):
                    attr_type = attr.get("Type")
                    attr_text = attr.get("Text")
                    condition["attributes"][attr_type.lower()] = attr_text
                
                # Extract traits (e.g., NEGATION, DIAGNOSIS, SYMPTOM)
                traits = [trait.get("Name") for trait in entity.get("traits", [])]
                condition["traits"] = traits
                
                conditions.append(condition)
        
        return {
            "success": True,
            "conditions": conditions,
            "count": len(conditions)
        }
    
    async def extract_procedures(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Extract tests, treatments, and procedures from clinical text
        
        Returns:
            Dictionary with procedures, tests, treatments
        """
        result = await self.detect_entities(text, language)
        
        if not result["success"]:
            return result
        
        procedures = []
        for entity in result["entities"]:
            if entity.get("category") == "TEST_TREATMENT_PROCEDURE":
                procedure = {
                    "text": entity.get("text"),
                    "type": entity.get("type"),
                    "confidence": entity.get("score", 0.0),
                    "attributes": {}
                }
                
                # Extract procedure attributes
                for attr in entity.get("attributes", []):
                    attr_type = attr.get("Type")
                    attr_text = attr.get("Text")
                    procedure["attributes"][attr_type.lower()] = attr_text
                
                procedures.append(procedure)
        
        return {
            "success": True,
            "procedures": procedures,
            "count": len(procedures)
        }
    
    async def analyze_clinical_note(
        self,
        text: str,
        language: str = "pt-BR",
        include_phi: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of clinical note
        
        Extracts:
        - Medications
        - Medical conditions
        - Procedures/tests
        - Anatomy references
        - PHI (optional)
        - Time expressions
        
        Args:
            text: Clinical note text
            language: Language code
            include_phi: Whether to include PHI detection
        
        Returns:
            Comprehensive analysis dictionary
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "AWS Comprehend Medical not enabled"
            }
        
        try:
            # Detect all entities
            entities_result = await self.detect_entities(text, language)
            
            if not entities_result["success"]:
                return entities_result
            
            # Organize entities by category
            analysis = {
                "success": True,
                "medications": [],
                "conditions": [],
                "procedures": [],
                "anatomy": [],
                "phi": [],
                "time_expressions": [],
                "summary": {
                    "total_entities": len(entities_result["entities"]),
                    "medication_count": 0,
                    "condition_count": 0,
                    "procedure_count": 0
                }
            }
            
            for entity in entities_result["entities"]:
                category = entity.get("category")
                entity_data = {
                    "text": entity.get("text"),
                    "confidence": entity.get("score", 0.0),
                    "type": entity.get("type"),
                    "attributes": entity.get("attributes", []),
                    "traits": entity.get("traits", [])
                }
                
                if category == "MEDICATION":
                    analysis["medications"].append(entity_data)
                    analysis["summary"]["medication_count"] += 1
                elif category == "MEDICAL_CONDITION":
                    analysis["conditions"].append(entity_data)
                    analysis["summary"]["condition_count"] += 1
                elif category == "TEST_TREATMENT_PROCEDURE":
                    analysis["procedures"].append(entity_data)
                    analysis["summary"]["procedure_count"] += 1
                elif category == "ANATOMY":
                    analysis["anatomy"].append(entity_data)
                elif category == "PROTECTED_HEALTH_INFORMATION" and include_phi:
                    analysis["phi"].append(entity_data)
                elif category == "TIME_EXPRESSION":
                    analysis["time_expressions"].append(entity_data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing clinical note: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def infer_icd10_codes(
        self,
        text: str,
        language: str = "pt-BR"
    ) -> Dict[str, Any]:
        """
        Infer ICD-10 codes from clinical text
        
        Note: AWS Comprehend Medical doesn't directly provide ICD-10 codes,
        but we can use extracted conditions to suggest ICD-10 codes
        
        Args:
            text: Clinical text
            language: Language code
        
        Returns:
            Dictionary with suggested ICD-10 codes based on conditions
        """
        conditions_result = await self.extract_conditions(text, language)
        
        if not conditions_result["success"]:
            return conditions_result
        
        # Map conditions to ICD-10 codes (simplified - in production, use database)
        icd10_suggestions = []
        for condition in conditions_result["conditions"]:
            condition_text = condition.get("text", "").lower()
            
            # Simple mapping (should be replaced with database lookup)
            icd10_mapping = {
                "hipertensão": "I10",
                "diabetes": "E11",
                "febre": "R50",
                "cefaleia": "R51",
                "dor abdominal": "R10",
                "tosse": "R05",
                "dispneia": "R06",
            }
            
            for key, code in icd10_mapping.items():
                if key in condition_text:
                    icd10_suggestions.append({
                        "icd10_code": code,
                        "condition": condition.get("text"),
                        "confidence": condition.get("confidence", 0.0)
                    })
                    break
        
        return {
            "success": True,
            "icd10_suggestions": icd10_suggestions,
            "count": len(icd10_suggestions)
        }


# Global instance
comprehend_medical_service = ComprehendMedicalService()

