from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db
from app.websocket_manager import ConnectionManager
from app.models.message import Message
from app.auth.auth import decode_access_token
import json

router = APIRouter()
manager = ConnectionManager()

MESSAGES_LIMIT = 25

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    room = websocket.query_params.get("room", "general")
    username = decode_access_token(token)

    if not username:
        await websocket.close(code=1008)
        print("Invalid or missing token")
        return
    
    await websocket.accept()

    db: Session = next(get_db())  
    await manager.connect(room, websocket)

    join_msg = Message(sender="System", content=f"{username} joined the room", room=room)
    db.add(join_msg)
    db.commit()

    await manager.broadcast(room, f"{username} joined the room", sender="System")

    recent_messages = (
        db.query(Message)
        .filter(Message.room == room)
        .order_by(Message.timestamp.desc())
        .limit(MESSAGES_LIMIT)
        .all()
    )

    for msg in reversed(recent_messages):
        data = {
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "room": msg.room,
            "type": "system" if msg.sender == "System" else "chat"
        }
        await websocket.send_text(json.dumps(data))
    
    try:
        while True:
            data = await websocket.receive_text()

            msg = Message(sender=username, content=data, room=room)
            db.add(msg)
            db.commit()

            await manager.broadcast(room, data, sender=username)
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)

        leave_msg = Message(sender="System", content=f"{username} left the room", room=room)
        db.add(leave_msg)
        db.commit()
        
        await manager.broadcast(room, f"{username} left the room", sender="System")
