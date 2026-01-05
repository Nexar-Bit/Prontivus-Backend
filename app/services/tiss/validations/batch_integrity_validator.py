"""
Batch Integrity Validator
Validates batch integrity and consistency
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tiss.batch import TISSBatch
from app.models.tiss.consultation import TISSConsultationGuide
from app.models.tiss.sadt import TISSSADTGuide
from app.models.tiss.hospitalization import TISHospitalizationGuide
from app.models.tiss.individual_fee import TISSIndividualFee

logger = logging.getLogger(__name__)


class BatchIntegrityValidator:
    """Validator for batch integrity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_batch_integrity(self, batch_id: int) -> Dict:
        """
        Validate batch integrity
        
        Args:
            batch_id: Batch ID to validate
            
        Returns:
            Dictionary with validation result
        """
        # Get batch
        query = select(TISSBatch).where(TISSBatch.id == batch_id)
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if not batch:
            return {
                'is_valid': False,
                'errors': [f'Batch {batch_id} not found']
            }
        
        errors = []
        warnings = []
        
        # Verify batch hash matches calculated hash
        if batch.hash_integridade:
            calculated_hash = await self._calculate_batch_hash(batch)
            if batch.hash_integridade != calculated_hash:
                errors.append('Batch integrity hash mismatch')
        
        # Verify all guides in batch exist and are valid
        guide_errors = await self._validate_batch_guides(batch)
        errors.extend(guide_errors)
        
        # Verify batch totals match sum of guides
        total_errors = await self._validate_batch_totals(batch)
        errors.extend(total_errors)
        
        # Verify batch structure
        structure_errors = await self._validate_batch_structure(batch)
        warnings.extend(structure_errors)
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'batch_id': batch_id,
            'batch_number': batch.numero_lote
        }
    
    async def _calculate_batch_hash(self, batch: TISSBatch) -> str:
        """Calculate hash for batch integrity"""
        data = {
            'numero_lote': batch.numero_lote,
            'data_envio': batch.data_envio.isoformat() if batch.data_envio else None,
            'guia_consultas': batch.guia_consultas,
            'guia_sadt': batch.guia_sadt,
            'guia_internacoes': batch.guia_internacoes,
            'guia_honorarios': batch.guia_honorarios,
            'valor_total': str(batch.valor_total) if batch.valor_total else None
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def _validate_batch_guides(self, batch: TISSBatch) -> List[str]:
        """Validate all guides in batch exist"""
        errors = []
        
        # Validate consultation guides
        if batch.guia_consultas:
            for guide_id in batch.guia_consultas:
                query = select(TISSConsultationGuide).where(TISSConsultationGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if not guide:
                    errors.append(f'Consultation guide {guide_id} not found')
        
        # Validate SADT guides
        if batch.guia_sadt:
            for guide_id in batch.guia_sadt:
                query = select(TISSSADTGuide).where(TISSSADTGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if not guide:
                    errors.append(f'SADT guide {guide_id} not found')
        
        # Validate hospitalization guides
        if batch.guia_internacoes:
            for guide_id in batch.guia_internacoes:
                query = select(TISHospitalizationGuide).where(TISHospitalizationGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if not guide:
                    errors.append(f'Hospitalization guide {guide_id} not found')
        
        # Validate individual fee guides
        if batch.guia_honorarios:
            for guide_id in batch.guia_honorarios:
                query = select(TISSIndividualFee).where(TISSIndividualFee.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if not guide:
                    errors.append(f'Individual fee guide {guide_id} not found')
        
        return errors
    
    async def _validate_batch_totals(self, batch: TISSBatch) -> List[str]:
        """Validate batch totals match sum of guides"""
        errors = []
        
        # Calculate total from guides
        calculated_total = 0
        
        # Sum consultation guides
        if batch.guia_consultas:
            for guide_id in batch.guia_consultas:
                query = select(TISSConsultationGuide).where(TISSConsultationGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if guide and guide.valor_total:
                    calculated_total += float(guide.valor_total)
        
        # Sum SADT guides
        if batch.guia_sadt:
            for guide_id in batch.guia_sadt:
                query = select(TISSSADTGuide).where(TISSSADTGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if guide and guide.valor_total:
                    calculated_total += float(guide.valor_total)
        
        # Sum hospitalization guides
        if batch.guia_internacoes:
            for guide_id in batch.guia_internacoes:
                query = select(TISHospitalizationGuide).where(TISHospitalizationGuide.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if guide and guide.valor_total:
                    calculated_total += float(guide.valor_total)
        
        # Sum individual fee guides
        if batch.guia_honorarios:
            for guide_id in batch.guia_honorarios:
                query = select(TISSIndividualFee).where(TISSIndividualFee.id == guide_id)
                result = await self.db.execute(query)
                guide = result.scalar_one_or_none()
                if guide and guide.valor_total:
                    calculated_total += float(guide.valor_total)
        
        # Compare with batch total (allow small floating point differences)
        if batch.valor_total:
            batch_total = float(batch.valor_total)
            if abs(calculated_total - batch_total) > 0.01:
                errors.append(f'Batch total mismatch: expected {batch_total}, calculated {calculated_total}')
        
        return errors
    
    async def _validate_batch_structure(self, batch: TISSBatch) -> List[str]:
        """Validate batch structure"""
        warnings = []
        
        # Check if batch has at least one guide
        total_guides = (
            len(batch.guia_consultas or []) +
            len(batch.guia_sadt or []) +
            len(batch.guia_internacoes or []) +
            len(batch.guia_honorarios or [])
        )
        
        if total_guides == 0:
            warnings.append('Batch has no guides')
        
        # Check if batch number is valid
        if not batch.numero_lote or len(batch.numero_lote) < 3:
            warnings.append('Batch number seems invalid')
        
        return warnings

