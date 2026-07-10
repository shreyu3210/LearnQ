from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import database
from app.schemas import user as user_schema, token as token_schema
from app.services import user_service, auth_service

from app.schemas.response import ResponseModel

router = APIRouter()
@router.post("/signup", response_model=ResponseModel[user_schema.User], status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user_signup(user: user_schema.UserCreate, db: Session = Depends(database.get_db)):
    db_user = user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = user_service.create_user(db=db, user=user)
    
    return {
        "status": "success",
        "message": "User created successfully",
        "data": new_user
    }


@router.post("/login", response_model=ResponseModel[token_schema.Token], tags=["Users"])
def login_for_access_token(user_credentials: user_schema.UserLogin, db: Session = Depends(database.get_db)):
    
    
    user = user_service.get_user_by_email(db, email=user_credentials.email)
    if not user or not auth_service.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            
        )
    
    access_token = auth_service.create_access_token(data={"sub": user.email, "name": user.name})
    token_data = {"access_token": access_token, "token_type": "bearer"}
    
    return {
        "status": "success",
        "message": "User logged in successfully",
        "data": token_data
    }

@router.get("/me", response_model=ResponseModel[user_schema.User], tags=["Users"])
def read_users_me(current_user: user_schema.User = Depends(auth_service.get_current_user)):
  return {
        "status": "success",
        "message": "User data retrieved successfully",
        "data": current_user
    }