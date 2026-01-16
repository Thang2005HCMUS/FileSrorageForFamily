import uuid6
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

# --- USER MODEL ---
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Thiết kế của bạn: Lưu ID root folder, cho phép NULL (để gán sau hoặc gán lúc tạo)
    # Không dùng ForeignKey để tránh circular dependency lúc insert
    root_folder_id = Column(UUID(as_uuid=True), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- FOLDER MODEL ---
class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # parent_id NULL -> Root (về mặt logic)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)
    
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- FILE MODEL (Để sẵn cho sau này) ---
class FileModel(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    filename = Column(String, nullable=False) # Tên hiển thị
    physical_path = Column(String, nullable=False) # Đường dẫn thật (UUID)
    mime_type = Column(String)
    size_bytes = Column(BigInteger, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())