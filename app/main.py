from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.routers import chat

app = FastAPI()

app.include_router(chat.router)
