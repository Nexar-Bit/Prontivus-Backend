"""
TISS Insurance Structure API Endpoints
CRUD endpoints para Convênios, Planos, TUSS vs Planos e histórico de cargas
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from database import get_async_session
from app.models import User, Clinic
from app.core.auth import get_current_user, RoleChecker, UserRole
from app.models.tiss.insurance_structure import (
    InsuranceCompany,
    InsurancePlanTISS,
    TUSSPlanCoverage,
    TUSSLoadHistory,
)
from app.models.tiss.tuss import TUSSCode
from app.services.tiss.insurance_structure_service import InsuranceStructureService

router = APIRouter(prefix="/tiss/insurance-structure", tags=["TISS Insurance Structure"])

require_admin = RoleChecker([UserRole.ADMIN, UserRole.SECRETARY])


# ==================== Insurance Company (Convênio) ====================

class InsuranceCompanyCreate(BaseModel):
    nome: str = Field(..., max_length=200)
    razao_social: Optional[str] = Field(None, max_length=200)
    cnpj: str = Field(..., max_length=18)
    registro_ans: str = Field(..., max_length=6)
    codigo_operadora: Optional[str] = Field(None, max_length=20)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    endereco: Optional[str] = None
    observacoes: Optional[str] = None


class InsuranceCompanyUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=200)
    razao_social: Optional[str] = Field(None, max_length=200)
    cnpj: Optional[str] = Field(None, max_length=18)
    registro_ans: Optional[str] = Field(None, max_length=6)
    codigo_operadora: Optional[str] = Field(None, max_length=20)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    endereco: Optional[str] = None
    is_active: Optional[bool] = None
    observacoes: Optional[str] = None


class InsuranceCompanyResponse(BaseModel):
    id: int
    clinic_id: int
    nome: str
    razao_social: Optional[str]
    cnpj: str
    registro_ans: str
    codigo_operadora: Optional[str]
    telefone: Optional[str]
    email: Optional[str]
    endereco: Optional[str]
    is_active: bool
    observacoes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    plans_count: Optional[int] = 0

    class Config:
        from_attributes = True


@router.get("/companies", response_model=List[InsuranceCompanyResponse])
async def list_insurance_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Listar todos os convênios"""
    query = select(InsuranceCompany).where(InsuranceCompany.clinic_id == current_user.clinic_id)
    
    if search:
        query = query.where(
            or_(
                InsuranceCompany.nome.ilike(f"%{search}%"),
                InsuranceCompany.cnpj.ilike(f"%{search}%"),
                InsuranceCompany.registro_ans.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.where(InsuranceCompany.is_active == is_active)
    
    query = query.order_by(InsuranceCompany.nome).offset(skip).limit(limit)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    # Adicionar contagem de planos
    companies_with_counts = []
    for company in companies:
        plan_count = await db.execute(
            select(InsurancePlanTISS).where(InsurancePlanTISS.insurance_company_id == company.id)
        )
        company_dict = InsuranceCompanyResponse.model_validate(company)
        company_dict.plans_count = len(plan_count.scalars().all())
        companies_with_counts.append(company_dict)
    
    return companies_with_counts


@router.get("/companies/{company_id}", response_model=InsuranceCompanyResponse)
async def get_insurance_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Obter detalhes de um convênio"""
    result = await db.execute(
        select(InsuranceCompany)
        .where(
            and_(
                InsuranceCompany.id == company_id,
                InsuranceCompany.clinic_id == current_user.clinic_id
            )
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    
    plan_count = await db.execute(
        select(InsurancePlanTISS).where(InsurancePlanTISS.insurance_company_id == company.id)
    )
    company_dict = InsuranceCompanyResponse.model_validate(company)
    company_dict.plans_count = len(plan_count.scalars().all())
    
    return company_dict


@router.post("/companies", response_model=InsuranceCompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_company(
    company_data: InsuranceCompanyCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Criar novo convênio"""
    # Verificar se CNPJ já existe
    existing = await db.execute(
        select(InsuranceCompany).where(InsuranceCompany.cnpj == company_data.cnpj)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    
    company = InsuranceCompany(
        clinic_id=current_user.clinic_id,
        **company_data.model_dump()
    )
    
    db.add(company)
    await db.commit()
    await db.refresh(company)
    
    return InsuranceCompanyResponse.model_validate(company)


@router.put("/companies/{company_id}", response_model=InsuranceCompanyResponse)
async def update_insurance_company(
    company_id: int,
    company_data: InsuranceCompanyUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Atualizar convênio"""
    result = await db.execute(
        select(InsuranceCompany)
        .where(
            and_(
                InsuranceCompany.id == company_id,
                InsuranceCompany.clinic_id == current_user.clinic_id
            )
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    
    # Verificar CNPJ se foi alterado
    if company_data.cnpj and company_data.cnpj != company.cnpj:
        existing = await db.execute(
            select(InsuranceCompany).where(
                and_(
                    InsuranceCompany.cnpj == company_data.cnpj,
                    InsuranceCompany.id != company_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado em outro convênio")
    
    # Atualizar campos
    update_data = company_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
    
    await db.commit()
    await db.refresh(company)
    
    return InsuranceCompanyResponse.model_validate(company)


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance_company(
    company_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Deletar convênio"""
    result = await db.execute(
        select(InsuranceCompany)
        .where(
            and_(
                InsuranceCompany.id == company_id,
                InsuranceCompany.clinic_id == current_user.clinic_id
            )
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    
    await db.delete(company)
    await db.commit()


@router.post("/companies/upload-excel")
async def upload_companies_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Upload em massa de convênios via Excel"""
    service = InsuranceStructureService(db)
    result = await service.upload_companies_excel(file, current_user.clinic_id, current_user.id)
    return result


# ==================== Insurance Plan (Plano) ====================

class InsurancePlanCreate(BaseModel):
    insurance_company_id: int
    nome_plano: str = Field(..., max_length=200)
    codigo_plano: Optional[str] = Field(None, max_length=50)
    numero_plano_ans: Optional[str] = Field(None, max_length=20)
    cobertura_percentual: Decimal = Field(default=Decimal("100.00"), ge=0, le=100)
    requer_autorizacao: bool = Field(default=False)
    limite_anual: Optional[Decimal] = None
    limite_por_procedimento: Optional[Decimal] = None
    data_inicio_vigencia: Optional[date] = None
    data_fim_vigencia: Optional[date] = None
    observacoes: Optional[str] = None
    configuracoes_extras: Optional[dict] = None


class InsurancePlanUpdate(BaseModel):
    nome_plano: Optional[str] = Field(None, max_length=200)
    codigo_plano: Optional[str] = Field(None, max_length=50)
    numero_plano_ans: Optional[str] = Field(None, max_length=20)
    cobertura_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    requer_autorizacao: Optional[bool] = None
    limite_anual: Optional[Decimal] = None
    limite_por_procedimento: Optional[Decimal] = None
    data_inicio_vigencia: Optional[date] = None
    data_fim_vigencia: Optional[date] = None
    is_active: Optional[bool] = None
    observacoes: Optional[str] = None
    configuracoes_extras: Optional[dict] = None


class InsurancePlanResponse(BaseModel):
    id: int
    insurance_company_id: int
    clinic_id: int
    nome_plano: str
    codigo_plano: Optional[str]
    numero_plano_ans: Optional[str]
    cobertura_percentual: Decimal
    requer_autorizacao: bool
    limite_anual: Optional[Decimal]
    limite_por_procedimento: Optional[Decimal]
    data_inicio_vigencia: Optional[date]
    data_fim_vigencia: Optional[date]
    is_active: bool
    observacoes: Optional[str]
    configuracoes_extras: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    insurance_company_nome: Optional[str] = None
    coverage_count: Optional[int] = 0

    class Config:
        from_attributes = True


@router.get("/plans", response_model=List[InsurancePlanResponse])
async def list_insurance_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    insurance_company_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Listar todos os planos"""
    query = select(InsurancePlanTISS).where(InsurancePlanTISS.clinic_id == current_user.clinic_id)
    
    if insurance_company_id:
        query = query.where(InsurancePlanTISS.insurance_company_id == insurance_company_id)
    
    if search:
        query = query.where(InsurancePlanTISS.nome_plano.ilike(f"%{search}%"))
    
    if is_active is not None:
        query = query.where(InsurancePlanTISS.is_active == is_active)
    
    query = query.order_by(InsurancePlanTISS.nome_plano).offset(skip).limit(limit)
    
    result = await db.execute(query.options(joinedload(InsurancePlanTISS.insurance_company)))
    plans = result.scalars().all()
    
    # Adicionar informações adicionais
    plans_with_info = []
    for plan in plans:
        coverage_count = await db.execute(
            select(TUSSPlanCoverage).where(TUSSPlanCoverage.insurance_plan_id == plan.id)
        )
        plan_dict = InsurancePlanResponse.model_validate(plan)
        plan_dict.insurance_company_nome = plan.insurance_company.nome if plan.insurance_company else None
        plan_dict.coverage_count = len(coverage_count.scalars().all())
        plans_with_info.append(plan_dict)
    
    return plans_with_info


@router.get("/plans/{plan_id}", response_model=InsurancePlanResponse)
async def get_insurance_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Obter detalhes de um plano"""
    result = await db.execute(
        select(InsurancePlanTISS)
        .where(
            and_(
                InsurancePlanTISS.id == plan_id,
                InsurancePlanTISS.clinic_id == current_user.clinic_id
            )
        )
        .options(joinedload(InsurancePlanTISS.insurance_company))
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    coverage_count = await db.execute(
        select(TUSSPlanCoverage).where(TUSSPlanCoverage.insurance_plan_id == plan.id)
    )
    plan_dict = InsurancePlanResponse.model_validate(plan)
    plan_dict.insurance_company_nome = plan.insurance_company.nome if plan.insurance_company else None
    plan_dict.coverage_count = len(coverage_count.scalars().all())
    
    return plan_dict


@router.post("/plans", response_model=InsurancePlanResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_plan(
    plan_data: InsurancePlanCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Criar novo plano"""
    # Verificar se convênio existe e pertence à clínica
    company_result = await db.execute(
        select(InsuranceCompany)
        .where(
            and_(
                InsuranceCompany.id == plan_data.insurance_company_id,
                InsuranceCompany.clinic_id == current_user.clinic_id
            )
        )
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    
    plan = InsurancePlanTISS(
        clinic_id=current_user.clinic_id,
        **plan_data.model_dump()
    )
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan, ["insurance_company"])
    
    plan_dict = InsurancePlanResponse.model_validate(plan)
    plan_dict.insurance_company_nome = plan.insurance_company.nome if plan.insurance_company else None
    
    return plan_dict


@router.put("/plans/{plan_id}", response_model=InsurancePlanResponse)
async def update_insurance_plan(
    plan_id: int,
    plan_data: InsurancePlanUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Atualizar plano"""
    result = await db.execute(
        select(InsurancePlanTISS)
        .where(
            and_(
                InsurancePlanTISS.id == plan_id,
                InsurancePlanTISS.clinic_id == current_user.clinic_id
            )
        )
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    
    await db.commit()
    await db.refresh(plan, ["insurance_company"])
    
    plan_dict = InsurancePlanResponse.model_validate(plan)
    plan_dict.insurance_company_nome = plan.insurance_company.nome if plan.insurance_company else None
    
    return plan_dict


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance_plan(
    plan_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Deletar plano"""
    result = await db.execute(
        select(InsurancePlanTISS)
        .where(
            and_(
                InsurancePlanTISS.id == plan_id,
                InsurancePlanTISS.clinic_id == current_user.clinic_id
            )
        )
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    await db.delete(plan)
    await db.commit()


@router.post("/plans/upload-excel")
async def upload_plans_excel(
    file: UploadFile = File(...),
    insurance_company_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Upload em massa de planos via Excel"""
    service = InsuranceStructureService(db)
    result = await service.upload_plans_excel(file, current_user.clinic_id, current_user.id, insurance_company_id)
    return result


# ==================== TUSS Plan Coverage (TUSS vs Planos) ====================

class TUSSPlanCoverageCreate(BaseModel):
    tuss_code_id: int
    insurance_plan_id: int
    coberto: bool = Field(default=True)
    cobertura_percentual: Decimal = Field(default=Decimal("100.00"), ge=0, le=100)
    valor_tabela: Optional[Decimal] = None
    valor_contratual: Optional[Decimal] = None
    valor_coparticipacao: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_franquia: Decimal = Field(default=Decimal("0.00"), ge=0)
    requer_autorizacao: bool = Field(default=False)
    prazo_autorizacao_dias: Optional[int] = None
    limite_quantidade: Optional[int] = None
    limite_periodo_dias: Optional[int] = None
    data_inicio_vigencia: date
    data_fim_vigencia: Optional[date] = None
    observacoes: Optional[str] = None
    regras_especiais: Optional[dict] = None


class TUSSPlanCoverageUpdate(BaseModel):
    coberto: Optional[bool] = None
    cobertura_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    valor_tabela: Optional[Decimal] = None
    valor_contratual: Optional[Decimal] = None
    valor_coparticipacao: Optional[Decimal] = Field(None, ge=0)
    valor_franquia: Optional[Decimal] = Field(None, ge=0)
    requer_autorizacao: Optional[bool] = None
    prazo_autorizacao_dias: Optional[int] = None
    limite_quantidade: Optional[int] = None
    limite_periodo_dias: Optional[int] = None
    data_inicio_vigencia: Optional[date] = None
    data_fim_vigencia: Optional[date] = None
    is_active: Optional[bool] = None
    observacoes: Optional[str] = None
    regras_especiais: Optional[dict] = None


class TUSSPlanCoverageResponse(BaseModel):
    id: int
    tuss_code_id: int
    insurance_plan_id: int
    clinic_id: int
    coberto: bool
    cobertura_percentual: Decimal
    valor_tabela: Optional[Decimal]
    valor_contratual: Optional[Decimal]
    valor_coparticipacao: Decimal
    valor_franquia: Decimal
    requer_autorizacao: bool
    prazo_autorizacao_dias: Optional[int]
    limite_quantidade: Optional[int]
    limite_periodo_dias: Optional[int]
    data_inicio_vigencia: date
    data_fim_vigencia: Optional[date]
    is_active: bool
    observacoes: Optional[str]
    regras_especiais: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    tuss_code: Optional[str] = None
    tuss_descricao: Optional[str] = None
    plan_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/coverage", response_model=List[TUSSPlanCoverageResponse])
async def list_tuss_plan_coverage(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    insurance_plan_id: Optional[int] = Query(None),
    tuss_code_id: Optional[int] = Query(None),
    coberto: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Listar coberturas TUSS vs Planos"""
    query = select(TUSSPlanCoverage).where(TUSSPlanCoverage.clinic_id == current_user.clinic_id)
    
    if insurance_plan_id:
        query = query.where(TUSSPlanCoverage.insurance_plan_id == insurance_plan_id)
    
    if tuss_code_id:
        query = query.where(TUSSPlanCoverage.tuss_code_id == tuss_code_id)
    
    if coberto is not None:
        query = query.where(TUSSPlanCoverage.coberto == coberto)
    
    if is_active is not None:
        query = query.where(TUSSPlanCoverage.is_active == is_active)
    
    query = query.order_by(TUSSPlanCoverage.data_inicio_vigencia.desc()).offset(skip).limit(limit)
    
    result = await db.execute(
        query.options(
            joinedload(TUSSPlanCoverage.tuss_code),
            joinedload(TUSSPlanCoverage.insurance_plan)
        )
    )
    coverages = result.scalars().all()
    
    # Adicionar informações relacionadas
    coverages_with_info = []
    for coverage in coverages:
        coverage_dict = TUSSPlanCoverageResponse.model_validate(coverage)
        if coverage.tuss_code:
            coverage_dict.tuss_code = coverage.tuss_code.codigo
            coverage_dict.tuss_descricao = coverage.tuss_code.descricao
        if coverage.insurance_plan:
            coverage_dict.plan_nome = coverage.insurance_plan.nome_plano
        coverages_with_info.append(coverage_dict)
    
    return coverages_with_info


@router.get("/coverage/{coverage_id}", response_model=TUSSPlanCoverageResponse)
async def get_tuss_plan_coverage(
    coverage_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Obter detalhes de uma cobertura"""
    result = await db.execute(
        select(TUSSPlanCoverage)
        .where(
            and_(
                TUSSPlanCoverage.id == coverage_id,
                TUSSPlanCoverage.clinic_id == current_user.clinic_id
            )
        )
        .options(
            joinedload(TUSSPlanCoverage.tuss_code),
            joinedload(TUSSPlanCoverage.insurance_plan)
        )
    )
    coverage = result.scalar_one_or_none()
    
    if not coverage:
        raise HTTPException(status_code=404, detail="Cobertura não encontrada")
    
    coverage_dict = TUSSPlanCoverageResponse.model_validate(coverage)
    if coverage.tuss_code:
        coverage_dict.tuss_code = coverage.tuss_code.codigo
        coverage_dict.tuss_descricao = coverage.tuss_code.descricao
    if coverage.insurance_plan:
        coverage_dict.plan_nome = coverage.insurance_plan.nome_plano
    
    return coverage_dict


@router.post("/coverage", response_model=TUSSPlanCoverageResponse, status_code=status.HTTP_201_CREATED)
async def create_tuss_plan_coverage(
    coverage_data: TUSSPlanCoverageCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Criar nova cobertura TUSS vs Plano"""
    # Verificar se TUSS code existe
    tuss_result = await db.execute(
        select(TUSSCode).where(TUSSCode.id == coverage_data.tuss_code_id)
    )
    if not tuss_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Código TUSS não encontrado")
    
    # Verificar se plano existe e pertence à clínica
    plan_result = await db.execute(
        select(InsurancePlanTISS)
        .where(
            and_(
                InsurancePlanTISS.id == coverage_data.insurance_plan_id,
                InsurancePlanTISS.clinic_id == current_user.clinic_id
            )
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    coverage = TUSSPlanCoverage(
        clinic_id=current_user.clinic_id,
        **coverage_data.model_dump()
    )
    
    db.add(coverage)
    await db.commit()
    await db.refresh(coverage, ["tuss_code", "insurance_plan"])
    
    coverage_dict = TUSSPlanCoverageResponse.model_validate(coverage)
    if coverage.tuss_code:
        coverage_dict.tuss_code = coverage.tuss_code.codigo
        coverage_dict.tuss_descricao = coverage.tuss_code.descricao
    if coverage.insurance_plan:
        coverage_dict.plan_nome = coverage.insurance_plan.nome_plano
    
    return coverage_dict


@router.put("/coverage/{coverage_id}", response_model=TUSSPlanCoverageResponse)
async def update_tuss_plan_coverage(
    coverage_id: int,
    coverage_data: TUSSPlanCoverageUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Atualizar cobertura"""
    result = await db.execute(
        select(TUSSPlanCoverage)
        .where(
            and_(
                TUSSPlanCoverage.id == coverage_id,
                TUSSPlanCoverage.clinic_id == current_user.clinic_id
            )
        )
    )
    coverage = result.scalar_one_or_none()
    
    if not coverage:
        raise HTTPException(status_code=404, detail="Cobertura não encontrada")
    
    update_data = coverage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coverage, field, value)
    
    await db.commit()
    await db.refresh(coverage, ["tuss_code", "insurance_plan"])
    
    coverage_dict = TUSSPlanCoverageResponse.model_validate(coverage)
    if coverage.tuss_code:
        coverage_dict.tuss_code = coverage.tuss_code.codigo
        coverage_dict.tuss_descricao = coverage.tuss_code.descricao
    if coverage.insurance_plan:
        coverage_dict.plan_nome = coverage.insurance_plan.nome_plano
    
    return coverage_dict


@router.delete("/coverage/{coverage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tuss_plan_coverage(
    coverage_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Deletar cobertura"""
    result = await db.execute(
        select(TUSSPlanCoverage)
        .where(
            and_(
                TUSSPlanCoverage.id == coverage_id,
                TUSSPlanCoverage.clinic_id == current_user.clinic_id
            )
        )
    )
    coverage = result.scalar_one_or_none()
    
    if not coverage:
        raise HTTPException(status_code=404, detail="Cobertura não encontrada")
    
    await db.delete(coverage)
    await db.commit()


@router.post("/coverage/upload-excel")
async def upload_coverage_excel(
    file: UploadFile = File(...),
    insurance_plan_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """Upload em massa de coberturas TUSS vs Planos via Excel"""
    service = InsuranceStructureService(db)
    result = await service.upload_coverage_excel(file, current_user.clinic_id, current_user.id, insurance_plan_id)
    return result


# ==================== Load History (Histórico de Cargas) ====================

class TUSSLoadHistoryResponse(BaseModel):
    id: int
    clinic_id: int
    insurance_company_id: Optional[int]
    tuss_plan_coverage_id: Optional[int]
    tipo_carga: str
    nome_arquivo: str
    total_registros: int
    registros_inseridos: int
    registros_atualizados: int
    registros_erro: int
    versao_tuss: Optional[str]
    data_referencia: Optional[date]
    observacoes: Optional[str]
    erros: Optional[dict]
    avisos: Optional[dict]
    created_by: Optional[int]
    created_at: datetime
    user_nome: Optional[str] = None
    insurance_company_nome: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/load-history", response_model=List[TUSSLoadHistoryResponse])
async def list_load_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tipo_carga: Optional[str] = Query(None),
    insurance_company_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Listar histórico de cargas TUSS"""
    query = select(TUSSLoadHistory).where(TUSSLoadHistory.clinic_id == current_user.clinic_id)
    
    if tipo_carga:
        query = query.where(TUSSLoadHistory.tipo_carga == tipo_carga)
    
    if insurance_company_id:
        query = query.where(TUSSLoadHistory.insurance_company_id == insurance_company_id)
    
    query = query.order_by(TUSSLoadHistory.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(
        query.options(
            joinedload(TUSSLoadHistory.user),
            joinedload(TUSSLoadHistory.insurance_company)
        )
    )
    histories = result.scalars().all()
    
    histories_with_info = []
    for history in histories:
        history_dict = TUSSLoadHistoryResponse.model_validate(history)
        if history.user:
            history_dict.user_nome = history.user.full_name if hasattr(history.user, 'full_name') else history.user.username
        if history.insurance_company:
            history_dict.insurance_company_nome = history.insurance_company.nome
        histories_with_info.append(history_dict)
    
    return histories_with_info


@router.get("/load-history/{history_id}", response_model=TUSSLoadHistoryResponse)
async def get_load_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Obter detalhes de uma carga"""
    result = await db.execute(
        select(TUSSLoadHistory)
        .where(
            and_(
                TUSSLoadHistory.id == history_id,
                TUSSLoadHistory.clinic_id == current_user.clinic_id
            )
        )
        .options(
            joinedload(TUSSLoadHistory.user),
            joinedload(TUSSLoadHistory.insurance_company)
        )
    )
    history = result.scalar_one_or_none()
    
    if not history:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    history_dict = TUSSLoadHistoryResponse.model_validate(history)
    if history.user:
        history_dict.user_nome = history.user.full_name if hasattr(history.user, 'full_name') else history.user.username
    if history.insurance_company:
        history_dict.insurance_company_nome = history.insurance_company.nome
    
    return history_dict
