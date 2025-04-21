from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.activate_connections: Dict[str, WebSocket] = {}

    # User connect
    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.activate_connections[username] = websocket
        print(f"{username} connected")

    # User disconnect
    def disconnect(self, username: str):
        self.activate_connections.pop(username, None)
        print(f"{username} disconnected")

    # Broadcast message (to others)
    async def broadcast(self, message: str, sender: str):
        for user, connection in self.activate_connections.items():
            if user != sender:
                await connection.send_text(F"{sender}: {message}")
     