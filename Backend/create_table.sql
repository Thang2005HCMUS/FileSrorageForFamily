-- 1. Bảng USERS
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    
    -- Đây là thiết kế của bạn: Lưu ID thư mục gốc vào đây.
    -- Cho phép NULL ban đầu để tạo User trước.
    -- KHÔNG tạo Foreign Key (REFERENCES) để tránh lỗi vòng lặp và tăng tốc insert.
    root_folder_id UUID, 
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng FOLDERS
CREATE TABLE folders (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Thư mục cha. Nếu NULL -> Đây là Root (về mặt logic)
    parent_id UUID REFERENCES folders(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ràng buộc: Trong cùng 1 thư mục cha, không được có 2 thư mục con trùng tên
    UNIQUE(owner_id, parent_id, name)
);

-- 3. Bảng FILES
CREATE TABLE files (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File bắt buộc phải thuộc về 1 folder nào đó (kể cả Root)
    folder_id UUID NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100), -- type
    size_bytes BIGINT NOT NULL, -- size
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Last_modifider
);

-- 4. Index tối ưu
-- Index cho User Login
CREATE INDEX idx_users_email ON users(email);

-- Index cho việc hiển thị nội dung thư mục (Quan trọng nhất)
-- Giúp lệnh: SELECT * FROM folders WHERE parent_id = ... chạy cực nhanh
CREATE INDEX idx_folders_parent ON folders(parent_id);

-- Index để check nhanh file trong folder
CREATE INDEX idx_files_folder ON files(folder_id);