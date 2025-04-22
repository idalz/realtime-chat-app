from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
from app.database import get_db
from app.websocket_manager import manager
from app.models.message import Message
from app.auth.auth import decode_access_token
from app.redis_client import redis_client
from app.logger import logger 


router = APIRouter()

MESSAGES_LIMIT = 25

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    room = websocket.query_params.get("room", "general")
    username = decode_access_token(token)

    if not username:
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    db: Session = next(get_db())  
    await manager.connect(room, websocket)

    join_msg = Message(sender="System", content=f"{username} joined the room", room=room)
    db.add(join_msg)
    db.commit()

    await manager.broadcast(room, f"{username} joined the room", sender="System")
    logger.info(f"{username} joined room '{room}'")
    
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

            await redis_client.publish(
                channel=f"room:{room}",
                message=json.dumps({
                    "sender": username,
                    "content": data,
                    "room": room,
                    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    "type": "chat"
                })
            )

            logger.info(f"{username} sent message in '{room}'")
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)

        leave_msg = Message(sender="System", content=f"{username} left the room", room=room)
        db.add(leave_msg)
        db.commit()

        await redis_client.publish(
            channel=f"room:{room}",
            message=json.dumps({
                "sender": username,
                "content": f"{username} left the room",
                "room": room,
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                "type": "chat"
            })
        )
        
        logger.info(f"{username} left room '{room}'")
        
@router.websocket("/ws/dm")
async def websocket_dm(websocket: WebSocket):
    token = websocket.query_params.get("token")
    recipient = websocket.query_params.get("to")

    username = decode_access_token(token)
    if not username or not recipient:
        await websocket.close(code=1008)
        return
    
    await websocket.accept()

    db: Session = next(get_db())

    messages = (
        db.query(Message)
        .filter(
            ((Message.sender == username) & (Message.recipient == recipient)) |
            ((((Message.sender == recipient) & (Message.recipient == username))))
        )
        .order_by(Message.timestamp.desc())
        .limit(MESSAGES_LIMIT)
        .all()
    )

    for msg in reversed(messages):
        data = {
            "sender": msg.sender,
            "recipient": msg.recipient,
            "content": msg.content,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "type": "dm"
        }
        await websocket.send_text(json.dumps(data))

    await manager.connect(f"{username}-dm-{recipient}", websocket)

    try:
        while True:
            content = await websocket.receive_text()

            msg = Message(sender=username, recipient=recipient, content=content)
            db.add(msg)
            db.commit()

            # Publish the message once to a Redis channel shared by both users
            sorted_users = sorted([username, recipient])
            channel = f"dm:{sorted_users[0]}:{sorted_users[1]}"

            payload = json.dumps({
                "sender": username,
                "recipient": recipient,
                "content": content,
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                "type": "dm"
            })

            await redis_client.publish(channel, payload)
    except WebSocketDisconnect:
        manager.disconnect(f"{username}-dm-{recipient}", websocket)
