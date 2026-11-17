"""
Seed initial demo users for MediSync AI.
Run with: python seed_users.py
"""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import get_sync_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash

DEMO_USERS = [
    {
        "email": "admin@medisync.local",
        "full_name": "Chief Medical Officer (Admin)",
        "password": "AdminPassword2026",
        "role": UserRole.ADMIN,
        "is_superuser": True,
    },
    {
        "email": "engineer@medisync.local",
        "full_name": "Sarah Chen (Integration Engineer)",
        "password": "EngineerPass2026",
        "role": UserRole.INTEGRATION_ENGINEER,
        "is_superuser": False,
    },
    {
        "email": "analyst@medisync.local",
        "full_name": "Dr. Marcus Vance (Clinical Analyst)",
        "password": "AnalystPass2026",
        "role": UserRole.CLINICAL_ANALYST,
        "is_superuser": False,
    },
    {
        "email": "viewer@medisync.local",
        "full_name": "Nurse Emily Taylor (Viewer)",
        "password": "ViewerPass2026",
        "role": UserRole.VIEWER,
        "is_superuser": False,
    },
]


def seed():
    print("Seeding demo users...")
    with get_sync_db() as db:
        for u_data in DEMO_USERS:
            existing = db.query(User).filter(User.email == u_data["email"]).first()
            if existing:
                print(f"[-] User already exists: {u_data['email']}")
                continue

            user = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=get_password_hash(u_data["password"]),
                role=u_data["role"],
                is_active=True,
                is_superuser=u_data["is_superuser"],
            )
            db.add(user)
            print(f"[+] Created user: {u_data['email']} (Role: {u_data['role'].value})")

        db.commit()
    print("Demo user seeding completed successfully!")


if __name__ == "__main__":
    seed()
