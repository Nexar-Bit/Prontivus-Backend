"""
Voice Processing Service for Clinical Documentation
Handles speech-to-text conversion with medical terminology support
"""

import asyncio
import base64
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import aiohttp
import httpx
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.voice_config import voice_settings
from app.models import User, Patient, Appointment, ClinicalRecord, VoiceSession, AIConfig
from app.models.icd10 import ICD10SearchIndex
from app.services.ai_service import create_ai_service, AIServiceError
from app.services.encryption_service import decrypt
from app.services.icd10_import import normalize_text

logger = logging.getLogger(__name__)

class VoiceProvider(Enum):
    GOOGLE = "google"
    AWS = "aws"
    AZURE = "azure"

class VoiceCommandType(Enum):
    SUBJECTIVE = "subjective"
    OBJECTIVE = "objective"
    ASSESSMENT = "assessment"
    PLAN = "plan"
    MEDICATION = "medication"
    DIAGNOSIS = "diagnosis"
    SYMPTOM = "symptom"
    VITAL_SIGNS = "vital_signs"

@dataclass
class VoiceCommand:
    command_type: VoiceCommandType
    content: str
    confidence: float
    timestamp: datetime
    raw_text: str

@dataclass
class MedicalTerm:
    term: str
    category: str
    icd10_codes: List[str]
    synonyms: List[str]
    confidence: float

class VoiceProcessingService:
    """Main service for voice processing and clinical documentation"""
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
        self.medical_terms = self._load_medical_terms()
        self.voice_provider = VoiceProvider.GOOGLE  # Default provider
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for voice data"""
        key_str = voice_settings.VOICE_ENCRYPTION_KEY or Fernet.generate_key().decode()
        return key_str.encode() if isinstance(key_str, str) else key_str
    
    def _load_medical_terms(self) -> Dict[str, MedicalTerm]:
        """Load medical terminology database"""
        return {
            "dor abdominal": MedicalTerm(
                term="dor abdominal",
                category="symptom",
                icd10_codes=["R10.9", "K59.0"],
                synonyms=["dor no abdome", "abdominalgia", "dor de barriga"],
                confidence=0.95
            ),
            "apendicite": MedicalTerm(
                term="apendicite",
                category="diagnosis",
                icd10_codes=["K35.9"],
                synonyms=["apendicite aguda", "inflamação do apêndice"],
                confidence=0.98
            ),
            "febre": MedicalTerm(
                term="febre",
                category="symptom",
                icd10_codes=["R50.9"],
                synonyms=["hipertermia", "temperatura elevada"],
                confidence=0.92
            ),
            "náusea": MedicalTerm(
                term="náusea",
                category="symptom",
                icd10_codes=["R11.0"],
                synonyms=["enjoo", "vontade de vomitar"],
                confidence=0.90
            ),
            "vômito": MedicalTerm(
                term="vômito",
                category="symptom",
                icd10_codes=["R11.0"],
                synonyms=["emese", "vomitar"],
                confidence=0.88
            ),
            "cefaleia": MedicalTerm(
                term="cefaleia",
                category="symptom",
                icd10_codes=["R51"],
                synonyms=["dor de cabeça", "cefalalgia"],
                confidence=0.94
            ),
            "hipertensão": MedicalTerm(
                term="hipertensão",
                category="diagnosis",
                icd10_codes=["I10"],
                synonyms=["pressão alta", "HAS"],
                confidence=0.96
            ),
            "diabetes": MedicalTerm(
                term="diabetes",
                category="diagnosis",
                icd10_codes=["E11.9"],
                synonyms=["DM", "diabetes mellitus"],
                confidence=0.97
            )
        }
    
    async def process_audio_stream(
        self, 
        audio_data: bytes, 
        user_id: int, 
        appointment_id: int,
        session_id: str,
        db: AsyncSession,
        use_aws_pipeline: bool = True
    ) -> Dict[str, Any]:
        """
        Process audio stream and return transcription with medical analysis
        
        Complete AWS Pipeline (if use_aws_pipeline=True):
        1. AWS Transcribe Medical → Speech to Text
        2. AWS Comprehend Medical → Extract medical entities
        3. AWS Bedrock → Generate ICD-10 suggestions and structure data
        
        Args:
            audio_data: Raw audio bytes
            user_id: ID of the user (doctor)
            appointment_id: ID of the appointment
            session_id: Unique session identifier
            db: Database session
            use_aws_pipeline: Whether to use complete AWS pipeline
            
        Returns:
            Dict containing transcription, commands, and medical terms
        """
        try:
            # Get user and appointment to access clinic_id
            user_query = select(User).where(User.id == user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            clinic_id = user.clinic_id if user else None
            
            # Encrypt audio data for HIPAA compliance
            encrypted_audio = self._encrypt_audio_data(audio_data)
            
            # Store encrypted audio temporarily
            await self._store_audio_session(session_id, encrypted_audio, user_id, appointment_id, db)
            
            # Use complete AWS pipeline if requested and available
            if use_aws_pipeline and self.voice_provider == VoiceProvider.AWS:
                return await self._process_aws_consultation_pipeline(
                    audio_data, clinic_id, session_id, db
                )
            
            # Fallback to standard processing
            # Convert speech to text (with AI if available)
            transcription = await self._speech_to_text(audio_data, clinic_id, db)
            
            # Process medical terminology (with AI + ICD-10 search)
            medical_analysis = await self._analyze_medical_terms(transcription, clinic_id, db)
            
            # Extract voice commands
            commands = self._extract_voice_commands(transcription)
            
            # Generate structured data
            structured_data = self._generate_structured_data(transcription, medical_analysis, commands)
            
            return {
                "transcription": transcription,
                "commands": [cmd.__dict__ for cmd in commands],
                "medical_terms": [term.__dict__ for term in medical_analysis],
                "structured_data": structured_data,
                "confidence": self._calculate_overall_confidence(transcription, commands),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline": "standard"
            }
            
        except Exception as e:
            logger.error(f"Error processing audio stream: {str(e)}")
            raise
    
    async def _process_aws_consultation_pipeline(
        self,
        audio_data: bytes,
        clinic_id: Optional[int],
        session_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Complete AWS consultation transcription pipeline:
        
        Flow:
        1. Patient Speaks → AWS Transcribe Medical (Speech to Text)
        2. AWS Comprehend Medical (Extract medical entities)
        3. AWS Bedrock (Generative AI) → Structure data and suggest ICD-10 codes
        4. System receives all information automatically filled in
        
        Args:
            audio_data: Raw audio bytes
            clinic_id: Clinic ID
            session_id: Session ID
            db: Database session
            
        Returns:
            Complete structured consultation data
        """
        try:
            from app.services.comprehend_medical_service import comprehend_medical_service
            
            # Step 1: AWS Transcribe Medical - Convert speech to text
            logger.info("Step 1: AWS Transcribe Medical - Converting speech to text...")
            transcription = await self._aws_transcribe(audio_data)
            
            if not transcription:
                raise Exception("Transcription failed - no text generated")
            
            logger.info(f"Transcription completed: {len(transcription)} characters")
            
            # Step 2: AWS Comprehend Medical - Extract medical entities
            logger.info("Step 2: AWS Comprehend Medical - Extracting medical entities...")
            clinical_analysis = await comprehend_medical_service.analyze_clinical_note(
                text=transcription,
                language="pt-BR",
                include_phi=False
            )
            
            if not clinical_analysis.get("success"):
                logger.warning("Comprehend Medical analysis failed, using basic extraction")
                clinical_analysis = {
                    "medications": [],
                    "conditions": [],
                    "procedures": [],
                    "anatomy": []
                }
            
            # Step 3: AWS Bedrock - Generate ICD-10 suggestions and structure data
            logger.info("Step 3: AWS Bedrock - Generating ICD-10 suggestions and structuring data...")
            icd10_result = await comprehend_medical_service.infer_icd10_codes(
                text=transcription,
                language="pt-BR",
                db_session=db
            )
            
            icd10_suggestions = icd10_result.get("icd10_suggestions", []) if icd10_result.get("success") else []
            
            # Step 4: Use Bedrock to structure the consultation data (SOAP format)
            structured_soap = await self._bedrock_structure_consultation(
                transcription=transcription,
                clinical_analysis=clinical_analysis,
                icd10_suggestions=icd10_suggestions
            )
            
            # Convert to MedicalTerm objects for compatibility
            medical_terms = []
            for condition in clinical_analysis.get("conditions", []):
                # Find matching ICD-10 code
                matching_icd = next(
                    (icd for icd in icd10_suggestions if icd.get("condition", "").lower() == condition.get("text", "").lower()),
                    None
                )
                
                medical_terms.append(MedicalTerm(
                    term=condition.get("text", ""),
                    category="diagnosis" if "DIAGNOSIS" in condition.get("traits", []) else "symptom",
                    icd10_codes=[matching_icd.get("icd10_code")] if matching_icd else [],
                    synonyms=[],
                    confidence=condition.get("confidence", 0.8)
                ))
            
            # Extract medications
            for medication in clinical_analysis.get("medications", []):
                medical_terms.append(MedicalTerm(
                    term=medication.get("text", ""),
                    category="medication",
                    icd10_codes=[],
                    synonyms=[],
                    confidence=medication.get("confidence", 0.8)
                ))
            
            # Generate structured data
            structured_data = {
                "soap_notes": structured_soap.get("soap_notes", {
                    "subjective": "",
                    "objective": "",
                    "assessment": "",
                    "plan": ""
                }),
                "symptoms": [c for c in clinical_analysis.get("conditions", []) if "SYMPTOM" in c.get("traits", [])],
                "diagnoses": [c for c in clinical_analysis.get("conditions", []) if "DIAGNOSIS" in c.get("traits", [])],
                "medications": clinical_analysis.get("medications", []),
                "procedures": clinical_analysis.get("procedures", []),
                "vital_signs": structured_soap.get("vital_signs", {}),
                "icd10_codes": [icd.get("icd10_code") for icd in icd10_suggestions],
                "confidence_scores": {
                    "transcription": 0.95,  # AWS Transcribe Medical is highly accurate
                    "entity_extraction": clinical_analysis.get("summary", {}).get("total_entities", 0) / max(len(transcription.split()), 1),
                    "icd10_suggestions": len(icd10_suggestions) / max(len(clinical_analysis.get("conditions", [])), 1)
                }
            }
            
            # Extract voice commands from structured data
            commands = []
            if structured_data["soap_notes"]["subjective"]:
                commands.append(VoiceCommand(
                    command_type=VoiceCommandType.SUBJECTIVE,
                    content=structured_data["soap_notes"]["subjective"],
                    confidence=0.9,
                    timestamp=datetime.utcnow(),
                    raw_text=transcription
                ))
            if structured_data["soap_notes"]["objective"]:
                commands.append(VoiceCommand(
                    command_type=VoiceCommandType.OBJECTIVE,
                    content=structured_data["soap_notes"]["objective"],
                    confidence=0.9,
                    timestamp=datetime.utcnow(),
                    raw_text=transcription
                ))
            if structured_data["soap_notes"]["assessment"]:
                commands.append(VoiceCommand(
                    command_type=VoiceCommandType.ASSESSMENT,
                    content=structured_data["soap_notes"]["assessment"],
                    confidence=0.9,
                    timestamp=datetime.utcnow(),
                    raw_text=transcription
                ))
            if structured_data["soap_notes"]["plan"]:
                commands.append(VoiceCommand(
                    command_type=VoiceCommandType.PLAN,
                    content=structured_data["soap_notes"]["plan"],
                    confidence=0.9,
                    timestamp=datetime.utcnow(),
                    raw_text=transcription
                ))
            
            return {
                "transcription": transcription,
                "commands": [cmd.__dict__ for cmd in commands],
                "medical_terms": [term.__dict__ for term in medical_terms],
                "structured_data": structured_data,
                "clinical_analysis": clinical_analysis,
                "icd10_suggestions": icd10_suggestions,
                "confidence": 0.92,  # High confidence for AWS pipeline
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline": "aws_complete"
            }
            
        except Exception as e:
            logger.error(f"Error in AWS consultation pipeline: {str(e)}", exc_info=True)
            # Fallback to standard processing
            raise
    
    async def _bedrock_structure_consultation(
        self,
        transcription: str,
        clinical_analysis: Dict[str, Any],
        icd10_suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use AWS Bedrock to structure consultation data into SOAP format
        
        Args:
            transcription: Full transcription text
            clinical_analysis: Results from Comprehend Medical
            icd10_suggestions: ICD-10 code suggestions
            
        Returns:
            Structured SOAP notes and additional data
        """
        try:
            import boto3
            import json
            import os
            import re
            
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            
            if not aws_access_key or not aws_secret_key:
                # Fallback to basic structure
                return self._basic_structure_soap(transcription, clinical_analysis)
            
            bedrock_client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            # Prepare prompt for Bedrock
            conditions_text = "\n".join([
                f"- {c.get('text', '')}" for c in clinical_analysis.get("conditions", [])[:10]
            ])
            medications_text = "\n".join([
                f"- {m.get('text', '')}" for m in clinical_analysis.get("medications", [])[:10]
            ])
            
            prompt = f"""You are a medical documentation assistant. Structure the following clinical consultation transcription into SOAP format.

Transcription:
{transcription[:2000]}

Extracted Medical Conditions:
{conditions_text}

Extracted Medications:
{medications_text}

ICD-10 Suggestions:
{json.dumps(icd10_suggestions[:5], indent=2)}

Please structure this into SOAP format:
- Subjective: Patient's complaints, history, symptoms
- Objective: Physical examination findings, vital signs, test results
- Assessment: Diagnosis, clinical impression
- Plan: Treatment plan, medications, follow-up

Also extract vital signs if mentioned (blood pressure, temperature, heart rate, respiratory rate, oxygen saturation).

Return a JSON object with this structure:
{{
  "soap_notes": {{
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "..."
  }},
  "vital_signs": {{
    "blood_pressure": "120/80",
    "temperature": "36.5",
    "heart_rate": "72",
    "respiratory_rate": "16",
    "oxygen_saturation": "98"
  }}
}}

Only return the JSON object, no additional text."""

            model_id = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            if content and len(content) > 0:
                ai_response = content[0].get('text', '')
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    structured = json.loads(json_match.group())
                    return structured
            
            # Fallback
            return self._basic_structure_soap(transcription, clinical_analysis)
            
        except Exception as e:
            logger.warning(f"Bedrock structure consultation failed: {str(e)}. Using basic structure.")
            return self._basic_structure_soap(transcription, clinical_analysis)
    
    def _basic_structure_soap(
        self,
        transcription: str,
        clinical_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic SOAP structure when Bedrock is not available"""
        return {
            "soap_notes": {
                "subjective": transcription[:len(transcription)//4] if transcription else "",
                "objective": "",
                "assessment": "\n".join([c.get("text", "") for c in clinical_analysis.get("conditions", [])[:3]]),
                "plan": "\n".join([m.get("text", "") for m in clinical_analysis.get("medications", [])[:3]])
            },
            "vital_signs": {}
        }
    
    async def _speech_to_text(self, audio_data: bytes, clinic_id: Optional[int] = None, db: Optional[AsyncSession] = None) -> str:
        """
        Convert audio to text using AI service if available, otherwise fallback to Google Speech API
        
        Args:
            audio_data: Raw audio bytes
            clinic_id: Clinic ID to check for AI configuration
            db: Database session
            
        Returns:
            Transcribed text
        """
        # Try to use AI service if configured
        if clinic_id and db:
            try:
                ai_transcription = await self._ai_speech_to_text(audio_data, clinic_id, db)
                if ai_transcription:
                    return ai_transcription
            except Exception as e:
                logger.warning(f"AI transcription failed, falling back to Google Speech: {str(e)}")
        
        # Fallback to Google Speech API
        if self.voice_provider == VoiceProvider.GOOGLE:
            return await self._google_speech_to_text(audio_data)
        elif self.voice_provider == VoiceProvider.AWS:
            return await self._aws_transcribe(audio_data)
        else:
            raise ValueError(f"Unsupported voice provider: {self.voice_provider}")
    
    async def _ai_speech_to_text(self, audio_data: bytes, clinic_id: int, db: AsyncSession) -> Optional[str]:
        """
        Convert audio to text using AI service (for transcription enhancement)
        Note: AI services typically don't handle raw audio directly, so we use Google Speech first
        then enhance with AI, or use AI to improve the transcription quality
        
        Args:
            audio_data: Raw audio bytes
            clinic_id: Clinic ID
            db: Database session
            
        Returns:
            Enhanced transcription or None if AI not available
        """
        try:
            # Get AI config for clinic
            ai_config_query = select(AIConfig).where(
                AIConfig.clinic_id == clinic_id,
                AIConfig.enabled == True
            )
            ai_config_result = await db.execute(ai_config_query)
            ai_config = ai_config_result.scalar_one_or_none()
            
            if not ai_config or not ai_config.api_key_encrypted:
                return None
            
            # First, get basic transcription from Google Speech (AI services don't handle raw audio well)
            basic_transcription = await self._google_speech_to_text(audio_data)
            
            if not basic_transcription:
                return None
            
            # Enhance transcription with AI for medical context
            ai_service = create_ai_service(
                provider=ai_config.provider,
                api_key_encrypted=ai_config.api_key_encrypted,
                model=ai_config.model or "gpt-4",
                base_url=ai_config.base_url,
                max_tokens=ai_config.max_tokens,
                temperature=ai_config.temperature
            )
            
            # Use AI to improve medical transcription
            system_prompt = """You are a medical transcription assistant. Improve the following medical transcription 
            for accuracy, especially for medical terminology. Return only the improved transcription without additional comments."""
            
            prompt = f"Improve this medical transcription for accuracy:\n\n{basic_transcription}"
            
            enhanced_transcription, usage = await ai_service.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            # Update token usage (handled by AI service internally)
            logger.info(f"AI transcription enhancement used {usage.get('tokens_used', 0)} tokens")
            
            return enhanced_transcription.strip()
            
        except AIServiceError as e:
            logger.warning(f"AI service error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error in AI transcription: {str(e)}")
            return None
    
    async def _google_speech_to_text(self, audio_data: bytes) -> str:
        """Convert audio to text using Google Speech-to-Text API"""
        try:
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare request payload
            payload = {
                "config": {
                    "encoding": "WEBM_OPUS",  # Adjust based on audio format
                    "sampleRateHertz": 48000,
                    "languageCode": "pt-BR",
                    "enableAutomaticPunctuation": True,
                    "enableWordTimeOffsets": True,
                    "model": "medical_dictation",  # Medical-specific model
                    "useEnhanced": True,
                    "speechContexts": [{
                        "phrases": list(self.medical_terms.keys()),
                        "boost": 20.0
                    }]
                },
                "audio": {
                    "content": audio_b64
                }
            }
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://speech.googleapis.com/v1/speech:recognize?key={voice_settings.GOOGLE_API_KEY}",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'results' in result and len(result['results']) > 0:
                        return result['results'][0]['alternatives'][0]['transcript']
                    else:
                        return ""
                else:
                    logger.error(f"Google Speech API error: {response.status_code} - {response.text}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error with Google Speech-to-Text: {str(e)}")
            return ""
    
    async def _aws_transcribe(self, audio_data: bytes) -> str:
        """
        Convert audio to text using AWS Transcribe Medical
        
        AWS Transcribe Medical provides medical-specific speech-to-text
        with automatic punctuation and medical terminology recognition
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        try:
            import boto3
            import tempfile
            import os
            from botocore.exceptions import ClientError
            
            # Get AWS credentials
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID") or voice_settings.AWS_ACCESS_KEY_ID
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or voice_settings.AWS_SECRET_ACCESS_KEY
            aws_region = os.getenv("AWS_REGION", "us-east-1") or voice_settings.AWS_REGION
            
            if not aws_access_key or not aws_secret_key:
                logger.warning("AWS credentials not configured. Falling back to Google Speech.")
                return await self._google_speech_to_text(audio_data)
            
            # Initialize AWS Transcribe client
            transcribe_client = boto3.client(
                'transcribe',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            # Initialize S3 client for storing audio (required by Transcribe)
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            try:
                # Upload audio to S3 (required for Transcribe)
                bucket_name = os.getenv("AWS_S3_BUCKET", "prontivus-transcribe-temp")
                job_name = f"transcribe-{hashlib.md5(audio_data).hexdigest()[:16]}"
                s3_key = f"audio/{job_name}.webm"
                
                # Create bucket if it doesn't exist (with error handling)
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                except ClientError:
                    # Bucket doesn't exist, try to create it
                    try:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': aws_region}
                        )
                    except ClientError as e:
                        logger.warning(f"Could not create S3 bucket: {e}. Using direct transcription.")
                        # Fallback: Use Transcribe Medical streaming (if available)
                        return await self._aws_transcribe_streaming(audio_data, transcribe_client)
                
                # Upload audio file
                s3_client.upload_file(temp_audio_path, bucket_name, s3_key)
                s3_uri = f"s3://{bucket_name}/{s3_key}"
                
                # Start transcription job with medical vocabulary
                transcribe_client.start_medical_transcription_job(
                    MedicalTranscriptionJobName=job_name,
                    Media={'MediaFileUri': s3_uri},
                    MediaFormat='webm',
                    LanguageCode='pt-BR',  # Portuguese (Brazil)
                    Type='CONVERSATION',  # Medical conversation type
                    OutputBucketName=bucket_name,
                    OutputKey=f"transcriptions/{job_name}.json",
                    Settings={
                        'ShowSpeakerLabels': False,
                        'MaxSpeakerLabels': 1,
                        'ChannelIdentification': False,
                        'ShowAlternatives': False
                    }
                )
                
                # Wait for transcription to complete (polling)
                import time
                max_wait_time = 300  # 5 minutes
                wait_interval = 5  # Check every 5 seconds
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    response = transcribe_client.get_medical_transcription_job(
                        MedicalTranscriptionJobName=job_name
                    )
                    
                    status = response['MedicalTranscriptionJob']['TranscriptionJobStatus']
                    
                    if status == 'COMPLETED':
                        # Get transcription result from S3
                        transcript_uri = response['MedicalTranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        # Download and parse transcript
                        import json
                        import urllib.request
                        
                        with urllib.request.urlopen(transcript_uri) as url:
                            transcript_data = json.loads(url.read().decode())
                        
                        transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                        
                        # Clean up S3 files
                        try:
                            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                            s3_client.delete_object(Bucket=bucket_name, Key=f"transcriptions/{job_name}.json")
                        except:
                            pass
                        
                        return transcript_text
                    
                    elif status == 'FAILED':
                        failure_reason = response['MedicalTranscriptionJob'].get('FailureReason', 'Unknown error')
                        logger.error(f"AWS Transcribe Medical job failed: {failure_reason}")
                        raise Exception(f"Transcription failed: {failure_reason}")
                    
                    # Wait before next check
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                
                # Timeout
                raise Exception("Transcription job timed out")
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                    
        except ImportError:
            logger.warning("boto3 not installed. Falling back to Google Speech.")
            return await self._google_speech_to_text(audio_data)
        except Exception as e:
            logger.error(f"Error with AWS Transcribe Medical: {str(e)}")
            # Fallback to Google Speech
            return await self._google_speech_to_text(audio_data)
    
    async def _aws_transcribe_streaming(self, audio_data: bytes, transcribe_client) -> str:
        """
        Fallback: Use AWS Transcribe streaming API (if S3 is not available)
        Note: This is a simplified implementation
        """
        logger.warning("AWS Transcribe streaming not fully implemented. Using Google Speech fallback.")
        return await self._google_speech_to_text(audio_data)
    
    async def _analyze_medical_terms(self, text: str, clinic_id: Optional[int] = None, db: Optional[AsyncSession] = None) -> List[MedicalTerm]:
        """
        Analyze text for medical terminology using AI and ICD-10 database
        
        Args:
            text: Transcription text
            clinic_id: Clinic ID for AI configuration
            db: Database session for ICD-10 search
            
        Returns:
            List of medical terms with ICD-10 codes
        """
        found_terms = []
        text_lower = text.lower()
        
        # First, check hardcoded dictionary (quick lookup)
        for term_key, medical_term in self.medical_terms.items():
            if term_key in text_lower:
                found_terms.append(medical_term)
            else:
                # Check synonyms
                for synonym in medical_term.synonyms:
                    if synonym.lower() in text_lower:
                        found_terms.append(medical_term)
                        break
        
        # Use AI to extract additional medical terms if available
        if clinic_id and db and text.strip():
            try:
                ai_terms = await self._ai_extract_medical_terms(text, clinic_id, db)
                found_terms.extend(ai_terms)
            except Exception as e:
                logger.warning(f"AI medical term extraction failed: {str(e)}")
        
        # Query ICD-10 database for code suggestions
        if db and text.strip():
            try:
                icd10_suggestions = await self._get_icd10_suggestions(text, db)
                # Convert ICD-10 suggestions to MedicalTerm objects
                for suggestion in icd10_suggestions:
                    # Check if we already have this term
                    existing = next((t for t in found_terms if suggestion['code'] in t.icd10_codes), None)
                    if not existing:
                        found_terms.append(MedicalTerm(
                            term=suggestion.get('description', ''),
                            category="diagnosis",
                            icd10_codes=[suggestion['code']],
                            synonyms=[],
                            confidence=0.85
                        ))
            except Exception as e:
                logger.warning(f"ICD-10 search failed: {str(e)}")
        
        # Remove duplicates
        seen = set()
        unique_terms = []
        for term in found_terms:
            term_key = (term.term.lower(), tuple(sorted(term.icd10_codes)))
            if term_key not in seen:
                seen.add(term_key)
                unique_terms.append(term)
        
        return unique_terms
    
    async def _ai_extract_medical_terms(self, text: str, clinic_id: int, db: AsyncSession) -> List[MedicalTerm]:
        """
        Use AI to extract medical terms from transcription
        
        Args:
            text: Transcription text
            clinic_id: Clinic ID
            db: Database session
            
        Returns:
            List of MedicalTerm objects
        """
        try:
            # Get AI config
            ai_config_query = select(AIConfig).where(
                AIConfig.clinic_id == clinic_id,
                AIConfig.enabled == True
            )
            ai_config_result = await db.execute(ai_config_query)
            ai_config = ai_config_result.scalar_one_or_none()
            
            if not ai_config or not ai_config.api_key_encrypted:
                return []
            
            # Create AI service
            ai_service = create_ai_service(
                provider=ai_config.provider,
                api_key_encrypted=ai_config.api_key_encrypted,
                model=ai_config.model or "gpt-4",
                base_url=ai_config.base_url,
                max_tokens=ai_config.max_tokens,
                temperature=ai_config.temperature
            )
            
            # Prompt AI to extract medical terms
            system_prompt = """You are a medical AI assistant. Extract medical terms (symptoms, diagnoses, medications) 
            from the transcription. Return a JSON array with objects containing: "term", "category" (symptom/diagnosis/medication), 
            and "confidence" (0.0-1.0)."""
            
            prompt = f"Extract medical terms from this transcription:\n\n{text}\n\nReturn only the JSON array."
            
            response, usage = await ai_service.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            # Parse AI response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                ai_terms_data = json.loads(json_match.group())
                
                # Convert to MedicalTerm objects
                medical_terms = []
                for term_data in ai_terms_data:
                    term_text = term_data.get('term', '').lower()
                    if term_text:
                        # Search ICD-10 for this term
                        icd10_codes = await self._search_icd10_for_term(term_text, db)
                        
                        medical_terms.append(MedicalTerm(
                            term=term_data.get('term', ''),
                            category=term_data.get('category', 'symptom'),
                            icd10_codes=icd10_codes,
                            synonyms=[],
                            confidence=float(term_data.get('confidence', 0.8))
                        ))
                
                return medical_terms
            
            return []
            
        except Exception as e:
            logger.error(f"Error in AI medical term extraction: {str(e)}")
            return []
    
    async def _get_icd10_suggestions(self, text: str, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get ICD-10 code suggestions from database based on transcription
        
        Args:
            text: Transcription text
            db: Database session
            limit: Maximum number of suggestions
            
        Returns:
            List of ICD-10 suggestions with code and description
        """
        try:
            # Extract key medical terms from text (simple keyword extraction)
            words = text.lower().split()
            medical_keywords = [w for w in words if len(w) > 4]  # Filter short words
            
            suggestions = []
            seen_codes = set()
            
            # Search for each keyword in ICD-10 database
            for keyword in medical_keywords[:5]:  # Limit to 5 keywords to avoid too many queries
                normalized = normalize_text(keyword)
                query = select(ICD10SearchIndex).filter(
                    ICD10SearchIndex.search_text.ilike(f"%{normalized}%")
                ).limit(limit)
                
                results = (await db.execute(query)).scalars().all()
                
                for result in results:
                    if result.code not in seen_codes:
                        seen_codes.add(result.code)
                        suggestions.append({
                            "code": result.code,
                            "description": result.description,
                            "level": result.level,
                            "confidence": 0.8  # Default confidence
                        })
                        
                        if len(suggestions) >= limit:
                            break
                
                if len(suggestions) >= limit:
                    break
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting ICD-10 suggestions: {str(e)}")
            return []
    
    async def _search_icd10_for_term(self, term: str, db: AsyncSession, limit: int = 3) -> List[str]:
        """
        Search ICD-10 database for a specific medical term
        
        Args:
            term: Medical term to search
            db: Database session
            limit: Maximum number of codes to return
            
        Returns:
            List of ICD-10 codes
        """
        try:
            normalized = normalize_text(term)
            query = select(ICD10SearchIndex).filter(
                ICD10SearchIndex.search_text.ilike(f"%{normalized}%")
            ).limit(limit)
            
            results = (await db.execute(query)).scalars().all()
            return [r.code for r in results]
            
        except Exception as e:
            logger.error(f"Error searching ICD-10 for term '{term}': {str(e)}")
            return []
    
    def _extract_voice_commands(self, text: str) -> List[VoiceCommand]:
        """Extract structured voice commands from text"""
        commands = []
        text_lower = text.lower()
        
        # Define command patterns
        command_patterns = {
            VoiceCommandType.SUBJECTIVE: [
                "adicionar queixa", "queixa principal", "história da doença",
                "sintomas", "relato do paciente"
            ],
            VoiceCommandType.OBJECTIVE: [
                "exame físico", "achados do exame", "sinais vitais",
                "inspeção", "palpação", "ausculta", "percussão"
            ],
            VoiceCommandType.ASSESSMENT: [
                "hipótese diagnóstica", "diagnóstico", "impressão diagnóstica",
                "avaliação", "conclusão"
            ],
            VoiceCommandType.PLAN: [
                "conduta", "plano terapêutico", "tratamento", "medicação",
                "exames complementares", "orientações"
            ],
            VoiceCommandType.MEDICATION: [
                "prescrever", "medicamento", "dose", "posologia",
                "antibiótico", "analgésico"
            ],
            VoiceCommandType.VITAL_SIGNS: [
                "pressão arterial", "temperatura", "frequência cardíaca",
                "frequência respiratória", "saturação"
            ]
        }
        
        for cmd_type, patterns in command_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Extract content after the command
                    start_idx = text_lower.find(pattern)
                    if start_idx != -1:
                        content_start = start_idx + len(pattern)
                        content = text[content_start:].strip()
                        if content.startswith(':'):
                            content = content[1:].strip()
                        
                        commands.append(VoiceCommand(
                            command_type=cmd_type,
                            content=content,
                            confidence=0.85,  # Default confidence
                            timestamp=datetime.utcnow(),
                            raw_text=text
                        ))
                        break
        
        return commands
    
    def _generate_structured_data(
        self, 
        transcription: str, 
        medical_terms: List[MedicalTerm], 
        commands: List[VoiceCommand]
    ) -> Dict[str, Any]:
        """Generate structured clinical data from voice input"""
        structured = {
            "soap_notes": {
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": ""
            },
            "symptoms": [],
            "diagnoses": [],
            "medications": [],
            "vital_signs": {},
            "icd10_codes": [],
            "confidence_scores": {}
        }
        
        # Process commands to populate SOAP sections
        for cmd in commands:
            if cmd.command_type == VoiceCommandType.SUBJECTIVE:
                structured["soap_notes"]["subjective"] += f"{cmd.content}\n"
            elif cmd.command_type == VoiceCommandType.OBJECTIVE:
                structured["soap_notes"]["objective"] += f"{cmd.content}\n"
            elif cmd.command_type == VoiceCommandType.ASSESSMENT:
                structured["soap_notes"]["assessment"] += f"{cmd.content}\n"
            elif cmd.command_type == VoiceCommandType.PLAN:
                structured["soap_notes"]["plan"] += f"{cmd.content}\n"
        
        # Process medical terms
        for term in medical_terms:
            if term.category == "symptom":
                structured["symptoms"].append({
                    "term": term.term,
                    "confidence": term.confidence,
                    "icd10_codes": term.icd10_codes
                })
            elif term.category == "diagnosis":
                structured["diagnoses"].append({
                    "term": term.term,
                    "confidence": term.confidence,
                    "icd10_codes": term.icd10_codes
                })
            
            # Add ICD-10 codes
            structured["icd10_codes"].extend(term.icd10_codes)
        
        # Remove duplicates from ICD-10 codes
        structured["icd10_codes"] = list(set(structured["icd10_codes"]))
        
        return structured
    
    def _calculate_overall_confidence(self, transcription: str, commands: List[VoiceCommand]) -> float:
        """Calculate overall confidence score for the transcription"""
        if not transcription:
            return 0.0
        
        # Base confidence from transcription length and medical terms
        base_confidence = min(len(transcription) / 100, 0.9)  # Max 0.9 for length
        
        # Boost confidence for medical terms
        medical_boost = len(commands) * 0.1
        
        # Boost confidence for command structure
        command_boost = min(len(commands) * 0.05, 0.2)
        
        return min(base_confidence + medical_boost + command_boost, 1.0)
    
    def _encrypt_audio_data(self, audio_data: bytes) -> bytes:
        """Encrypt audio data for HIPAA compliance"""
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(audio_data)
    
    def _decrypt_audio_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt audio data"""
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_data)
    
    async def _store_audio_session(
        self, 
        session_id: str, 
        encrypted_audio: bytes, 
        user_id: int, 
        appointment_id: int, 
        db: AsyncSession
    ) -> None:
        """Store encrypted audio session data"""
        try:
            # Create or update voice session
            voice_session = VoiceSession(
                session_id=session_id,
                user_id=user_id,
                appointment_id=appointment_id,
                encrypted_audio_data=encrypted_audio,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24)  # Auto-delete after 24h
            )
            
            db.add(voice_session)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error storing audio session: {str(e)}")
            await db.rollback()
            raise
    
    async def create_clinical_record_from_voice(
        self,
        session_id: str,
        user_id: int,
        appointment_id: int,
        db: AsyncSession
    ) -> ClinicalRecord:
        """Create clinical record from voice session data"""
        try:
            # Get voice session
            voice_session_query = select(VoiceSession).where(
                VoiceSession.session_id == session_id,
                VoiceSession.user_id == user_id
            )
            voice_session_result = await db.execute(voice_session_query)
            voice_session = voice_session_result.scalar_one_or_none()
            
            if not voice_session:
                raise ValueError("Voice session not found")
            
            # Decrypt and process audio
            decrypted_audio = self._decrypt_audio_data(voice_session.encrypted_audio_data)
            voice_data = await self.process_audio_stream(
                decrypted_audio, user_id, appointment_id, session_id, db
            )
            
            # Create clinical record
            clinical_record = ClinicalRecord(
                appointment_id=appointment_id,
                subjective=voice_data["structured_data"]["soap_notes"]["subjective"],
                objective=voice_data["structured_data"]["soap_notes"]["objective"],
                assessment=voice_data["structured_data"]["soap_notes"]["assessment"],
                plan=voice_data["structured_data"]["soap_notes"]["plan"],
                notes=voice_data["transcription"],
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            db.add(clinical_record)
            await db.commit()
            await db.refresh(clinical_record)
            
            return clinical_record
            
        except Exception as e:
            logger.error(f"Error creating clinical note from voice: {str(e)}")
            await db.rollback()
            raise

# Global instance
voice_service = VoiceProcessingService()
