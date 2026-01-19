import os
import shutil
import uuid6
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.db.base import get_db
from app.db.models import User, FileItem
from app.core.deps import get_current_user
from fastapi.responses import FileResponse
import mimetypes
from fastapi import Response
import zipfile
from fastapi import BackgroundTasks
from sqlalchemy import text
from pydantic import BaseModel # Thêm import này

# ... (Các import khác giữ nguyên)

# Model nhận dữ liệu từ Client
class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None
router = APIRouter()
STORAGE_BASE = "storage/completed"
@router.post("/create_folder")
async def create_folder(
    folder_in: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Kiểm tra tên folder có trùng trong cùng thư mục cha không
    # (Optional - nhưng nên làm để tránh lỗi Unique Constraint của DB)
    
    new_folder_id = uuid6.uuid7()
    
    # Xử lý parent_id
    pid = folder_in.parent_id if folder_in.parent_id and folder_in.parent_id != "root" else current_user.root_folder_id

    new_folder = FileItem(
        id=new_folder_id,
        owner_id=current_user.id,
        parent_id=pid,
        name=folder_in.name,
        type="folder", # Quan trọng: Đánh dấu là folder
        mime_type=None,
        size_bytes=0
    )
    
    try:
        db.add(new_folder)
        await db.commit()
        await db.refresh(new_folder)
        return new_folder
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Tên thư mục có thể đã tồn tại hoặc lỗi hệ thống.")
@router.post("/upload")
async def upload_file(
    parent_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_file_id = uuid6.uuid7()
    
    # Tạo folder cho user nếu chưa có: storage/completed/<owner_id>
    user_storage_path = os.path.join(STORAGE_BASE, str(current_user.id))
    os.makedirs(user_storage_path, exist_ok=True)
    
    # File name trên ổ cứng là UUID
    final_file_path = os.path.join(user_storage_path, str(new_file_id))
    
    try:
        with open(final_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(final_file_path)
        
        # Xử lý parent_id (nếu gửi lên chuỗi "root" hoặc rỗng thì lấy root mặc định)
        content_type = file.content_type
        
        # Nếu nó là generic (octet-stream) hoặc null -> Tự đoán dựa vào tên file
        if not content_type or content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(file.filename)
            if guessed_type:
                content_type = guessed_type
        
        # ---------------------------------------------

        # Xử lý parent_id
        pid = parent_id if parent_id and parent_id != "root" else current_user.root_folder_id

        new_file_record = FileItem(
            id=new_file_id,
            owner_id=current_user.id,
            parent_id=pid,
            name=file.filename,
            type="file",
            mime_type=content_type, # <-- Dùng biến đã được xử lý
            size_bytes=file_size
        )
        db.add(new_file_record)
        await db.commit()
        await db.refresh(new_file_record)
        
        return {
            "id": new_file_record.id,
            "name": new_file_record.name,
            "size": new_file_record.size_bytes,
            "status": "success"
        }

    except Exception as e:
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_files(
    folder_id: str = None, # Nếu null thì lấy root
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Nếu không gửi folder_id, mặc định lấy root của user
    target_folder_id = folder_id if folder_id else current_user.root_folder_id
    
    # Query lấy tất cả file có parent_id tương ứng
    query = select(FileItem).where(
        FileItem.owner_id == current_user.id,
        FileItem.parent_id == target_folder_id
    ).order_by(
        FileItem.type.desc(), # Folder lên trước
        FileItem.name.asc()   # Tên A-Z
    )
    
    result = await db.execute(query)
    files = result.scalars().all()
    
    return files

# 2. API Xem nội dung file (Stream Video/Ảnh)
@router.get("/content/{file_id}")
async def get_file_content(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Tìm file trong DB
    result = await db.execute(select(FileItem).where(
        FileItem.id == file_id,
        FileItem.owner_id == current_user.id
    ))
    file_item = result.scalar_one_or_none()
    
    if not file_item or file_item.type == 'folder':
        raise HTTPException(status_code=404, detail="File not found")

    # Lấy đường dẫn vật lý (dùng property ảo trong model)
    # Lưu ý: file_item.get_physical_path là property chúng ta đã viết ở model
    file_path = file_item.get_physical_path 
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File on disk missing")

    # Trả về FileResponse (Hỗ trợ stream video range request tự động)
    return FileResponse(
        path=file_path,
        media_type=file_item.mime_type,
        filename=file_item.name
    )

class ItemUpdate(BaseModel):
    name: str

# 3. API Đổi tên (Rename)
@router.patch("/items/{item_id}")
async def rename_item(
    item_id: str,
    item_in: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Tìm item
    result = await db.execute(select(FileItem).where(
        FileItem.id == item_id, 
        FileItem.owner_id == current_user.id
    ))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy file/folder")
        
    # Cập nhật tên
    item.name = item_in.name
    
    try:
        await db.commit()
        await db.refresh(item)
        return item
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Lỗi đổi tên: " + str(e))

# 4. API Xóa (Delete)
@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Tìm item
    result = await db.execute(select(FileItem).where(
        FileItem.id == item_id, 
        FileItem.owner_id == current_user.id
    ))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy file/folder")
    
    try:
        # Nếu là File -> Xóa file vật lý trên ổ cứng
        if item.type == 'file':
            # Dùng property ảo get_physical_path để lấy đường dẫn
            file_path = item.get_physical_path
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        
        # Nếu là Folder -> Logic phức tạp hơn (xóa đệ quy file con). 
        # Tuy nhiên, nếu DB bạn set ON DELETE CASCADE, các dòng con trong DB sẽ mất.
        # Lưu ý: Các file vật lý con của folder này sẽ thành file rác (orphan).
        # Để đơn giản cho bài này, ta chỉ xóa DB record.
        
        await db.delete(item)
        await db.commit()
        
        return Response(status_code=204) # 204 No Content
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi khi xóa: " + str(e))


@router.get("/download_folder/{folder_id}")
async def download_folder(
    folder_id: str,
    background_tasks: BackgroundTasks, # Xóa file sau khi gửi xong
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. SQL Đệ quy: Lấy toàn bộ cây thư mục con cháu
    query = text("""
        WITH RECURSIVE folder_tree AS (
            -- Neo: Lấy folder gốc
            SELECT id, owner_id, name, type, parent_id, CAST(name AS TEXT) as relative_path 
            FROM files 
            WHERE id = :target_id AND owner_id = :owner_id
            
            UNION ALL
            
            -- Đệ quy: Lấy con
            SELECT child.id, child.owner_id, child.name, child.type, child.parent_id,
                   CAST(parent.relative_path || '/' || child.name AS TEXT)
            FROM files child
            JOIN folder_tree parent ON child.parent_id = parent.id
        )
        SELECT * FROM folder_tree;
    """)

    result = await db.execute(query, {"target_id": folder_id, "owner_id": current_user.id})
    all_items = result.fetchall()

    if not all_items:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục")

    # 2. Tạo file ZIP tạm
    root_name = all_items[0].name
    zip_filename = f"{root_name}_{uuid6.uuid7()}.zip"
    zip_path = os.path.join("storage", zip_filename)

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in all_items:
                # item.relative_path chính là đường dẫn ảo (VD: TaiLieu/Hinh/a.jpg)
                
                if item.type == 'file':
                    # Tính đường dẫn thật trên ổ cứng
                    real_path = os.path.join(STORAGE_BASE, str(current_user.id), str(item.id))
                    if os.path.exists(real_path):
                        zipf.write(real_path, arcname=item.relative_path)
                else:
                    # Tạo folder rỗng trong zip
                    zfi = zipfile.ZipInfo(item.relative_path + "/")
                    zipf.writestr(zfi, "")
                    
    except Exception as e:
        if os.path.exists(zip_path): os.remove(zip_path)
        raise HTTPException(status_code=500, detail=f"Lỗi nén: {e}")

    # 3. Gửi file và xóa ngay lập tức
    background_tasks.add_task(os.remove, zip_path)
    
    return FileResponse(
        path=zip_path, 
        filename=f"{root_name}.zip",
        media_type='application/zip'
    )

# app/routers/files.py

@router.post("/upload_chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    parent_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Tạo folder tạm riêng cho upload_id này
    temp_dir = os.path.join("storage", "temp", upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 2. Lưu mảnh ghép thành file riêng: VD "3.part"
    part_file_path = os.path.join(temp_dir, f"{chunk_index}.part")
    
    try:
        with open(part_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Kiểm tra xem đã đủ tất cả các mảnh chưa?
        # Đếm số file .part trong folder
        uploaded_parts = len([name for name in os.listdir(temp_dir) if name.endswith('.part')])
        
        if uploaded_parts == total_chunks:
            # --- ĐÃ ĐỦ MẢNH -> TIẾN HÀNH GỘP FILE ---
            return await merge_files(upload_id, total_chunks, parent_id, file.filename, file.content_type, db, current_user)

        return {"status": "chunk_received", "index": chunk_index}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Hàm phụ trợ để gộp file (Tách ra cho gọn)
async def merge_files(upload_id, total_chunks, parent_id, filename, content_type, db, user):
    temp_dir = os.path.join("storage", "temp", upload_id)
    new_file_id = uuid6.uuid7()
    
    user_path = os.path.join(STORAGE_BASE, str(user.id))
    os.makedirs(user_path, exist_ok=True)
    final_path = os.path.join(user_path, str(new_file_id))
    
    try:
        # Mở file đích để ghi
        with open(final_path, "wb") as outfile:
            # Lặp từ 0 -> total_chunks để gộp đúng thứ tự
            for i in range(total_chunks):
                part_path = os.path.join(temp_dir, f"{i}.part")
                with open(part_path, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)
        
        # Xóa folder tạm
        shutil.rmtree(temp_dir)
        
        # Lưu DB (Logic cũ)
        file_size = os.path.getsize(final_path)
        
        # Đoán mime type nếu cần
        if not content_type or content_type == "application/octet-stream":
             guessed_type, _ = mimetypes.guess_type(filename)
             if guessed_type: content_type = guessed_type

        pid = parent_id if parent_id and parent_id != "root" else user.root_folder_id

        new_file = FileItem(
            id=new_file_id,
            owner_id=user.id,
            parent_id=pid,
            name=filename,
            type="file",
            mime_type=content_type,
            size_bytes=file_size
        )
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        
        return {"status": "completed", "file_id": new_file.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge Error: {e}")