"""
AWS AI Integration Tests
Tests for AWS Transcribe Medical, Comprehend Medical, and Bedrock integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


def test_voice_processing_service_import():
    """Test that VoiceProcessingService can be imported"""
    from app.services.voice_processing import VoiceProcessingService, VoiceProvider
    
    assert VoiceProcessingService is not None
    assert VoiceProvider is not None
    
    service = VoiceProcessingService()
    assert service is not None


def test_comprehend_medical_service_import():
    """Test that ComprehendMedicalService can be imported"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    assert ComprehendMedicalService is not None
    
    service = ComprehendMedicalService()
    assert service is not None


def test_comprehend_medical_service_initialization():
    """Test ComprehendMedicalService initialization"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    # Service should initialize even without AWS credentials
    assert hasattr(service, 'enabled')
    assert hasattr(service, 'client')
    assert hasattr(service, 'bedrock_client')
    assert hasattr(service, 'is_enabled')


@pytest.mark.asyncio
async def test_comprehend_medical_detect_entities_no_credentials():
    """Test detect_entities when AWS credentials are not configured"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    # Should return error when not enabled
    result = await service.detect_entities("Test text", "pt-BR")
    
    assert result["success"] is False
    assert "error" in result
    assert "entities" in result


@pytest.mark.asyncio
async def test_comprehend_medical_extract_conditions_no_credentials():
    """Test extract_conditions when AWS credentials are not configured"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    result = await service.extract_conditions("Patient has fever and headache", "pt-BR")
    
    # Should return error when not enabled
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_infer_icd10_codes_no_credentials():
    """Test infer_icd10_codes when AWS credentials are not configured"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    result = await service.infer_icd10_codes("Patient has hypertension", "pt-BR")
    
    # Should return error when not enabled
    assert result["success"] is False
    assert "icd10_suggestions" in result


@pytest.mark.asyncio
async def test_aws_transcribe_fallback():
    """Test that AWS Transcribe falls back to Google Speech when credentials are missing"""
    from app.services.voice_processing import VoiceProcessingService, VoiceProvider
    
    service = VoiceProcessingService()
    service.voice_provider = VoiceProvider.AWS
    
    # Mock Google Speech as fallback
    with patch.object(service, '_google_speech_to_text', new_callable=AsyncMock) as mock_google:
        mock_google.return_value = "Transcribed text"
        
        # Should fall back to Google when AWS credentials are missing
        result = await service._aws_transcribe(b"fake audio data")
        
        # Should have called Google as fallback
        assert result == "Transcribed text"


def test_voice_processing_medical_terms():
    """Test that medical terms are loaded"""
    from app.services.voice_processing import VoiceProcessingService
    
    service = VoiceProcessingService()
    
    assert hasattr(service, 'medical_terms')
    assert isinstance(service.medical_terms, dict)
    assert len(service.medical_terms) > 0


@pytest.mark.asyncio
async def test_voice_processing_analyze_medical_terms():
    """Test medical term analysis without database"""
    from app.services.voice_processing import VoiceProcessingService
    
    service = VoiceProcessingService()
    
    text = "Patient has abdominal pain and fever"
    result = await service._analyze_medical_terms(text, None, None)
    
    # Should find medical terms from hardcoded dictionary
    assert isinstance(result, list)
    # Should find at least "dor abdominal" and "febre" if text matches


@pytest.mark.asyncio
async def test_basic_structure_soap():
    """Test basic SOAP structure generation"""
    from app.services.voice_processing import VoiceProcessingService
    
    service = VoiceProcessingService()
    
    transcription = "Patient complains of headache. Blood pressure 120/80. Diagnosis: Migraine."
    clinical_analysis = {
        "conditions": [
            {"text": "headache", "traits": ["SYMPTOM"], "confidence": 0.9}
        ],
        "medications": []
    }
    
    result = service._basic_structure_soap(transcription, clinical_analysis)
    
    assert "soap_notes" in result
    assert "subjective" in result["soap_notes"]
    assert "objective" in result["soap_notes"]
    assert "assessment" in result["soap_notes"]
    assert "plan" in result["soap_notes"]
    assert "vital_signs" in result


def test_voice_provider_enum():
    """Test VoiceProvider enum values"""
    from app.services.voice_processing import VoiceProvider
    
    assert VoiceProvider.GOOGLE.value == "google"
    assert VoiceProvider.AWS.value == "aws"
    assert VoiceProvider.AZURE.value == "azure"


@pytest.mark.asyncio
async def test_comprehend_medical_empty_text():
    """Test Comprehend Medical with empty text"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    result = await service.detect_entities("", "pt-BR")
    
    assert result["success"] is False
    assert "error" in result
    assert "Empty text" in result["error"] or "not enabled" in result["error"]


def test_comprehend_medical_service_methods():
    """Test that all Comprehend Medical service methods exist"""
    from app.services.comprehend_medical_service import ComprehendMedicalService
    
    service = ComprehendMedicalService()
    
    # Check all main methods exist
    assert hasattr(service, 'detect_entities')
    assert hasattr(service, 'detect_phi')
    assert hasattr(service, 'extract_medications')
    assert hasattr(service, 'extract_conditions')
    assert hasattr(service, 'extract_procedures')
    assert hasattr(service, 'analyze_clinical_note')
    assert hasattr(service, 'infer_icd10_codes')
    assert hasattr(service, '_bedrock_suggest_icd10')


def test_voice_processing_service_methods():
    """Test that all Voice Processing service methods exist"""
    from app.services.voice_processing import VoiceProcessingService
    
    service = VoiceProcessingService()
    
    # Check main methods exist
    assert hasattr(service, 'process_audio_stream')
    assert hasattr(service, '_aws_transcribe')
    assert hasattr(service, '_google_speech_to_text')
    assert hasattr(service, '_analyze_medical_terms')
    assert hasattr(service, '_process_aws_consultation_pipeline')
    assert hasattr(service, '_bedrock_structure_consultation')
    assert hasattr(service, '_basic_structure_soap')


# Note: Integration tests with real AWS services would require:
# - AWS credentials configured
# - Mock AWS services (moto library)
# - Database fixtures
# - Audio file fixtures
# - More comprehensive test coverage
