"""
Menu Management API Endpoints
Role-based menu structure management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User
from app.models.menu import UserRole as UserRoleModel, MenuGroup, MenuItem
from app.models.menu import role_menu_permissions
from app.schemas.menu import (
    MenuGroupResponse,
    MenuItemResponse,
    MenuStructureResponse,
    UserRoleResponse,
    MenuGroupCreate,
    MenuItemCreate,
    UserRoleCreate,
    MenuItemUpdate,
    MenuGroupUpdate,
)

router = APIRouter(prefix="/menu", tags=["Menu Management"])


@router.get("/user", response_model=MenuStructureResponse)
async def get_user_menu(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get menu structure for the current authenticated user
    
    Returns menu items based on user's role and permissions
    """
    try:
        # Get user's role
        role_id = current_user.role_id
        
        # If user has role_id, use it; otherwise fall back to enum role
        if not role_id:
            # Map enum role to role name
            role_name_map = {
                "admin": "SuperAdmin",
                "secretary": "Secretaria",
                "doctor": "Medico",
                "patient": "Paciente"
            }
            role_name = role_name_map.get(current_user.role.value, "Paciente")
            
            # Find role by name
            result = await db.execute(
                select(UserRoleModel).where(UserRoleModel.name == role_name)
            )
            role = result.scalar_one_or_none()
            if not role:
                # Return empty menu if role not found
                return MenuStructureResponse(groups=[])
            role_id = role.id
        else:
            # Get role object for role_id
            result = await db.execute(
                select(UserRoleModel).where(UserRoleModel.id == role_id)
            )
            role = result.scalar_one_or_none()
            if not role:
                return MenuStructureResponse(groups=[])
        
        # Get menu items for this role
        result = await db.execute(
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
        menu_items = result.scalars().all()
        
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
            })
        
        # Convert to list and sort by order_index
        groups = sorted(groups_dict.values(), key=lambda x: x["order_index"])
        
        return MenuStructureResponse(groups=groups)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user menu: {str(e)}"
        )


@router.get("/{role_name}", response_model=MenuStructureResponse)
async def get_menu_by_role(
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get menu structure for a specific role
    
    Only SuperAdmin can access this endpoint
    """
    # Check if user is SuperAdmin
    if not current_user.role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. SuperAdmin access required."
        )
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. SuperAdmin access required."
        )
    
    # Get role by name
    result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    # Get menu items for this role
    result = await db.execute(
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
    menu_items = result.scalars().all()
    
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
        })
    
    # Convert to list and sort by order_index
    groups = sorted(groups_dict.values(), key=lambda x: x["order_index"])
    
    return MenuStructureResponse(groups=groups)


# ==================== Admin Endpoints (SuperAdmin only) ====================

@router.post("/admin/groups", response_model=MenuGroupResponse)
async def create_menu_group(
    group_data: MenuGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new menu group (SuperAdmin only)"""
    # Verify SuperAdmin access
    if not current_user.role_id:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    group = MenuGroup(
        name=group_data.name,
        description=group_data.description,
        order_index=group_data.order_index,
        icon=group_data.icon,
        is_active=group_data.is_active if group_data.is_active is not None else True
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return MenuGroupResponse.model_validate(group)


@router.post("/admin/items", response_model=MenuItemResponse)
async def create_menu_item(
    item_data: MenuItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new menu item (SuperAdmin only)"""
    # Verify SuperAdmin access
    if not current_user.role_id:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    # Verify group exists
    group_result = await db.execute(
        select(MenuGroup).where(MenuGroup.id == item_data.group_id)
    )
    group = group_result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Menu group not found")
    
    item = MenuItem(
        group_id=item_data.group_id,
        name=item_data.name,
        route=item_data.route,
        icon=item_data.icon,
        order_index=item_data.order_index,
        permissions_required=item_data.permissions_required,
        description=item_data.description,
        is_active=item_data.is_active if item_data.is_active is not None else True,
        is_external=item_data.is_external if item_data.is_external is not None else False,
        badge=item_data.badge
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    return MenuItemResponse.model_validate(item)


@router.get("/admin/roles", response_model=List[UserRoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List all user roles (SuperAdmin only)"""
    # Verify SuperAdmin access
    if not current_user.role_id:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    result = await db.execute(select(UserRoleModel).order_by(UserRoleModel.id))
    roles = result.scalars().all()
    
    return [UserRoleResponse.model_validate(role) for role in roles]


@router.post("/admin/roles/{role_id}/menu-items/{menu_item_id}")
async def assign_menu_item_to_role(
    role_id: int,
    menu_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Assign a menu item to a role (SuperAdmin only)"""
    # Verify SuperAdmin access
    if not current_user.role_id:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    # Verify role and menu item exist
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == role_id)
    )
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    item_result = await db.execute(
        select(MenuItem).where(MenuItem.id == menu_item_id)
    )
    item = item_result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    # Check if association already exists
    result = await db.execute(
        select(role_menu_permissions).where(
            and_(
                role_menu_permissions.c.role_id == role_id,
                role_menu_permissions.c.menu_item_id == menu_item_id
            )
        )
    )
    existing = result.first()
    
    if existing:
        return {"message": "Menu item already assigned to role"}
    
    # Insert association
    await db.execute(
        role_menu_permissions.insert().values(
            role_id=role_id,
            menu_item_id=menu_item_id
        )
    )
    await db.commit()
    
    return {"message": "Menu item assigned to role successfully"}


@router.delete("/admin/roles/{role_id}/menu-items/{menu_item_id}")
async def remove_menu_item_from_role(
    role_id: int,
    menu_item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Remove a menu item from a role (SuperAdmin only)"""
    # Verify SuperAdmin access
    if not current_user.role_id:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    role_result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.id == current_user.role_id)
    )
    user_role = role_result.scalar_one_or_none()
    
    if not user_role or user_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    
    # Delete association
    await db.execute(
        role_menu_permissions.delete().where(
            and_(
                role_menu_permissions.c.role_id == role_id,
                role_menu_permissions.c.menu_item_id == menu_item_id
            )
        )
    )
    await db.commit()
    
    return {"message": "Menu item removed from role successfully"}

