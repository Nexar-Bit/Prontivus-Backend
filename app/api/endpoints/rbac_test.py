"""
RBAC Test Endpoints
Test endpoints to verify role-based and permission-based access control
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User
from app.middleware.permissions import (
    require_super_admin,
    require_admin_clinica,
    require_medico,
    require_secretaria,
    require_paciente,
    require_staff,
    require_admin,
    require_permission,
    require_any_permission,
    require_all_permissions,
    RequireRole,
    RequirePermission
)
from app.services.menu_service import MenuService

router = APIRouter(prefix="/test/rbac", tags=["RBAC Testing"])


class TestResponse(BaseModel):
    """Test endpoint response"""
    message: str
    user_id: int
    username: str
    role: str
    role_name: Optional[str]
    permissions: List[str]
    access_granted: bool


# ==================== Role-Based Test Endpoints ====================

@router.get("/super-admin", response_model=TestResponse)
async def test_super_admin(
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires SuperAdmin role"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="SuperAdmin access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/admin-clinica", response_model=TestResponse)
async def test_admin_clinica(
    current_user: User = Depends(require_admin_clinica()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires AdminClinica role"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="AdminClinica access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/medico", response_model=TestResponse)
async def test_medico(
    current_user: User = Depends(require_medico()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires Medico role"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Medico access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/secretaria", response_model=TestResponse)
async def test_secretaria(
    current_user: User = Depends(require_secretaria()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires Secretaria role"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Secretaria access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/paciente", response_model=TestResponse)
async def test_paciente(
    current_user: User = Depends(require_paciente()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires Paciente role"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Paciente access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/staff", response_model=TestResponse)
async def test_staff(
    current_user: User = Depends(require_staff()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires any staff role (SuperAdmin, AdminClinica, Medico, or Secretaria)"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Staff access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/admin", response_model=TestResponse)
async def test_admin(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires any admin role (SuperAdmin or AdminClinica)"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Admin access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


# ==================== Permission-Based Test Endpoints ====================

@router.get("/permission/{permission}", response_model=TestResponse)
async def test_permission(
    permission: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires a specific permission"""
    menu_service = MenuService(db)
    has_permission = await menu_service.user_has_permission(current_user.id, permission)
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required permission: {permission}"
        )
    
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message=f"Permission '{permission}' access granted",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/any-permission", response_model=TestResponse)
async def test_any_permission(
    current_user: User = Depends(require_any_permission(["patients.view", "appointments.view", "financial.view"])),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires at least one of the specified permissions (OR logic)"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="Any permission access granted (OR logic)",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


@router.get("/all-permissions", response_model=TestResponse)
async def test_all_permissions(
    current_user: User = Depends(require_all_permissions(["patients.view", "appointments.view"])),
    db: AsyncSession = Depends(get_async_session)
):
    """Test endpoint: Requires all specified permissions (AND logic)"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    return TestResponse(
        message="All permissions access granted (AND logic)",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


# ==================== User Info Endpoint ====================

@router.get("/user-info", response_model=TestResponse)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get current user's role and permissions (no restrictions)"""
    menu_service = MenuService(db)
    user_role = await menu_service.get_user_role(current_user.id)
    permissions = await menu_service.get_user_permissions(current_user.id)
    menu_items = await menu_service.get_user_menu(current_user.id)
    
    return TestResponse(
        message=f"User info retrieved. Menu items: {len(menu_items)}",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        role_name=user_role.name if user_role else None,
        permissions=list(permissions),
        access_granted=True
    )


# ==================== Route Access Test ====================

@router.get("/route-access/{route:path}", response_model=dict)
async def test_route_access(
    route: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Test if user can access a specific route"""
    menu_service = MenuService(db)
    can_access = await menu_service.user_can_access_route(current_user.id, route)
    
    return {
        "route": route,
        "user_id": current_user.id,
        "username": current_user.username,
        "can_access": can_access,
        "message": f"User {'can' if can_access else 'cannot'} access route: {route}"
    }

