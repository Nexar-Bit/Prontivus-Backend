"""
Permission Middleware
Role-Based Access Control (RBAC) dependencies for route protection
"""
from typing import List, Optional, Union
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User
from app.models.menu import UserRole as UserRoleModel, MenuItem, role_menu_permissions
from app.services.menu_service import MenuService


class RequirePermission:
    """
    Dependency class to check if user has required permission
    """
    
    def __init__(self, permission: str):
        """
        Initialize permission checker
        
        Args:
            permission: Permission string required (e.g., "patients.view", "financial.edit")
        """
        self.permission = permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
    ) -> User:
        """
        Check if current user has the required permission
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            User object if permission granted
            
        Raises:
            HTTPException: If user doesn't have required permission
        """
        menu_service = MenuService(db)
        has_permission = await menu_service.user_has_permission(current_user.id, self.permission)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {self.permission}"
            )
        
        return current_user


class RequireRole:
    """
    Dependency class to check if user has one of the required roles
    """
    
    def __init__(self, roles: Union[str, List[str]]):
        """
        Initialize role checker
        
        Args:
            roles: Single role name or list of role names (e.g., "SuperAdmin" or ["SuperAdmin", "AdminClinica"])
        """
        if isinstance(roles, str):
            self.roles = [roles]
        else:
            self.roles = roles
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
    ) -> User:
        """
        Check if current user has one of the required roles
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            User object if role matches
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        menu_service = MenuService(db)
        user_role = await menu_service.get_user_role(current_user.id)
        
        if not user_role or user_role.name not in self.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.roles)}"
            )
        
        return current_user


class RequireAnyPermission:
    """
    Dependency class to check if user has at least one of the required permissions
    """
    
    def __init__(self, permissions: List[str]):
        """
        Initialize permission checker with multiple permissions (OR logic)
        
        Args:
            permissions: List of permission strings (user needs at least one)
        """
        self.permissions = permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
    ) -> User:
        """
        Check if current user has at least one of the required permissions
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            User object if at least one permission granted
            
        Raises:
            HTTPException: If user doesn't have any of the required permissions
        """
        menu_service = MenuService(db)
        
        for permission in self.permissions:
            if await menu_service.user_has_permission(current_user.id, permission):
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required one of: {', '.join(self.permissions)}"
        )


class RequireAllPermissions:
    """
    Dependency class to check if user has all required permissions
    """
    
    def __init__(self, permissions: List[str]):
        """
        Initialize permission checker with multiple permissions (AND logic)
        
        Args:
            permissions: List of permission strings (user needs all)
        """
        self.permissions = permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
    ) -> User:
        """
        Check if current user has all required permissions
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            User object if all permissions granted
            
        Raises:
            HTTPException: If user doesn't have all required permissions
        """
        menu_service = MenuService(db)
        
        for permission in self.permissions:
            if not await menu_service.user_has_permission(current_user.id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Missing permission: {permission}"
                )
        
        return current_user


# Convenience functions for common role checks
def require_super_admin():
    """Require SuperAdmin role"""
    return RequireRole("SuperAdmin")


def require_admin_clinica():
    """Require AdminClinica role"""
    return RequireRole("AdminClinica")


def require_medico():
    """Require Medico role"""
    return RequireRole("Medico")


def require_secretaria():
    """Require Secretaria role"""
    return RequireRole("Secretaria")


def require_paciente():
    """Require Paciente role"""
    return RequireRole("Paciente")


def require_staff():
    """Require any staff role (SuperAdmin, AdminClinica, Medico, or Secretaria)"""
    return RequireRole(["SuperAdmin", "AdminClinica", "Medico", "Secretaria"])


def require_admin():
    """Require any admin role (SuperAdmin or AdminClinica)"""
    return RequireRole(["SuperAdmin", "AdminClinica"])


# Convenience functions for common permission checks
def require_permission(permission: str):
    """
    Require a specific permission
    
    Args:
        permission: Permission string (e.g., "patients.view", "financial.edit")
        
    Returns:
        RequirePermission dependency
    """
    return RequirePermission(permission)


def require_any_permission(permissions: List[str]):
    """
    Require at least one of the specified permissions (OR logic)
    
    Args:
        permissions: List of permission strings
        
    Returns:
        RequireAnyPermission dependency
    """
    return RequireAnyPermission(permissions)


def require_all_permissions(permissions: List[str]):
    """
    Require all specified permissions (AND logic)
    
    Args:
        permissions: List of permission strings
        
    Returns:
        RequireAllPermissions dependency
    """
    return RequireAllPermissions(permissions)

