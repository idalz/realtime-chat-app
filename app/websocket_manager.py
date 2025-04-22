from typing import Dict, List
from fastapi import WebSocket
import json
from datetime import datetime, timezone
from app.logger import logger 

class ConnectionManager:
    def __init__(self):
        self.activate_connections: Dict[str, List[WebSocket]] = {}

    # Connect to room
    async def connect(self, key: str, websocket: WebSocket):
        if key not in self.activate_connections:
            self.activate_connections[key] = []
        self.activate_connections[key].append(websocket)
        print(f"Connected: {key}")

    # Disconnect from room
    def disconnect(self, key: str, websocket: WebSocket):
        if room in self.activate_connections:
            self.activate_connections[key].remove(websocket)
            print(f"  Disconnected from room: {key }")

    # Broadcast message (to others)
    async def broadcast(self, key: str, message: str, sender: str, msg_type="chat", recipient=None):
        data = {
            "sender": sender,
            "recipient": recipient,
            "content": message,
            "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "type": msg_type
        }

        if key in self.activate_connections:
            for connection in self.activate_connections[key]:
                try:
                    await connection.send_text(json.dumps(data))
                except Exception as e:
                    logger.error(f"Error sending message to {key}: {e}")
     