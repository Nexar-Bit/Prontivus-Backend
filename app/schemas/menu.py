"""
Menu Management Schemas
Pydantic models for menu management API
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserRoleResponse(BaseModel):
    """User Role Response Schema"""
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool = False

    class Config:
        from_attributes = True


class UserRoleCreate(BaseModel):
    """User Role Create Schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    is_system: bool = False


class MenuItemResponse(BaseModel):
    """Menu Item Response Schema"""
    id: int
    group_id: int
    name: str
    route: str
    icon: Optional[str] = None
    order_index: int = 0
    permissions_required: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: bool = True
    is_external: bool = False
    badge: Optional[str] = None

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    """Menu Item Create Schema"""
    group_id: int
    name: str = Field(..., min_length=1, max_length=100)
    route: str = Field(..., min_length=1, max_length=200)
    icon: Optional[str] = Field(None, max_length=50)
    order_index: int = 0
    permissions_required: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: bool = True
    is_external: bool = False
    badge: Optional[str] = Field(None, max_length=20)


class MenuItemUpdate(BaseModel):
    """Menu Item Update Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    route: Optional[str] = Field(None, min_length=1, max_length=200)
    icon: Optional[str] = Field(None, max_length=50)
    order_index: Optional[int] = None
    permissions_required: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_external: Optional[bool] = None
    badge: Optional[str] = Field(None, max_length=20)


class MenuGroupResponse(BaseModel):
    """Menu Group Response Schema"""
    id: int
    name: str
    description: Optional[str] = None
    order_index: int = 0
    icon: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class MenuGroupCreate(BaseModel):
    """Menu Group Create Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    order_index: int = 0
    icon: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class MenuGroupUpdate(BaseModel):
    """Menu Group Update Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    order_index: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class MenuItemGrouped(BaseModel):
    """Menu Item in Grouped Structure"""
    id: int
    name: str
    route: str
    icon: Optional[str] = None
    order_index: int
    description: Optional[str] = None
    badge: Optional[str] = None
    is_external: bool = False


class MenuGroupStructure(BaseModel):
    """Menu Group in Structure Response"""
    id: int
    name: str
    description: Optional[str] = None
    order_index: int
    icon: Optional[str] = None
    items: List[MenuItemGrouped] = []


class MenuStructureResponse(BaseModel):
    """Complete Menu Structure Response"""
    groups: List[MenuGroupStructure] = []

