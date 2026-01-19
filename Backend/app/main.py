from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, files

app = FastAPI(title=settings.PROJECT_NAME)

# Cấu hình CORS để Android/Tkinter gọi được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}/files", tags=["Files"])

@app.get("/")
def root():
    return {"message": "Family File Server is running!"}