"""
TISS API Endpoints
Complete TISS module endpoints
"""

from .consultation import router as consultation_router
from .sadt import router as sadt_router
from .hospitalization import router as hospitalization_router
from .individual_fee import router as individual_fee_router
from .batch import router as batch_router
from .tuss import router as tuss_router
from .submission import router as submission_router
from .insurance_structure import router as insurance_structure_router
from .preauth import router as preauth_router

__all__ = [
    'consultation_router', 
    'sadt_router',
    'hospitalization_router',
    'individual_fee_router',
    'batch_router', 
    'tuss_router', 
    'submission_router',
    'insurance_structure_router',
    'preauth_router',
]

