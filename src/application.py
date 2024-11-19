from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic_core import ValidationError

from src.chat_manager import manager
from src.schemas import *
from src.exceptions import *


app = FastAPI()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = None

    try:
        await manager.connect(websocket)
        while True:
            await manager.receive(websocket)

    except ConnectionTimeoutError:
        await websocket.close()
        manager.disconnect(client_id)

    except ValidationError as e:
        print(f"Error: Validation error {e}")

    except WebSocketDisconnect as e:
        manager.disconnect(client_id)
        await manager.broadcast(message={
            "type": "user_disconnected", 
            "client_id": client_id
        }, exclude=None)

    except Exception as e:
        print(f"Error: {e}")
        if client_id:
            manager.disconnect(client_id)
        await websocket.close()
