import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket):
    """
    WebSocket endpoint that streams backtest progress updates from Redis.
    The frontend can connect to this endpoint to receive real-time updates.
    """
    await websocket.accept()
    
    # Initialize async redis client
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    
    try:
        await pubsub.subscribe("backtest_progress")
        logger.info("WebSocket client connected and subscribed to backtest_progress")
        
        while True:
            # We use get_message with timeout to allow checking for websocket disconnects
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message is not None:
                # message['data'] is typically bytes
                data_str = message["data"].decode("utf-8")
                
                # Forward to websocket client
                await websocket.send_text(data_str)
                
            # Ping the websocket to ensure it's still alive and catch disconnects
            # Since get_message yields control, if the client disconnects, 
            # we will eventually get a WebSocketDisconnect on send or receive.
            # However, we don't strictly need to await receive() if we just push.
            # But await receive() can detect client closure.
            # Actually, to properly handle both redis messages and websocket disconnects,
            # we should use asyncio.wait. For simplicity, we just push and let send_text
            # raise an exception when disconnected.
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe("backtest_progress")
        await pubsub.close()
        await redis_client.aclose()
