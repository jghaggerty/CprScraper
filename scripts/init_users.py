#!/usr/bin/env python3
"""
Script to initialize the database with default users for testing.
Creates admin, product manager, and business analyst users.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.user_service import UserService
from src.database.connection import get_db_session
from src.database.models import User, Role, UserRole
from sqlalchemy.orm import Session


def create_default_roles(session: Session):
    """Create default roles if they don't exist."""
    roles_data = [
        {
            "name": "admin",
            "display_name": "Administrator",
            "description": "Full system access with user management capabilities",
            "permissions": [
                "dashboard:read", "dashboard:write", "users:read", "users:write",
                "roles:read", "roles:write", "reports:read", "reports:write",
                "notifications:read", "notifications:write", "export:read", "export:write"
            ]
        },
        {
            "name": "product_manager",
            "display_name": "Product Manager",
            "description": "Access to dashboard, reports, and user management for their team",
            "permissions": [
                "dashboard:read", "dashboard:write", "users:read", "users:write",
                "reports:read", "reports:write", "notifications:read", "notifications:write", "export:read"
            ]
        },
        {
            "name": "business_analyst",
            "display_name": "Business Analyst",
            "description": "Access to dashboard, reports, and analytics data",
            "permissions": [
                "dashboard:read", "reports:read", "notifications:read", "export:read"
            ]
        }
    ]
    
    for role_data in roles_data:
        existing_role = session.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_active=True
            )
            session.add(role)
            print(f"Created role: {role_data['display_name']}")
        else:
            print(f"Role already exists: {role_data['display_name']}")
    
    session.commit()


def create_default_users(session: Session, user_service: UserService):
    """Create default users for testing."""
    users_data = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "first_name": "System",
            "last_name": "Administrator",
            "password": "password123",
            "role_names": ["admin"]
        },
        {
            "username": "pm_user",
            "email": "pm@example.com",
            "first_name": "Product",
            "last_name": "Manager",
            "password": "password123",
            "role_names": ["product_manager"]
        },
        {
            "username": "ba_user",
            "email": "ba@example.com",
            "first_name": "Business",
            "last_name": "Analyst",
            "password": "password123",
            "role_names": ["business_analyst"]
        }
    ]
    
    for user_data in users_data:
        existing_user = session.query(User).filter(User.username == user_data["username"]).first()
        if not existing_user:
            try:
                user = user_service.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    password=user_data["password"],
                    role_names=user_data["role_names"]
                )
                print(f"Created user: {user_data['username']} ({user_data['role_names'][0]})")
            except ValueError as e:
                print(f"Error creating user {user_data['username']}: {e}")
        else:
            print(f"User already exists: {user_data['username']}")


def main():
    """Main function to initialize the database."""
    print("Initializing database with default users...")
    
    user_service = UserService()
    
    with get_db_session() as session:
        # Create default roles
        print("\nCreating default roles...")
        create_default_roles(session)
        
        # Create default users
        print("\nCreating default users...")
        create_default_users(session, user_service)
    
    print("\nDatabase initialization complete!")
    print("\nDefault users created:")
    print("- admin / password123 (Administrator)")
    print("- pm_user / password123 (Product Manager)")
    print("- ba_user / password123 (Business Analyst)")
    print("\nYou can now log in to the dashboard using these credentials.")


if __name__ == "__main__":
    main() 