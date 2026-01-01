import asyncio
import json
from app.core.redis import redis_client
from app.routers.chat_ws import active_connections

async def listen_chat():
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("chat:*")

    async for msg in pubsub.listen():
        if msg["type"] != "pmessage":
            continue

        try:
            # channel is like "chat:1"
            channel = msg["channel"]
            order_id = channel.split(":")[1]
            data = json.loads(msg["data"])

            # Broadcast to all connections for this order_id
            # active_connections keys are "{order_id}:{user_id}"
            
            # Create a list of sockets to send to to avoid concurrent modification issues during iteration
            # (though active_connections is dict, iterating keys is safe behavior in Py3 if not modifying keys)
            targets = [ws for key, ws in active_connections.items() if key.startswith(f"{order_id}:")]

            for ws in targets:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    print(f"Error sending message to ws: {e}")
        except Exception as e:
            print(f"Error processing redis message: {e}")
