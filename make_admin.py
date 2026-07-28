from sqlmodel import Session, select
from backend.app.db.database import engine
from backend.app.models.user import User

# This is a one-time script to make a user an admin, for testing RBAC
with Session(engine) as session:
    user = session.exec(select(User).where(User.email == "normaluser2@example.com")).first()
    if user:
        user.role = "admin"
        session.add(user)
        session.commit()
        print(f"{user.email} is now an admin!")
    else:
        print("User not found")