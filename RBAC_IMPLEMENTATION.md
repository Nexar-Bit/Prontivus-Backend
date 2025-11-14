# RBAC Middleware Implementation ✅

## Summary

Role-Based Access Control (RBAC) middleware has been successfully implemented for menu and route protection. The system provides both role-based and permission-based access control with full backward compatibility.

## What Was Implemented

### 1. Permission Middleware (`/backend/app/middleware/permissions.py`) ✅

Created comprehensive permission middleware with the following dependencies:

#### Role-Based Dependencies:
- `RequireRole(roles)` - Check if user has one of the required roles
- `require_super_admin()` - Require SuperAdmin role
- `require_admin_clinica()` - Require AdminClinica role
- `require_medico()` - Require Medico role
- `require_secretaria()` - Require Secretaria role
- `require_paciente()` - Require Paciente role
- `require_staff()` - Require any staff role
- `require_admin()` - Require any admin role

#### Permission-Based Dependencies:
- `RequirePermission(permission)` - Check if user has a specific permission
- `RequireAnyPermission(permissions)` - Check if user has at least one permission (OR logic)
- `RequireAllPermissions(permissions)` - Check if user has all permissions (AND logic)
- `require_permission(permission)` - Convenience function
- `require_any_permission(permissions)` - Convenience function
- `require_all_permissions(permissions)` - Convenience function

### 2. Menu Service (`/backend/app/services/menu_service.py`) ✅

Created menu service with helper functions:

- `get_user_role(user_id: int) -> UserRole` - Get user's role from database
- `get_user_menu(user_id: int) -> List[MenuItem]` - Get menu items available to user
- `get_user_permissions(user_id: int) -> Set[str]` - Get all permissions for user
- `user_has_permission(user_id: int, permission: str) -> bool` - Check specific permission
- `user_can_access_route(user_id: int, route: str) -> bool` - Check route access
- `get_menu_structure(user_id: int) -> List[dict]` - Get menu structure grouped by groups

### 3. JWT Token Extension ✅

Updated JWT token creation to include:
- `role_id` - User's role ID from menu system
- `role_name` - User's role name (e.g., "SuperAdmin", "Medico")
- `permissions` - List of user permissions

**Token Payload Structure:**
```json
{
  "user_id": 1,
  "username": "admin",
  "role": "admin",
  "role_id": 1,
  "role_name": "SuperAdmin",
  "clinic_id": 1,
  "permissions": ["patients.view", "appointments.view", "financial.edit"]
}
```

### 4. Login Response Enhancement ✅

Updated login response to include:
- `menu` - Complete menu structure for the user (grouped by menu groups)
- `permissions` - List of user permissions

**Login Response Structure:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...},
  "menu": [
    {
      "id": 1,
      "name": "Dashboard",
      "items": [...]
    }
  ],
  "permissions": ["patients.view", "appointments.view"]
}
```

### 5. Test Endpoints (`/backend/app/api/endpoints/rbac_test.py`) ✅

Created comprehensive test endpoints:

#### Role-Based Test Endpoints:
- `GET /api/test/rbac/super-admin` - Test SuperAdmin access
- `GET /api/test/rbac/admin-clinica` - Test AdminClinica access
- `GET /api/test/rbac/medico` - Test Medico access
- `GET /api/test/rbac/secretaria` - Test Secretaria access
- `GET /api/test/rbac/paciente` - Test Paciente access
- `GET /api/test/rbac/staff` - Test staff access (any staff role)
- `GET /api/test/rbac/admin` - Test admin access (SuperAdmin or AdminClinica)

#### Permission-Based Test Endpoints:
- `GET /api/test/rbac/permission/{permission}` - Test specific permission
- `GET /api/test/rbac/any-permission` - Test OR logic (any of multiple permissions)
- `GET /api/test/rbac/all-permissions` - Test AND logic (all permissions required)

#### Utility Endpoints:
- `GET /api/test/rbac/user-info` - Get current user's role and permissions
- `GET /api/test/rbac/route-access/{route}` - Test if user can access a route

## Usage Examples

### Using Role-Based Protection

```python
from app.middleware.permissions import require_super_admin, require_staff

@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_super_admin())
):
    """Only SuperAdmin can access"""
    return {"message": "Admin access granted"}

@router.get("/staff-only")
async def staff_endpoint(
    current_user: User = Depends(require_staff())
):
    """Any staff member can access"""
    return {"message": "Staff access granted"}
```

### Using Permission-Based Protection

```python
from app.middleware.permissions import require_permission, require_any_permission

@router.get("/patients")
async def list_patients(
    current_user: User = Depends(require_permission("patients.view"))
):
    """User must have patients.view permission"""
    return {"patients": [...]}

@router.post("/patients")
async def create_patient(
    current_user: User = Depends(require_permission("patients.create"))
):
    """User must have patients.create permission"""
    return {"message": "Patient created"}

@router.get("/reports")
async def get_reports(
    current_user: User = Depends(
        require_any_permission(["reports.view", "reports.admin"])
    )
):
    """User must have at least one of the permissions"""
    return {"reports": [...]}
```

### Using Menu Service

```python
from app.services.menu_service import MenuService

async def some_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    menu_service = MenuService(db)
    
    # Get user's role
    role = await menu_service.get_user_role(current_user.id)
    
    # Get user's permissions
    permissions = await menu_service.get_user_permissions(current_user.id)
    
    # Check specific permission
    can_edit = await menu_service.user_has_permission(
        current_user.id, 
        "patients.edit"
    )
    
    # Check route access
    can_access = await menu_service.user_can_access_route(
        current_user.id,
        "/patients"
    )
```

## Backward Compatibility

✅ **Full backward compatibility maintained:**
- Existing `RoleChecker` from `app.core.auth` still works
- Existing endpoints using `require_admin()`, `require_staff()`, etc. continue to function
- New RBAC middleware can be used alongside existing auth dependencies
- JWT tokens still work with old format (new fields are optional)

## Testing

### Test Role-Based Access:

```bash
# Test as SuperAdmin
curl -H "Authorization: Bearer <superadmin_token>" \
  http://localhost:8000/api/test/rbac/super-admin

# Test as Medico (should fail for super-admin endpoint)
curl -H "Authorization: Bearer <medico_token>" \
  http://localhost:8000/api/test/rbac/super-admin
# Expected: 403 Forbidden

# Test staff endpoint (should work for any staff)
curl -H "Authorization: Bearer <secretary_token>" \
  http://localhost:8000/api/test/rbac/staff
```

### Test Permission-Based Access:

```bash
# Test specific permission
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/test/rbac/permission/patients.view

# Test any permission (OR logic)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/test/rbac/any-permission

# Test all permissions (AND logic)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/test/rbac/all-permissions
```

### Get User Info:

```bash
# Get current user's role and permissions
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/test/rbac/user-info
```

## Integration with Existing Endpoints

To add RBAC protection to existing endpoints, simply replace or add the dependency:

**Before:**
```python
@router.get("/endpoint")
async def endpoint(current_user: User = Depends(get_current_user)):
    ...
```

**After (Role-Based):**
```python
@router.get("/endpoint")
async def endpoint(
    current_user: User = Depends(require_super_admin())
):
    ...
```

**After (Permission-Based):**
```python
@router.get("/endpoint")
async def endpoint(
    current_user: User = Depends(require_permission("endpoint.view"))
):
    ...
```

## Files Created/Modified

### Created:
- `backend/app/middleware/permissions.py` - Permission middleware
- `backend/app/services/menu_service.py` - Menu service
- `backend/app/api/endpoints/rbac_test.py` - Test endpoints

### Modified:
- `backend/app/api/endpoints/auth.py` - Updated login to include menu and permissions
- `backend/app/schemas/auth.py` - Updated LoginResponse schema
- `backend/main.py` - Registered rbac_test router

## Next Steps (Optional Enhancements)

1. **Add Permission Checks to Existing Endpoints:**
   - Update admin endpoints to use `require_super_admin()`
   - Update financial endpoints to use permission checks
   - Update patient endpoints to use role/permission checks

2. **Permission Management UI:**
   - Create admin interface to manage permissions
   - Allow assigning permissions to roles
   - Enable permission testing interface

3. **Permission Caching:**
   - Cache user permissions in Redis
   - Invalidate cache on role/permission changes
   - Improve performance for permission checks

4. **Audit Logging:**
   - Log permission denials
   - Track permission usage
   - Generate permission audit reports

## Notes

- All middleware maintains backward compatibility with existing auth system
- Permission checks are performed against database (can be cached for performance)
- Menu structure is included in login response for frontend use
- JWT tokens include permissions for stateless permission checking (optional)
- Test endpoints are available for verification and debugging

