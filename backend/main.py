
import os
import json
import time
import glob
import asyncio
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ble_service import ble_manager

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

os.makedirs(IMAGES_DIR, exist_ok=True)

# Models
class RunConfig(BaseModel):
    dataset: str
    startTime: float

class RunResult(BaseModel):
    dataset: str
    startTime: float
    endTime: float
    duration: float
    activeDuration: Optional[float] = None
    totalRuns: int
    accuracy: float
    fps: float
    notes: Optional[str] = None

# Global State
current_run: Optional[RunConfig] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Bridge BLE updates to WebSockets
async def forward_ble_to_ws(message):
    await manager.broadcast(message)

ble_manager.register_callback(forward_ble_to_ws)

# --- BLE Background Connection Loop ---

async def ble_connect_loop():
    """Keep trying to connect to Arduino in the background."""
    while not ble_manager.connected:
        try:
            success = await ble_manager.scan_and_connect()
            if success:
                print("[BLE] ✓ Ready! Listening for inference results...\n")
                return
            else:
                print("[BLE]   Retrying in 5 seconds...\n")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"[BLE] ✗ Error: {e}")
            print("[BLE]   Retrying in 5 seconds...\n")
            await asyncio.sleep(5)

# --- Lifespan (replaces deprecated on_event) ---

@asynccontextmanager
async def lifespan(app):
    print("\n" + "="*60)
    print("  TinyML Extinction Testing Backend")
    print("="*60 + "\n")
    task = asyncio.create_task(ble_connect_loop())
    yield
    task.cancel()
    await ble_manager.disconnect()

app = FastAPI(lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BLE Endpoints ---

@app.get("/api/status")
async def get_status():
    return {"ble_connected": ble_manager.connected}

@app.post("/api/connect")
async def connect_ble():
    success = await ble_manager.scan_and_connect()
    return {"success": success, "connected": ble_manager.connected}

# --- Image Endpoints ---

@app.get("/api/images")
async def list_images(dataset: str = Query("person", enum=["person", "emnist"])):
    target_dir = os.path.join(IMAGES_DIR, dataset)
    if not os.path.exists(target_dir):
        return {"images": []}
    
    files = glob.glob(os.path.join(target_dir, "*.*"))
    image_names = [os.path.basename(f) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return {"images": sorted(image_names)}

@app.get("/api/images/{dataset}/{filename}")
async def get_image(dataset: str, filename: str):
    if ".." in dataset or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
        
    file_path = os.path.join(IMAGES_DIR, dataset, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"message": "Image not found"})

# --- Session & History Endpoints ---

@app.post("/api/run/start")
async def start_run(config: RunConfig):
    global current_run
    current_run = config
    return {"message": "Run started", "config": current_run}

@app.get("/api/labels")
async def get_labels():
    labels_path = os.path.join(IMAGES_DIR, "labels.json")
    if os.path.exists(labels_path):
        return FileResponse(labels_path)
    return {}

@app.post("/api/run/stop")
async def stop_run(result: RunResult):
    global current_run
    current_run = None
    
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            pass
    
    record = result.dict()
    record["timestamp"] = datetime.now().isoformat()
    history.insert(0, record)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
        
    return {"message": "Run saved", "record": record}

@app.get("/api/history")
async def get_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

@app.delete("/api/history/{timestamp}")
async def delete_history_item(timestamp: str):
    if not os.path.exists(HISTORY_FILE):
         return JSONResponse(status_code=404, content={"message": "History file not found"})
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        new_history = [item for item in history if item.get("timestamp") != timestamp]
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(new_history, f, indent=2)
            
        return {"message": "Item deleted", "deleted_timestamp": timestamp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/ble")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
