# Menu System Setup Guide

## Quick Start

The role-based menu management system is **fully implemented** and ready to use. Follow these steps to set it up:

---

## Step 1: Run Database Migration

The migration creates all necessary tables:
- `user_roles`
- `menu_groups`
- `menu_items`
- `role_menu_permissions`
- Adds `role_id` and `permissions` to `users` table

```bash
cd backend
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade add_migration_jobs -> add_menu_management, Add menu management tables and update user model
```

---

## Step 2: Seed Initial Data

Run the seed script to populate:
- 5 user roles (SuperAdmin, AdminClinica, Medico, Secretaria, Paciente)
- 11 menu groups
- 30+ menu items
- Role-menu associations
- Default SuperAdmin user

```bash
cd backend
python seed_menu_data.py
```

**Expected Output:**
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
  ✓ Assigned items to Medico
  ✓ Assigned items to Secretaria
  ✓ Assigned items to Paciente

Creating default SuperAdmin user...
  ✓ Created SuperAdmin user (username: superadmin, password: admin123)
  ⚠️  WARNING: Change the default password in production!

✅ Menu data seeding completed successfully!
```

---

## Step 3: Verify Setup

### 3.1. Check Database Tables

```bash
# Using psql
psql -U postgres -d prontivus_clinic -c "\dt" | grep -E "user_roles|menu_groups|menu_items|role_menu_permissions"

# Or check via Python
python -c "
from database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
menu_tables = [t for t in tables if 'menu' in t or 'role' in t]
print('Menu tables:', menu_tables)
"
```

### 3.2. Test API Endpoint

```bash
# First, login as SuperAdmin to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "admin123"}'

# Use the token to get menu
curl -X GET "http://localhost:8000/api/v1/menu/user" \
  -H "Authorization: Bearer <your_token_here>"
```

**Expected Response:**
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
    },
    ...
  ]
}
```

---

## Step 4: Assign Roles to Existing Users

If you have existing users, update them to use the new role system:

```sql
-- Example: Assign AdminClinica role to a user
UPDATE users 
SET role_id = 2  -- AdminClinica role_id
WHERE username = 'your_admin_username';
```

Or via Python:

```python
from database import get_async_session
from app.models import User
from app.models.menu import UserRole as UserRoleModel
from sqlalchemy import select

async with get_async_session() as db:
    # Get role
    result = await db.execute(
        select(UserRoleModel).where(UserRoleModel.name == "AdminClinica")
    )
    role = result.scalar_one()
    
    # Get user
    result = await db.execute(
        select(User).where(User.username == "your_admin_username")
    )
    user = result.scalar_one()
    
    # Assign role
    user.role_id = role.id
    await db.commit()
```

---

## Step 5: Frontend Integration

The frontend can now fetch the menu structure:

```typescript
// Example: Fetch menu for current user
const response = await fetch(`${API_URL}/api/v1/menu/user`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const menuData = await response.json();
// menuData.groups contains the menu structure
```

---

## Available API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/menu/user` | Get menu for current user |
| GET | `/api/v1/menu/{role_name}` | Get menu for specific role (SuperAdmin only) |

### Admin Endpoints (SuperAdmin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/menu/admin/groups` | Create menu group |
| POST | `/api/v1/menu/admin/items` | Create menu item |
| GET | `/api/v1/menu/admin/roles` | List all roles |
| POST | `/api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}` | Assign menu item to role |
| DELETE | `/api/v1/menu/admin/roles/{role_id}/menu-items/{menu_item_id}` | Remove menu item from role |

---

## Default SuperAdmin Credentials

⚠️ **IMPORTANT: Change these in production!**

- **Username:** `superadmin`  
- **Password:** `admin123`  
- **Email:** `admin@prontivus.com`

---

## Troubleshooting

### Issue: Migration fails
**Solution:**
```bash
# Check current migration status
alembic current

# Check migration history
alembic history

# If needed, manually set revision
alembic stamp head
```

### Issue: Seed script fails
**Solution:**
1. Ensure migration ran successfully first
2. Check database connection in `config.py`
3. Verify all imports are correct
4. Check for duplicate entries (script should handle this)

### Issue: Menu not showing for user
**Solution:**
1. Verify user has `role_id` set:
   ```sql
   SELECT id, username, role_id FROM users WHERE username = 'your_username';
   ```
2. Check if role exists:
   ```sql
   SELECT * FROM user_roles WHERE id = <user_role_id>;
   ```
3. Verify menu items are assigned:
   ```sql
   SELECT mi.name, mi.route 
   FROM menu_items mi
   JOIN role_menu_permissions rmp ON mi.id = rmp.menu_item_id
   WHERE rmp.role_id = <user_role_id> AND mi.is_active = true;
   ```

---

## Next Steps

1. **Change Default Password:** Update SuperAdmin password immediately
2. **Assign Roles:** Update existing users with appropriate `role_id`
3. **Customize Menu:** Add/modify menu items via API or seed script
4. **Frontend Integration:** Update frontend to use menu API
5. **Testing:** Test menu visibility for each role

---

## Files Reference

- **Models:** `backend/app/models/menu.py`
- **Migration:** `backend/alembic/versions/2025_11_13_0027-add_menu_management_tables.py`
- **Seed Script:** `backend/seed_menu_data.py`
- **API Endpoints:** `backend/app/api/endpoints/menu.py`
- **Schemas:** `backend/app/schemas/menu.py`
- **Documentation:** `backend/MENU_SYSTEM_IMPLEMENTATION.md`

---

**Status:** ✅ **READY TO USE**

The system is fully implemented. Run the migration and seed script to get started!

