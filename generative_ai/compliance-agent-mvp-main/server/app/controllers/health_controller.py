import asyncio
from fastapi import APIRouter
from app.utils.stream_emitter import StreamEmitter

router = APIRouter()


@router.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


@router.get("/api/health/stream")
async def health_stream():
    """
    Long-running streaming health endpoint that sends health status and keep-alive messages every 5 seconds.
    The stream will continue indefinitely until the client disconnects.
    """
    emitter = StreamEmitter()
    
    async def send_health_updates():
        # Send health status updates every 5 seconds
        # The StreamEmitter's keep_alive feature will also send keep-alive messages
        while True:
            await emitter.emit({
                "type": "health_status",
                "data": {
                    "status": "ok",
                    "timestamp": asyncio.get_event_loop().time()
                }
            })
            await asyncio.sleep(5)
    
    return emitter.stream_response(
        send_health_updates(),
        keep_alive=True,
        keep_alive_interval=5
    )
