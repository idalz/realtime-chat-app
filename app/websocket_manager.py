from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.activate_connections: Dict[str, List[WebSocket]] = {}

    # Connect to room
    async def connect(self, room: str, websocket: WebSocket):
        if room not in self.activate_connections:
            self.activate_connections[room] = []
        self.activate_connections[room].append(websocket)
        print(f"New connection in room: {room}")

    # Disconnect from room
    def disconnect(self, room: str, websocket: WebSocket):
        if room in self.activate_connections:
            self.activate_connections[room].remove(websocket)
            print(f"  Disconnected from room: {room}")

    # Broadcast message (to others)
    async def broadcast(self, room: str, message: str, sender: str):
        if room in self.activate_connections:
            for connection in self.activate_connections[room]:
                await connection.send_text(f"{sender}: {message}")
     