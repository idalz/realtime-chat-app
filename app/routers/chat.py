from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db
from app.websocket_manager import ConnectionManager
from app.models.message import Message
from app.auth.auth import decode_access_token

router = APIRouter()
manager = ConnectionManager()

MESSAGES_LIMIT = 25

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    username = decode_access_token(token)

    if not username:
        await websocket.close(code=1008)
        print("Invalid or missing token")
        return
    
    await websocket.accept()

    db: Session = next(get_db())  

    await manager.connect(username, websocket)

    recent_messages = (
        db.query(Message)
        .order_by(Message.timestamp.desc())
        .limit(MESSAGES_LIMIT)
        .all()
    )

    for msg in reversed(recent_messages):
        await websocket.send_text(f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {msg.sender}: {msg.content}")
    
    try:
        while True:
            data = await websocket.receive_text()

            msg = Message(sender=username, content=data)
            db.add(msg)
            db.commit()

            await manager.broadcast(data, sender=username)
    except WebSocketDisconnect:
        manager.disconnect(username)
