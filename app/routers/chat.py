from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, sender=username)
    except WebSocketDisconnect:
        manager.disconnect(username)
