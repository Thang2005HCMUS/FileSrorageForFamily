import uuid6
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.db.models import User, Folder
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from datetime import timedelta

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Check email trùng
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email này đã được đăng ký."
        )

    # 2. Logic Transaction
    new_user_id = uuid6.uuid7()
    new_folder_id = uuid6.uuid7()
    
    # Tạo User Object
    new_user = User(
        id=new_user_id,
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        root_folder_id=new_folder_id 
    )
    
    # Tạo Folder Object
    root_folder = Folder(
        id=new_folder_id,
        owner_id=new_user_id,
        parent_id=None,
        name="Home"
    )
    
    try:
        # --- SỬA ĐỔI QUAN TRỌNG TẠI ĐÂY ---
        
        # Bước A: Thêm User vào session
        db.add(new_user)
        
        # Bước B: Đẩy User xuống DB ngay lập tức (nhưng chưa Commit hẳn)
        # Để bảng 'users' có dữ liệu ID này trước.
        await db.flush() 
        
        # Bước C: Bây giờ mới thêm Folder (lúc này DB đã thấy User ID rồi nên không lỗi FK)
        db.add(root_folder)
        
        # Bước D: Chốt đơn tất cả
        await db.commit()
        await db.refresh(new_user)
        
        return new_user
        
    except Exception as e:
        await db.rollback()
        # In lỗi ra console để dễ debug nếu có lỗi khác
        print(f"Error Registering: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Tìm user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # 2. Check pass
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Tạo Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, # Lưu User ID vào token
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}