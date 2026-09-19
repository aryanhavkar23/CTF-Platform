"""
CLI utility to bootstrap or promote an administrator account in the CTF Platform.

Usage:
    # Interactive mode:
    python scripts/create_admin.py

    # Non-interactive CLI flag mode:
    python scripts/create_admin.py --username admin --email admin@example.com --password StrongPassword123!
"""

import sys
import os
import argparse
import getpass

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


def create_or_promote_admin(username: str, email: str, password: str = None):
    """Promotes an existing user or creates a new administrator account."""
    db = SessionLocal()
    try:
        email = email.strip().lower()
        username = username.strip()

        # Check if user exists by email or username
        user = db.query(User).filter((User.email == email) | (User.username == username)).first()

        if user:
            user.role = UserRole.ADMIN
            user.is_active = True
            user.is_verified = True
            if password:
                user.hashed_password = hash_password(password)
            db.commit()
            db.refresh(user)
            print(f"[*] Success: Existing user '{user.username}' ({user.email}) has been promoted to ADMIN!")
            return user
        else:
            if not password:
                print("[-] Error: Password is required to create a new administrator account.")
                sys.exit(1)

            new_admin = User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            print(f"[*] Success: New administrator account '{new_admin.username}' ({new_admin.email}) created successfully!")
            return new_admin
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create or promote an administrator account.")
    parser.add_argument("--username", type=str, help="Username of the admin")
    parser.add_argument("--email", type=str, help="Email of the admin")
    parser.add_argument("--password", type=str, help="Password for the admin account (optional if user already exists)")

    args = parser.parse_args()

    username = args.username
    email = args.email
    password = args.password

    # Interactive prompt if flags were not supplied
    if not username and not email:
        username = input("Enter admin username: ").strip()
        email = input("Enter admin email: ").strip()

    # Check if user already exists
    db = SessionLocal()
    existing_user = None
    try:
        q = db.query(User)
        if email:
            existing_user = q.filter(User.email == email.strip().lower()).first()
        if not existing_user and username:
            existing_user = q.filter(User.username == username.strip()).first()
    finally:
        db.close()

    if not existing_user and not password:
        password = getpass.getpass("Enter admin password: ").strip()

    if not username and not email:
        print("[-] Error: Username or email must be provided.")
        sys.exit(1)

    create_or_promote_admin(username or (existing_user.username if existing_user else ""), 
                            email or (existing_user.email if existing_user else ""), 
                            password)



if __name__ == "__main__":
    main()
