-- Xóa bảng cũ
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Bảng USERS
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    root_folder_id UUID, -- Trỏ đến bảng files
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng FILES (Gộp chung File và Folder)
CREATE TABLE files (
    id UUID PRIMARY KEY, -- Đây cũng chính là tên file vật lý trên đĩa
    
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- parent_id: NULL = Root. Thay đổi cái này là di chuyển cả nhánh cây -> Cực nhanh
    parent_id UUID REFERENCES files(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL, -- Tên hiển thị (VD: "bao_cao.pdf")
    
    type VARCHAR(20) NOT NULL, -- 'file' hoặc 'folder'
    
    -- Đã BỎ physical_path
    
    mime_type VARCHAR(100), -- Để trình duyệt biết là ảnh hay video
    size_bytes BIGINT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(owner_id, parent_id, name)
);

-- 3. Index
CREATE INDEX idx_files_parent ON files(parent_id);
CREATE INDEX idx_files_type ON files(type);