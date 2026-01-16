from fastapi import FastAPI
from app.core.config import settings
from app.routers import auth
# from app.routers import files (sẽ add sau)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include Router
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {"message": "Family File Server is running!"}