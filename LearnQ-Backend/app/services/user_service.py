from sqlalchemy.orm import Session
from app.db import models
from app.schemas import user as user_schema
from app.services import auth_service

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: user_schema.UserCreate):
    hashed_password = auth_service.hash_password(user.password)

    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        role=user.role if hasattr(user, 'role') and user.role else 'user'
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user