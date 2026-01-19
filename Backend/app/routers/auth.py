import uuid6
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from app.db.base import get_db
from app.db.models import User, FileItem
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký.")

    new_user_id = uuid6.uuid7()
    new_root_id = uuid6.uuid7()
    
    new_user = User(
        id=new_user_id,
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        root_folder_id=new_root_id
    )
    
    root_folder = FileItem(
        id=new_root_id,
        owner_id=new_user_id,
        parent_id=None,
        name="Home",
        type="folder",
        size_bytes=0
    )
    
    try:
        db.add(new_user)
        await db.flush() # Quan trọng: Lưu User ID trước
        db.add(root_folder)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai email hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
