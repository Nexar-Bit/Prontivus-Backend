# Menu Management System Setup Guide

This guide explains how to set up and use the role-based menu management system.

## Overview

The menu management system provides:
- **Role-based menu structure**: Different menu items for different user roles
- **Dynamic menu generation**: Menus are generated based on user's role and permissions
- **Admin management**: SuperAdmin can manage menu structure via API
- **Granular permissions**: Each menu item can have specific permission requirements

## Database Structure

### Tables Created

1. **user_roles**: System roles (SuperAdmin, AdminClinica, Medico, Secretaria, Paciente)
2. **menu_groups**: Groups of related menu items (e.g., "Dashboard", "Pacientes")
3. **menu_items**: Individual menu items with routes and icons
4. **role_menu_permissions**: Many-to-many relationship between roles and menu items

### User Model Updates

- `role_id`: Foreign key to `user_roles` table
- `permissions`: JSON field for granular permissions

## Setup Instructions

### 1. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This will create all the menu-related tables and update the users table.

### 2. Seed Initial Data

Run the seed script to populate initial menu structure:

```bash
cd backend
python seed_menu_data.py
```

This script will:
- Create 5 system roles (SuperAdmin, AdminClinica, Medico, Secretaria, Paciente)
- Create 11 menu groups
- Create ~30 menu items
- Assign menu items to appropriate roles
- Create a default SuperAdmin user (username: `superadmin`, password: `admin123`)

**⚠️ IMPORTANT**: Change the default SuperAdmin password in production!

### 3. Update Existing Users (Optional)

If you have existing users in the database, update them to have `role_id`:

```bash
cd backend
python update_users_role_id.py
```

This script maps existing enum roles to the new `role_id` foreign keys.

### 4. Verify Setup

Check that the migration ran successfully:

```bash
# Check database tables
psql -U your_user -d your_database -c "\dt" | grep -E "(user_roles|menu_groups|menu_items|role_menu_permissions)"

# Check seeded data
psql -U your_user -d your_database -c "SELECT COUNT(*) FROM user_roles;"
psql -U your_user -d your_database -c "SELECT COUNT(*) FROM menu_groups;"
psql -U your_user -d your_database -c "SELECT COUNT(*) FROM menu_items;"
```

## API Endpoints

### User Endpoints

#### Get Current User's Menu
```http
GET /api/menu/user
Authorization: Bearer <token>
```

Returns menu structure for the authenticated user based on their role.

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

#### Get Menu for Specific Role (SuperAdmin only)
```http
GET /api/menu/{role_name}
Authorization: Bearer <superadmin_token>
```

Returns menu structure for a specific role. Only SuperAdmin can access this.

### Admin Endpoints (SuperAdmin only)

#### Create Menu Group
```http
POST /api/menu/admin/groups
Authorization: Bearer <superadmin_token>
Content-Type: application/json

{
  "name": "New Group",
  "description": "Group description",
  "order_index": 12,
  "icon": "star",
  "is_active": true
}
```

#### Create Menu Item
```http
POST /api/menu/admin/items
Authorization: Bearer <superadmin_token>
Content-Type: application/json

{
  "group_id": 1,
  "name": "New Item",
  "route": "/new-route",
  "icon": "star",
  "order_index": 1,
  "permissions_required": ["permission1", "permission2"],
  "description": "Item description",
  "is_active": true,
  "is_external": false,
  "badge": null
}
```

#### List All Roles
```http
GET /api/menu/admin/roles
Authorization: Bearer <superadmin_token>
```

#### Assign Menu Item to Role
```http
POST /api/menu/admin/roles/{role_id}/menu-items/{menu_item_id}
Authorization: Bearer <superadmin_token>
```

#### Remove Menu Item from Role
```http
DELETE /api/menu/admin/roles/{role_id}/menu-items/{menu_item_id}
Authorization: Bearer <superadmin_token>
```

## Role Structure

### SuperAdmin
- Full system access
- All menu items
- Can manage menu structure

### AdminClinica
- Clinic management
- Patient management
- Financial management
- Reports
- Most administrative functions

### Medico
- Clinical records
- Patient information
- Appointments
- Prescriptions
- Clinical reports

### Secretaria
- Patient registration
- Appointment scheduling
- Reception
- Operational reports

### Paciente
- Own appointments
- Own medical records
- Own settings
- Limited access

## Frontend Integration

### Fetching User Menu

```typescript
// Fetch menu for current user
const response = await fetch('/api/menu/user', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const menuData = await response.json();

// Render menu structure
menuData.groups.forEach(group => {
  console.log(`Group: ${group.name}`);
  group.items.forEach(item => {
    console.log(`  - ${item.name}: ${item.route}`);
  });
});
```

### Example Menu Structure

```typescript
interface MenuGroup {
  id: number;
  name: string;
  description?: string;
  order_index: number;
  icon?: string;
  items: MenuItem[];
}

interface MenuItem {
  id: number;
  name: string;
  route: string;
  icon?: string;
  order_index: number;
  description?: string;
  badge?: string;
  is_external: boolean;
}
```

## Migration Details

The migration file `2025_11_13_0027-add_menu_management_tables.py` creates:

1. **user_roles** table with columns:
   - id, name, description, is_system, created_at, updated_at

2. **menu_groups** table with columns:
   - id, name, description, order_index, icon, is_active, created_at, updated_at

3. **menu_items** table with columns:
   - id, group_id, name, route, icon, order_index, permissions_required (JSON), 
   - description, is_active, is_external, badge, created_at, updated_at

4. **role_menu_permissions** association table:
   - role_id, menu_item_id (composite primary key)

5. Updates **users** table:
   - Adds `role_id` column (foreign key to user_roles)
   - Adds `permissions` column (JSON field)

## Troubleshooting

### Migration Fails

If migration fails, check:
1. Database connection settings in `config.py`
2. Previous migrations are applied: `alembic current`
3. Database user has CREATE TABLE permissions

### Seed Script Fails

If seed script fails:
1. Ensure migration has been run first
2. Check database connection
3. Verify no duplicate data exists (script handles this gracefully)

### Menu Not Showing

If menu endpoints return empty:
1. Verify user has `role_id` set
2. Check that menu items are assigned to user's role
3. Verify menu items are active (`is_active = true`)
4. Check user's role exists in `user_roles` table

### Permission Denied

If getting 403 errors:
1. Verify user has `role_id` set
2. Check that user's role is "SuperAdmin" for admin endpoints
3. Verify JWT token is valid and not expired

## Next Steps

1. **Update existing users**: Assign `role_id` to existing users based on their `role` enum
2. **Customize menus**: Use admin endpoints to customize menu structure
3. **Add permissions**: Implement permission checking in frontend based on `permissions_required` field
4. **Frontend integration**: Update frontend to fetch and render menus dynamically

## Security Notes

- SuperAdmin endpoints require authentication and SuperAdmin role
- Menu items can have `permissions_required` for additional checks
- User's `permissions` JSON field can store granular permissions
- Always validate permissions on both frontend and backend

