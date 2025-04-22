from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import chat, auth
from app.redis_listener import redis_subscriber
import asyncio

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(redis_subscriber())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.include_router(chat.router)
app.include_router(auth.router)
