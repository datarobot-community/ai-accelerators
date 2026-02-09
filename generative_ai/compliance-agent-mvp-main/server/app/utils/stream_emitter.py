"""
StreamEmitter - Generic Python utility for streaming JSON events in FastAPI endpoints

Example Usage:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# Basic usage
@router.post("/api/stream")
async def stream_endpoint(request: dict):
    emitter = StreamEmitter()
    
    async def process():
        await emitter.emit({"type": "start", "data": "Processing..."})
        result = await some_async_operation()
        await emitter.emit({"type": "update", "progress": 50})
        await emitter.emit({"type": "complete", "result": result})
    
    return emitter.stream_response(process())

# Alternative shorthand
@router.post("/api/stream2")
async def stream_endpoint2():
    async def process(emitter: StreamEmitter):
        await emitter.emit({"type": "start"})
        await do_work()
        await emitter.emit({"type": "complete"})
    
    return await stream_with_emitter(process)

# With event-driven pattern
@router.post("/api/stream3")
async def stream_endpoint3():
    stream = StreamEmitter()
    events = EventEmitter()
    
    @events.on("agent_start")
    async def handle_agent_start(event):
        await stream.emit(event)
    
    async def process():
        await events.emit({"type": "agent_start", "agent": "my_agent"})
        await events.emit({"type": "agent_complete", "agent": "my_agent"})
    
    return stream.stream_response(process())
```
"""

import json
import asyncio
from typing import Any, Callable, Awaitable, AsyncGenerator, Optional, TypeVar, Generic
from dataclasses import is_dataclass
from fastapi.responses import StreamingResponse


T = TypeVar('T')


class StreamEmitter:
    """Generic event emitter for FastAPI streaming responses."""
    
    def __init__(self, media_type: str = "application/x-ndjson"):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.media_type = media_type
        self._done = object()
        self._started = False
        self._keep_alive_task: Optional[asyncio.Task] = None
    
    async def emit(self, event: dict[str, Any]) -> None:
        if not self._started:
            self._started = True
        
        serialized = self._serialize(event)
        await self.queue.put(serialized)
    
    async def emit_error(self, message: str, error_type: str = "error") -> None:
        await self.emit({
            "type": error_type,
            "data": {"message": message}
        })
    
    async def complete(self) -> None:
        await self.queue.put(self._done)
    
    def _serialize(self, obj: Any) -> dict[str, Any]:
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif is_dataclass(obj) and not isinstance(obj, type):
            obj_dict = {}
            for field_name in obj.__dataclass_fields__:
                field_value = getattr(obj, field_name)
                serialized_value = self._serialize(field_value)
                if serialized_value is not None:
                    obj_dict[field_name] = serialized_value
            return obj_dict
        elif isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items() if self._serialize(v) is not None}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return {k: self._serialize(v) for k, v in obj.__dict__.items() 
                   if not k.startswith('_') and self._serialize(v) is not None}
        else:
            return str(obj)
    
    async def _keep_alive(self, interval: int = 5) -> None:
        try:
            while True:
                await asyncio.sleep(interval)
                await self.emit({"type": "keep_alive"})
        except asyncio.CancelledError:
            pass
    
    async def _generate(self, task: asyncio.Task) -> AsyncGenerator[bytes, None]:
        try:
            while True:
                event = await self.queue.get()
                
                if event is self._done:
                    break
                
                yield json.dumps(event).encode() + b"\n"
            
            # Ensure task completes before closing the stream
            # This is important for DataRobot deployments where connections must close cleanly
            if not task.done():
                try:
                    await task
                except Exception:
                    # Exception already handled in wrapper's error handling
                    pass
            else:
                # Task already completed, check for exceptions to ensure proper cleanup
                try:
                    task.result()
                except Exception:
                    # Exception already handled in wrapper's error handling
                    pass
        
        except Exception as e:
            print(f"Error in stream generation: {e}")
            error_event = {"type": "error", "data": {"message": str(e)}}
            yield json.dumps(error_event).encode() + b"\n"
            
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        finally:
            # Clean up keep-alive task
            if self._keep_alive_task and not self._keep_alive_task.done():
                self._keep_alive_task.cancel()
                try:
                    await self._keep_alive_task
                except asyncio.CancelledError:
                    pass
    
    def stream_response(
        self,
        task: Awaitable[None],
        keep_alive: bool = True,
        keep_alive_interval: int = 5
    ) -> StreamingResponse:
        async def wrapper():
            try:
                await task
            except Exception as e:
                print(f"Error in task: {e}")
                await self.emit_error(str(e))
            finally:
                await self.complete()
        
        task_obj = asyncio.create_task(wrapper())
        
        if keep_alive:
            self._keep_alive_task = asyncio.create_task(
                self._keep_alive(keep_alive_interval)
            )
        
        return StreamingResponse(
            self._generate(task_obj),
            media_type=self.media_type
        )


class EventEmitter(Generic[T]):
    """Type-safe event emitter with callback registration."""
    
    def __init__(self):
        self._listeners: dict[str, list[Callable[[T], Awaitable[None]]]] = {}
    
    def on(self, event_type: str):
        def decorator(func: Callable[[T], Awaitable[None]]):
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(func)
            return func
        return decorator
    
    async def emit(self, event: T) -> None:
        event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
        
        if not event_type:
            raise ValueError("Event must have a 'type' field")
        
        listeners = self._listeners.get(event_type, [])
        
        for listener in listeners:
            try:
                await listener(event)
            except Exception as e:
                print(f"Error in event listener for {event_type}: {e}")
    
    def remove(self, event_type: str, listener: Callable[[T], Awaitable[None]]) -> None:
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass


async def stream_with_emitter(
    func: Callable[[StreamEmitter], Awaitable[None]],
    keep_alive: bool = True
) -> StreamingResponse:
    emitter = StreamEmitter()
    return emitter.stream_response(func(emitter), keep_alive=keep_alive)
