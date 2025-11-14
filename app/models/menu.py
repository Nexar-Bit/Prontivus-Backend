"""
Menu Management Models
Role-based menu structure for the Prontivus system
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from database import Base
from app.models import BaseModel


class UserRole(BaseModel):
    """
    User Role Model
    Defines system roles: SuperAdmin, AdminClinica, Medico, Secretaria, Paciente
    """
    __tablename__ = "user_roles"
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted
    
    # Relationships
    users = relationship("User", back_populates="user_role")
    menu_items = relationship("MenuItem", secondary="role_menu_permissions", back_populates="roles")


class MenuGroup(BaseModel):
    """
    Menu Group Model
    Groups related menu items together (e.g., "Dashboard", "Patients", "Financial")
    """
    __tablename__ = "menu_groups"
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, default=0, nullable=False, index=True)
    icon = Column(String(50), nullable=True)  # Icon name for the group
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    menu_items = relationship("MenuItem", back_populates="group", cascade="all, delete-orphan", order_by="MenuItem.order_index")


class MenuItem(BaseModel):
    """
    Menu Item Model
    Individual menu items with routes, icons, and permission requirements
    """
    __tablename__ = "menu_items"
    
    group_id = Column(Integer, ForeignKey("menu_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    route = Column(String(200), nullable=False, index=True)  # Frontend route path
    icon = Column(String(50), nullable=True)  # Icon name (e.g., "home", "users")
    order_index = Column(Integer, default=0, nullable=False, index=True)
    permissions_required = Column(JSON, nullable=True)  # List of permission strings required
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_external = Column(Boolean, default=False, nullable=False)  # External link
    badge = Column(String(20), nullable=True)  # Optional badge text
    
    # Relationships
    group = relationship("MenuGroup", back_populates="menu_items")
    roles = relationship("UserRole", secondary="role_menu_permissions", back_populates="menu_items")


# Association table for many-to-many relationship between roles and menu items
from sqlalchemy import Table

role_menu_permissions = Table(
    "role_menu_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("user_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_item_id", Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), primary_key=True),
)

