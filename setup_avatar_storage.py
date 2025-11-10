#!/usr/bin/env python3
"""
Setup script for avatar storage directory
Creates the necessary directory structure for storing user avatars
"""
import os
from pathlib import Path

def setup_avatar_storage():
    """Create avatar storage directory structure"""
    # Get storage directory from environment or use default
    storage_dir = os.getenv("STORAGE_DIR", "storage")
    avatar_dir = os.path.join(storage_dir, "avatars")
    
    # Create directories
    Path(avatar_dir).mkdir(parents=True, exist_ok=True)
    
    # Create .gitkeep to ensure directory is tracked in git
    gitkeep_path = os.path.join(avatar_dir, ".gitkeep")
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, 'w') as f:
            f.write("# This file ensures the avatars directory is tracked in git\n")
    
    print(f"✅ Avatar storage directory created: {avatar_dir}")
    print(f"   Full path: {os.path.abspath(avatar_dir)}")
    
    # Create a README in the storage directory
    readme_path = os.path.join(storage_dir, "README.md")
    if not os.path.exists(readme_path):
        readme_content = """# Storage Directory

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
"""
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"✅ Created README.md in storage directory")

if __name__ == "__main__":
    setup_avatar_storage()

