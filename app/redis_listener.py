import asyncio
import json
from app.redis_client import redis_client
from app.websocket_manager import manager

async def redis_subscriber():
   pubsub = redis_client.pubsub()
   await pubsub.psubscribe("room:*", "dm:*")
   print("Redis subscriber started.")

   async for message in pubsub.listen():
    if message is None or message.get("type") != "pmessage":
        continue

    data = message.get("data")
    if not isinstance(data, str):
        continue 
    
    try:
        msg_data = json.loads(data)
        msg_type = msg_data.get("type", "chat")
        
        # For room chats
        if msg_type == "chat":
            room = msg_data["room"]
            sender = msg_data["sender"]
            content = msg_data["content"]
            await manager.broadcast(room, content, sender, msg_type)
        # For dms
        elif msg_type == "dm":
            sender = msg_data["sender"]
            recipient = msg_data["recipient"]
            content = msg_data["content"]

        for user in [sender, recipient]:
            key = f"{user}-dm-{recipient if user == sender else sender}"
            await manager.broadcast(key, content, sender, msg_type="dm", recipient=recipient)

    except Exception as e:
        print(f"Redis subscriber error: {e}")
