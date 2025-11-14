"""
Menu Service
Service layer for menu and permission management
"""
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models import User
from app.models.menu import (
    UserRole as UserRoleModel,
    MenuGroup,
    MenuItem,
    role_menu_permissions
)


class MenuService:
    """
    Service for menu and permission operations
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize menu service
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_user_role(self, user_id: int) -> Optional[UserRoleModel]:
        """
        Get user's role from database
        
        Args:
            user_id: User ID
            
        Returns:
            UserRole object or None if not found
        """
        # Get user with role relationship
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # If user has role_id, get role from that
        if user.role_id:
            role_query = select(UserRoleModel).where(UserRoleModel.id == user.role_id)
            role_result = await self.db.execute(role_query)
            return role_result.scalar_one_or_none()
        
        # Fallback: Map enum role to role name
        role_name_map = {
            "admin": "SuperAdmin",
            "secretary": "Secretaria",
            "doctor": "Medico",
            "patient": "Paciente"
        }
        
        role_name = role_name_map.get(user.role.value)
        if not role_name:
            return None
        
        # Find role by name
        role_query = select(UserRoleModel).where(UserRoleModel.name == role_name)
        role_result = await self.db.execute(role_query)
        return role_result.scalar_one_or_none()
    
    async def get_user_menu(self, user_id: int) -> List[MenuItem]:
        """
        Get menu items available to a user based on their role
        
        Args:
            user_id: User ID
            
        Returns:
            List of MenuItem objects the user can access
        """
        # Get user's role
        role = await self.get_user_role(user_id)
        if not role:
            return []
        
        # Get menu items for this role
        query = (
            select(MenuItem)
            .join(role_menu_permissions, MenuItem.id == role_menu_permissions.c.menu_item_id)
            .where(
                and_(
                    role_menu_permissions.c.role_id == role.id,
                    MenuItem.is_active == True
                )
            )
            .options(selectinload(MenuItem.group))
            .order_by(MenuItem.group_id, MenuItem.order_index)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_permissions(self, user_id: int) -> Set[str]:
        """
        Get all permissions for a user based on their role and menu items
        
        Args:
            user_id: User ID
            
        Returns:
            Set of permission strings
        """
        menu_items = await self.get_user_menu(user_id)
        permissions = set()
        
        for item in menu_items:
            if item.permissions_required:
                if isinstance(item.permissions_required, list):
                    permissions.update(item.permissions_required)
                elif isinstance(item.permissions_required, str):
                    permissions.add(item.permissions_required)
        
        return permissions
    
    async def user_has_permission(self, user_id: int, permission: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user_id: User ID
            permission: Permission string to check
            
        Returns:
            True if user has permission, False otherwise
        """
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def user_can_access_route(self, user_id: int, route: str) -> bool:
        """
        Check if user can access a specific route based on menu items
        
        Args:
            user_id: User ID
            route: Route path to check
            
        Returns:
            True if user can access route, False otherwise
        """
        menu_items = await self.get_user_menu(user_id)
        return any(item.route == route for item in menu_items)
    
    async def get_menu_structure(self, user_id: int) -> List[dict]:
        """
        Get menu structure grouped by menu groups for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of menu groups with their items
        """
        menu_items = await self.get_user_menu(user_id)
        
        # Group items by menu group
        groups_dict = {}
        for item in menu_items:
            group = item.group
            if group.id not in groups_dict:
                groups_dict[group.id] = {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "order_index": group.order_index,
                    "icon": group.icon,
                    "items": []
                }
            
            groups_dict[group.id]["items"].append({
                "id": item.id,
                "name": item.name,
                "route": item.route,
                "icon": item.icon,
                "order_index": item.order_index,
                "description": item.description,
                "badge": item.badge,
                "is_external": item.is_external,
                "permissions_required": item.permissions_required,
            })
        
        # Convert to list and sort by order_index
        groups = sorted(groups_dict.values(), key=lambda x: x["order_index"])
        
        return groups

