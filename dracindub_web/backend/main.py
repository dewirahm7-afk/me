# backend/main.py
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

# Import managers first
from core.session_manager import session_manager
from core.processor import processing_manager
from api.websockets import websocket_manager

# 🔥 IMPORT ROUTER
from api.endpoints import router as api_router

app = FastAPI(title="DracinDub Web", version="2.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 INCLUDE API ROUTER
app.include_router(api_router)

# Get the correct base directory
BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

print(f"Base directory: {BASE_DIR}")
print(f"Frontend directory: {FRONTEND_DIR}")
print(f"Frontend exists: {FRONTEND_DIR.exists()}")

# Mount static files - serve the entire frontend directory
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    print("Static files mounted successfully")
else:
    print(f"WARNING: Frontend directory not found at {FRONTEND_DIR}")

@app.get("/")
async def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding='utf-8'))
    else:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DracinDub Web</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .error { color: red; }
                .info { color: blue; }
            </style>
        </head>
        <body>
            <h1>DracinDub Web - Auto Dubbing Studio</h1>
            <div class="error">Frontend files not found. Please check the frontend directory.</div>
            <div class="info">Backend is running correctly. Frontend path: """ + str(FRONTEND_DIR) + """</div>
            <div class="info">API Test: <a href="/api/test">/api/test</a></div>
            <div class="info">Health: <a href="/health">/health</a></div>
        </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy", 
        "version": "2.0.0", 
        "frontend_path": str(FRONTEND_DIR),
        "backend": "running"
    })

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages
            try:
                import json
                message = json.loads(data)
                if message.get('type') == 'join_session':
                    session_id = message.get('data', {}).get('session_id')
                    if session_id:
                        websocket_manager.add_to_session(client_id, session_id)
                        await websocket.send_text(json.dumps({
                            "type": "session_joined",
                            "data": {"session_id": session_id}
                        }))
            except Exception as e:
                print(f"WebSocket message error: {e}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)

if __name__ == "__main__":
    print("Starting DracinDub Web Server...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Create workspaces directory if it doesn't exist
    workspaces_dir = Path("workspaces")
    workspaces_dir.mkdir(exist_ok=True)
    print(f"Workspaces directory: {workspaces_dir.absolute()}")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
