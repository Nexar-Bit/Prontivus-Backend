"""
TISS Pre-Authorization API Endpoints
Endpoints para validação, geração e envio de Guias de Solicitação de Autorização TISS
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from database import get_async_session
from app.models import User, Appointment, Patient
from app.core.auth import get_current_user, RoleChecker, UserRole
from app.models.tiss.preauth_guide import (
    TISSPreAuthGuide,
    PreAuthGuideStatus,
    PreAuthGuideSubmissionStatus,
)
from app.models.tiss.insurance_structure import InsurancePlanTISS
from app.services.tiss.preauth_validation_service import PreAuthValidationService
from app.services.tiss.preauth_guide_service import PreAuthGuideService

router = APIRouter(prefix="/tiss/preauth", tags=["TISS Pre-Authorization"])

require_admin = RoleChecker([UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR])


# ==================== Pre-Authorization Validation ====================

class PreAuthValidationRequest(BaseModel):
    tuss_code: str = Field(..., description="Código TUSS do procedimento")
    tabela: Optional[str] = Field(None, description="Tabela TUSS (01, 02, 03, etc.)")
    insurance_plan_id: int = Field(..., description="ID do plano de saúde")
    appointment_date: Optional[date] = Field(None, description="Data prevista do procedimento")


class PreAuthValidationResponse(BaseModel):
    requires_preauth: bool
    coverage: Optional[dict] = None
    tuss_code_id: Optional[int] = None
    insurance_plan_id: int
    coverage_id: Optional[int] = None
    message: str
    source: Optional[str] = None
    error: Optional[str] = None


@router.post("/validate", response_model=PreAuthValidationResponse)
async def validate_preauth(
    validation_data: PreAuthValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Validar se um procedimento requer pré-autorização"""
    service = PreAuthValidationService(db)
    
    result = await service.check_requires_preauth(
        tuss_code=validation_data.tuss_code,
        tabela=validation_data.tabela,
        insurance_plan_id=validation_data.insurance_plan_id,
        clinic_id=current_user.clinic_id,
        appointment_date=validation_data.appointment_date
    )
    
    return PreAuthValidationResponse(**result)


@router.post("/appointments/{appointment_id}/validate")
async def validate_appointment_preauth(
    appointment_id: int,
    tuss_code: Optional[str] = Query(None),
    tabela: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Validar pré-autorização para um agendamento específico"""
    service = PreAuthValidationService(db)
    
    result = await service.validate_appointment_preauth(
        appointment_id=appointment_id,
        tuss_code=tuss_code,
        tabela=tabela
    )
    
    # Se requer pré-autorização, atualizar status do agendamento
    if result.get('requires_preauth'):
        appointment_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.id == appointment_id,
                    Appointment.clinic_id == current_user.clinic_id
                )
            )
        )
        appointment = appointment_result.scalar_one_or_none()
        
        if appointment:
            # Manter status como SCHEDULED mas adicionar flag de pré-autorização pendente
            # Ou criar um novo status PENDING_PREAUTH se necessário
            # Por enquanto, apenas retornar a informação
            pass
    
    return result


# ==================== Pre-Authorization Guide ====================

class PreAuthGuideCreate(BaseModel):
    appointment_id: Optional[int] = None
    patient_id: int
    insurance_plan_id: int
    tuss_code: str
    tabela_tuss: str
    tuss_descricao: str
    valor_solicitado: Decimal
    data_prevista_procedimento: date
    observacoes: Optional[str] = None
    dados_adicionais: Optional[dict] = None


class PreAuthGuideResponse(BaseModel):
    id: int
    numero_guia: str
    numero_guia_operadora: Optional[str]
    appointment_id: Optional[int]
    patient_id: int
    insurance_plan_id: Optional[int]
    tuss_code: str
    tuss_descricao: str
    valor_solicitado: Decimal
    valor_aprovado: Optional[Decimal]
    status: str
    submission_status: str
    data_solicitacao: date
    data_prevista_procedimento: date
    data_resposta: Optional[date]
    data_validade: Optional[date]
    metodo_envio: Optional[str]
    protocolo_operadora: Optional[str]
    motivo_negacao: Optional[str]
    tentativas_envio: int
    created_at: datetime
    patient_nome: Optional[str] = None
    plan_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/guides", response_model=List[PreAuthGuideResponse])
async def list_preauth_guides(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    appointment_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    status: Optional[PreAuthGuideStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Listar guias de solicitação de autorização"""
    query = select(TISSPreAuthGuide).where(
        TISSPreAuthGuide.clinic_id == current_user.clinic_id
    )
    
    if appointment_id:
        query = query.where(TISSPreAuthGuide.appointment_id == appointment_id)
    
    if patient_id:
        query = query.where(TISSPreAuthGuide.patient_id == patient_id)
    
    if status:
        query = query.where(TISSPreAuthGuide.status == status)
    
    query = query.order_by(TISSPreAuthGuide.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(
        query.options(
            joinedload(TISSPreAuthGuide.patient),
            joinedload(TISSPreAuthGuide.insurance_plan)
        )
    )
    guides = result.scalars().all()
    
    guides_with_info = []
    for guide in guides:
        guide_dict = PreAuthGuideResponse.model_validate(guide)
        if guide.patient:
            guide_dict.patient_nome = guide.patient.full_name
        if guide.insurance_plan:
            guide_dict.plan_nome = guide.insurance_plan.nome_plano
        guides_with_info.append(guide_dict)
    
    return guides_with_info


@router.get("/guides/{guide_id}", response_model=PreAuthGuideResponse)
async def get_preauth_guide(
    guide_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Obter detalhes de uma guia de solicitação"""
    result = await db.execute(
        select(TISSPreAuthGuide)
        .where(
            and_(
                TISSPreAuthGuide.id == guide_id,
                TISSPreAuthGuide.clinic_id == current_user.clinic_id
            )
        )
        .options(
            joinedload(TISSPreAuthGuide.patient),
            joinedload(TISSPreAuthGuide.insurance_plan)
        )
    )
    guide = result.scalar_one_or_none()
    
    if not guide:
        raise HTTPException(status_code=404, detail="Guia não encontrada")
    
    guide_dict = PreAuthGuideResponse.model_validate(guide)
    if guide.patient:
        guide_dict.patient_nome = guide.patient.full_name
    if guide.insurance_plan:
        guide_dict.plan_nome = guide.insurance_plan.nome_plano
    
    return guide_dict


@router.post("/guides", response_model=PreAuthGuideResponse, status_code=status.HTTP_201_CREATED)
async def create_preauth_guide(
    guide_data: PreAuthGuideCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Criar nova guia de solicitação de autorização"""
    service = PreAuthGuideService(db)
    
    guide = await service.create_preauth_guide(
        clinic_id=current_user.clinic_id,
        created_by=current_user.id,
        **guide_data.model_dump()
    )
    
    await db.commit()
    await db.refresh(guide, ["patient", "insurance_plan"])
    
    guide_dict = PreAuthGuideResponse.model_validate(guide)
    if guide.patient:
        guide_dict.patient_nome = guide.patient.full_name
    if guide.insurance_plan:
        guide_dict.plan_nome = guide.insurance_plan.nome_plano
    
    return guide_dict


@router.post("/guides/{guide_id}/generate-xml")
async def generate_preauth_xml(
    guide_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Gerar XML da guia de solicitação"""
    result = await db.execute(
        select(TISSPreAuthGuide)
        .where(
            and_(
                TISSPreAuthGuide.id == guide_id,
                TISSPreAuthGuide.clinic_id == current_user.clinic_id
            )
        )
    )
    guide = result.scalar_one_or_none()
    
    if not guide:
        raise HTTPException(status_code=404, detail="Guia não encontrada")
    
    service = PreAuthGuideService(db)
    xml_content = await service.generate_xml(guide)
    
    # Atualizar guia com XML
    guide.xml_content = xml_content
    guide.metodo_envio = 'xml'
    await db.commit()
    
    return {
        'guide_id': guide_id,
        'xml_content': xml_content,
        'numero_guia': guide.numero_guia
    }


@router.post("/guides/{guide_id}/send")
async def send_preauth_guide(
    guide_id: int,
    method: str = Query("webservice", description="Método de envio: webservice, xml, manual"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Enviar guia de solicitação ao convênio"""
    result = await db.execute(
        select(TISSPreAuthGuide)
        .where(
            and_(
                TISSPreAuthGuide.id == guide_id,
                TISSPreAuthGuide.clinic_id == current_user.clinic_id
            )
        )
    )
    guide = result.scalar_one_or_none()
    
    if not guide:
        raise HTTPException(status_code=404, detail="Guia não encontrada")
    
    service = PreAuthGuideService(db)
    
    # Gerar XML se ainda não foi gerado
    if not guide.xml_content:
        guide.xml_content = await service.generate_xml(guide)
    
    # Enviar guia
    send_result = await service.send_guide(guide, method)
    
    # Atualizar status
    guide.submission_status = PreAuthGuideSubmissionStatus.SENT if send_result['success'] else PreAuthGuideSubmissionStatus.ERROR
    guide.status = PreAuthGuideStatus.PENDING
    guide.metodo_envio = method
    guide.tentativas_envio += 1
    guide.ultima_tentativa_envio = datetime.now()
    guide.sent_at = datetime.now()
    
    if send_result.get('protocolo'):
        guide.protocolo_operadora = send_result['protocolo']
    
    await db.commit()
    
    # Atualizar status do agendamento se houver
    if guide.appointment_id:
        appointment_result = await db.execute(
            select(Appointment).where(Appointment.id == guide.appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        if appointment:
            # Manter agendamento com status apropriado
            # O status pode ser atualizado para PENDING_PREAUTH se necessário
            pass
    
    return {
        'guide_id': guide_id,
        'success': send_result['success'],
        'message': send_result.get('message', 'Guia enviada com sucesso'),
        'protocolo': send_result.get('protocolo'),
        'status': guide.status.value,
        'submission_status': guide.submission_status.value
    }


@router.post("/guides/{guide_id}/update-status")
async def update_preauth_status(
    guide_id: int,
    status: PreAuthGuideStatus,
    authorization_number: Optional[str] = None,
    approved_amount: Optional[Decimal] = None,
    valid_until: Optional[date] = None,
    denial_reason: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Atualizar status de uma guia (após receber resposta do convênio)"""
    result = await db.execute(
        select(TISSPreAuthGuide)
        .where(
            and_(
                TISSPreAuthGuide.id == guide_id,
                TISSPreAuthGuide.clinic_id == current_user.clinic_id
            )
        )
    )
    guide = result.scalar_one_or_none()
    
    if not guide:
        raise HTTPException(status_code=404, detail="Guia não encontrada")
    
    guide.status = status
    guide.data_resposta = date.today()
    
    if authorization_number:
        guide.numero_guia_operadora = authorization_number
    
    if approved_amount:
        guide.valor_aprovado = approved_amount
    
    if valid_until:
        guide.data_validade = valid_until
    
    if denial_reason:
        guide.motivo_negacao = denial_reason
    
    await db.commit()
    
    # Atualizar status do agendamento se aprovado
    if status == PreAuthGuideStatus.APPROVED and guide.appointment_id:
        appointment_result = await db.execute(
            select(Appointment).where(Appointment.id == guide.appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        if appointment:
            # Atualizar status do agendamento para confirmado
            from app.models import AppointmentStatus
            appointment.status = AppointmentStatus.SCHEDULED  # Ou outro status apropriado
    
    return {
        'guide_id': guide_id,
        'status': status.value,
        'message': 'Status atualizado com sucesso'
    }
