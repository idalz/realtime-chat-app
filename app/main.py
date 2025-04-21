from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.routers import chat, auth

app = FastAPI()

app.include_router(chat.router)
app.include_router(auth.router)
