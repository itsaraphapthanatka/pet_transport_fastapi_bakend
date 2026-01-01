import redis.asyncio as redis
import json

import os

redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)

async def publish(channel: str, data: dict):
    await redis_client.publish(channel, json.dumps(data))
