"""
TISS Pre-Authorization Validation Service
Serviço para validar se procedimentos requerem pré-autorização baseado em TUSS vs Planos
"""

from datetime import date, datetime
from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.tiss.insurance_structure import (
    InsuranceCompany,
    InsurancePlanTISS,
    TUSSPlanCoverage,
)
from app.models.tiss.tuss import TUSSCode
from app.models import Patient, Appointment


class PreAuthValidationService:
    """Serviço para validar pré-autorizações baseado em TUSS vs Planos"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_requires_preauth(
        self,
        tuss_code: str,
        tabela: Optional[str],
        insurance_plan_id: int,
        clinic_id: int,
        appointment_date: Optional[date] = None
    ) -> Dict:
        """
        Verifica se um procedimento requer pré-autorização
        
        Returns:
            {
                'requires_preauth': bool,
                'coverage': {
                    'coberto': bool,
                    'cobertura_percentual': Decimal,
                    'valor_contratual': Decimal,
                    'valor_coparticipacao': Decimal,
                    'requer_autorizacao': bool,
                    'prazo_autorizacao_dias': int,
                    ...
                },
                'tuss_code_id': int,
                'insurance_plan_id': int,
                'message': str
            }
        """
        if not appointment_date:
            appointment_date = date.today()
        
        # Buscar código TUSS
        query = select(TUSSCode).where(TUSSCode.codigo == tuss_code)
        if tabela:
            query = query.where(TUSSCode.tabela == tabela)
        query = query.where(TUSSCode.is_active == True)
        
        result = await self.db.execute(query)
        tuss_code_obj = result.scalar_one_or_none()
        
        if not tuss_code_obj:
            return {
                'requires_preauth': False,
                'coverage': None,
                'tuss_code_id': None,
                'insurance_plan_id': insurance_plan_id,
                'message': f'Código TUSS {tuss_code} não encontrado',
                'error': 'TUSS_CODE_NOT_FOUND'
            }
        
        # Buscar plano
        plan_result = await self.db.execute(
            select(InsurancePlanTISS)
            .where(
                and_(
                    InsurancePlanTISS.id == insurance_plan_id,
                    InsurancePlanTISS.clinic_id == clinic_id,
                    InsurancePlanTISS.is_active == True
                )
            )
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            return {
                'requires_preauth': False,
                'coverage': None,
                'tuss_code_id': tuss_code_obj.id,
                'insurance_plan_id': insurance_plan_id,
                'message': 'Plano não encontrado',
                'error': 'PLAN_NOT_FOUND'
            }
        
        # Verificar cobertura específica TUSS vs Plano
        coverage_query = select(TUSSPlanCoverage).where(
            and_(
                TUSSPlanCoverage.tuss_code_id == tuss_code_obj.id,
                TUSSPlanCoverage.insurance_plan_id == insurance_plan_id,
                TUSSPlanCoverage.clinic_id == clinic_id,
                TUSSPlanCoverage.is_active == True,
                TUSSPlanCoverage.data_inicio_vigencia <= appointment_date,
                or_(
                    TUSSPlanCoverage.data_fim_vigencia.is_(None),
                    TUSSPlanCoverage.data_fim_vigencia >= appointment_date
                )
            )
        ).order_by(TUSSPlanCoverage.data_inicio_vigencia.desc())
        
        coverage_result = await self.db.execute(coverage_query)
        coverage = coverage_result.scalar_one_or_none()
        
        # Se não houver cobertura específica, usar regras do plano
        if not coverage:
            return {
                'requires_preauth': plan.requer_autorizacao,
                'coverage': {
                    'coberto': True,  # Assumir coberto se não houver regra específica
                    'cobertura_percentual': plan.cobertura_percentual,
                    'valor_contratual': None,
                    'valor_coparticipacao': None,
                    'requer_autorizacao': plan.requer_autorizacao,
                    'prazo_autorizacao_dias': None,
                    'limite_quantidade': None,
                    'limite_periodo_dias': None,
                },
                'tuss_code_id': tuss_code_obj.id,
                'insurance_plan_id': insurance_plan_id,
                'message': 'Usando regras gerais do plano (sem cobertura específica TUSS)',
                'source': 'plan_default'
            }
        
        # Retornar informações da cobertura específica
        return {
            'requires_preauth': coverage.requer_autorizacao or (not coverage.coberto),
            'coverage': {
                'coberto': coverage.coberto,
                'cobertura_percentual': coverage.cobertura_percentual,
                'valor_tabela': float(coverage.valor_tabela) if coverage.valor_tabela else None,
                'valor_contratual': float(coverage.valor_contratual) if coverage.valor_contratual else None,
                'valor_coparticipacao': float(coverage.valor_coparticipacao) if coverage.valor_coparticipacao else None,
                'valor_franquia': float(coverage.valor_franquia) if coverage.valor_franquia else None,
                'requer_autorizacao': coverage.requer_autorizacao,
                'prazo_autorizacao_dias': coverage.prazo_autorizacao_dias,
                'limite_quantidade': coverage.limite_quantidade,
                'limite_periodo_dias': coverage.limite_periodo_dias,
            },
            'tuss_code_id': tuss_code_obj.id,
            'insurance_plan_id': insurance_plan_id,
            'coverage_id': coverage.id,
            'message': 'Cobertura específica encontrada',
            'source': 'tuss_coverage'
        }
    
    async def validate_appointment_preauth(
        self,
        appointment_id: int,
        tuss_code: Optional[str] = None,
        tabela: Optional[str] = None
    ) -> Dict:
        """
        Valida pré-autorização para um agendamento
        
        Se o agendamento tiver um plano de saúde associado, verifica se requer pré-autorização
        """
        # Buscar agendamento
        appointment_result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        
        if not appointment:
            return {
                'requires_preauth': False,
                'message': 'Agendamento não encontrado',
                'error': 'APPOINTMENT_NOT_FOUND'
            }
        
        # TODO: Buscar plano de saúde do paciente
        # Por enquanto, retornar que não requer se não houver plano
        # Isso precisa ser integrado com o sistema de planos de saúde dos pacientes
        
        if not tuss_code:
            return {
                'requires_preauth': False,
                'message': 'Código TUSS não informado',
                'error': 'TUSS_CODE_REQUIRED'
            }
        
        # Buscar plano do paciente (precisa ser implementado)
        # Por enquanto, retornar validação genérica
        
        return {
            'requires_preauth': False,
            'message': 'Validação de pré-autorização requer plano de saúde do paciente',
            'error': 'PATIENT_INSURANCE_PLAN_REQUIRED'
        }
