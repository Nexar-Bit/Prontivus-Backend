"""
TUSS Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from database import get_async_session
from app.models import User
from app.core.auth import get_current_user
from app.services.tiss.tuss_service import TUSSService

router = APIRouter(prefix="/tiss/tuss", tags=["TUSS"])


@router.get("/search")
async def search_tuss_codes(
    search_term: str = Query(..., description="Search term for TUSS code description"),
    tabela: Optional[str] = Query(None, description="Filter by table code"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Search TUSS codes"""
    service = TUSSService(db)
    codes = await service.search_tuss_codes(search_term, tabela, limit)
    
    return {
        "codes": [
            {
                "id": code.id,
                "codigo": code.codigo,
                "descricao": code.descricao,
                "tabela": code.tabela,
                "data_inicio_vigencia": code.data_inicio_vigencia.isoformat(),
                "data_fim_vigencia": code.data_fim_vigencia.isoformat() if code.data_fim_vigencia else None
            }
            for code in codes
        ]
    }


@router.get("/{codigo}")
async def get_tuss_code(
    codigo: str,
    tabela: Optional[str] = Query(None, description="Table code"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get TUSS code by code"""
    service = TUSSService(db)
    code = await service.get_tuss_code(codigo, tabela)
    
    if not code:
        raise HTTPException(status_code=404, detail="TUSS code not found")
    
    return {
        "id": code.id,
        "codigo": code.codigo,
        "descricao": code.descricao,
        "tabela": code.tabela,
        "data_inicio_vigencia": code.data_inicio_vigencia.isoformat(),
        "data_fim_vigencia": code.data_fim_vigencia.isoformat() if code.data_fim_vigencia else None
    }


@router.post("/validate")
async def validate_tuss_code(
    codigo: str,
    tabela: str,
    icd_code: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Validate TUSS code and optionally check ICD compatibility"""
    service = TUSSService(db)
    result = await service.validate_tuss_code(codigo, tabela, icd_code)
    return result

