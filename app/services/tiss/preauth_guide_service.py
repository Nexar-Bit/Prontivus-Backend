"""
TISS Pre-Authorization Guide Service
Serviço para gerar e enviar Guias de Solicitação de Autorização TISS
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.tiss.preauth_guide import (
    TISSPreAuthGuide,
    PreAuthGuideStatus,
    PreAuthGuideSubmissionStatus,
)
from app.models.tiss.insurance_structure import InsuranceCompany, InsurancePlanTISS
from app.models.tiss.tuss import TUSSCode
from app.models import Patient, Appointment
from sqlalchemy.orm import selectinload


class PreAuthGuideService:
    """Serviço para gerenciar Guias de Solicitação de Autorização TISS"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_preauth_guide(
        self,
        clinic_id: int,
        created_by: int,
        appointment_id: Optional[int],
        patient_id: int,
        insurance_plan_id: int,
        tuss_code: str,
        tabela_tuss: str,
        tuss_descricao: str,
        valor_solicitado: Decimal,
        data_prevista_procedimento: date,
        observacoes: Optional[str] = None,
        dados_adicionais: Optional[dict] = None
    ) -> TISSPreAuthGuide:
        """Criar nova guia de solicitação de autorização"""
        
        # Buscar código TUSS
        tuss_result = await self.db.execute(
            select(TUSSCode).where(
                and_(
                    TUSSCode.codigo == tuss_code,
                    TUSSCode.tabela == tabela_tuss
                )
            )
        )
        tuss_code_obj = tuss_result.scalar_one_or_none()
        
        # Buscar plano
        plan_result = await self.db.execute(
            select(InsurancePlanTISS).where(
                and_(
                    InsurancePlanTISS.id == insurance_plan_id,
                    InsurancePlanTISS.clinic_id == clinic_id
                )
            )
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise ValueError(f"Plano ID {insurance_plan_id} não encontrado")
        
        # Gerar número único da guia
        numero_guia = self._generate_guide_number(clinic_id)
        
        # Criar guia
        guide = TISSPreAuthGuide(
            clinic_id=clinic_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            insurance_plan_id=insurance_plan_id,
            insurance_company_id=plan.insurance_company_id if plan else None,
            tuss_code_id=tuss_code_obj.id if tuss_code_obj else None,
            numero_guia=numero_guia,
            tuss_code=tuss_code,
            tuss_descricao=tuss_descricao,
            tabela_tuss=tabela_tuss,
            valor_solicitado=valor_solicitado,
            data_solicitacao=date.today(),
            data_prevista_procedimento=data_prevista_procedimento,
            data_expiracao=self._calculate_expiration_date(),
            status=PreAuthGuideStatus.DRAFT,
            submission_status=PreAuthGuideSubmissionStatus.NOT_SENT,
            observacoes=observacoes,
            dados_adicionais=dados_adicionais,
            created_by=created_by
        )
        
        self.db.add(guide)
        await self.db.flush()
        
        return guide
    
    def _generate_guide_number(self, clinic_id: int) -> str:
        """Gerar número único da guia"""
        # Formato: CLINIC_ID + TIMESTAMP + RANDOM
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4())[:8].upper()
        return f"{clinic_id:04d}{timestamp}{random_part}"
    
    def _calculate_expiration_date(self, days: int = 30) -> date:
        """Calcular data de expiração da solicitação"""
        from datetime import timedelta
        return date.today() + timedelta(days=days)
    
    async def generate_xml(self, guide: TISSPreAuthGuide) -> str:
        """
        Gerar XML da guia de solicitação de autorização no padrão TISS
        
        Formato baseado no padrão TISS 3.05.02 - Guia de Solicitação de Autorização
        """
        # Buscar dados relacionados
        patient_result = await self.db.execute(
            select(Patient).where(Patient.id == guide.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        
        plan_result = await self.db.execute(
            select(InsurancePlanTISS)
            .where(InsurancePlanTISS.id == guide.insurance_plan_id)
            .options(selectinload(InsurancePlanTISS.insurance_company))
        )
        plan = plan_result.scalar_one_or_none()
        
        if not patient or not plan:
            raise ValueError("Paciente ou plano não encontrado")
        
        # Buscar configuração TISS da clínica
        from app.models import TissConfig
        config_result = await self.db.execute(
            select(TissConfig).where(TissConfig.clinic_id == guide.clinic_id)
        )
        tiss_config = config_result.scalar_one_or_none()
        
        if not tiss_config:
            raise ValueError("Configuração TISS da clínica não encontrada")
        
        prestador = tiss_config.prestador or {}
        operadora = tiss_config.operadora or {}
        
        # Gerar XML
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.ans.gov.br/padroes/tiss/schemas http://www.ans.gov.br/padroes/tiss/schemas/tissV3_05_02.xsd">
    <ans:cabecalho>
        <ans:identificacaoTransacao>
            <ans:tipoTransacao>ENVIO_LOTE_GUIAS</ans:tipoTransacao>
            <ans:sequencialTransacao>1</ans:sequencialTransacao>
            <ans:dataRegistroTransacao>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}</ans:dataRegistroTransacao>
            <ans:horaRegistroTransacao>{datetime.now().strftime("%H:%M:%S")}</ans:horaRegistroTransacao>
        </ans:identificacaoTransacao>
        <ans:origem>
            <ans:identificacaoPrestador>
                <ans:cnpjPrestador>{prestador.get('cnpj', '')}</ans:cnpjPrestador>
            </ans:identificacaoPrestador>
        </ans:origem>
        <ans:destino>
            <ans:registroANS>{operadora.get('registro_ans', '')}</ans:registroANS>
        </ans:destino>
        <ans:versaoPadrao>3.05.02</ans:versaoPadrao>
    </ans:cabecalho>
    <ans:prestadorParaOperadora>
        <ans:loteGuias>
            <ans:numeroLote>{guide.numero_guia}</ans:numeroLote>
            <ans:guiasTISS>
                <ans:guiaSolicitacaoSP_SADT>
                    <ans:identificacaoGuiaSolicitacao>
                        <ans:numeroGuiaPrestador>{guide.numero_guia}</ans:numeroGuiaPrestador>
                        <ans:dataSolicitacao>{guide.data_solicitacao.strftime("%Y-%m-%d")}</ans:dataSolicitacao>
                    </ans:identificacaoGuiaSolicitacao>
                    <ans:beneficiario>
                        <ans:numeroCarteira>{plan.numero_plano_ans or ''}</ans:numeroCarteira>
                        <ans:atendimentoRN>N</ans:atendimentoRN>
                        <ans:nomeBeneficiario>{patient.full_name}</ans:nomeBeneficiario>
                        <ans:numeroCNS>{patient.cpf or ''}</ans:numeroCNS>
                        <ans:identificacaoBeneficiario>
                            <ans:cpf>{patient.cpf or ''}</ans:cpf>
                        </ans:identificacaoBeneficiario>
                        <ans:dataNascimento>{patient.date_of_birth.strftime("%Y-%m-%d")}</ans:dataNascimento>
                        <ans:sexo>{patient.gender.value.upper() if patient.gender else 'I'}</ans:sexo>
                    </ans:beneficiario>
                    <ans:solicitante>
                        <ans:contratadoSolicitante>
                            <ans:cnpjContratado>{prestador.get('cnpj', '')}</ans:cnpjContratado>
                            <ans:nomeContratado>{prestador.get('nome', '')}</ans:nomeContratado>
                        </ans:contratadoSolicitante>
                        <ans:profissionalSolicitante>
                            <ans:nomeProfissional>{prestador.get('nome', '')}</ans:nomeProfissional>
                            <ans:conselhoProfissional>
                                <ans:siglaConselho>CRM</ans:siglaConselho>
                                <ans:numeroConselho>{prestador.get('cbo', '')}</ans:numeroConselho>
                                <ans:UFConselho>SP</ans:UFConselho>
                            </ans:conselhoProfissional>
                        </ans:profissionalSolicitante>
                    </ans:solicitante>
                    <ans:procedimentosSolicitados>
                        <ans:procedimentoSolicitado>
                            <ans:dataSolicitacao>{guide.data_solicitacao.strftime("%Y-%m-%d")}</ans:dataSolicitacao>
                            <ans:procedimento>
                                <ans:codigoTabela>{guide.tabela_tuss}</ans:codigoTabela>
                                <ans:codigoProcedimento>{guide.tuss_code}</ans:codigoProcedimento>
                                <ans:descricaoProcedimento>{guide.tuss_descricao}</ans:descricaoProcedimento>
                            </ans:procedimento>
                            <ans:quantidadeSolicitada>1</ans:quantidadeSolicitada>
                            <ans:valorSolicitado>{float(guide.valor_solicitado):.2f}</ans:valorSolicitado>
                        </ans:procedimentoSolicitado>
                    </ans:procedimentosSolicitados>
                    <ans:observacao>{guide.observacoes or ''}</ans:observacao>
                </ans:guiaSolicitacaoSP_SADT>
            </ans:guiasTISS>
        </ans:loteGuias>
    </ans:prestadorParaOperadora>
</ans:mensagemTISS>"""
        
        return xml
    
    async def send_guide(
        self,
        guide: TISSPreAuthGuide,
        method: str = "webservice"
    ) -> Dict:
        """
        Enviar guia ao convênio
        
        Methods:
            - webservice: Enviar via webservice SOAP/REST
            - xml: Salvar XML para envio manual
            - manual: Marcar como enviada manualmente
        """
        if method == "manual":
            return {
                'success': True,
                'message': 'Guia marcada como enviada manualmente',
                'method': 'manual'
            }
        
        if method == "xml":
            # XML já foi gerado, apenas confirmar
            return {
                'success': True,
                'message': 'XML gerado e pronto para envio',
                'method': 'xml',
                'xml_content': guide.xml_content
            }
        
        if method == "webservice":
            # TODO: Implementar envio via webservice
            # Por enquanto, simular envio
            # Em produção, integrar com o serviço de submission TISS
            
            # Simular resposta do convênio
            protocolo = f"PROT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return {
                'success': True,
                'message': 'Guia enviada via webservice',
                'method': 'webservice',
                'protocolo': protocolo
            }
        
        return {
            'success': False,
            'message': f'Método de envio inválido: {method}',
            'method': method
        }
