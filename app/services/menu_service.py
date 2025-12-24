"""
Menu Service
Service layer for menu and permission management
"""
from typing import List, Optional, Set, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import time

from app.models import User
from app.models.menu import (
    UserRole as UserRoleModel,
    MenuGroup,
    MenuItem,
    role_menu_permissions
)

# Simple in-memory cache for menu data per role (cleared every 5 minutes)
_menu_cache: Dict[int, Tuple[List[MenuItem], Set[str], List[dict], float]] = {}
_cache_ttl = 300  # 5 minutes


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
    
    async def get_user_role_from_user(self, user: User) -> Optional[UserRoleModel]:
        """
        Get user's role from User object (optimized - no additional query if role is already loaded)
        
        Args:
            user: User object (may already have user_role loaded via selectinload)
            
        Returns:
            UserRole object or None if not found
        """
        # If user_role relationship is already loaded, use it directly
        if user.user_role is not None:
            return user.user_role
        
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
    
    async def get_user_role(self, user_id: int) -> Optional[UserRoleModel]:
        """
        Get user's role from database (legacy method - prefer get_user_role_from_user)
        
        Args:
            user_id: User ID
            
        Returns:
            UserRole object or None if not found
        """
        # Get user with role relationship
        query = select(User).options(selectinload(User.user_role)).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return await self.get_user_role_from_user(user)
    
    async def get_user_menu_from_role_id(self, role_id: int) -> List[MenuItem]:
        """
        Get menu items for a role ID (optimized - doesn't need user object)
        
        Args:
            role_id: Role ID
            
        Returns:
            List of MenuItem objects for this role
        """
        # Get menu items for this role in a single query with group eager loaded
        query = (
            select(MenuItem)
            .join(role_menu_permissions, MenuItem.id == role_menu_permissions.c.menu_item_id)
            .where(
                and_(
                    role_menu_permissions.c.role_id == role_id,
                    MenuItem.is_active == True
                )
            )
            .options(selectinload(MenuItem.group))
            .order_by(MenuItem.group_id, MenuItem.order_index)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_menu(self, user_id: int) -> List[MenuItem]:
        """
        Get menu items available to a user based on their role (legacy method)
        
        Args:
            user_id: User ID
            
        Returns:
            List of MenuItem objects the user can access
        """
        # Get user's role
        role = await self.get_user_role(user_id)
        if not role:
            return []
        
        return await self.get_user_menu_from_role_id(role.id)
    
    async def get_user_permissions_from_menu_items(self, menu_items: List[MenuItem]) -> Set[str]:
        """
        Extract permissions from menu items (optimized - no database query)
        
        Args:
            menu_items: List of MenuItem objects
            
        Returns:
            Set of permission strings
        """
        permissions = set()
        
        for item in menu_items:
            if item.permissions_required:
                if isinstance(item.permissions_required, list):
                    permissions.update(item.permissions_required)
                elif isinstance(item.permissions_required, str):
                    permissions.add(item.permissions_required)
        
        return permissions
    
    async def get_user_permissions(self, user_id: int) -> Set[str]:
        """
        Get all permissions for a user based on their role and menu items (legacy method)
        
        Args:
            user_id: User ID
            
        Returns:
            Set of permission strings
        """
        menu_items = await self.get_user_menu(user_id)
        return await self.get_user_permissions_from_menu_items(menu_items)
    
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
    
    async def get_menu_structure_from_menu_items(self, menu_items: List[MenuItem]) -> List[dict]:
        """
        Build menu structure from menu items (optimized - no database query)
        
        Args:
            menu_items: List of MenuItem objects (with group already loaded)
            
        Returns:
            List of menu groups with their items
        """
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
    
    async def get_menu_structure(self, user_id: int) -> List[dict]:
        """
        Get menu structure grouped by menu groups for a user (legacy method)
        
        Args:
            user_id: User ID
            
        Returns:
            List of menu groups with their items
        """
        menu_items = await self.get_user_menu(user_id)
        return await self.get_menu_structure_from_menu_items(menu_items)
    
    def _get_cached_menu_data(self, role_id: int) -> Optional[Tuple[List[MenuItem], Set[str], List[dict]]]:
        """Get cached menu data for a role if available and not expired"""
        global _menu_cache
        if role_id in _menu_cache:
            menu_items, permissions, menu_structure, cached_time = _menu_cache[role_id]
            if time.time() - cached_time < _cache_ttl:
                return menu_items, permissions, menu_structure
            else:
                # Cache expired, remove it
                del _menu_cache[role_id]
        return None
    
    def _cache_menu_data(self, role_id: int, menu_items: List[MenuItem], permissions: Set[str], menu_structure: List[dict]):
        """Cache menu data for a role"""
        global _menu_cache
        _menu_cache[role_id] = (menu_items, permissions, menu_structure, time.time())
    
    async def get_user_menu_data_optimized(
        self, 
        user: User
    ) -> Tuple[Optional[UserRoleModel], Set[str], List[dict]]:
        """
        Get user role, permissions, and menu structure in optimized way
        This method minimizes database queries by reusing the user object and caching
        
        Args:
            user: User object (should have user_role loaded via selectinload for best performance)
            
        Returns:
            Tuple of (user_role, permissions_set, menu_structure_list)
        """
        # Get role (will use already-loaded relationship if available)
        user_role = await self.get_user_role_from_user(user)
        
        if not user_role or not user_role.id:
            return None, set(), []
        
        role_id = user_role.id
        
        # Check cache first
        cached_data = self._get_cached_menu_data(role_id)
        if cached_data:
            menu_items, permissions, menu_structure = cached_data
            return user_role, permissions, menu_structure
        
        # Get menu items for this role (single query with eager loading)
        menu_items = await self.get_user_menu_from_role_id(role_id)
        
        # Extract permissions and build menu structure from menu_items (no additional queries)
        permissions = await self.get_user_permissions_from_menu_items(menu_items)
        menu_structure = await self.get_menu_structure_from_menu_items(menu_items)
        
        # Cache the results
        self._cache_menu_data(role_id, menu_items, permissions, menu_structure)
        
        return user_role, permissions, menu_structure

