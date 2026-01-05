"""
TUSS Service
Manages TUSS (Terminologia Unificada da Saúde Suplementar) codes
"""

import logging
from typing import Optional, List, Dict
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from decimal import Decimal

from app.models.tiss.tuss import TUSSCode, TUSSVersionHistory

logger = logging.getLogger(__name__)


class TUSSService:
    """Service for managing TUSS codes"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tuss_code(
        self, 
        codigo: str, 
        tabela: Optional[str] = None,
        data_vigencia: Optional[date] = None
    ) -> Optional[TUSSCode]:
        """
        Get TUSS code by code and optionally table
        
        Args:
            codigo: TUSS code
            tabela: Table code (optional)
            data_vigencia: Validity date (defaults to today)
        
        Returns:
            TUSSCode object or None
        """
        if data_vigencia is None:
            data_vigencia = date.today()
        
        query = select(TUSSCode).where(
            and_(
                TUSSCode.codigo == codigo,
                TUSSCode.is_active == True,
                TUSSCode.data_inicio_vigencia <= data_vigencia,
                or_(
                    TUSSCode.data_fim_vigencia.is_(None),
                    TUSSCode.data_fim_vigencia >= data_vigencia
                )
            )
        )
        
        if tabela:
            query = query.where(TUSSCode.tabela == tabela)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_tuss_codes(
        self,
        search_term: str,
        tabela: Optional[str] = None,
        limit: int = 50
    ) -> List[TUSSCode]:
        """
        Search TUSS codes by description
        
        Args:
            search_term: Search term (description)
            tabela: Filter by table code (optional)
            limit: Maximum results
        
        Returns:
            List of TUSSCode objects
        """
        query = select(TUSSCode).where(
            and_(
                TUSSCode.descricao.ilike(f"%{search_term}%"),
                TUSSCode.is_active == True
            )
        )
        
        if tabela:
            query = query.where(TUSSCode.tabela == tabela)
        
        query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_tuss_by_table(self, tabela: str) -> List[TUSSCode]:
        """Get all active TUSS codes for a specific table"""
        query = select(TUSSCode).where(
            and_(
                TUSSCode.tabela == tabela,
                TUSSCode.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def validate_tuss_code(
        self,
        codigo: str,
        tabela: str,
        icd_code: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Validate TUSS code and optionally check ICD compatibility
        
        Args:
            codigo: TUSS code
            tabela: Table code
            icd_code: ICD-10 code for compatibility check (optional)
        
        Returns:
            Validation result dictionary
        """
        tuss_code = await self.get_tuss_code(codigo, tabela)
        
        if not tuss_code:
            return {
                "is_valid": False,
                "error": f"TUSS code {codigo} not found in table {tabela}",
                "tuss_code": None
            }
        
        result = {
            "is_valid": True,
            "tuss_code": {
                "codigo": tuss_code.codigo,
                "descricao": tuss_code.descricao,
                "tabela": tuss_code.tabela,
            },
            "icd_compatible": None
        }
        
        # TODO: Implement ICD compatibility check
        if icd_code:
            # This would check if the TUSS code is compatible with the ICD code
            # Implementation depends on ANS compatibility tables
            result["icd_compatible"] = True  # Placeholder
        
        return result
    
    async def import_tuss_codes(
        self,
        codes_data: List[Dict],
        versao_tuss: str
    ) -> Dict[str, int]:
        """
        Import TUSS codes from external source (e.g., ANS file)
        
        Args:
            codes_data: List of TUSS code dictionaries
            versao_tuss: TUSS version
        
        Returns:
            Import statistics
        """
        imported = 0
        updated = 0
        errors = 0
        
        for code_data in codes_data:
            try:
                # Check if code already exists
                existing = await self.get_tuss_code(
                    code_data["codigo"],
                    code_data.get("tabela")
                )
                
                if existing:
                    # Update existing code
                    existing.descricao = code_data.get("descricao", existing.descricao)
                    existing.data_fim_vigencia = code_data.get("data_fim_vigencia")
                    existing.versao_tuss = versao_tuss
                    updated += 1
                else:
                    # Create new code
                    new_code = TUSSCode(
                        codigo=code_data["codigo"],
                        descricao=code_data["descricao"],
                        tabela=code_data["tabela"],
                        data_inicio_vigencia=code_data.get("data_inicio_vigencia", date.today()),
                        data_fim_vigencia=code_data.get("data_fim_vigencia"),
                        versao_tuss=versao_tuss,
                        is_active=True
                    )
                    self.db.add(new_code)
                    imported += 1
                    
                    # Create version history entry
                    history = TUSSVersionHistory(
                        tuss_code_id=new_code.id,
                        versao_nova=versao_tuss,
                        data_alteracao=date.today(),
                        motivo="Importação inicial"
                    )
                    self.db.add(history)
                
            except Exception as e:
                logger.error(f"Error importing TUSS code {code_data.get('codigo')}: {e}")
                errors += 1
        
        await self.db.commit()
        
        return {
            "imported": imported,
            "updated": updated,
            "errors": errors,
            "total": len(codes_data)
        }

