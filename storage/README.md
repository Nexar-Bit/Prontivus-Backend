# Storage Directory

This directory contains uploaded files for the Prontivus system.

## Structure

- `avatars/` - User profile avatars organized by clinic_id
- `uploads/` - Patient files and documents

## Security

- These directories should not be publicly accessible
- Access is controlled through the FastAPI application
- Files are served through the `/storage` endpoint with authentication

## Backup

Make sure to include this directory in your backup strategy.
