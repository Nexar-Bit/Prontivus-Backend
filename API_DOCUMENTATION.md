# Prontivus Backend API Documentation

Complete list of all backend API endpoints organized by module.

**Base URL:** `/api/v1` (or `/api` for legacy endpoints)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Users](#users)
3. [Patients](#patients)
4. [Appointments](#appointments)
5. [Clinical](#clinical)
6. [Financial](#financial)
7. [TISS](#tiss)
8. [Stock/Inventory](#stockinventory)
9. [Procedures](#procedures)
10. [Analytics](#analytics)
11. [Admin](#admin)
12. [Licenses](#licenses)
13. [Voice Processing](#voice-processing)
14. [Migration](#migration)
15. [Files](#files)
16. [Patient Calling](#patient-calling)
17. [WebSocket Calling](#websocket-calling)
18. [Notifications](#notifications)
19. [User Settings](#user-settings)
20. [Messages](#messages)
21. [Menu Management](#menu-management)
22. [RBAC Testing](#rbac-testing)
23. [Patient Dashboard](#patient-dashboard)
24. [Secretary Dashboard](#secretary-dashboard)
25. [Doctor Dashboard](#doctor-dashboard)
26. [AI Configuration](#ai-configuration)
27. [AI Usage](#ai-usage)
28. [Fiscal Configuration](#fiscal-configuration)
29. [Reports](#reports)
30. [ICD-10](#icd-10)
31. [Payment Methods](#payment-methods)
32. [Report Configuration](#report-configuration)
33. [Support](#support)

---

## Authentication

**Base Path:** `/api/v1/auth`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/auth/loauth/logingin` | User login | Public |
| POST | `/auth/register` | User registration | Public |
| GET | `/auth/me` | Get current user information | Authenticated |
| POST | `/auth/refresh` | Refresh access token | Authenticated |
| POST | `/auth/logout` | User logout | Authenticated |
| GET | `/auth/verify-token` | Verify token validity | Authenticated |
| POST | `/auth/forgot-password` | Request password reset | Public |
| POST | `/auth/reset-password` | Reset password with token | Public |
| GET | `/auth/google/authorize` | Get Google OAuth authorization URL | Public |
| GET | `/auth/google/callback` | Google OAuth callback | Public |

---

## Users

**Base Path:** `/api/v1/users`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/users/doctors` | Get list of doctors for patients to book appointments | Authenticated |
| GET | `/users` | List users in the current clinic | Staff / SuperAdmin |
| POST | `/users` | Create a new user | Admin |
| PATCH | `/users/{user_id}` | Update a user | Admin |
| DELETE | `/users/{user_id}` | Delete a user | Admin |

---

## Patients

**Base Path:** `/api/v1/patients`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/patients` | List all patients for the current user's clinic | Staff |
| GET | `/patients/me` | Get the current user's patient profile | Authenticated |
| PUT | `/patients/me` | Update the current user's patient profile | Authenticated |
| GET | `/patients/{patient_id}` | Get a specific patient by ID | Staff |
| POST | `/patients` | Create a new patient | Staff |
| PUT | `/patients/{patient_id}` | Update a patient | Staff |
| DELETE | `/patients/{patient_id}` | Soft delete a patient | Staff |

---

## Appointments

**Base Path:** `/api/v1/appointments`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/appointments` | List appointments with optional filters | Staff |
| GET | `/appointments/doctor/my-appointments` | Get appointments for the current doctor | Doctor |
| GET | `/appointments/patient-appointments` | Get appointments for the current patient | Patient |
| POST | `/appointments/{appointment_id}/cancel` | Cancel own appointment | Patient |
| POST | `/appointments/patient/book` | Book a new appointment | Patient |
| GET | `/appointments/doctor/{doctor_id}/availability` | Get available time slots for a doctor | Authenticated |
| POST | `/appointments/{appointment_id}/reschedule` | Reschedule own appointment | Patient |
| GET | `/appointments/{appointment_id}` | Get a specific appointment by ID | Staff |
| POST | `/appointments` | Create a new appointment | Staff |
| PUT | `/appointments/{appointment_id}` | Update an appointment | Staff |
| GET | `/appointments/doctor/queue` | Get the queue of patients for the current doctor | Doctor |
| PATCH | `/appointments/{appointment_id}/status` | Update appointment status | Staff |
| DELETE | `/appointments/{appointment_id}` | Delete an appointment | Admin |
| POST | `/appointments/{appointment_id}/consultation-token` | Generate unique room token for video consultation | Staff |
| GET | `/appointments/available-slots` | Get available time slots for a specific doctor | Authenticated |
| WEBSOCKET | `/ws/appointments` | WebSocket channel for real-time appointment updates | Authenticated |

---

## Clinical

**Base Path:** `/api/v1/clinical`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/appointments/{appointment_id}/clinical-record/autosave` | Autosave partial SOAP note changes | Doctor |
| GET | `/clinical-records/{record_id}/versions` | List versions of a clinical record | Staff |
| POST | `/appointments/{appointment_id}/clinical-record` | Create or update SOAP note for an appointment | Doctor |
| GET | `/appointments/{appointment_id}/clinical-record` | Get clinical record for an appointment | Staff |
| GET | `/patients/{patient_id}/clinical-records` | Get patient's complete clinical history | Staff |
| GET | `/clinical/me/history` | Patient self-access to clinical history | Patient |
| GET | `/clinical/doctor/my-clinical-records` | Get all clinical records for current doctor | Doctor |

---

## Financial

**Base Path:** `/api/v1/financial`

### Service Items

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/service-items` | Get list of service items | Authenticated |
| POST | `/financial/service-items` | Create a new service item | Staff |
| PUT | `/financial/service-items/{item_id}` | Update a service item | Staff |
| DELETE | `/financial/service-items/{item_id}` | Delete a service item | Staff |

### Invoices

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/invoices` | Get list of invoices with optional filtering | Staff |
| GET | `/financial/invoices/me` | Get current patient's invoices | Patient |
| GET | `/financial/invoices/{invoice_id}` | Get detailed invoice information | Staff |
| POST | `/financial/invoices` | Create a new invoice | Staff |
| POST | `/financial/invoices/from-appointment` | Create invoice from completed appointment | Staff |
| PUT | `/financial/invoices/{invoice_id}` | Update an invoice | Staff |
| POST | `/financial/invoices/{invoice_id}/mark-paid` | Mark an invoice as paid | Staff |
| GET | `/financial/invoices/{invoice_id}/payments` | Get all payments for a specific invoice | Staff |

### Payments

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/financial/payments` | Create a new payment for an invoice | Staff |
| PUT | `/financial/payments/{payment_id}` | Update a payment | Staff |

### Insurance Plans

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/insurance-plans` | Get list of insurance plans | Authenticated |
| POST | `/financial/insurance-plans` | Create a new insurance plan | Admin |
| PUT | `/financial/insurance-plans/{plan_id}` | Update an insurance plan | Admin |

### Pre-Authorization Requests

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/preauth-requests` | Get list of pre-authorization requests | Staff |
| POST | `/financial/preauth-requests` | Create a new pre-authorization request | Staff |
| PUT | `/financial/preauth-requests/{request_id}` | Update a pre-authorization request | Staff |

### Doctor Financial

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/doctor/accounts-receivable` | Get accounts receivable for current doctor | Doctor |
| GET | `/financial/doctor/delinquency` | Get delinquency (overdue accounts) for current doctor | Doctor |
| GET | `/financial/doctor/accounts-payable` | Get accounts payable for current doctor | Doctor |
| POST | `/financial/doctor/expenses` | Create a new expense for current doctor | Doctor |
| GET | `/financial/doctor/expenses/{expense_id}` | Get a specific expense by ID | Doctor |
| PUT | `/financial/doctor/expenses/{expense_id}` | Update an expense | Doctor |
| DELETE | `/financial/doctor/expenses/{expense_id}` | Delete an expense | Doctor |

### Accounts Receivable

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/accounts-receivable/summary` | Get accounts receivable summary | Staff |
| GET | `/financial/accounts-receivable/aging-report` | Get detailed aging report | Staff |

---

## TISS

**Base Path:** `/api/v1`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/invoices/{invoice_id}/tiss-xml` | Generate and download TISS XML for an invoice | Staff |
| GET | `/invoices/{invoice_id}/tiss-xml/preview` | Preview TISS XML for an invoice | Staff |
| POST | `/invoices/batch-tiss-xml` | Generate TISS XML for multiple invoices (ZIP) | Staff |
| POST | `/invoices/{invoice_id}/tiss-xml/validate` | Validate TISS XML for an invoice | Staff |

---

## TISS Templates

**Base Path:** `/api/v1/financial`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/templates` | Get list of TISS templates | Staff |
| GET | `/financial/templates/{template_id}` | Get a specific TISS template by ID | Staff |
| POST | `/financial/templates` | Create a new TISS template | Staff |
| PUT | `/financial/templates/{template_id}` | Update a TISS template | Staff |
| DELETE | `/financial/templates/{template_id}` | Delete a TISS template | Staff |
| POST | `/financial/admin/{clinic_id}/templates` | Create TISS template for a specific clinic | SuperAdmin |
| GET | `/financial/admin/{clinic_id}/templates` | Get TISS templates for a specific clinic | SuperAdmin |

---

## TISS Config

**Base Path:** `/api/v1/financial`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/financial/tiss-config` | Get TISS config for the current clinic | Staff |
| PUT | `/financial/tiss-config` | Create or update TISS config for current clinic | Staff |
| GET | `/financial/tiss-config/admin/{clinic_id}` | Get TISS config for a specific clinic | SuperAdmin |
| PUT | `/financial/tiss-config/admin/{clinic_id}` | Update TISS config for a specific clinic | SuperAdmin |

---

## Stock/Inventory

**Base Path:** `/api/v1/stock`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/stock/products` | Create a new product | Staff |
| GET | `/stock/products` | Get list of products | Authenticated |
| GET | `/stock/products/{product_id}` | Get a specific product with recent movements | Authenticated |
| PUT | `/stock/products/{product_id}` | Update a product | Staff |
| DELETE | `/stock/products/{product_id}` | Delete a product | Staff |
| POST | `/stock/stock-movements` | Create a new stock movement | Staff |
| POST | `/stock/stock-movements/adjustment` | Manually adjust stock for a product | Staff |
| GET | `/stock/stock-movements` | Get stock movements with optional filters | Staff |
| GET | `/stock/stock-movements/low-stock` | Get products below minimum stock level | Staff |
| GET | `/stock/dashboard/summary` | Get stock dashboard summary | Staff |

---

## Procedures

**Base Path:** `/api/v1/procedures`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/procedures` | Create a new procedure | Staff |
| GET | `/procedures` | Retrieve a list of procedures | Authenticated |
| GET | `/procedures/{procedure_id}` | Retrieve a specific procedure by ID | Authenticated |
| PUT | `/procedures/{procedure_id}` | Update an existing procedure | Staff |
| DELETE | `/procedures/{procedure_id}` | Soft delete a procedure | Staff |
| POST | `/procedures/{procedure_id}/products` | Add a product to a procedure's technical sheet | Staff |
| PUT | `/procedure-products/{procedure_product_id}` | Update a product in a procedure's technical sheet | Staff |
| DELETE | `/procedure-products/{procedure_product_id}` | Remove a product from a procedure's technical sheet | Staff |

---

## Analytics

**Base Path:** `/api/v1/analytics`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/analytics/ping` | Health check for analytics | Authenticated |
| GET | `/analytics/dashboard/stats` | Get dashboard statistics for current clinic | Staff |
| GET | `/analytics/clinical` | Get clinical analytics | Staff |
| GET | `/analytics/financial` | Get financial analytics | Staff |
| GET | `/analytics/operational` | Get operational analytics | Staff |
| GET | `/analytics/inventory` | Get inventory analytics | Staff |
| GET | `/analytics/export/clinical/pdf` | Export clinical report to PDF | Staff |
| GET | `/analytics/export/dashboard/excel` | Export comprehensive dashboard data to Excel | Staff |
| GET | `/analytics/export/financial/excel` | Export financial report to Excel | Staff |
| GET | `/analytics/export/operational/excel` | Export operational report to Excel | Staff |
| POST | `/analytics/schedule` | Schedule a report | Staff |
| POST | `/analytics/custom/run` | Run a custom report | Staff |
| POST | `/analytics/export/custom/excel` | Export custom report to Excel | Staff |
| GET | `/analytics/vital-signs` | Extract and aggregate vital signs from clinical records | Staff |

---

## Admin

**Base Path:** `/api/v1/admin`

### Clinics

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/admin/clinics/stats` | Get clinic statistics | SuperAdmin |
| GET | `/admin/clinics` | List all clinics with filtering options | SuperAdmin |
| GET | `/admin/clinics/me` | Get current user's clinic information | Staff |
| PUT | `/admin/clinics/me` | Update current user's clinic information | Admin |
| GET | `/admin/clinics/{clinic_id}` | Get a specific clinic by ID | SuperAdmin |
| POST | `/admin/clinics` | Create a new clinic | SuperAdmin |
| PUT | `/admin/clinics/{clinic_id}` | Update a clinic | SuperAdmin |
| PATCH | `/admin/clinics/{clinic_id}/license` | Update clinic license information | SuperAdmin |
| DELETE | `/admin/clinics/{clinic_id}` | Delete a clinic from the database | SuperAdmin |

### System Logs

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/admin/logs` | List system logs | SuperAdmin |
| POST | `/admin/logs` | Create a log entry | SuperAdmin |
| PUT | `/admin/logs/{log_id}` | Update a log entry | SuperAdmin |
| DELETE | `/admin/logs/{log_id}` | Delete a log entry | SuperAdmin |

### Modules

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/admin/modules` | Get list of available modules | Staff |
| PATCH | `/admin/clinics/me/modules` | Update current clinic's active modules | Admin |
| PATCH | `/admin/clinics/{clinic_id}/modules` | Update clinic active modules | SuperAdmin |

### Database

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/admin/database/test-connections` | Test database connections for each module | SuperAdmin |

---

## Licenses

**Base Path:** `/api/v1/licenses`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/licenses` | Create a new license | SuperAdmin |
| POST | `/licenses/activate` | Public activation endpoint | Public |
| GET | `/licenses` | List all licenses | SuperAdmin |
| GET | `/licenses/me` | Get current clinic's license information | Staff |
| GET | `/licenses/entitlements` | Get entitlements for current clinic | Staff |
| GET | `/licenses/{license_id}` | Get a specific license by ID | SuperAdmin |
| PUT | `/licenses/{license_id}` | Update a license | SuperAdmin |
| DELETE | `/licenses/{license_id}` | Delete a license (sets status to CANCELLED) | SuperAdmin |

---

## Voice Processing

**Base Path:** `/api/v1/voice`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/voice/process` | Process voice audio and return transcription with medical analysis | Doctor |
| POST | `/voice/sessions` | Create a new voice session for an appointment | Doctor |
| GET | `/voice/sessions/{session_id}` | Get voice session information | Doctor |
| GET | `/voice/sessions` | List voice sessions for the current user | Doctor |
| POST | `/voice/sessions/{session_id}/create-note` | Create a clinical note from voice session data | Doctor |
| GET | `/voice/medical-terms` | Get medical terms for voice processing | Doctor |
| GET | `/voice/configuration` | Get voice processing configuration for current user | Doctor |
| DELETE | `/voice/sessions/{session_id}` | Delete a voice session and its associated data | Doctor |

---

## Migration

**Base Path:** `/api/v1/migration`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/migration/jobs` | Create a migration job | SuperAdmin |
| POST | `/migration/jobs/{job_id}/upload` | Upload migration data | SuperAdmin |
| GET | `/migration/jobs` | List migration jobs | SuperAdmin |
| POST | `/migration/jobs/{job_id}/rollback` | Rollback a migration job | SuperAdmin |

---

## Files

**Base Path:** `/api/v1/files`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/files/upload` | Upload a file | Authenticated |
| GET | `/files` | List files with optional filters | Authenticated |
| GET | `/files/{file_id}` | Download a file | Authenticated |

---

## Patient Calling

**Base Path:** `/api/v1/patient-calling`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/patient-calling/call` | Call a patient for consultation | Staff |
| POST | `/patient-calling/answer/{appointment_id}` | Mark call as answered | Staff |
| POST | `/patient-calling/complete/{appointment_id}` | Mark call as completed | Staff |
| GET | `/patient-calling/active` | Get active calls for the clinic | Staff |

---

## WebSocket Calling

**Base Path:** `/ws`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| WEBSOCKET | `/ws/patient-calling/{clinic_id}` | WebSocket endpoint for patient calling notifications | Authenticated |

---

## Notifications

**Base Path:** `/api/v1/notifications`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/notifications` | Return synthesized notifications for current user | Authenticated |
| POST | `/notifications/{kind}/{source_id}/read` | Mark notification as read | Authenticated |
| DELETE | `/notifications/{kind}/{source_id}` | Delete a notification | Authenticated |

---

## User Settings

**Base Path:** `/api/v1/settings`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/settings/me` | Get current user's settings | Authenticated |
| PUT | `/settings/me` | Update current user's settings | Authenticated |
| POST | `/settings/me/profile` | Update user profile information | Authenticated |
| POST | `/settings/me/avatar` | Upload user avatar image | Authenticated |
| POST | `/settings/me/change-password` | Change user password | Authenticated |
| DELETE | `/settings/me/avatar` | Delete user avatar | Authenticated |
| POST | `/settings/me/test-email` | Send a test email notification | Authenticated |
| POST | `/settings/me/push-subscription` | Subscribe to push notifications | Authenticated |
| POST | `/settings/me/push-subscription/unsubscribe` | Unsubscribe from push notifications | Authenticated |
| GET | `/settings/me/push-public-key` | Get VAPID public key for push notification subscription | Authenticated |
| POST | `/settings/me/test-push` | Send a test push notification | Authenticated |
| POST | `/settings/me/test-sms` | Send a test SMS notification | Authenticated |
| POST | `/settings/me/test-appointment-reminder` | Send a test appointment reminder notification | Authenticated |
| POST | `/settings/me/test-system-update` | Send a test system update notification | Authenticated |
| POST | `/settings/me/test-marketing` | Send a test marketing notification | Authenticated |
| POST | `/settings/me/test-privacy` | Test privacy settings functionality | Authenticated |
| POST | `/settings/me/2fa/setup` | Setup Two Factor Authentication | Authenticated |
| POST | `/settings/me/2fa/verify` | Verify 2FA code and enable 2FA | Authenticated |
| POST | `/settings/me/2fa/disable` | Disable Two Factor Authentication | Authenticated |
| GET | `/settings/me/2fa/status` | Get 2FA status | Authenticated |
| POST | `/settings/me/test-login-alert` | Send a test login alert | Authenticated |

---

## Messages

**Base Path:** `/api/v1/messages`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/messages/threads` | List all message threads for current user | Authenticated |
| GET | `/messages/threads/{thread_id}` | Get a specific thread with all messages | Authenticated |
| POST | `/messages/threads` | Create a new message thread | Authenticated |
| POST | `/messages/threads/{thread_id}/send` | Send a message in a thread | Authenticated |
| DELETE | `/messages/threads/{thread_id}` | Archive (soft delete) a thread | Authenticated |

---

## Menu Management

**Base Path:** `/api/v1/menu`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/menu/user` | Get menu structure for current authenticated user | Authenticated |
| GET | `/menu/{role_name}` | Get menu structure for a specific role | SuperAdmin |
| POST | `/menu/admin/groups` | Create a new menu group | SuperAdmin |
| POST | `/menu/admin/items` | Create a new menu item | SuperAdmin |
| GET | `/menu/admin/roles` | List all user roles | SuperAdmin |
| POST | `/menu/admin/roles/{role_id}/menu-items/{menu_item_id}` | Assign a menu item to a role | SuperAdmin |
| DELETE | `/menu/admin/roles/{role_id}/menu-items/{menu_item_id}` | Remove a menu item from a role | SuperAdmin |

---

## RBAC Testing

**Base Path:** `/api/v1/test/rbac`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/test/rbac/super-admin` | Test endpoint: Requires SuperAdmin role | SuperAdmin |
| GET | `/test/rbac/admin-clinica` | Test endpoint: Requires AdminClinica role | AdminClinica |
| GET | `/test/rbac/medico` | Test endpoint: Requires Medico role | Medico |
| GET | `/test/rbac/secretaria` | Test endpoint: Requires Secretaria role | Secretaria |
| GET | `/test/rbac/paciente` | Test endpoint: Requires Paciente role | Paciente |
| GET | `/test/rbac/staff` | Test endpoint: Requires any staff role | Staff |
| GET | `/test/rbac/admin` | Test endpoint: Requires any admin role | Admin |
| GET | `/test/rbac/permission/{permission}` | Test endpoint: Requires a specific permission | Varies |
| GET | `/test/rbac/any-permission` | Test endpoint: Requires at least one of the specified permissions | Varies |
| GET | `/test/rbac/all-permissions` | Test endpoint: Requires all specified permissions | Varies |
| GET | `/test/rbac/user-info` | Get current user's role and permissions | Authenticated |
| GET | `/test/rbac/route-access/{route:path}` | Test if user can access a specific route | Authenticated |

---

## Patient Dashboard

**Base Path:** `/api/v1/patient`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/patient/dashboard` | Get comprehensive patient dashboard data | Patient |
| GET | `/patient/prescriptions` | Get all prescriptions for current patient | Patient |
| GET | `/patient/exam-results` | Get all exam results for current patient | Patient |

---

## Secretary Dashboard

**Base Path:** `/api/v1/secretary`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/secretary/dashboard` | Get comprehensive secretary dashboard data | Secretary |
| GET | `/secretary/registration-stats` | Get registration statistics for cadastros page | Secretary |
| GET | `/secretary/tasks` | Get tasks for current user's clinic | Secretary |
| POST | `/secretary/tasks` | Create a new task | Secretary |
| PATCH | `/secretary/tasks/{task_id}` | Update a task | Secretary |
| DELETE | `/secretary/tasks/{task_id}` | Delete a task | Secretary |

---

## Doctor Dashboard

**Base Path:** `/api/v1/doctor`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/doctor/dashboard` | Get comprehensive doctor dashboard data | Doctor |
| GET | `/doctor/financial/dashboard` | Get comprehensive financial dashboard data for current doctor | Doctor |
| GET | `/doctor/financial/cash-flow` | Get cash flow data for current doctor | Doctor |

---

## AI Configuration

**Base Path:** `/api/v1/ai-config`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/ai-config` | Get AI configuration for a clinic | Staff |
| PUT | `/ai-config` | Update AI configuration for a clinic | Admin |
| POST | `/ai-config/test-connection` | Test AI connection with provided or saved credentials | Admin |
| GET | `/ai-config/stats` | Get AI usage statistics for a clinic | Staff |
| POST | `/ai-config/reset-monthly-usage` | Reset monthly token usage for a clinic | SuperAdmin |

---

## AI Usage

**Base Path:** `/api/v1/ai`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/ai/analyze-clinical` | Analyze clinical data using AI | Doctor |
| POST | `/ai/suggest-diagnosis` | Suggest possible diagnoses based on symptoms | Doctor |
| POST | `/ai/suggest-treatment` | Generate treatment suggestions for a diagnosis | Doctor |
| POST | `/ai/chat` | General AI chat/completion endpoint | Doctor |

---

## Fiscal Configuration

**Base Path:** `/api/v1/fiscal-config`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/fiscal-config` | Get fiscal configuration | SuperAdmin |
| PUT | `/fiscal-config` | Update fiscal configuration | SuperAdmin |
| POST | `/fiscal-config/test-connection` | Test fiscal integration connection | SuperAdmin |
| POST | `/fiscal-config/upload-certificate` | Upload fiscal certificate | SuperAdmin |
| GET | `/fiscal-config/documents` | Get fiscal documents history | SuperAdmin |
| GET | `/fiscal-config/stats` | Get fiscal integration statistics | SuperAdmin |

---

## Reports

**Base Path:** `/api/v1/reports`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/reports/active-clients` | Get active clients report | SuperAdmin |
| GET | `/reports/active-clients/stats` | Get active clients statistics | SuperAdmin |

---

## ICD-10

**Base Path:** `/api/v1/icd10`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/icd10/import` | Import ICD-10 data from a CSV ZIP package | SuperAdmin |
| POST | `/icd10/import-all` | Import all ICD-10 data from CSV, XML, and CNV packages | SuperAdmin |
| GET | `/icd10/search` | Search ICD-10 codes by normalized text | Authenticated |
| GET | `/icd10/code/{code}` | Lookup a specific ICD-10 code | Authenticated |

---

## Payment Methods

**Base Path:** `/api/v1/payment-methods`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/payment-methods` | Get all payment method configurations for current clinic | Authenticated |
| POST | `/payment-methods` | Create a new payment method configuration | Admin |
| PUT | `/payment-methods/{config_id}` | Update a payment method configuration | Admin |
| DELETE | `/payment-methods/{config_id}` | Delete a payment method configuration | Admin |
| POST | `/payment-methods/initialize` | Initialize default payment method configurations for clinic | Admin |

---

## Report Configuration

**Base Path:** `/api/v1/report-config`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/report-config` | Get report configuration for current clinic | Staff |
| PUT | `/report-config` | Create or update report configuration for current clinic | Admin |

---

## Support

**Base Path:** `/api/v1/support`

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/support/tickets` | Get current patient's support tickets | Patient |
| POST | `/support/tickets` | Create a new support ticket | Patient |
| GET | `/support/tickets/{ticket_id}` | Get a specific support ticket | Patient |
| PUT | `/support/tickets/{ticket_id}` | Update a support ticket (patients can only update their own) | Patient |
| GET | `/support/articles` | Get help articles | Authenticated |
| GET | `/support/articles/categories` | Get list of unique article categories | Authenticated |
| GET | `/support/articles/{article_id}` | Get a specific help article and increment view count | Authenticated |
| POST | `/support/articles/{article_id}/helpful` | Mark a help article as helpful | Authenticated |

---

## Health Check

**Base Path:** `/` (root)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/` | Health check endpoint | Public |
| GET | `/favicon.ico` | Return empty favicon to avoid 404 errors | Public |
| GET | `/api/health` | Detailed health check endpoint | Public |

---

## Access Control Summary

- **Public**: No authentication required
- **Authenticated**: Requires valid JWT token
- **Staff**: Requires any staff role (Admin, Doctor, Secretary)
- **Admin**: Requires AdminClinica role
- **Doctor**: Requires Medico role
- **Secretary**: Requires Secretaria role
- **Patient**: Requires Paciente role
- **SuperAdmin**: Requires SuperAdmin role

---

## Notes

1. All endpoints are prefixed with `/api/v1` (or `/api` for legacy endpoints)
2. Legacy endpoints are deprecated and will be removed in v2.0.0
3. WebSocket endpoints use the `/ws` prefix
4. Static files are served from `/storage` path
5. Most endpoints require authentication via JWT token in the Authorization header
6. Role-based access control (RBAC) is enforced on all endpoints
7. Some endpoints have additional permission-based checks beyond role requirements

---

**Total Endpoints:** ~263+ API endpoints

**Last Updated:** Generated from codebase analysis

