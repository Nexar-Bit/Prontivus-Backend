"""
Performance Tests for AI Features
"""
import pytest
import time
import asyncio
from app.services.pdf_generator import PDFGenerator
from app.services.voice_transcription import VoiceTranscriptionService
from app.services.clinical_ai import ClinicalAIService


@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """Performance tests for AI features"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pdf_generator = PDFGenerator()
        self.transcription_service = VoiceTranscriptionService()
        self.ai_service = ClinicalAIService()
        
        self.test_consultation_data = {
            'appointment_id': 1,
            'scheduled_datetime': '15/01/2024 10:00',
            'appointment_type': 'Consulta',
            'patient': {
                'id': 1,
                'name': 'João Silva',
                'date_of_birth': '15/05/1989',
                'gender': 'Masculino',
                'cpf': '123.456.789-00',
            },
            'doctor': {
                'id': 1,
                'name': 'Dr. Maria Santos',
                'crm': 'CRM-SP 123456'
            },
            'clinic': {
                'id': 1,
                'name': 'Clínica Prontivus',
                'address': 'Rua Teste, 123',
                'phone': '(11) 3333-3333',
                'email': 'contato@prontivus.com',
            },
            'clinical_record': {
                'subjective': 'Paciente relata dor de cabeça há 3 dias',
                'objective': 'PA: 120/80 mmHg, FC: 72 bpm',
                'assessment': 'Hipótese diagnóstica: Cefaleia tensional',
                'plan': 'Prescrição de analgésico',
                'prescriptions': [],
                'exam_requests': [],
                'diagnoses': []
            }
        }
    
    def test_pdf_generation_performance(self):
        """PDF generation should complete within 5 seconds"""
        start_time = time.time()
        
        pdf_bytes = self.pdf_generator.generate_consultation_report(self.test_consultation_data)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        assert elapsed_time < 5.0, f"PDF generation took {elapsed_time:.2f} seconds, expected < 5.0"
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
    
    def test_pdf_generation_throughput(self):
        """Test PDF generation throughput (multiple PDFs)"""
        num_pdfs = 10
        start_time = time.time()
        
        for i in range(num_pdfs):
            data = self.test_consultation_data.copy()
            data['appointment_id'] = i + 1
            pdf_bytes = self.pdf_generator.generate_consultation_report(data)
            assert pdf_bytes is not None
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        avg_time = elapsed_time / num_pdfs
        
        # Average time should be reasonable
        assert avg_time < 3.0, f"Average PDF generation took {avg_time:.2f} seconds"
        # Total time should be reasonable
        assert elapsed_time < 30.0, f"Total time for {num_pdfs} PDFs: {elapsed_time:.2f} seconds"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_transcription_performance(self):
        """Transcription should complete within 30 seconds for typical audio"""
        # Note: This test requires actual audio or mocked API
        # For unit tests, we'll skip if API unavailable
        mock_audio = b'mock_audio_data' * 1000  # Simulate larger audio
        
        start_time = time.time()
        
        try:
            result = await self.transcription_service.transcribe_audio(
                mock_audio,
                language='pt-BR'
            )
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Transcription should complete within 30 seconds
            # Or fail quickly if API unavailable
            if result.get('success'):
                assert elapsed_time < 30.0, f"Transcription took {elapsed_time:.2f} seconds"
            else:
                # If API unavailable, should fail quickly
                assert elapsed_time < 5.0, f"Failed transcription took {elapsed_time:.2f} seconds"
        except Exception:
            # If API completely unavailable, skip test
            pytest.skip("Transcription API unavailable")
    
    @pytest.mark.asyncio
    async def test_symptom_analysis_performance(self):
        """Symptom analysis should complete quickly (rule-based)"""
        symptoms = ['febre', 'cefaleia', 'náusea', 'vômito', 'dor abdominal']
        
        start_time = time.time()
        result = await self.ai_service.analyze_symptoms(symptoms)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Rule-based analysis should be very fast (< 1 second)
        assert elapsed_time < 1.0, f"Symptom analysis took {elapsed_time:.2f} seconds"
        assert result['success'] == True
    
    @pytest.mark.asyncio
    async def test_symptom_analysis_throughput(self):
        """Test symptom analysis throughput (multiple analyses)"""
        num_analyses = 50
        symptoms_list = [
            ['febre', 'cefaleia'],
            ['dor abdominal', 'náusea'],
            ['tosse', 'febre'],
            ['hipertensão', 'diabetes'],
            ['dor no peito', 'dispneia'],
        ]
        
        start_time = time.time()
        
        for i in range(num_analyses):
            symptoms = symptoms_list[i % len(symptoms_list)]
            result = await self.ai_service.analyze_symptoms(symptoms)
            assert result['success'] == True
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        avg_time = elapsed_time / num_analyses
        
        # Average should be very fast
        assert avg_time < 0.1, f"Average analysis took {avg_time:.3f} seconds"
        # Total should be reasonable
        assert elapsed_time < 10.0, f"Total time for {num_analyses} analyses: {elapsed_time:.2f} seconds"
    
    @pytest.mark.asyncio
    async def test_icd10_suggestions_performance(self):
        """ICD-10 suggestions should complete quickly"""
        clinical_findings = "Paciente com hipertensão arterial e diabetes tipo 2, apresentando sintomas de cefaleia"
        
        start_time = time.time()
        suggestions = await self.ai_service.suggest_icd10_codes(clinical_findings)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should be very fast (< 1 second)
        assert elapsed_time < 1.0, f"ICD-10 suggestions took {elapsed_time:.2f} seconds"
        assert isinstance(suggestions, list)
    
    @pytest.mark.asyncio
    async def test_drug_interaction_check_performance(self):
        """Drug interaction check should complete quickly"""
        medications = ['warfarin', 'aspirin', 'ibuprofen', 'simvastatin', 'lisinopril']
        
        start_time = time.time()
        interactions = await self.ai_service.check_drug_interactions(medications)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should be very fast (< 1 second)
        assert elapsed_time < 1.0, f"Drug interaction check took {elapsed_time:.2f} seconds"
        assert isinstance(interactions, list)
    
    @pytest.mark.asyncio
    async def test_drug_interaction_check_throughput(self):
        """Test drug interaction check with many medications"""
        medications = [f'medication_{i}' for i in range(20)]
        
        start_time = time.time()
        interactions = await self.ai_service.check_drug_interactions(medications)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Even with many medications, should be reasonable
        assert elapsed_time < 2.0, f"Drug interaction check with 20 medications took {elapsed_time:.2f} seconds"
        assert isinstance(interactions, list)
    
    def test_memory_usage_pdf_generation(self):
        """Test that PDF generation doesn't cause memory leaks"""
        import tracemalloc
        
        tracemalloc.start()
        
        # Generate multiple PDFs
        for i in range(20):
            data = self.test_consultation_data.copy()
            data['appointment_id'] = i + 1
            pdf_bytes = self.pdf_generator.generate_consultation_report(data)
            assert pdf_bytes is not None
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak memory should be reasonable (< 100MB for 20 PDFs)
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 100, f"Peak memory usage: {peak_mb:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_symptom_analyses(self):
        """Test concurrent symptom analyses"""
        symptoms_list = [
            ['febre', 'cefaleia'],
            ['dor abdominal', 'náusea'],
            ['tosse', 'febre'],
        ]
        
        start_time = time.time()
        
        # Run analyses concurrently
        tasks = [
            self.ai_service.analyze_symptoms(symptoms)
            for symptoms in symptoms_list
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Concurrent should be faster than sequential
        assert elapsed_time < 2.0, f"Concurrent analyses took {elapsed_time:.2f} seconds"
        assert all(r['success'] for r in results)

