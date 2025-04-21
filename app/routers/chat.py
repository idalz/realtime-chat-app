from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db
from app.websocket_manager import ConnectionManager
from app.models.message import Message

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    db: Session = next(get_db())
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_text()

            msg = Message(sender=username, content=data)
            db.add(msg)
            db.commit()
            await manager.broadcast(data, sender=username)
    except WebSocketDisconnect:
        manager.disconnect(username)
