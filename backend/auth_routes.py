from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth_utils import create_access_token, hash_password, verify_password
from database import get_db
from models import User
from schemas import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/signup", response_model=UserResponse)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    is_active = user_in.role == "customer"
    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        department=user_in.department,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    access_token = create_access_token(
        data={"sub": user.email, "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=60),
    )
    return {"access_token": access_token, "token_type": "bearer"}