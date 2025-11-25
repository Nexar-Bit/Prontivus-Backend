"""
Tests for AI Clinical Diagnosis Service
"""
import pytest
from app.services.clinical_ai import ClinicalAIService, clinical_ai


@pytest.mark.unit
class TestAIDiagnosis:
    """Test suite for AI diagnosis functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.ai_service = ClinicalAIService()
    
    def test_service_initialization(self):
        """Test that service initializes correctly"""
        assert self.ai_service is not None
        assert len(self.ai_service.icd10_codes) > 0
        assert len(self.ai_service.drug_interactions) > 0
        assert len(self.ai_service.symptom_database) > 0
    
    def test_icd10_codes_loaded(self):
        """Test that ICD-10 codes are loaded"""
        codes = self.ai_service.icd10_codes
        assert isinstance(codes, dict)
        assert len(codes) > 0
        
        # Check for common codes
        assert 'I10' in codes  # Hipertensão
        assert 'E11' in codes  # Diabetes tipo 2
        assert 'J06' in codes  # Infecções respiratórias
    
    def test_symptom_database_loaded(self):
        """Test that symptom database is loaded"""
        symptoms = self.ai_service.symptom_database
        assert isinstance(symptoms, dict)
        assert len(symptoms) > 0
        
        # Check for common symptoms
        assert 'febre' in symptoms
        assert 'cefaleia' in symptoms
        assert 'dor abdominal' in symptoms
    
    def test_drug_interactions_loaded(self):
        """Test that drug interactions are loaded"""
        interactions = self.ai_service.drug_interactions
        assert isinstance(interactions, dict)
        assert len(interactions) > 0
        
        # Check for common medications
        assert 'warfarin' in interactions
        assert 'aspirin' in interactions
    
    @pytest.mark.asyncio
    async def test_symptom_analysis(self):
        """Test symptom analysis returns differential diagnoses"""
        symptoms = ['febre', 'cefaleia']
        
        result = await self.ai_service.analyze_symptoms(symptoms)
        
        assert result['success'] == True
        assert 'differential_diagnoses' in result
        assert isinstance(result['differential_diagnoses'], list)
        assert len(result['differential_diagnoses']) > 0
        
        # Check diagnosis structure
        diagnosis = result['differential_diagnoses'][0]
        assert 'icd10_code' in diagnosis
        assert 'description' in diagnosis
        assert 'confidence' in diagnosis
        assert 'supporting_symptoms' in diagnosis
        assert 'recommended_tests' in diagnosis
        
        # Verify confidence is a valid float
        assert isinstance(diagnosis['confidence'], float)
        assert 0.0 <= diagnosis['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_symptom_analysis_with_patient_data(self):
        """Test symptom analysis with patient data"""
        symptoms = ['febre', 'tosse']
        patient_data = {
            'age': 45,
            'gender': 'M',
            'medical_history': ['hipertensão']
        }
        
        result = await self.ai_service.analyze_symptoms(symptoms, patient_data)
        
        assert result['success'] == True
        assert result['patient_data_used'] == True
        assert 'differential_diagnoses' in result
    
    @pytest.mark.asyncio
    async def test_symptom_analysis_empty_list(self):
        """Test symptom analysis with empty symptoms list"""
        result = await self.ai_service.analyze_symptoms([])
        
        assert result['success'] == True
        assert len(result['differential_diagnoses']) == 0
    
    @pytest.mark.asyncio
    async def test_icd10_suggestions(self):
        """Test ICD-10 code suggestions"""
        clinical_findings = "Paciente com hipertensão arterial e diabetes tipo 2"
        
        suggestions = await self.ai_service.suggest_icd10_codes(clinical_findings)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Check suggestion structure
        suggestion = suggestions[0]
        assert 'code' in suggestion
        assert 'description' in suggestion
        assert 'match_score' in suggestion
        assert 'category' in suggestion
        
        # Verify match score is valid
        assert isinstance(suggestion['match_score'], float)
        assert 0.0 <= suggestion['match_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_icd10_suggestions_empty_findings(self):
        """Test ICD-10 suggestions with empty findings"""
        suggestions = await self.ai_service.suggest_icd10_codes("")
        
        assert isinstance(suggestions, list)
        # May return empty list or some default suggestions
    
    @pytest.mark.asyncio
    async def test_drug_interaction_check(self):
        """Test drug interaction detection"""
        medications = ['warfarin', 'aspirin']
        
        interactions = await self.ai_service.check_drug_interactions(medications)
        
        assert isinstance(interactions, list)
        assert len(interactions) > 0
        
        # Check interaction structure
        interaction = interactions[0]
        assert 'drug1' in interaction
        assert 'drug2' in interaction
        assert 'severity' in interaction
        assert 'description' in interaction
        assert 'recommendation' in interaction
        
        # Verify severity is valid
        assert interaction['severity'] in ['mild', 'moderate', 'severe']
    
    @pytest.mark.asyncio
    async def test_drug_interaction_check_no_interactions(self):
        """Test drug interaction check with medications that don't interact"""
        medications = ['paracetamol', 'vitamin_c']
        
        interactions = await self.ai_service.check_drug_interactions(medications)
        
        # Should return empty list or no interactions
        assert isinstance(interactions, list)
    
    @pytest.mark.asyncio
    async def test_drug_interaction_check_single_medication(self):
        """Test drug interaction check with single medication"""
        medications = ['warfarin']
        
        interactions = await self.ai_service.check_drug_interactions(medications)
        
        # Should return empty list (need at least 2 medications)
        assert isinstance(interactions, list)
        assert len(interactions) == 0
    
    def test_suggest_tests(self):
        """Test test suggestions based on ICD-10 code"""
        tests = self.ai_service._suggest_tests('I10')
        
        assert isinstance(tests, list)
        assert len(tests) > 0
        assert all(isinstance(test, str) for test in tests)
    
    def test_get_code_category(self):
        """Test ICD-10 code category retrieval"""
        category = self.ai_service._get_code_category('I10')
        
        assert isinstance(category, str)
        assert len(category) > 0
        assert 'circulatório' in category.lower() or 'circulatorio' in category.lower()
    
    def test_get_interaction_severity(self):
        """Test interaction severity determination"""
        severity = self.ai_service._get_interaction_severity('warfarin', 'aspirin')
        
        assert severity in ['mild', 'moderate', 'severe']
        # Warfarin + Aspirin should be severe
        assert severity == 'severe'
    
    def test_get_interaction_recommendation(self):
        """Test interaction recommendation retrieval"""
        recommendation = self.ai_service._get_interaction_recommendation('severe')
        
        assert isinstance(recommendation, str)
        assert len(recommendation) > 0
        assert 'ATENÇÃO' in recommendation or 'atenção' in recommendation.lower()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_symptom_analysis_performance(self):
        """Test that symptom analysis completes quickly"""
        import time
        
        symptoms = ['febre', 'cefaleia', 'náusea', 'vômito']
        
        start_time = time.time()
        result = await self.ai_service.analyze_symptoms(symptoms)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Analysis should complete within 1 second (rule-based)
        assert elapsed_time < 1.0, f"Analysis took {elapsed_time:.2f} seconds"
        assert result['success'] == True

