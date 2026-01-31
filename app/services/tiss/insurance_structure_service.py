"""
TISS Insurance Structure Service
Serviço para processar uploads em Excel e gerenciar estrutura de convênios/planos/TUSS
"""

import pandas as pd
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.tiss.insurance_structure import (
    InsuranceCompany,
    InsurancePlanTISS,
    TUSSPlanCoverage,
    TUSSLoadHistory,
)
from app.models.tiss.tuss import TUSSCode


class InsuranceStructureService:
    """Serviço para gerenciar estrutura de convênios, planos e coberturas TUSS"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def upload_companies_excel(
        self, 
        file, 
        clinic_id: int, 
        user_id: int
    ) -> Dict:
        """
        Processar upload de convênios via Excel
        
        Formato esperado do Excel:
        - nome (obrigatório)
        - razao_social
        - cnpj (obrigatório, único)
        - registro_ans (obrigatório)
        - codigo_operadora
        - telefone
        - email
        - endereco
        - observacoes
        """
        inserted = 0
        updated = 0
        errors = []
        warnings = []
        
        try:
            # Ler Excel
            file_content = await file.read()
            df = pd.read_excel(BytesIO(file_content))
            
            # Validar colunas obrigatórias
            required_columns = ['nome', 'cnpj', 'registro_ans']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
            
            # Processar cada linha
            for idx, row in df.iterrows():
                try:
                    cnpj = str(row['cnpj']).strip().replace('.', '').replace('-', '').replace('/', '')
                    
                    # Verificar se já existe
                    existing = await self.db.execute(
                        select(InsuranceCompany).where(
                            and_(
                                InsuranceCompany.cnpj == cnpj,
                                InsuranceCompany.clinic_id == clinic_id
                            )
                        )
                    )
                    existing_company = existing.scalar_one_or_none()
                    
                    company_data = {
                        'clinic_id': clinic_id,
                        'nome': str(row['nome']).strip(),
                        'cnpj': cnpj,
                        'registro_ans': str(row['registro_ans']).strip(),
                        'razao_social': str(row.get('razao_social', '')).strip() or None,
                        'codigo_operadora': str(row.get('codigo_operadora', '')).strip() or None,
                        'telefone': str(row.get('telefone', '')).strip() or None,
                        'email': str(row.get('email', '')).strip() or None,
                        'endereco': str(row.get('endereco', '')).strip() or None,
                        'observacoes': str(row.get('observacoes', '')).strip() or None,
                    }
                    
                    if existing_company:
                        # Atualizar
                        for key, value in company_data.items():
                            if key != 'clinic_id' and key != 'cnpj':
                                setattr(existing_company, key, value)
                        updated += 1
                    else:
                        # Inserir
                        company = InsuranceCompany(**company_data)
                        self.db.add(company)
                        inserted += 1
                
                except Exception as e:
                    errors.append({
                        'linha': idx + 2,  # +2 porque Excel começa em 1 e tem cabeçalho
                        'erro': str(e),
                        'dados': row.to_dict()
                    })
            
            await self.db.commit()
            
            # Registrar histórico
            filename = file.filename if hasattr(file, 'filename') else 'upload.xlsx'
            history = TUSSLoadHistory(
                clinic_id=clinic_id,
                tipo_carga='insurance_companies',
                nome_arquivo=filename,
                total_registros=len(df),
                registros_inseridos=inserted,
                registros_atualizados=updated,
                registros_erro=len(errors),
                created_by=user_id,
                erros=errors if errors else None,
                avisos=warnings if warnings else None
            )
            self.db.add(history)
            await self.db.commit()
            
            return {
                'success': True,
                'total_registros': len(df),
                'registros_inseridos': inserted,
                'registros_atualizados': updated,
                'registros_erro': len(errors),
                'erros': errors[:10],  # Limitar a 10 erros
                'avisos': warnings
            }
        
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'erro': str(e),
                'total_registros': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
    
    async def upload_plans_excel(
        self,
        file,
        clinic_id: int,
        user_id: int,
        insurance_company_id: Optional[int] = None
    ) -> Dict:
        """
        Processar upload de planos via Excel
        
        Formato esperado do Excel:
        - insurance_company_id ou cnpj_operadora (para identificar o convênio)
        - nome_plano (obrigatório)
        - codigo_plano
        - numero_plano_ans
        - cobertura_percentual (padrão: 100.00)
        - requer_autorizacao (padrão: false)
        - limite_anual
        - limite_por_procedimento
        - data_inicio_vigencia
        - data_fim_vigencia
        - observacoes
        """
        inserted = 0
        updated = 0
        errors = []
        warnings = []
        
        try:
            df = pd.read_excel(BytesIO(file))
            
            required_columns = ['nome_plano']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
            
            for idx, row in df.iterrows():
                try:
                    # Identificar convênio
                    company_id = insurance_company_id
                    if not company_id and 'cnpj_operadora' in row:
                        cnpj = str(row['cnpj_operadora']).strip().replace('.', '').replace('-', '').replace('/', '')
                        company_result = await self.db.execute(
                            select(InsuranceCompany).where(
                                and_(
                                    InsuranceCompany.cnpj == cnpj,
                                    InsuranceCompany.clinic_id == clinic_id
                                )
                            )
                        )
                        company = company_result.scalar_one_or_none()
                        if not company:
                            errors.append({
                                'linha': idx + 2,
                                'erro': f'Convênio com CNPJ {cnpj} não encontrado',
                                'dados': row.to_dict()
                            })
                            continue
                        company_id = company.id
                    elif not company_id and 'insurance_company_id' in row:
                        company_id = int(row['insurance_company_id'])
                    
                    if not company_id:
                        errors.append({
                            'linha': idx + 2,
                            'erro': 'Convênio não identificado. Informe insurance_company_id ou cnpj_operadora',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    # Verificar se convênio existe
                    company_result = await self.db.execute(
                        select(InsuranceCompany).where(
                            and_(
                                InsuranceCompany.id == company_id,
                                InsuranceCompany.clinic_id == clinic_id
                            )
                        )
                    )
                    if not company_result.scalar_one_or_none():
                        errors.append({
                            'linha': idx + 2,
                            'erro': f'Convênio ID {company_id} não encontrado',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    nome_plano = str(row['nome_plano']).strip()
                    codigo_plano = str(row.get('codigo_plano', '')).strip() or None
                    
                    # Verificar se já existe
                    query = select(InsurancePlanTISS).where(
                        and_(
                            InsurancePlanTISS.insurance_company_id == company_id,
                            InsurancePlanTISS.clinic_id == clinic_id,
                            InsurancePlanTISS.nome_plano == nome_plano
                        )
                    )
                    if codigo_plano:
                        query = query.where(InsurancePlanTISS.codigo_plano == codigo_plano)
                    
                    existing = await self.db.execute(query)
                    existing_plan = existing.scalar_one_or_none()
                    
                    # Processar datas
                    data_inicio = None
                    data_fim = None
                    if 'data_inicio_vigencia' in row and pd.notna(row['data_inicio_vigencia']):
                        if isinstance(row['data_inicio_vigencia'], str):
                            data_inicio = datetime.strptime(row['data_inicio_vigencia'], '%Y-%m-%d').date()
                        else:
                            data_inicio = row['data_inicio_vigencia'].date() if hasattr(row['data_inicio_vigencia'], 'date') else None
                    
                    if 'data_fim_vigencia' in row and pd.notna(row['data_fim_vigencia']):
                        if isinstance(row['data_fim_vigencia'], str):
                            data_fim = datetime.strptime(row['data_fim_vigencia'], '%Y-%m-%d').date()
                        else:
                            data_fim = row['data_fim_vigencia'].date() if hasattr(row['data_fim_vigencia'], 'date') else None
                    
                    plan_data = {
                        'insurance_company_id': company_id,
                        'clinic_id': clinic_id,
                        'nome_plano': nome_plano,
                        'codigo_plano': codigo_plano,
                        'numero_plano_ans': str(row.get('numero_plano_ans', '')).strip() or None,
                        'cobertura_percentual': Decimal(str(row.get('cobertura_percentual', 100.00))),
                        'requer_autorizacao': bool(row.get('requer_autorizacao', False)),
                        'limite_anual': Decimal(str(row['limite_anual'])) if pd.notna(row.get('limite_anual')) else None,
                        'limite_por_procedimento': Decimal(str(row['limite_por_procedimento'])) if pd.notna(row.get('limite_por_procedimento')) else None,
                        'data_inicio_vigencia': data_inicio,
                        'data_fim_vigencia': data_fim,
                        'observacoes': str(row.get('observacoes', '')).strip() or None,
                    }
                    
                    if existing_plan:
                        for key, value in plan_data.items():
                            if key not in ['insurance_company_id', 'clinic_id']:
                                setattr(existing_plan, key, value)
                        updated += 1
                    else:
                        plan = InsurancePlanTISS(**plan_data)
                        self.db.add(plan)
                        inserted += 1
                
                except Exception as e:
                    errors.append({
                        'linha': idx + 2,
                        'erro': str(e),
                        'dados': row.to_dict()
                    })
            
            await self.db.commit()
            
            # Registrar histórico
            filename = file.filename if hasattr(file, 'filename') else 'upload.xlsx'
            history = TUSSLoadHistory(
                clinic_id=clinic_id,
                insurance_company_id=insurance_company_id,
                tipo_carga='insurance_plans',
                nome_arquivo=filename,
                total_registros=len(df),
                registros_inseridos=inserted,
                registros_atualizados=updated,
                registros_erro=len(errors),
                created_by=user_id,
                erros=errors if errors else None,
                avisos=warnings if warnings else None
            )
            self.db.add(history)
            await self.db.commit()
            
            return {
                'success': True,
                'total_registros': len(df),
                'registros_inseridos': inserted,
                'registros_atualizados': updated,
                'registros_erro': len(errors),
                'erros': errors[:10],
                'avisos': warnings
            }
        
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'erro': str(e),
                'total_registros': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
    
    async def upload_coverage_excel(
        self,
        file,
        clinic_id: int,
        user_id: int,
        insurance_plan_id: Optional[int] = None
    ) -> Dict:
        """
        Processar upload de coberturas TUSS vs Planos via Excel
        
        Formato esperado do Excel:
        - insurance_plan_id ou codigo_plano (para identificar o plano)
        - tuss_code_id ou codigo_tuss (para identificar o código TUSS)
        - coberto (padrão: true)
        - cobertura_percentual (padrão: 100.00)
        - valor_tabela
        - valor_contratual
        - valor_coparticipacao (padrão: 0.00)
        - valor_franquia (padrão: 0.00)
        - requer_autorizacao (padrão: false)
        - prazo_autorizacao_dias
        - limite_quantidade
        - limite_periodo_dias
        - data_inicio_vigencia (obrigatório)
        - data_fim_vigencia
        - observacoes
        """
        inserted = 0
        updated = 0
        errors = []
        warnings = []
        
        try:
            df = pd.read_excel(BytesIO(file))
            
            required_columns = ['data_inicio_vigencia']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
            
            for idx, row in df.iterrows():
                try:
                    # Identificar plano
                    plan_id = insurance_plan_id
                    if not plan_id and 'codigo_plano' in row:
                        codigo_plano = str(row['codigo_plano']).strip()
                        plan_result = await self.db.execute(
                            select(InsurancePlanTISS).where(
                                and_(
                                    InsurancePlanTISS.codigo_plano == codigo_plano,
                                    InsurancePlanTISS.clinic_id == clinic_id
                                )
                            )
                        )
                        plan = plan_result.scalar_one_or_none()
                        if not plan:
                            errors.append({
                                'linha': idx + 2,
                                'erro': f'Plano com código {codigo_plano} não encontrado',
                                'dados': row.to_dict()
                            })
                            continue
                        plan_id = plan.id
                    elif not plan_id and 'insurance_plan_id' in row:
                        plan_id = int(row['insurance_plan_id'])
                    
                    if not plan_id:
                        errors.append({
                            'linha': idx + 2,
                            'erro': 'Plano não identificado. Informe insurance_plan_id ou codigo_plano',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    # Verificar se plano existe
                    plan_result = await self.db.execute(
                        select(InsurancePlanTISS).where(
                            and_(
                                InsurancePlanTISS.id == plan_id,
                                InsurancePlanTISS.clinic_id == clinic_id
                            )
                        )
                    )
                    if not plan_result.scalar_one_or_none():
                        errors.append({
                            'linha': idx + 2,
                            'erro': f'Plano ID {plan_id} não encontrado',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    # Identificar código TUSS
                    tuss_code_id = None
                    if 'tuss_code_id' in row and pd.notna(row['tuss_code_id']):
                        tuss_code_id = int(row['tuss_code_id'])
                    elif 'codigo_tuss' in row:
                        codigo_tuss = str(row['codigo_tuss']).strip()
                        tabela = str(row.get('tabela_tuss', '')).strip() if 'tabela_tuss' in row else None
                        
                        query = select(TUSSCode).where(TUSSCode.codigo == codigo_tuss)
                        if tabela:
                            query = query.where(TUSSCode.tabela == tabela)
                        
                        tuss_result = await self.db.execute(query)
                        tuss_code = tuss_result.scalar_one_or_none()
                        if not tuss_code:
                            errors.append({
                                'linha': idx + 2,
                                'erro': f'Código TUSS {codigo_tuss} não encontrado',
                                'dados': row.to_dict()
                            })
                            continue
                        tuss_code_id = tuss_code.id
                    
                    if not tuss_code_id:
                        errors.append({
                            'linha': idx + 2,
                            'erro': 'Código TUSS não identificado. Informe tuss_code_id ou codigo_tuss',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    # Processar data de início
                    data_inicio = None
                    if pd.notna(row['data_inicio_vigencia']):
                        if isinstance(row['data_inicio_vigencia'], str):
                            data_inicio = datetime.strptime(row['data_inicio_vigencia'], '%Y-%m-%d').date()
                        else:
                            data_inicio = row['data_inicio_vigencia'].date() if hasattr(row['data_inicio_vigencia'], 'date') else None
                    
                    if not data_inicio:
                        errors.append({
                            'linha': idx + 2,
                            'erro': 'data_inicio_vigencia inválida',
                            'dados': row.to_dict()
                        })
                        continue
                    
                    # Processar data de fim
                    data_fim = None
                    if 'data_fim_vigencia' in row and pd.notna(row['data_fim_vigencia']):
                        if isinstance(row['data_fim_vigencia'], str):
                            data_fim = datetime.strptime(row['data_fim_vigencia'], '%Y-%m-%d').date()
                        else:
                            data_fim = row['data_fim_vigencia'].date() if hasattr(row['data_fim_vigencia'], 'date') else None
                    
                    # Verificar se já existe
                    existing = await self.db.execute(
                        select(TUSSPlanCoverage).where(
                            and_(
                                TUSSPlanCoverage.tuss_code_id == tuss_code_id,
                                TUSSPlanCoverage.insurance_plan_id == plan_id,
                                TUSSPlanCoverage.clinic_id == clinic_id,
                                TUSSPlanCoverage.data_inicio_vigencia == data_inicio
                            )
                        )
                    )
                    existing_coverage = existing.scalar_one_or_none()
                    
                    coverage_data = {
                        'tuss_code_id': tuss_code_id,
                        'insurance_plan_id': plan_id,
                        'clinic_id': clinic_id,
                        'coberto': bool(row.get('coberto', True)),
                        'cobertura_percentual': Decimal(str(row.get('cobertura_percentual', 100.00))),
                        'valor_tabela': Decimal(str(row['valor_tabela'])) if pd.notna(row.get('valor_tabela')) else None,
                        'valor_contratual': Decimal(str(row['valor_contratual'])) if pd.notna(row.get('valor_contratual')) else None,
                        'valor_coparticipacao': Decimal(str(row.get('valor_coparticipacao', 0.00))),
                        'valor_franquia': Decimal(str(row.get('valor_franquia', 0.00))),
                        'requer_autorizacao': bool(row.get('requer_autorizacao', False)),
                        'prazo_autorizacao_dias': int(row['prazo_autorizacao_dias']) if pd.notna(row.get('prazo_autorizacao_dias')) else None,
                        'limite_quantidade': int(row['limite_quantidade']) if pd.notna(row.get('limite_quantidade')) else None,
                        'limite_periodo_dias': int(row['limite_periodo_dias']) if pd.notna(row.get('limite_periodo_dias')) else None,
                        'data_inicio_vigencia': data_inicio,
                        'data_fim_vigencia': data_fim,
                        'observacoes': str(row.get('observacoes', '')).strip() or None,
                    }
                    
                    if existing_coverage:
                        for key, value in coverage_data.items():
                            if key not in ['tuss_code_id', 'insurance_plan_id', 'clinic_id', 'data_inicio_vigencia']:
                                setattr(existing_coverage, key, value)
                        updated += 1
                    else:
                        coverage = TUSSPlanCoverage(**coverage_data)
                        self.db.add(coverage)
                        inserted += 1
                
                except Exception as e:
                    errors.append({
                        'linha': idx + 2,
                        'erro': str(e),
                        'dados': row.to_dict()
                    })
            
            await self.db.commit()
            
            # Registrar histórico
            filename = file.filename if hasattr(file, 'filename') else 'upload.xlsx'
            history = TUSSLoadHistory(
                clinic_id=clinic_id,
                tipo_carga='tuss_plan_coverage',
                nome_arquivo=filename,
                total_registros=len(df),
                registros_inseridos=inserted,
                registros_atualizados=updated,
                registros_erro=len(errors),
                created_by=user_id,
                erros=errors if errors else None,
                avisos=warnings if warnings else None
            )
            self.db.add(history)
            await self.db.commit()
            
            return {
                'success': True,
                'total_registros': len(df),
                'registros_inseridos': inserted,
                'registros_atualizados': updated,
                'registros_erro': len(errors),
                'erros': errors[:10],
                'avisos': warnings
            }
        
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'erro': str(e),
                'total_registros': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
