from fastapi import Depends, HTTPException, status, Request # <-- Thêm Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.base import get_db
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)

async def get_current_user(
    request: Request, # <-- Thêm biến request
    token_in_header: str | None = Depends(oauth2_scheme), # Cho phép Null
    db: AsyncSession = Depends(get_db)
) -> User:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- LOGIC MỚI ---
    # 1. Ưu tiên lấy Token từ Header (Authorization: Bearer ...)
    # 2. Nếu không có, lấy từ URL Query (?token=...)
    token = token_in_header or request.query_params.get("token")

    if not token:
        raise credentials_exception
    # -----------------

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user