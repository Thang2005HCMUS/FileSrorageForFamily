import uuid6
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    root_folder_id = Column(UUID(as_uuid=True), nullable=True) # Trỏ logic sang files
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FileItem(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=True, index=True)
    
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True) # 'file' hoặc 'folder'
    
    mime_type = Column(String, nullable=True)
    size_bytes = Column(BigInteger, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def get_physical_path(self):
        # Đường dẫn vật lý: storage/completed/<owner_id>/<file_id>
        if self.type == 'folder':
            return None
        return f"storage/completed/{str(self.owner_id)}/{str(self.id)}"