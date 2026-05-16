from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, create_access_token
from database import get_db
from models import User
from schemas import UserCreate, TokenResponse, MessageResponse

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. Returns 409 if email already exists."""
    # Check for existing email
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user with hashed password
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserCreate, db: Session = Depends(get_db)):
    """Authenticate user and return JWT. Returns 401 with {"message": ...} on failure."""
    user = db.query(User).filter(User.email == user_data.email).first()

    # IMPORTANT: Use JSONResponse, NOT HTTPException
    # Spec requires {"message": "Invalid email or password"} — HTTPException returns {"detail": ...}
    if not user or not verify_password(user_data.password, user.hashed_password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid email or password"},
        )

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token}
