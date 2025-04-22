import asyncio
from app.redis_listener import redis_subscriber

if __name__ == "__main__":
    asyncio.run(redis_subscriber())