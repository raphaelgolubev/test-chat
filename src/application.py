from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic_core import ValidationError

from src.chat_manager import ChatRoom, ChatManager
from src.schemas import *
from src.exceptions import *


app = FastAPI()
room = ChatRoom()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager = ChatManager(room)
    client_id = None

    try:
        await manager.connect(websocket)
        client_id = manager.current_client_id
        while True:
            await manager.receive(websocket)

    except ConnectionTimeoutError:
        await websocket.close()
        manager.disconnect()

    except ValidationError as e:
        print(f"Error: Validation error {e}")

    except WebSocketDisconnect as e:
        manager.disconnect()
        await manager.send_user_disconnected(client_id)

    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect()
        await websocket.close()
