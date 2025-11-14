"""
Seed Menu Data Script
Creates initial menu structure, roles, and assigns menu items to roles
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from passlib.context import CryptContext

# Database connection will be created in the function
from app.models import User, Clinic
from app.models.menu import UserRole as UserRoleModel, MenuGroup, MenuItem, role_menu_permissions
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_menu_data():
    """Seed initial menu structure and roles"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # ==================== Create User Roles ====================
            print("Creating user roles...")
            
            roles_data = [
                {
                    "name": "SuperAdmin",
                    "description": "Super Administrator with full system access",
                    "is_system": True
                },
                {
                    "name": "AdminClinica",
                    "description": "Clinic Administrator with clinic management access",
                    "is_system": True
                },
                {
                    "name": "Medico",
                    "description": "Doctor with clinical and patient management access",
                    "is_system": True
                },
                {
                    "name": "Secretaria",
                    "description": "Secretary with appointment and patient registration access",
                    "is_system": True
                },
                {
                    "name": "Paciente",
                    "description": "Patient with limited access to own records",
                    "is_system": True
                }
            ]
            
            created_roles = {}
            for role_data in roles_data:
                result = await db.execute(
                    select(UserRoleModel).where(UserRoleModel.name == role_data["name"])
                )
                existing_role = result.scalar_one_or_none()
                
                if not existing_role:
                    role = UserRoleModel(**role_data)
                    db.add(role)
                    await db.flush()
                    created_roles[role_data["name"]] = role
                    print(f"  ✓ Created role: {role_data['name']}")
                else:
                    created_roles[role_data["name"]] = existing_role
                    print(f"  - Role already exists: {role_data['name']}")
            
            await db.commit()
            
            # ==================== Create Menu Groups ====================
            print("\nCreating menu groups...")
            
            groups_data = [
                {"name": "Dashboard", "description": "Main dashboard and overview", "order_index": 1, "icon": "home"},
                {"name": "Pacientes", "description": "Patient management", "order_index": 2, "icon": "users"},
                {"name": "Agendamentos", "description": "Appointment scheduling", "order_index": 3, "icon": "calendar"},
                {"name": "Prontuário", "description": "Clinical records and EHR", "order_index": 4, "icon": "file-text"},
                {"name": "Financeiro", "description": "Financial management", "order_index": 5, "icon": "dollar-sign"},
                {"name": "Estoque", "description": "Inventory management", "order_index": 6, "icon": "package"},
                {"name": "Procedimentos", "description": "Medical procedures", "order_index": 7, "icon": "activity"},
                {"name": "Relatórios", "description": "Reports and analytics", "order_index": 8, "icon": "bar-chart"},
                {"name": "TISS", "description": "TISS integration", "order_index": 9, "icon": "file"},
                {"name": "Administração", "description": "System administration", "order_index": 10, "icon": "settings"},
                {"name": "Configurações", "description": "User and system settings", "order_index": 11, "icon": "cog"},
            ]
            
            created_groups = {}
            for group_data in groups_data:
                result = await db.execute(
                    select(MenuGroup).where(MenuGroup.name == group_data["name"])
                )
                existing_group = result.scalar_one_or_none()
                
                if not existing_group:
                    group = MenuGroup(**group_data)
                    db.add(group)
                    await db.flush()
                    created_groups[group_data["name"]] = group
                    print(f"  ✓ Created group: {group_data['name']}")
                else:
                    created_groups[group_data["name"]] = existing_group
                    print(f"  - Group already exists: {group_data['name']}")
            
            await db.commit()
            
            # ==================== Create Menu Items ====================
            print("\nCreating menu items...")
            
            # Get group IDs
            dashboard_group = created_groups["Dashboard"]
            pacientes_group = created_groups["Pacientes"]
            agendamentos_group = created_groups["Agendamentos"]
            prontuario_group = created_groups["Prontuário"]
            financeiro_group = created_groups["Financeiro"]
            estoque_group = created_groups["Estoque"]
            procedimentos_group = created_groups["Procedimentos"]
            relatorios_group = created_groups["Relatórios"]
            tiss_group = created_groups["TISS"]
            admin_group = created_groups["Administração"]
            config_group = created_groups["Configurações"]
            
            menu_items_data = [
                # Dashboard
                {"group": "Dashboard", "name": "Início", "route": "/dashboard", "icon": "home", "order_index": 1},
                
                # Pacientes
                {"group": "Pacientes", "name": "Cadastros", "route": "/secretaria/cadastros", "icon": "user-plus", "order_index": 1},
                {"group": "Pacientes", "name": "Lista de Pacientes", "route": "/patients", "icon": "users", "order_index": 2},
                {"group": "Pacientes", "name": "Buscar Paciente", "route": "/patients/search", "icon": "search", "order_index": 3},
                
                # Agendamentos
                {"group": "Agendamentos", "name": "Consultas", "route": "/secretaria/consultas", "icon": "calendar", "order_index": 1},
                {"group": "Agendamentos", "name": "Recepção", "route": "/secretaria/recepcao", "icon": "clipboard-check", "order_index": 2},
                {"group": "Agendamentos", "name": "Agenda Médica", "route": "/medico/agenda", "icon": "calendar-days", "order_index": 3},
                
                # Prontuário
                {"group": "Prontuário", "name": "Atendimentos", "route": "/medico/atendimentos", "icon": "stethoscope", "order_index": 1},
                {"group": "Prontuário", "name": "Prontuários", "route": "/medico/prontuarios", "icon": "file-text", "order_index": 2},
                {"group": "Prontuário", "name": "Prescrições", "route": "/medico/prescricoes", "icon": "pill", "order_index": 3},
                
                # Financeiro
                {"group": "Financeiro", "name": "Faturamento", "route": "/financeiro/faturamento", "icon": "receipt", "order_index": 1},
                {"group": "Financeiro", "name": "Pagamentos", "route": "/financeiro/pagamentos", "icon": "credit-card", "order_index": 2},
                {"group": "Financeiro", "name": "Relatórios Financeiros", "route": "/relatorios/financeiro", "icon": "trending-up", "order_index": 3},
                {"group": "Financeiro", "name": "Histórico TISS", "route": "/financeiro/tiss-history", "icon": "history", "order_index": 4},
                
                # Estoque
                {"group": "Estoque", "name": "Gestão de Estoque", "route": "/estoque", "icon": "package", "order_index": 1},
                {"group": "Estoque", "name": "Movimentações", "route": "/estoque/movements", "icon": "arrow-left-right", "order_index": 2},
                
                # Procedimentos
                {"group": "Procedimentos", "name": "Gestão de Procedimentos", "route": "/procedimentos", "icon": "activity", "order_index": 1},
                
                # Relatórios
                {"group": "Relatórios", "name": "Relatórios Clínicos", "route": "/relatorios/clinico", "icon": "file-bar-chart", "order_index": 1},
                {"group": "Relatórios", "name": "Relatórios Operacionais", "route": "/relatorios/operacional", "icon": "bar-chart", "order_index": 2},
                {"group": "Relatórios", "name": "Relatórios Customizados", "route": "/relatorios/custom", "icon": "sliders", "order_index": 3},
                
                # TISS
                {"group": "TISS", "name": "Configuração TISS", "route": "/financeiro/tiss-config", "icon": "settings", "order_index": 1},
                {"group": "TISS", "name": "Templates TISS", "route": "/financeiro/tiss-templates", "icon": "file-code", "order_index": 2},
                
                # Administração
                {"group": "Administração", "name": "Usuários", "route": "/admin/usuarios", "icon": "users", "order_index": 1},
                {"group": "Administração", "name": "Clínicas", "route": "/admin/clinics", "icon": "building", "order_index": 2},
                {"group": "Administração", "name": "Logs do Sistema", "route": "/admin/logs", "icon": "file-text", "order_index": 3},
                {"group": "Administração", "name": "Migração de Dados", "route": "/migration", "icon": "database", "order_index": 4},
                
                # Configurações
                {"group": "Configurações", "name": "Configurações", "route": "/settings", "icon": "settings", "order_index": 1},
                {"group": "Configurações", "name": "Configurações Admin", "route": "/admin/settings", "icon": "shield", "order_index": 2},
            ]
            
            created_items = {}
            for item_data in menu_items_data:
                group = created_groups[item_data["group"]]
                
                result = await db.execute(
                    select(MenuItem).where(
                        MenuItem.group_id == group.id,
                        MenuItem.name == item_data["name"]
                    )
                )
                existing_item = result.scalar_one_or_none()
                
                if not existing_item:
                    item = MenuItem(
                        group_id=group.id,
                        name=item_data["name"],
                        route=item_data["route"],
                        icon=item_data["icon"],
                        order_index=item_data["order_index"]
                    )
                    db.add(item)
                    await db.flush()
                    created_items[f"{item_data['group']}_{item_data['name']}"] = item
                    print(f"  ✓ Created item: {item_data['name']} ({item_data['group']})")
                else:
                    created_items[f"{item_data['group']}_{item_data['name']}"] = existing_item
                    print(f"  - Item already exists: {item_data['name']}")
            
            await db.commit()
            
            # ==================== Assign Menu Items to Roles ====================
            print("\nAssigning menu items to roles...")
            
            # SuperAdmin - All items
            superadmin_role = created_roles["SuperAdmin"]
            for item_key, item in created_items.items():
                # Check if association already exists
                check_result = await db.execute(
                    select(role_menu_permissions).where(
                        and_(
                            role_menu_permissions.c.role_id == superadmin_role.id,
                            role_menu_permissions.c.menu_item_id == item.id
                        )
                    )
                )
                if not check_result.first():
                    await db.execute(
                        role_menu_permissions.insert().values(
                            role_id=superadmin_role.id,
                            menu_item_id=item.id
                        )
                    )
            await db.commit()
            print(f"  ✓ Assigned all items to SuperAdmin")
            
            # AdminClinica - Most items except SuperAdmin-specific
            admin_role = created_roles["AdminClinica"]
            admin_items = [
                "Dashboard_Início",
                "Pacientes_Cadastros",
                "Pacientes_Lista de Pacientes",
                "Pacientes_Buscar Paciente",
                "Agendamentos_Consultas",
                "Agendamentos_Recepção",
                "Prontuário_Atendimentos",
                "Prontuário_Prontuários",
                "Prontuário_Prescrições",
                "Financeiro_Faturamento",
                "Financeiro_Pagamentos",
                "Financeiro_Relatórios Financeiros",
                "Financeiro_Histórico TISS",
                "Estoque_Gestão de Estoque",
                "Estoque_Movimentações",
                "Procedimentos_Gestão de Procedimentos",
                "Relatórios_Relatórios Clínicos",
                "Relatórios_Relatórios Operacionais",
                "Relatórios_Relatórios Customizados",
                "TISS_Configuração TISS",
                "TISS_Templates TISS",
                "Administração_Usuários",
                "Administração_Clínicas",
                "Administração_Logs do Sistema",
                "Configurações_Configurações",
                "Configurações_Configurações Admin",
            ]
            for item_key in admin_items:
                if item_key in created_items:
                    # Check if association already exists
                    check_result = await db.execute(
                        select(role_menu_permissions).where(
                            and_(
                                role_menu_permissions.c.role_id == admin_role.id,
                                role_menu_permissions.c.menu_item_id == created_items[item_key].id
                            )
                        )
                    )
                    if not check_result.first():
                        await db.execute(
                            role_menu_permissions.insert().values(
                                role_id=admin_role.id,
                                menu_item_id=created_items[item_key].id
                            )
                        )
            await db.commit()
            print(f"  ✓ Assigned items to AdminClinica")
            
            # Medico - Clinical and appointment items
            medico_role = created_roles["Medico"]
            medico_items = [
                "Dashboard_Início",
                "Pacientes_Lista de Pacientes",
                "Pacientes_Buscar Paciente",
                "Agendamentos_Agenda Médica",
                "Prontuário_Atendimentos",
                "Prontuário_Prontuários",
                "Prontuário_Prescrições",
                "Relatórios_Relatórios Clínicos",
                "Configurações_Configurações",
            ]
            for item_key in medico_items:
                if item_key in created_items:
                    # Check if association already exists
                    check_result = await db.execute(
                        select(role_menu_permissions).where(
                            and_(
                                role_menu_permissions.c.role_id == medico_role.id,
                                role_menu_permissions.c.menu_item_id == created_items[item_key].id
                            )
                        )
                    )
                    if not check_result.first():
                        await db.execute(
                            role_menu_permissions.insert().values(
                                role_id=medico_role.id,
                                menu_item_id=created_items[item_key].id
                            )
                        )
            await db.commit()
            print(f"  ✓ Assigned items to Medico")
            
            # Secretaria - Patient and appointment management
            secretaria_role = created_roles["Secretaria"]
            secretaria_items = [
                "Dashboard_Início",
                "Pacientes_Cadastros",
                "Pacientes_Lista de Pacientes",
                "Pacientes_Buscar Paciente",
                "Agendamentos_Consultas",
                "Agendamentos_Recepção",
                "Relatórios_Relatórios Operacionais",
                "Configurações_Configurações",
            ]
            for item_key in secretaria_items:
                if item_key in created_items:
                    # Check if association already exists
                    check_result = await db.execute(
                        select(role_menu_permissions).where(
                            and_(
                                role_menu_permissions.c.role_id == secretaria_role.id,
                                role_menu_permissions.c.menu_item_id == created_items[item_key].id
                            )
                        )
                    )
                    if not check_result.first():
                        await db.execute(
                            role_menu_permissions.insert().values(
                                role_id=secretaria_role.id,
                                menu_item_id=created_items[item_key].id
                            )
                        )
            await db.commit()
            print(f"  ✓ Assigned items to Secretaria")
            
            # Paciente - Patient portal items
            paciente_role = created_roles["Paciente"]
            paciente_items = [
                "Dashboard_Início",
                "Agendamentos_Consultas",
                "Prontuário_Prontuários",
                "Configurações_Configurações",
            ]
            for item_key in paciente_items:
                if item_key in created_items:
                    # Check if association already exists
                    check_result = await db.execute(
                        select(role_menu_permissions).where(
                            and_(
                                role_menu_permissions.c.role_id == paciente_role.id,
                                role_menu_permissions.c.menu_item_id == created_items[item_key].id
                            )
                        )
                    )
                    if not check_result.first():
                        await db.execute(
                            role_menu_permissions.insert().values(
                                role_id=paciente_role.id,
                                menu_item_id=created_items[item_key].id
                            )
                        )
            await db.commit()
            print(f"  ✓ Assigned items to Paciente")
            
            # ==================== Create Default SuperAdmin User ====================
            print("\nCreating default SuperAdmin user...")
            
            # Check if SuperAdmin already exists (by username)
            result = await db.execute(
                select(User).where(User.username == "superadmin")
            )
            existing_admin = result.scalar_one_or_none()
            
            if not existing_admin:
                # Get or create a default clinic
                clinic_result = await db.execute(select(Clinic).limit(1))
                clinic = clinic_result.scalar_one_or_none()
                
                if not clinic:
                    clinic = Clinic(
                        name="Default Clinic",
                        legal_name="Default Clinic",
                        tax_id="00000000000000",
                        is_active=True
                    )
                    db.add(clinic)
                    await db.flush()
                    print("  ✓ Created default clinic")
                
                # Create SuperAdmin user
                superadmin_user = User(
                    username="superadmin",
                    email="admin@prontivus.com",
                    hashed_password=pwd_context.hash("admin123"),  # Change this in production!
                    first_name="Super",
                    last_name="Admin",
                    role="admin",  # Legacy enum
                    role_id=superadmin_role.id,
                    clinic_id=clinic.id,
                    is_active=True,
                    is_verified=True,
                    permissions={"all": True}  # Full permissions
                )
                db.add(superadmin_user)
                await db.commit()
                print("  ✓ Created SuperAdmin user (username: superadmin, password: admin123)")
                print("  ⚠️  WARNING: Change the default password in production!")
            else:
                # Update existing admin to have role_id
                if not existing_admin.role_id:
                    existing_admin.role_id = superadmin_role.id
                    await db.commit()
                    print("  ✓ Updated existing admin with role_id")
                else:
                    print("  - SuperAdmin user already exists with role_id")
            
            print("\n✅ Menu data seeding completed successfully!")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding menu data: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_menu_data())

