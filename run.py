"""
StudyMindAI Unified Application Launcher.
Starts the FastAPI backend service and serves the modern animated SPA frontend.
"""

import sys
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 65)
    print("[StudyMindAI] Advanced Adaptive Learning Platform (v2.0)")
    print("=" * 65)
    print("Starting Unified High-Performance FastAPI Server...")
    print("Modern Animated SPA & REST API: http://localhost:8000")
    print("Interactive OpenAPI Documentation: http://localhost:8000/docs")
    print("=" * 65)

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
