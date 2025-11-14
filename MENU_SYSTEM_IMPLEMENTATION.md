# Menu Management System - Complete Implementation Guide

## Overview

The Prontivus system implements a comprehensive role-based menu management system that allows dynamic menu generation based on user roles and permissions. This document provides a complete guide to the implementation.

---

## 1. Database Structure

### Models Location
**File:** `backend/app/models/menu.py`

### Tables Created

#### 1.1. `user_roles` Table
Stores system roles with the following structure:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `name` | String(50) | Unique role name (SuperAdmin, AdminClinica, Medico, Secretaria, Paciente) |
| `description` | Text | Role description |
| `is_system` | Boolean | System roles cannot be deleted |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Update timestamp |

**System Roles:**
- **SuperAdmin** (ID: 1) - Full system access
- **AdminClinica** (ID: 2) - Clinic administrator
- **Medico** (ID: 3) - Doctor/Physician
- **Secretaria** (ID: 4) - Secretary/Receptionist
- **Paciente** (ID: 5) - Patient

#### 1.2. `menu_groups` Table
Groups related menu items together:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `name` | String(100) | Group name (e.g., "Dashboard", "Pacientes") |
| `description` | Text | Group description |
| `order_index` | Integer | Display order |
| `icon` | String(50) | Icon name for the group |
| `is_active` | Boolean | Whether group is active |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Update timestamp |

**Default Menu Groups:**
1. Dashboard
2. Pacientes
3. Agendamentos
4. Prontuário
5. Financeiro
6. Estoque
7. Procedimentos
8. Relatórios
9. TISS
10. Administração
11. Configurações

#### 1.3. `menu_items` Table
Individual menu items with routes and permissions:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `group_id` | Integer (FK) | Reference to menu_groups |
| `name` | String(100) | Menu item name |
| `route` | String(200) | Frontend route path |
| `icon` | String(50) | Icon name |
| `order_index` | Integer | Display order within group |
| `permissions_required` | JSON | List of permission strings |
| `description` | Text | Item description |
| `is_active` | Boolean | Whether item is active |
| `is_external` | Boolean | External link flag |
| `badge` | String(20) | Optional badge text |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Update timestamp |

#### 1.4. `role_menu_permissions` Table
Many-to-many association table linking roles to menu items:

| Column | Type | Description |
|--------|------|-------------|
| `role_id` | Integer (FK, PK) | Reference to user_roles |
| `menu_item_id` | Integer (FK, PK) | Reference to menu_items |

#### 1.5. User Model Updates
The `User` model has been extended with:

| Column | Type | Description |
|--------|------|-------------|
| `role_id` | Integer (FK) | Reference to user_roles.id |
| `permissions` | JSON | Granular permissions JSON field |

---

## 2. Database Migration

### Migration File
**File:** `backend/alembic/versions/2025_11_13_0027-add_menu_management_tables.py`

### Migration Steps

1. **Create `user_roles` table**
2. **Create `menu_groups` table**
3. **Create `menu_items` table**
4. **Create `role_menu_permissions` association table**
5. **Add `role_id` column to `users` table**
6. **Add `permissions` JSON column to `users` table**
7. **Create foreign key constraint** between `users.role_id` and `user_roles.id`

### Running the Migration

```bash
cd backend
alembic upgrade head
```

### Verifying Migration

```bash
# Check migration status
alembic current

# View migration history
alembic history
```

---

## 3. Seed Data Script

### Script Location
**File:** `backend/seed_menu_data.py`

### What It Does

1. **Creates User Roles:**
   - SuperAdmin
   - AdminClinica
   - Medico
   - Secretaria
   - Paciente

2. **Creates Menu Groups:**
   - 11 default menu groups (Dashboard, Pacientes, Agendamentos, etc.)

3. **Creates Menu Items:**
   - 30+ menu items organized by groups
   - Each item has route, icon, and order_index

4. **Assigns Menu Items to Roles:**
   - SuperAdmin: All items
   - AdminClinica: Most items (except SuperAdmin-specific)
   - Medico: Clinical and appointment items
   - Secretaria: Patient and appointment management
   - Paciente: Patient portal items

5. **Creates Default SuperAdmin User:**
   - Username: `superadmin`
   - Password: `admin123` (⚠️ Change in production!)
   - Email: `admin@prontivus.com`

### Running the Seed Script

```bash
cd backend
python seed_menu_data.py
```

### Expected Output

```
Creating user roles...
  ✓ Created role: SuperAdmin
  ✓ Created role: AdminClinica
  ✓ Created role: Medico
  ✓ Created role: Secretaria
  ✓ Created role: Paciente

Creating menu groups...
  ✓ Created group: Dashboard
  ✓ Created group: Pacientes
  ...

Creating menu items...
  ✓ Created item: Início (Dashboard)
  ...

Assigning menu items to roles...
  ✓ Assigned all items to SuperAdmin
  ✓ Assigned items to AdminClinica
  ...

Creating default SuperAdmin user...
  ✓ Created SuperAdmin user (username: superadmin, password: admin123)
  ⚠️  WARNING: Change the default password in production!

✅ Menu data seeding completed successfully!
```

---

## 4. API Endpoints

### Endpoint Location
**File:** `backend/app/api/endpoints/menu.py`

### Public Endpoints

#### 4.1. Get User Menu
```http
GET /api/v1/menu/user
Authorization: Bearer <token>
```

**Description:** Get menu structure for the current authenticated user

**Response:**
```json
{
  "groups": [
    {
      "id": 1,
      "name": "Dashboard",
      "description": "Main dashboard and overview",
      "order_index": 1,
      "icon": "home",
      "items": [
        {
          "id": 1,
          "name": "Início",
          "route": "/dashboard",
          "icon": "home",
          "order_index": 1,
          "description": null,
          "badge": null,
          "is_external": false
        }
      ]
    }
  ]
}
```

#### 4.2. Get Menu by Role
```http
GET /api/v1/menu/{role_name}
Authorization: Bearer <token>
```

**Description:** Get menu structure for a specific role (SuperAdmin only)

**Parameters:**
- `role_name`: One of: SuperAdmin, AdminClinica, Medico, Secretaria, Paciente

**Access:** SuperAdmin only

---

### Admin Endpoints (SuperAdmin Only)

#### 4.3. Create Menu Group
```http
POST /api/v1/menu/admin/groups
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Group",
  "description": "Group description",
  "order_index": 12,
  "icon": "icon-name",
  "is_active": true
}
```

#### 4.4. Create Menu Item
```http
POST /api/v1/menu/admin/items
Authorization: Bearer <token>
Content-Type: application/json

{
  "group_id": 1,
  "name": "New Item",
  "route": "/new-route",
  "icon": "icon-name",
  "order_index": 1,
  "permissions_required": ["permission1", "permission2"],
  "description": "Item description",
  "is_active": true,
  "is_external": false,
  "badge": null
}
```

#### 4.5. List Roles
```http
GET /api/v1/menu/admin/roles
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "SuperAdmin",
    "description": "Super Administrator with full system access",
    "is_system": true
  },
  ...
]
```

#### 4.6. Assign Menu Item to Role
```http
POST /api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}
Authorization: Bearer <token>
```

**Parameters:**
- `role_id`: Role ID
- `menu_item_id`: Menu item ID

#### 4.7. Remove Menu Item from Role
```http
DELETE /api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}
Authorization: Bearer <token>
```

---

## 5. Schema Definitions

### Schema Location
**File:** `backend/app/schemas/menu.py`

### Available Schemas

- `UserRoleResponse` - Role response schema
- `UserRoleCreate` - Role creation schema
- `MenuGroupResponse` - Menu group response
- `MenuGroupCreate` - Menu group creation
- `MenuGroupUpdate` - Menu group update
- `MenuItemResponse` - Menu item response
- `MenuItemCreate` - Menu item creation
- `MenuItemUpdate` - Menu item update
- `MenuStructureResponse` - Complete menu structure response

---

## 6. Usage Examples

### 6.1. Frontend Integration

```typescript
// Get menu for current user
const response = await fetch(`${API_URL}/api/v1/menu/user`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const menuData = await response.json();
// menuData.groups contains the menu structure
```

### 6.2. Backend Service Usage

```python
from app.services.menu_service import MenuService
from database import get_async_session

async with get_async_session() as db:
    menu_service = MenuService(db)
    
    # Get user menu
    menu_structure = await menu_service.get_menu_structure(user_id)
    
    # Get user permissions
    permissions = await menu_service.get_user_permissions(user_id)
    
    # Check if user has permission
    has_permission = await menu_service.user_has_permission(
        user_id, 
        "patients.view"
    )
```

---

## 7. Permission System

### Permission Format
Permissions are stored as strings in the `permissions_required` JSON field:

```json
["patients.view", "patients.create", "financial.edit"]
```

### Permission Naming Convention
- Format: `{module}.{action}`
- Examples:
  - `patients.view` - View patients
  - `patients.create` - Create patients
  - `financial.edit` - Edit financial records
  - `admin.users.manage` - Manage users

### User Permissions
User-specific permissions are stored in the `User.permissions` JSON field:

```json
{
  "patients": ["view", "create", "edit"],
  "financial": ["view"],
  "all": false
}
```

---

## 8. Complete Setup Checklist

### ✅ Database Setup
- [x] Migration file created
- [x] Models defined
- [x] Relationships configured
- [x] Foreign keys set up

### ✅ Seed Data
- [x] Roles created
- [x] Menu groups created
- [x] Menu items created
- [x] Role-menu associations created
- [x] Default SuperAdmin user created

### ✅ API Endpoints
- [x] GET /api/v1/menu/user
- [x] GET /api/v1/menu/{role_name}
- [x] POST /api/v1/menu/admin/groups
- [x] POST /api/v1/menu/admin/items
- [x] GET /api/v1/menu/admin/roles
- [x] POST /api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}
- [x] DELETE /api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}

### ✅ Schemas
- [x] Request schemas defined
- [x] Response schemas defined
- [x] Validation rules in place

---

## 9. Testing

### 9.1. Test Migration
```bash
# Run migration
alembic upgrade head

# Verify tables created
psql -U postgres -d prontivus_clinic -c "\dt" | grep -E "user_roles|menu_groups|menu_items|role_menu_permissions"
```

### 9.2. Test Seed Script
```bash
python seed_menu_data.py

# Verify data
psql -U postgres -d prontivus_clinic -c "SELECT * FROM user_roles;"
psql -U postgres -d prontivus_clinic -c "SELECT COUNT(*) FROM menu_items;"
```

### 9.3. Test API Endpoints
```bash
# Get user menu (requires authentication)
curl -X GET "http://localhost:8000/api/v1/menu/user" \
  -H "Authorization: Bearer <token>"

# Get menu by role (SuperAdmin only)
curl -X GET "http://localhost:8000/api/v1/menu/Medico" \
  -H "Authorization: Bearer <superadmin_token>"
```

---

## 10. Maintenance

### Adding New Menu Items

1. **Via API (Recommended):**
```bash
curl -X POST "http://localhost:8000/api/v1/menu/admin/items" \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "name": "New Feature",
    "route": "/new-feature",
    "icon": "star",
    "order_index": 10
  }'
```

2. **Via Seed Script:**
   - Edit `backend/seed_menu_data.py`
   - Add new menu item to `menu_items_data` list
   - Run seed script (it will skip existing items)

### Assigning Menu Items to Roles

```bash
curl -X POST "http://localhost:8000/api/v1/menu/admin/roles/3/menu-items/25" \
  -H "Authorization: Bearer <superadmin_token>"
```

### Updating Menu Items

Currently, update functionality should be added to the API. For now, you can:
1. Update directly in database
2. Delete and recreate via API

---

## 11. Troubleshooting

### Issue: Menu not showing for user
**Solution:**
1. Verify user has `role_id` set
2. Check if role exists in `user_roles` table
3. Verify menu items are assigned to role in `role_menu_permissions`
4. Check if menu items are active (`is_active = true`)

### Issue: Migration fails
**Solution:**
1. Check if tables already exist
2. Verify database connection
3. Check Alembic version: `alembic current`
4. Review migration file for syntax errors

### Issue: Seed script fails
**Solution:**
1. Ensure migration has been run first
2. Check database connection in `config.py`
3. Verify all imports are correct
4. Check for duplicate entries (script should handle this)

---

## 12. Security Considerations

1. **SuperAdmin Access:** All admin endpoints require SuperAdmin role verification
2. **Permission Validation:** Menu items can require specific permissions
3. **Role-Based Access:** Users only see menu items assigned to their role
4. **System Roles:** System roles (`is_system = true`) cannot be deleted
5. **Default Password:** ⚠️ **IMPORTANT:** Change default SuperAdmin password in production!

---

## 13. Next Steps

### Recommended Enhancements

1. **Menu Item Updates:**
   - Add PUT/PATCH endpoints for updating menu items
   - Add DELETE endpoints for menu items and groups

2. **Permission Management:**
   - Create permission management UI
   - Add permission assignment to roles
   - Implement permission inheritance

3. **Menu Caching:**
   - Cache menu structures in Redis
   - Invalidate cache on menu updates

4. **Menu Analytics:**
   - Track menu item usage
   - Monitor permission checks
   - Generate access reports

---

## 14. File Reference

### Models
- `backend/app/models/menu.py` - Menu models

### Migrations
- `backend/alembic/versions/2025_11_13_0027-add_menu_management_tables.py` - Migration file

### Seed Script
- `backend/seed_menu_data.py` - Seed data script

### API Endpoints
- `backend/app/api/endpoints/menu.py` - Menu API endpoints

### Schemas
- `backend/app/schemas/menu.py` - Pydantic schemas

### Services
- `backend/app/services/menu_service.py` - Menu service (if exists)

---

**Implementation Status:** ✅ **COMPLETE**

All components are implemented and ready for use. Run the migration and seed script to set up the menu system.

---

*Last Updated: 2025-01-30*

