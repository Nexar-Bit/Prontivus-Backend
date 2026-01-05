"""
TISS Hospitalization Form Service
Handles hospitalization guide form creation, validation, and XML generation
"""

import logging
from typing import Dict, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import json

from app.models.tiss.hospitalization import TISHospitalizationGuide
from app.models.tiss.audit_log import TISSAuditLog
from app.models import Invoice, Clinic, User
from app.services.tiss.versioning import TISSVersioningService
from app.services.tiss.tuss_service import TUSSService

logger = logging.getLogger(__name__)


class HospitalizationFormService:
    """Service for managing hospitalization guides"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.versioning = TISSVersioningService(db)
        self.tuss_service = TUSSService(db)
    
    async def create_hospitalization_guide(
        self,
        invoice_id: int,
        clinic_id: int,
        user_id: int,
        guide_data: Dict
    ) -> TISHospitalizationGuide:
        """Create a new hospitalization guide"""
        from app.models import Invoice
        invoice_query = select(Invoice).where(Invoice.id == invoice_id)
        invoice_result = await self.db.execute(invoice_query)
        invoice = invoice_result.scalar_one_or_none()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        numero_guia = await self._generate_guide_number(clinic_id)
        versao_tiss = await self.versioning.get_current_version()
        
        guide = TISHospitalizationGuide(
            clinic_id=clinic_id,
            invoice_id=invoice_id,
            appointment_id=invoice.appointment_id,
            numero_guia=numero_guia,
            data_emissao=date.today(),
            prestador_data=guide_data.get("prestador", {}),
            operadora_data=guide_data.get("operadora", {}),
            beneficiario_data=guide_data.get("beneficiario", {}),
            contratado_data=guide_data.get("contratado", {}),
            internacao_data=guide_data.get("internacao", {}),
            valor_total=Decimal(str(guide_data.get("valor_total", 0))),
            status='draft',
            versao_tiss=versao_tiss
        )
        
        self.db.add(guide)
        await self.db.flush()
        guide.hash_integridade = await self._calculate_integrity_hash(guide)
        
        await self._create_audit_log(
            clinic_id=clinic_id,
            user_id=user_id,
            action='create',
            entity_type='hospitalization_guide',
            entity_id=guide.id
        )
        
        await self.db.commit()
        await self.db.refresh(guide)
        
        logger.info(f"Created hospitalization guide {guide.id} for invoice {invoice_id}")
        return guide
    
    async def validate_hospitalization_guide(self, guide_id: int) -> Dict[str, any]:
        """Validate a hospitalization guide"""
        query = select(TISHospitalizationGuide).where(TISHospitalizationGuide.id == guide_id)
        result = await self.db.execute(query)
        guide = result.scalar_one_or_none()
        
        if not guide:
            return {"is_valid": False, "errors": [f"Guide {guide_id} not found"]}
        
        errors = []
        
        if not guide.prestador_data.get("cnpj"):
            errors.append("Prestador CNPJ is required")
        if not guide.operadora_data.get("registro_ans"):
            errors.append("Operadora Registro ANS is required")
        if not guide.beneficiario_data.get("numero_carteira"):
            errors.append("Beneficiário número da carteira is required")
        
        # Validate hospitalization data
        internacao = guide.internacao_data
        if not internacao.get("data_internacao"):
            errors.append("Data de internação is required")
        if not internacao.get("data_alta"):
            errors.append("Data de alta is required")
        
        if guide.valor_total <= 0:
            errors.append("Valor total must be greater than zero")
        
        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": []}
    
    async def generate_xml(self, guide_id: int) -> str:
        """Generate XML for a hospitalization guide"""
        query = select(TISHospitalizationGuide).where(TISHospitalizationGuide.id == guide_id)
        result = await self.db.execute(query)
        guide = result.scalar_one_or_none()
        
        if not guide:
            raise ValueError(f"Guide {guide_id} not found")
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas">
    <ans:cabecalho>
        <ans:versaoPadrao>{guide.versao_tiss}</ans:versaoPadrao>
    </ans:cabecalho>
    <ans:prestadorParaOperadora>
        <ans:loteGuias>
            <ans:numeroLoteGuia>{guide.numero_guia}</ans:numeroLoteGuia>
            <ans:guiasTISS>
                <ans:guiaInternacao>
                    <!-- XML content will be generated here -->
                </ans:guiaInternacao>
            </ans:guiasTISS>
        </ans:loteGuias>
    </ans:prestadorParaOperadora>
</ans:mensagemTISS>"""
        
        guide.xml_content = xml_content
        guide.hash_integridade = await self._calculate_integrity_hash(guide)
        await self.db.commit()
        
        return xml_content
    
    async def lock_guide(self, guide_id: int, user_id: int):
        """Lock guide to prevent editing after submission"""
        query = select(TISHospitalizationGuide).where(TISHospitalizationGuide.id == guide_id)
        result = await self.db.execute(query)
        guide = result.scalar_one_or_none()
        
        if guide:
            guide.is_locked = True
            guide.submitted_at = datetime.now()
            await self._create_audit_log(
                clinic_id=guide.clinic_id,
                user_id=user_id,
                action='lock',
                entity_type='hospitalization_guide',
                entity_id=guide_id
            )
            await self.db.commit()
    
    async def _generate_guide_number(self, clinic_id: int) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{clinic_id}{timestamp}"
    
    async def _calculate_integrity_hash(self, guide: TISHospitalizationGuide) -> str:
        data = {
            "numero_guia": guide.numero_guia,
            "data_emissao": guide.data_emissao.isoformat(),
            "prestador": guide.prestador_data,
            "operadora": guide.operadora_data,
            "beneficiario": guide.beneficiario_data,
            "contratado": guide.contratado_data,
            "internacao": guide.internacao_data,
            "valor_total": str(guide.valor_total)
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def _create_audit_log(
        self,
        clinic_id: int,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        changes: Optional[Dict] = None
    ):
        log = TISSAuditLog(
            clinic_id=clinic_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes
        )
        self.db.add(log)


