from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
from app.database import get_db
from app.websocket_manager import manager
from app.auth.auth import decode_access_token, get_current_user
from app.redis_client import redis_client
from app.logger import logger 
from app.models.message import Message
from app.models.user import User
from app.models.room import Room


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

    system_user = db.query(User).filter_by(username="System").first()

    join_msg = Message(
        sender_id=system_user.id,
        receiver_id=None,
        content=f"{username} joined the room",
        room=room
    )

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
            "sender": msg.sender.username if msg.sender else "System",
            "content": msg.content,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "room": msg.room,
            "type": "system" if not msg.sender else "chat"
        }
        await websocket.send_text(json.dumps(data))
    
    try:
        while True:
            data = await websocket.receive_text()

            sender = db.query(User).filter_by(username=username).first()
            msg = Message(sender_id=sender.id, content=data, room=room, receiver_id=None)
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

        leave_msg = Message(
            sender_id=system_user.id,
            receiver_id=None,
            content=f"{username} left the room",
            room=room
        )
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
    finally:
        db.close()
        
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

    sender = db.query(User).filter_by(username=username).first()
    receiver = db.query(User).filter_by(username=recipient).first()

    messages = (
        db.query(Message)
        .filter(
            ((Message.sender_id == sender.id) & (Message.receiver_id == receiver.id)) |
            ((Message.sender_id == receiver.id) & (Message.receiver_id == sender.id))
        )
        .order_by(Message.timestamp.desc())
        .limit(MESSAGES_LIMIT)
        .all()
    ) 

    for msg in reversed(messages):
        data = {
            "sender": msg.sender.username if msg.sender else "Unknown",
            "recipient": msg.receiver.username if msg.receiver else "Unknown",
            "content": msg.content,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "type": "dm"
        }
        await websocket.send_text(json.dumps(data))

    await manager.connect(f"{username}-dm-{recipient}", websocket)

    try:
        while True:
            content = await websocket.receive_text()

            msg = Message(sender_id=sender.id, receiver_id=receiver.id, content=content)
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
    finally:
        db.close()

@router.get("/rooms")
def get_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ✅
):
    rooms = db.query(Room).all()
    return {"rooms": [room.name for room in rooms]}
  
@router.get("/dms")
def get_dms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find users the current user has chat with
    sent = db.query(User).join(Message, User.id == Message.receiver_id)\
        .filter(Message.sender_id == current_user.id)

    received = db.query(User).join(Message, User.id == Message.sender_id)\
        .filter(Message.receiver_id == current_user.id)

    # Combine and remove duplicates
    users = {user.username for user in sent.union(received).all() if user.username != current_user.username}

    return {"dms": list(users)} 
