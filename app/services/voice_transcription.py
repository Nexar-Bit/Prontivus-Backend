"""
Voice Transcription Service
Simplified transcription service using SpeechRecognition library
Provides direct audio-to-text conversion with medical term enhancement
"""

import io
import tempfile
import os
import re
from typing import Dict, List, Optional
import logging
import asyncio

# Handle Python 3.13 compatibility - aifc module was removed
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError as e:
    # If speech_recognition fails to import (e.g., due to missing aifc in Python 3.13)
    # Create a mock recognizer that will fail gracefully
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning(f"SpeechRecognition not available: {e}. Will try OpenAI Whisper as fallback.")

# Try OpenAI as fallback for Python 3.13+
try:
    from openai import AsyncOpenAI
    import os
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Voice transcription may be limited.")

logger = logging.getLogger(__name__)


class VoiceTranscriptionService:
    """
    Voice Transcription Service for direct audio-to-text conversion
    Uses SpeechRecognition library with Google Speech-to-Text API
    """
    
    def __init__(self):
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = None
            logger.warning("SpeechRecognition not available. Will use OpenAI Whisper as fallback.")
        else:
            self.recognizer = sr.Recognizer()
            # Adjust for ambient noise
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True
        
        # Initialize OpenAI client if available and SpeechRecognition is not
        self.openai_client = None
        if not SPEECH_RECOGNITION_AVAILABLE and OPENAI_AVAILABLE:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=openai_api_key)
                logger.info("Using OpenAI Whisper for transcription (Python 3.13 compatible)")
            else:
                logger.warning("OPENAI_API_KEY not found. Voice transcription will be disabled.")
        
        self.medical_terms = self._load_medical_terms()
    
    def _load_medical_terms(self) -> List[str]:
        """
        Load Portuguese medical terminology for enhancement
        In production, this should be loaded from database
        """
        return [
            "dor abdominal", "cefaleia", "náusea", "vômito", "febre",
            "hipertensão", "diabetes", "cardíaco", "respiratório",
            "medicação", "dosagem", "sintomas", "diagnóstico",
            "tratamento", "exame físico", "prescrição", "paciente",
            "consulta", "queixa principal", "história clínica",
            "pressão arterial", "temperatura", "frequência cardíaca",
            "respiração", "saturação", "glicemia", "colesterol",
            "analgésico", "anti-inflamatório", "antibiótico",
            "alergia", "reação", "efeito colateral", "contraindicação"
        ]
    
    async def transcribe_audio(
        self, 
        audio_file: bytes, 
        language: str = 'pt-BR',
        enhance_medical_terms: bool = True,
        structure_soap: bool = False
    ) -> Dict:
        """
        Transcribe audio file to text with optional medical term enhancement
        
        Args:
            audio_file: Audio file bytes
            language: Language code (default: pt-BR)
            enhance_medical_terms: Whether to enhance medical terminology
            structure_soap: Whether to structure into SOAP format
        
        Returns:
            Dictionary with transcription results
        """
        # Check if any transcription method is available
        if not SPEECH_RECOGNITION_AVAILABLE and not (self.openai_client and OPENAI_AVAILABLE):
            return {
                'success': False,
                'error': 'Voice transcription is not available. SpeechRecognition library is not compatible with Python 3.13. Please configure OPENAI_API_KEY to use OpenAI Whisper as alternative.',
                'raw_text': '',
                'enhanced_text': '',
                'structured_notes': {}
            }
        
        try:
            # Perform transcription using available method
            if SPEECH_RECOGNITION_AVAILABLE and self.recognizer:
                # Use SpeechRecognition (Python < 3.13)
                audio_data = await self._convert_audio_format(audio_file)
                text = await self._transcribe_with_google(audio_data, language)
            elif self.openai_client and OPENAI_AVAILABLE:
                # Use OpenAI Whisper (Python 3.13+ compatible)
                text = await self._transcribe_with_openai(audio_file, language)
            else:
                return {
                    'success': False,
                    'error': 'No transcription method available',
                    'raw_text': '',
                    'enhanced_text': '',
                    'structured_notes': {}
                }
            
            if not text:
                return {
                    'success': False,
                    'error': 'No speech detected in audio',
                    'raw_text': '',
                    'enhanced_text': '',
                    'structured_notes': {}
                }
            
            # Enhance medical terminology
            enhanced_text = text
            if enhance_medical_terms:
                enhanced_text = self._enhance_medical_terms(text)
            
            # Structure into SOAP format if requested
            structured_notes = {}
            if structure_soap:
                structured_notes = self._structure_into_soap(enhanced_text)
            
            # Calculate confidence (placeholder - Google API doesn't provide this directly)
            confidence = self._estimate_confidence(text)
            
            return {
                'success': True,
                'raw_text': text,
                'enhanced_text': enhanced_text,
                'structured_notes': structured_notes,
                'confidence': confidence,
                'language': language,
                'word_count': len(text.split())
            }
            
        except Exception as e:
            error_type = type(e).__name__
            if SPEECH_RECOGNITION_AVAILABLE:
                if error_type == 'UnknownValueError':
                    logger.error("Speech Recognition could not understand audio")
                    return {
                        'success': False,
                        'error': 'Não foi possível entender o áudio. Verifique a qualidade do áudio.',
                        'raw_text': '',
                        'enhanced_text': '',
                        'structured_notes': {}
                    }
                elif error_type == 'RequestError':
                    logger.error(f"Speech Recognition service error: {str(e)}")
                    return {
                        'success': False,
                        'error': f'Erro no serviço de reconhecimento de voz: {str(e)}',
                        'raw_text': '',
                        'enhanced_text': '',
                        'structured_notes': {}
                    }
            
            logger.error(f"Transcription error: {str(e)}")
            return {
                'success': False,
                'error': f'Erro na transcrição: {str(e)}',
                'raw_text': '',
                'enhanced_text': '',
                'structured_notes': {}
            }
    
    async def _convert_audio_format(self, audio_file: bytes) -> bytes:
        """
        Convert various audio formats to WAV format required by SpeechRecognition
        
        Args:
            audio_file: Audio file bytes in any format
        
        Returns:
            WAV format audio bytes
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return audio_file
        
        try:
            # Try to detect format and convert
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_file))
            
            # Convert to WAV format (mono, 16kHz sample rate for better recognition)
            audio_segment = audio_segment.set_channels(1)  # Mono
            audio_segment = audio_segment.set_frame_rate(16000)  # 16kHz
            
            # Export to WAV
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            return wav_buffer.read()
            
        except Exception as e:
            # If conversion fails, assume it's already WAV or try to use as-is
            logger.warning(f"Audio conversion warning: {str(e)}, using original format")
            return audio_file
    
    async def _transcribe_with_google(self, audio_data: bytes, language: str) -> str:
        """
        Transcribe using Google Speech-to-Text API
        
        Args:
            audio_data: WAV format audio bytes
            language: Language code (e.g., 'pt-BR', 'en-US')
        
        Returns:
            Transcribed text
        """
        if not SPEECH_RECOGNITION_AVAILABLE or self.recognizer is None:
            raise Exception("Speech Recognition is not available")
        
        try:
            # Create temporary file for SpeechRecognition
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio.flush()
                temp_path = temp_audio.name
            
            try:
                # Use SpeechRecognition to transcribe
                with sr.AudioFile(temp_path) as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    # Record audio
                    audio = self.recognizer.record(source)
                    
                    # Transcribe using Google Speech Recognition
                    text = self.recognizer.recognize_google(audio, language=language)
                    
                return text
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except sr.UnknownValueError:
            raise Exception("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            raise Exception(f"Could not request results from Google Speech Recognition service: {e}")
    
    async def _transcribe_with_openai(self, audio_file: bytes, language: str) -> str:
        """
        Transcribe using OpenAI Whisper API (Python 3.13+ compatible)
        
        Args:
            audio_file: Audio file bytes in any format
            language: Language code (e.g., 'pt-BR', 'en-US', 'es-ES')
        
        Returns:
            Transcribed text
        """
        if not self.openai_client:
            raise Exception("OpenAI client is not available")
        
        try:
            # Create a temporary file for the audio
            suffix = '.mp3'  # Default suffix, OpenAI Whisper supports many formats
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_audio:
                temp_audio.write(audio_file)
                temp_audio.flush()
                temp_path = temp_audio.name
            
            try:
                # Map language codes (OpenAI uses ISO 639-1, e.g., 'pt' instead of 'pt-BR')
                language_map = {
                    'pt-BR': 'pt',
                    'pt-PT': 'pt',
                    'en-US': 'en',
                    'en-GB': 'en',
                    'es-ES': 'es',
                    'es-MX': 'es',
                    'fr-FR': 'fr',
                    'de-DE': 'de',
                    'it-IT': 'it',
                    'ja-JP': 'ja',
                    'ko-KR': 'ko',
                    'zh-CN': 'zh'
                }
                whisper_language = language_map.get(language, language.split('-')[0] if '-' in language else language)
                
                # Open the file and transcribe
                with open(temp_path, 'rb') as audio_file_obj:
                    transcript = await self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file_obj,
                        language=whisper_language if whisper_language in ['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh'] else None
                    )
                
                return transcript.text
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"OpenAI Whisper transcription error: {str(e)}")
            raise Exception(f"OpenAI Whisper transcription failed: {str(e)}")
    
    def _enhance_medical_terms(self, text: str) -> str:
        """
        Enhance medical terminology in transcribed text
        Capitalizes medical terms for better readability
        
        Args:
            text: Raw transcribed text
        
        Returns:
            Text with enhanced medical terms
        """
        enhanced_text = text
        
        # Sort terms by length (longest first) to avoid partial matches
        sorted_terms = sorted(self.medical_terms, key=len, reverse=True)
        
        for term in sorted_terms:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            enhanced_text = pattern.sub(term.title(), enhanced_text)
        
        return enhanced_text
    
    def _structure_into_soap(self, text: str) -> Dict[str, str]:
        """
        Attempt to structure text into SOAP format using keyword detection
        
        Args:
            text: Transcribed text
        
        Returns:
            Dictionary with SOAP structure (subjective, objective, assessment, plan)
        """
        soap_structure = {
            'subjective': '',
            'objective': '', 
            'assessment': '',
            'plan': ''
        }
        
        # Keywords for each SOAP section
        subjective_keywords = [
            'sente', 'dor', 'queixa', 'sintoma', 'história', 'relata',
            'paciente diz', 'paciente refere', 'queixa principal',
            'descreve', 'menciona', 'informa'
        ]
        
        objective_keywords = [
            'pressão', 'temperatura', 'frequência', 'exame', 'resultado',
            'pa', 'fc', 'fr', 'sat', 'glicemia', 'peso', 'altura',
            'ausculta', 'palpação', 'inspeção', 'percussão',
            'exame físico', 'sinais vitais', 'achados'
        ]
        
        assessment_keywords = [
            'diagnóstico', 'hipótese', 'impressão', 'avaliação',
            'conclusão', 'achado', 'sugere', 'compatível com',
            'indicativo de', 'provável'
        ]
        
        plan_keywords = [
            'tratamento', 'medicação', 'prescrição', 'encaminhamento',
            'orientação', 'conduta', 'solicitar', 'solicitação',
            'exame', 'retorno', 'seguimento', 'recomendação'
        ]
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            sentence_lower = sentence.lower()
            
            # Categorize sentence based on keywords
            if any(keyword in sentence_lower for keyword in subjective_keywords):
                soap_structure['subjective'] += sentence.strip() + '. '
            elif any(keyword in sentence_lower for keyword in objective_keywords):
                soap_structure['objective'] += sentence.strip() + '. '
            elif any(keyword in sentence_lower for keyword in assessment_keywords):
                soap_structure['assessment'] += sentence.strip() + '. '
            elif any(keyword in sentence_lower for keyword in plan_keywords):
                soap_structure['plan'] += sentence.strip() + '. '
            else:
                # If no keywords match, add to subjective (most common)
                soap_structure['subjective'] += sentence.strip() + '. '
        
        # Clean up trailing spaces
        for key in soap_structure:
            soap_structure[key] = soap_structure[key].strip()
        
        return soap_structure
    
    def _estimate_confidence(self, text: str) -> float:
        """
        Estimate transcription confidence based on text characteristics
        
        Args:
            text: Transcribed text
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        # Base confidence
        confidence = 0.7
        
        # Increase confidence if text contains medical terms
        text_lower = text.lower()
        medical_term_count = sum(1 for term in self.medical_terms if term in text_lower)
        if medical_term_count > 0:
            confidence += min(0.2, medical_term_count * 0.05)
        
        # Increase confidence if text is reasonably long
        word_count = len(text.split())
        if word_count > 10:
            confidence += 0.1
        
        # Cap at 0.95 (never 100% confident)
        return min(0.95, confidence)
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages for transcription
        
        Returns:
            List of language dictionaries with code and name
        """
        return [
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "es-ES", "name": "Spanish (Spain)"},
            {"code": "es-MX", "name": "Spanish (Mexico)"},
            {"code": "fr-FR", "name": "French (France)"},
            {"code": "de-DE", "name": "German"},
            {"code": "it-IT", "name": "Italian"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "ko-KR", "name": "Korean"},
            {"code": "zh-CN", "name": "Chinese (Simplified)"},
        ]


# Singleton instance
voice_transcriber = VoiceTranscriptionService()

