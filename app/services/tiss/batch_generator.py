"""
Batch Generator Service
Creates and manages TISS batches (lotes)
"""

import logging
from typing import List, Dict, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import json

from app.models.tiss.batch import TISSBatch
from app.models.tiss.consultation import TISSConsultationGuide
from app.models.tiss.sadt import TISSSADTGuide
from app.models.tiss.hospitalization import TISHospitalizationGuide
from app.models.tiss.individual_fee import TISSIndividualFee
from app.services.tiss.versioning import TISSVersioningService

logger = logging.getLogger(__name__)


class BatchGeneratorService:
    """Service for generating TISS batches"""
    
    MAX_GUIAS_PER_LOTE = 1000
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.versioning = TISSVersioningService(db)
    
    async def create_batch(
        self,
        clinic_id: int,
        guide_ids: List[int],
        guide_type: str
    ) -> TISSBatch:
        """
        Create a new batch from guide IDs
        
        Args:
            clinic_id: Clinic ID
            guide_ids: List of guide IDs
            guide_type: Type of guides ('consultation', 'sadt', 'hospitalization', 'individual_fee')
        
        Returns:
            Created TISSBatch
        """
        if len(guide_ids) > self.MAX_GUIAS_PER_LOTE:
            raise ValueError(f"Maximum {self.MAX_GUIAS_PER_LOTE} guides per batch")
        
        # Validate all guides exist and belong to clinic
        guides = await self._validate_guides(clinic_id, guide_ids, guide_type)
        
        # Calculate total value
        valor_total = sum(Decimal(str(g.valor_total)) for g in guides)
        
        # Generate batch number
        numero_lote = await self._generate_batch_number(clinic_id)
        
        # Get current TISS version
        versao_tiss = await self.versioning.get_current_version()
        
        # Create batch
        batch = TISSBatch(
            clinic_id=clinic_id,
            numero_lote=numero_lote,
            data_envio=date.today(),
            hora_envio=datetime.now().strftime('%H:%M'),
            guias_ids=guide_ids,
            guias_tipo=guide_type,
            valor_total_lote=valor_total,
            versao_tiss=versao_tiss,
            submission_status='pending'
        )
        
        self.db.add(batch)
        await self.db.flush()
        
        # Calculate integrity hash
        batch.hash_integridade = await self._calculate_batch_hash(batch, guides)
        
        await self.db.commit()
        await self.db.refresh(batch)
        
        logger.info(f"Created batch {batch.id} with {len(guide_ids)} guides")
        return batch
    
    async def generate_batch_xml(self, batch_id: int) -> str:
        """
        Generate XML for a batch
        
        Args:
            batch_id: Batch ID
        
        Returns:
            XML string
        """
        query = select(TISSBatch).where(TISSBatch.id == batch_id)
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Get guides
        guides = await self._get_batch_guides(batch)
        
        # Generate XML (simplified - full implementation would use proper TISS XML structure)
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas">',
            '    <ans:cabecalho>',
            f'        <ans:versaoPadrao>{batch.versao_tiss}</ans:versaoPadrao>',
            '    </ans:cabecalho>',
            '    <ans:prestadorParaOperadora>',
            '        <ans:loteGuias>',
            f'            <ans:numeroLoteGuia>{batch.numero_lote}</ans:numeroLoteGuia>',
            '            <ans:guiasTISS>',
        ]
        
        # Add guide XMLs (simplified)
        for guide in guides:
            if hasattr(guide, 'xml_content') and guide.xml_content:
                xml_parts.append(guide.xml_content)
        
        xml_parts.extend([
            '            </ans:guiasTISS>',
            '        </ans:loteGuias>',
            '    </ans:prestadorParaOperadora>',
            '</ans:mensagemTISS>'
        ])
        
        xml_content = '\n'.join(xml_parts)
        
        # Update batch
        batch.xml_content = xml_content
        batch.hash_integridade = await self._calculate_batch_hash(batch, guides)
        await self.db.commit()
        
        return xml_content
    
    async def _validate_guides(
        self,
        clinic_id: int,
        guide_ids: List[int],
        guide_type: str
    ) -> List:
        """Validate guides exist and belong to clinic"""
        guides = []
        
        for guide_id in guide_ids:
            if guide_type == 'consultation':
                query = select(TISSConsultationGuide).where(
                    TISSConsultationGuide.id == guide_id,
                    TISSConsultationGuide.clinic_id == clinic_id
                )
            elif guide_type == 'sadt':
                query = select(TISSSADTGuide).where(
                    TISSSADTGuide.id == guide_id,
                    TISSSADTGuide.clinic_id == clinic_id
                )
            elif guide_type == 'hospitalization':
                query = select(TISHospitalizationGuide).where(
                    TISHospitalizationGuide.id == guide_id,
                    TISHospitalizationGuide.clinic_id == clinic_id
                )
            elif guide_type == 'individual_fee':
                query = select(TISSIndividualFee).where(
                    TISSIndividualFee.id == guide_id,
                    TISSIndividualFee.clinic_id == clinic_id
                )
            else:
                raise ValueError(f"Invalid guide type: {guide_type}")
            
            result = await self.db.execute(query)
            guide = result.scalar_one_or_none()
            
            if not guide:
                raise ValueError(f"Guide {guide_id} not found or doesn't belong to clinic")
            
            if guide.is_locked:
                raise ValueError(f"Guide {guide_id} is locked and cannot be added to batch")
            
            guides.append(guide)
        
        return guides
    
    async def _get_batch_guides(self, batch: TISSBatch) -> List:
        """Get all guides in a batch"""
        return await self._validate_guides(batch.clinic_id, batch.guias_ids, batch.guias_tipo)
    
    async def _generate_batch_number(self, clinic_id: int) -> str:
        """Generate unique batch number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"LOTE{clinic_id}{timestamp}"
    
    async def _calculate_batch_hash(self, batch: TISSBatch, guides: List) -> str:
        """Calculate SHA-256 hash for batch integrity"""
        data = {
            "numero_lote": batch.numero_lote,
            "data_envio": batch.data_envio.isoformat(),
            "guias_ids": batch.guias_ids,
            "valor_total": str(batch.valor_total_lote)
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

