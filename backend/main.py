"""
StudyMindAI FastAPI Application Main Entrypoint.
Serves high-performance REST APIs and the modern SPA Frontend.
"""

import os
from dotenv import load_dotenv

# Load environment configuration (.env)
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from database.db import DatabaseManager, DEFAULT_DB_PATH
from database.seed_data import seed_database
from backend.routers import auth, subjects, quiz, analytics, ml, tutor

# Path configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[StudyMindAI Backend] Initializing database and ensuring content seeds...")
    seed_database(DEFAULT_DB_PATH)
    print("[StudyMindAI Backend] Ready to serve API and modern UI.")
    yield

app = FastAPI(
    title="StudyMindAI API",
    description="Intelligent Adaptive Learning Platform with Deep Knowledge Tracing",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "platform": "StudyMindAI",
        "version": "2.0.0",
        "features": ["DKT_GRU", "Adaptive_Quizzing", "IRT_Baselines", "AI_Tutor"]
    }


# Include API Routers
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(quiz.router)
app.include_router(analytics.router)
app.include_router(ml.router)
app.include_router(tutor.router)


# Mount Static Frontend
if os.path.exists(FRONTEND_DIR):
    # Mount subdirectories (css, js, assets)
    css_dir = os.path.join(FRONTEND_DIR, "css")
    js_dir = os.path.join(FRONTEND_DIR, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

    # Serve index.html for root and SPA routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't hijack API routes
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})
        
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
