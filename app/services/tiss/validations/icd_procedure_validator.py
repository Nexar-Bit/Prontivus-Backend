"""
ICD x Procedure Validator
Validates compatibility between ICD codes and procedures
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.tiss.tuss_service import TUSSService

logger = logging.getLogger(__name__)


class ICDProcedureValidator:
    """Validator for ICD-10 code and procedure compatibility"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tuss_service = TUSSService(db)
    
    async def validate_icd_procedure_compatibility(
        self, 
        icd_code: str, 
        procedure_code: str,
        procedure_table: str = "06"
    ) -> Dict:
        """
        Validate if an ICD code is compatible with a procedure code
        
        Args:
            icd_code: ICD-10 code
            procedure_code: TUSS procedure code
            procedure_table: TUSS table code (default: 06 for SADT)
            
        Returns:
            Dictionary with validation result
        """
        errors = []
        warnings = []
        
        # Verify ICD code exists (try to import ICD10Code dynamically)
        try:
            from app.models.icd10 import ICD10Code
            icd_query = select(ICD10Code).where(ICD10Code.code == icd_code)
            icd_result = await self.db.execute(icd_query)
            icd = icd_result.scalar_one_or_none()
            
            if not icd:
                errors.append(f"ICD-10 code {icd_code} not found")
            else:
                # Check if ICD is valid (not deleted)
                if hasattr(icd, 'deleted') and icd.deleted:
                    warnings.append(f"ICD-10 code {icd_code} is marked as deleted")
        except ImportError:
            # ICD10 model not available, skip validation
            warnings.append(f"ICD-10 validation not available (model not found)")
            icd = None
        
        # Verify procedure code exists
        tuss_validation = await self.tuss_service.validate_tuss_code(procedure_code, procedure_table)
        if not tuss_validation["is_valid"]:
            errors.append(f"Procedure code {procedure_code} not found in table {procedure_table}")
        
        # Basic compatibility checks
        if icd and tuss_validation["is_valid"]:
            # Check if ICD is valid (not deleted)
            if icd.deleted:
                warnings.append(f"ICD-10 code {icd_code} is marked as deleted")
            
            # Additional compatibility rules can be added here
            # For example, checking procedure category against ICD category
            # This would require additional data or rules
        
        return {
            'is_compatible': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'icd_code': icd_code,
            'procedure_code': procedure_code
        }
    
    async def validate_guide_icd_procedures(self, guide_data: Dict) -> Dict:
        """
        Validate all ICD-procedure combinations in a guide
        
        Args:
            guide_data: Guide data dictionary with procedures and diagnoses
            
        Returns:
            Dictionary with validation results for all combinations
        """
        procedures = guide_data.get('procedimentos', []) or guide_data.get('procedimentos_executados', [])
        diagnoses = guide_data.get('diagnosticos', []) or guide_data.get('diagnosticos_principal', [])
        
        if not procedures:
            return {
                'is_valid': False,
                'errors': ['No procedures found in guide'],
                'validations': []
            }
        
        if not diagnoses:
            return {
                'is_valid': False,
                'errors': ['No diagnoses found in guide'],
                'validations': []
            }
        
        validations = []
        all_errors = []
        
        # Validate each procedure against each diagnosis
        for proc in procedures:
            proc_code = proc.get('codigo_procedimento')
            proc_table = proc.get('codigo_tabela', '06')
            
            for diag in diagnoses:
                icd_code = diag.get('codigo') or diag.get('codigo_diagnostico')
                
                if proc_code and icd_code:
                    validation = await self.validate_icd_procedure_compatibility(
                        icd_code, 
                        proc_code,
                        proc_table
                    )
                    validations.append({
                        'procedure_code': proc_code,
                        'icd_code': icd_code,
                        'validation': validation
                    })
                    
                    if not validation['is_compatible']:
                        all_errors.extend(validation['errors'])
        
        return {
            'is_valid': len(all_errors) == 0,
            'errors': all_errors,
            'validations': validations
        }

