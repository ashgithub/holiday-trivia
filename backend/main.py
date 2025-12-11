from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI(title="All-Hands Quiz Game", version="0.1.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend assets (CSS, JS)
app.mount("/assets", StaticFiles(directory="../frontend"), name="assets")

# API routes under /api/
@app.get("/api/")
async def root():
    """Root API endpoint"""
    return {"message": "All-Hands Quiz Game API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Serve HTML pages at root level
@app.get("/")
async def participant_page():
    """Serve participant page"""
    return FileResponse("../frontend/index.html")

@app.get("/admin")
async def admin_page():
    """Serve admin page"""
    return FileResponse("../frontend/admin.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
