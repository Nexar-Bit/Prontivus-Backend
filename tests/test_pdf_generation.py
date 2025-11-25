"""
Tests for PDF Generation Service
"""
import pytest
import os
import tempfile
from pathlib import Path
from app.services.pdf_generator import PDFGenerator


@pytest.mark.unit
class TestPDFGeneration:
    """Test suite for PDF generation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pdf_generator = PDFGenerator()
        self.test_consultation_data = {
            'appointment_id': 1,
            'scheduled_datetime': '15/01/2024 10:00',
            'appointment_type': 'Consulta',
            'reason': 'Dor de cabeça',
            'notes': 'Paciente relata dor de cabeça há 3 dias',
            'patient': {
                'id': 1,
                'name': 'João Silva',
                'date_of_birth': '15/05/1989',
                'gender': 'Masculino',
                'cpf': '123.456.789-00',
                'address': 'Rua Teste, 123',
                'phone': '(11) 99999-9999',
                'email': 'joao@teste.com'
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
                'logo_path': 'public/Logo/Prontivus Horizontal Transparents.png'
            },
            'clinical_record': {
                'subjective': 'Paciente relata dor de cabeça há 3 dias',
                'objective': 'PA: 120/80 mmHg, FC: 72 bpm',
                'assessment': 'Hipótese diagnóstica: Cefaleia tensional',
                'plan': 'Prescrição de analgésico e orientações',
                'prescriptions': [
                    {
                        'medication_name': 'Paracetamol',
                        'dosage': '500mg',
                        'frequency': '8/8h',
                        'duration': '5 dias',
                        'instructions': 'Tomar após as refeições'
                    }
                ],
                'exam_requests': [],
                'diagnoses': []
            }
        }
    
    def test_consultation_report_generation(self):
        """Test consultation report PDF generation"""
        # Generate PDF
        pdf_bytes = self.pdf_generator.generate_consultation_report(self.test_consultation_data)
        
        # Verify PDF was generated
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        
        # Verify PDF header (PDF files start with %PDF)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_consultation_report_content(self):
        """Test that consultation report contains expected content"""
        pdf_bytes = self.pdf_generator.generate_consultation_report(self.test_consultation_data)
        
        # Convert to string to check content (basic check)
        pdf_str = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Check for patient name
        assert 'João Silva' in pdf_str or 'Joao Silva' in pdf_str
        # Check for doctor name
        assert 'Maria Santos' in pdf_str
        # Check for clinic name
        assert 'Prontivus' in pdf_str or 'prontivus' in pdf_str
    
    def test_prescription_generation(self):
        """Test prescription PDF generation"""
        prescription_data = {
            'clinic': {
                'name': 'Clínica Prontivus',
                'address': 'Rua Teste, 123',
                'phone': '(11) 3333-3333',
                'email': 'contato@prontivus.com'
            },
            'patient': {
                'name': 'João Silva',
                'id': 1
            },
            'doctor': {
                'name': 'Dr. Maria Santos',
                'crm': 'CRM-SP 123456'
            },
            'medications': [
                {
                    'name': 'Paracetamol',
                    'dosage': '500mg',
                    'frequency': '8/8h',
                    'duration': '5 dias',
                    'notes': 'Tomar após as refeições'
                }
            ],
            'issued_date': '15/01/2024 10:00'
        }
        
        pdf_bytes = self.pdf_generator.generate_prescription(prescription_data)
        
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_prescription_content(self):
        """Test that prescription contains medication information"""
        prescription_data = {
            'clinic': {'name': 'Clínica Prontivus', 'address': '', 'phone': '', 'email': ''},
            'patient': {'name': 'João Silva', 'id': 1},
            'doctor': {'name': 'Dr. Maria Santos', 'crm': 'CRM-SP 123456'},
            'medications': [
                {
                    'name': 'Paracetamol',
                    'dosage': '500mg',
                    'frequency': '8/8h',
                    'duration': '5 dias',
                    'notes': 'Tomar após as refeições'
                }
            ],
            'issued_date': '15/01/2024 10:00'
        }
        
        pdf_bytes = self.pdf_generator.generate_prescription(prescription_data)
        pdf_str = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Check for medication name
        assert 'Paracetamol' in pdf_str or 'paracetamol' in pdf_str
    
    def test_medical_certificate_generation(self):
        """Test medical certificate PDF generation"""
        certificate_data = {
            'clinic': {
                'name': 'Clínica Prontivus',
                'address': 'Rua Teste, 123',
                'phone': '(11) 3333-3333',
                'email': 'contato@prontivus.com'
            },
            'patient': {
                'name': 'João Silva',
                'document': '123.456.789-00'
            },
            'doctor': {
                'name': 'Dr. Maria Santos',
                'crm': 'CRM-SP 123456'
            },
            'justification': 'Paciente necessita de repouso médico',
            'validity_days': 7
        }
        
        pdf_bytes = self.pdf_generator.generate_medical_certificate(certificate_data)
        
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_pdf_generation_with_empty_data(self):
        """Test PDF generation handles empty data gracefully"""
        empty_data = {
            'patient': {'name': ''},
            'doctor': {'name': ''},
            'clinic': {'name': ''}
        }
        
        # Should not raise exception, but may generate minimal PDF
        try:
            pdf_bytes = self.pdf_generator.generate_consultation_report(empty_data)
            assert pdf_bytes is not None
        except Exception as e:
            # If it raises, should be a meaningful error
            assert 'patient' in str(e).lower() or 'data' in str(e).lower()
    
    @pytest.mark.performance
    def test_pdf_generation_performance(self):
        """Test that PDF generation completes within acceptable time"""
        import time
        
        start_time = time.time()
        pdf_bytes = self.pdf_generator.generate_consultation_report(self.test_consultation_data)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # PDF generation should complete within 5 seconds
        assert elapsed_time < 5.0, f"PDF generation took {elapsed_time:.2f} seconds, expected < 5.0"
        assert pdf_bytes is not None

