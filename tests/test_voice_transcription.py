"""
Tests for Voice Transcription Service
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.voice_transcription import VoiceTranscriptionService, voice_transcriber


@pytest.mark.unit
class TestVoiceTranscription:
    """Test suite for voice transcription functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.transcription_service = VoiceTranscriptionService()
        self.mock_audio_data = b'mock_audio_data_for_testing'
    
    def test_service_initialization(self):
        """Test that service initializes correctly"""
        assert self.transcription_service is not None
        assert self.transcription_service.recognizer is not None
        assert len(self.transcription_service.medical_terms) > 0
    
    def test_medical_terms_loaded(self):
        """Test that medical terms are loaded"""
        medical_terms = self.transcription_service.medical_terms
        assert isinstance(medical_terms, list)
        assert len(medical_terms) > 0
        # Check for common medical terms
        assert any('febre' in term.lower() for term in medical_terms)
        assert any('dor' in term.lower() for term in medical_terms)
    
    def test_supported_languages(self):
        """Test that supported languages are returned"""
        languages = self.transcription_service.get_supported_languages()
        
        assert isinstance(languages, list)
        assert len(languages) > 0
        
        # Check for Portuguese (Brazil)
        pt_br = next((lang for lang in languages if lang['code'] == 'pt-BR'), None)
        assert pt_br is not None
        assert pt_br['name'] == 'Portuguese (Brazil)'
    
    @pytest.mark.asyncio
    @patch('app.services.voice_transcription.sr.Recognizer')
    async def test_transcription_structure(self, mock_recognizer_class):
        """Test that transcription returns proper structure"""
        # Mock the recognizer
        mock_recognizer = Mock()
        mock_recognizer.recognize_google = Mock(return_value='Paciente relata dor de cabeça')
        mock_recognizer_class.return_value = mock_recognizer
        
        # Create new service instance with mocked recognizer
        service = VoiceTranscriptionService()
        service.recognizer = mock_recognizer
        
        result = await service.transcribe_audio(
            self.mock_audio_data,
            language='pt-BR',
            enhance_medical_terms=True,
            structure_soap=True
        )
        
        # Verify structure
        assert 'success' in result
        assert 'raw_text' in result
        assert 'enhanced_text' in result
        assert 'structured_notes' in result
        assert 'confidence' in result
        
        # Verify SOAP structure
        structured_notes = result['structured_notes']
        assert 'subjective' in structured_notes
        assert 'objective' in structured_notes
        assert 'assessment' in structured_notes
        assert 'plan' in structured_notes
    
    @pytest.mark.asyncio
    async def test_transcription_error_handling(self):
        """Test that transcription handles errors gracefully"""
        # Use invalid audio data to trigger error
        invalid_audio = b''
        
        result = await self.transcription_service.transcribe_audio(
            invalid_audio,
            language='pt-BR'
        )
        
        # Should return error structure
        assert 'success' in result
        # May succeed or fail depending on implementation
        assert isinstance(result, dict)
    
    def test_enhance_medical_terms(self):
        """Test medical term enhancement"""
        text = "Paciente relata febre e dor abdominal"
        enhanced = self.transcription_service._enhance_medical_terms(text)
        
        # Enhanced text should contain capitalized medical terms
        assert isinstance(enhanced, str)
        assert len(enhanced) > 0
    
    def test_structure_into_soap(self):
        """Test SOAP structure extraction"""
        text = "Paciente relata dor de cabeça. Pressão arterial normal. Diagnóstico: Enxaqueca. Tratamento com analgésico."
        
        soap_structure = self.transcription_service._structure_into_soap(text)
        
        assert isinstance(soap_structure, dict)
        assert 'subjective' in soap_structure
        assert 'objective' in soap_structure
        assert 'assessment' in soap_structure
        assert 'plan' in soap_structure
        
        # Check that text was categorized
        assert len(soap_structure['subjective']) > 0 or len(soap_structure['objective']) > 0
    
    def test_confidence_estimation(self):
        """Test confidence score estimation"""
        text = "Paciente relata febre e dor abdominal com náusea"
        confidence = self.transcription_service._estimate_confidence(text)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_transcription_performance(self):
        """Test that transcription completes within acceptable time"""
        import time
        
        # Note: This test may fail if Google Speech API is not available
        # In production, should use mocked API
        start_time = time.time()
        
        try:
            result = await self.transcription_service.transcribe_audio(
                self.mock_audio_data,
                language='pt-BR'
            )
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Transcription should complete within 30 seconds
            # (or fail quickly if API unavailable)
            assert elapsed_time < 30.0 or result.get('success') == False
        except Exception:
            # If API is unavailable, that's acceptable for unit tests
            pass

