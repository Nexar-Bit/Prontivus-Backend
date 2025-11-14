# User-Related Tables Correlation Report

## ✅ Database Status: All Correlations Are Correct!

---

## 1. User Roles Table (`user_roles`)

**Total Roles:** 5

| ID | Name | Description | is_system |
|----|------|-------------|-----------|
| 1 | **SuperAdmin** | Super Administrator with full system access | True |
| 2 | AdminClinica | Clinic Administrator with clinic management access | True |
| 3 | Medico | Doctor with clinical and patient management access | True |
| 4 | Secretaria | Secretary with appointment and patient registration access | True |
| 5 | Paciente | Patient with limited access to own records | True |

**✅ The SuperAdmin role EXISTS in the database (ID: 1)**

---

## 2. Users Table (`users`)

**Total Users:** 9

### Key Fields:
- `role`: Legacy enum field (UserRole.ADMIN, UserRole.SECRETARY, etc.)
- `role_id`: Foreign key to `user_roles.id` (new role system)
- `clinic_id`: Foreign key to `clinics.id`

### All Users Status:

| Username | Enum Role | role_id | Role Name | Status |
|----------|-----------|---------|-----------|--------|
| superadmin | ADMIN | 1 | SuperAdmin | ✅ Correct |
| admin | ADMIN | 1 | SuperAdmin | ✅ Correct |
| secretary | SECRETARY | 4 | Secretaria | ✅ Correct |
| dr.smith | DOCTOR | 3 | Medico | ✅ Correct |
| dr.jones | DOCTOR | 3 | Medico | ✅ Correct |
| patient1 | PATIENT | 5 | Paciente | ✅ Correct |
| testuser | ADMIN | 1 | SuperAdmin | ✅ Correct |
| testuser123 | ADMIN | 1 | SuperAdmin | ✅ Correct |
| joana123@gmail.com | SECRETARY | 4 | Secretaria | ✅ Correct |

**✅ All users have valid role_id assignments**

---

## 3. Enum Role to Role_ID Mapping

**All mappings are correct (0 mismatches):**

| Enum Role | Expected Role Name | Users Count | Mismatches |
|-----------|-------------------|-------------|------------|
| admin | SuperAdmin | 4 | 0 ✅ |
| secretary | Secretaria | 2 | 0 ✅ |
| doctor | Medico | 2 | 0 ✅ |
| patient | Paciente | 1 | 0 ✅ |

---

## 4. SuperAdmin User Detailed Check

**User: `superadmin`**

- ✅ **ID:** 9
- ✅ **Email:** admin@prontivus.com
- ✅ **Enum Role:** `admin` (UserRole.ADMIN)
- ✅ **Role ID:** 1
- ✅ **Role Name:** `SuperAdmin`
- ✅ **Role Description:** Super Administrator with full system access
- ✅ **Clinic ID:** 2

**✅ The 'superadmin' user is correctly configured with SuperAdmin role**

---

## 5. All Users with Admin Enum Role

**Found 4 users with enum role 'admin':**

1. **superadmin** → role_id=1, role_name='SuperAdmin' ✅
2. **admin** → role_id=1, role_name='SuperAdmin' ✅
3. **testuser** → role_id=1, role_name='SuperAdmin' ✅
4. **testuser123** → role_id=1, role_name='SuperAdmin' ✅

**All admin enum users are correctly mapped to SuperAdmin role**

---

## 6. Foreign Key Constraints

### ✅ All role_id foreign keys are valid
- All `users.role_id` values reference existing `user_roles.id` values
- No orphaned role_id references

### ✅ All clinic_id foreign keys are valid
- All `users.clinic_id` values reference existing `clinics.id` values
- No orphaned clinic_id references

---

## 7. Table Relationships

### Users → UserRoles (Many-to-One)
```
users.role_id → user_roles.id
```

**Status:** ✅ All relationships valid

### Users → Clinics (Many-to-One)
```
users.clinic_id → clinics.id
```

**Status:** ✅ All relationships valid

### UserRoles → MenuItems (Many-to-Many)
```
user_roles.id ← role_menu_permissions → menu_items.id
```

**Status:** ✅ Relationship table exists

---

## 8. Important Notes

### Role Name vs Username
- **Role Name:** `SuperAdmin` (in `user_roles` table, ID: 1)
- **Username:** `superadmin` (in `users` table, lowercase)
- These are **different things**:
  - **Role Name** = The role type (SuperAdmin, AdminClinica, Medico, etc.)
  - **Username** = The login username for a specific user

### Multiple Users Can Have Same Role
- 4 users have the `SuperAdmin` role (role_id=1):
  - superadmin
  - admin
  - testuser
  - testuser123

### Legacy Enum vs New Role System
- **Legacy:** `users.role` enum field (UserRole.ADMIN, UserRole.SECRETARY, etc.)
- **New:** `users.role_id` foreign key to `user_roles` table
- **Mapping:**
  - `UserRole.ADMIN` → `SuperAdmin` (role_id=1)
  - `UserRole.SECRETARY` → `Secretaria` (role_id=4)
  - `UserRole.DOCTOR` → `Medico` (role_id=3)
  - `UserRole.PATIENT` → `Paciente` (role_id=5)

---

## 9. Summary

### ✅ Everything is Correct!

1. ✅ **SuperAdmin role exists** in `user_roles` table (ID: 1, Name: "SuperAdmin")
2. ✅ **'superadmin' user exists** with correct role_id=1
3. ✅ **All foreign key relationships are valid**
4. ✅ **All enum-to-role mappings are correct**
5. ✅ **No orphaned references**
6. ✅ **All users have valid role_id assignments**

### The Confusion Explained

You mentioned: *"There are super admin, admin, doctor, secretary, patient in the role. but there is no super admin role. username is only superadmin."*

**Clarification:**
- ✅ **There IS a SuperAdmin role** in the database (ID: 1, Name: "SuperAdmin")
- ✅ **The username is 'superadmin'** (lowercase) - this is correct
- ✅ **The role name is 'SuperAdmin'** (camelCase) - this is correct
- ✅ **The user 'superadmin' has role_id=1** which points to the SuperAdmin role

**The role name and username are different by design:**
- **Role Name:** `SuperAdmin` (the type of role)
- **Username:** `superadmin` (the login username)

---

## 10. Verification Commands

To verify the correlation yourself:

```bash
# Check roles
python check_database_roles.py

# Check full correlation
python check_user_tables_correlation.py
```

---

**Report Generated:** 2025-01-30  
**Database Status:** ✅ All Correlations Correct

