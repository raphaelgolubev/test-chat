import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic_core import ValidationError

from src.connection_manager import manager
from src.schemas import *


app = FastAPI()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = None
    
    try:
        # Ожидаем приветственное сообщение в течение 10 секунд
        await websocket.accept()
        received_data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        hello_message = HelloMessage.model_validate(received_data)
        if hello_message.type != "hello":
            await websocket.close()
            raise Exception("Invalid hello message")
        
        # Получаем идентификатор пользователя и кладем в словарь
        client_id = hello_message.data["user"]
        await manager.connect(websocket, client_id)
        
        # Отправляем статус чата
        status_message = ChatStatus(
            data={"active_clients": list(manager.active_connections.keys())}
        )
        await manager.broadcast(status_message.model_dump())
        
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "receive_status":
                status_message = ChatStatus(
                    data={"active_clients": list(manager.active_connections.keys())}
                )
                await manager.send_personal_message(status_message.model_dump(), client_id)
                
            elif data["type"] == "send_message":
                if len(data["data"]["text"]) > 30:  # Ограничение на длину сообщения
                    error_message = ErrorMessage(
                        data={"message": "Сообщение слишком длинное"}
                    )
                    await manager.send_personal_message(error_message.model_dump(), client_id)
                    continue
                
                receive_message = ReceiveMessage(
                    data={
                        "sender": client_id,
                        "timestamp": int(datetime.now().timestamp()),
                        "text": data["data"]["text"]
                    }
                )
                
                if "receivers" in data["data"] and data["data"]["receivers"]:
                    # Отправка конкретным получателям
                    for receiver in data["data"]["receivers"]:
                        if receiver in manager.active_connections:
                            await manager.send_personal_message(receive_message.model_dump(), receiver)
                else:
                    # Отправка всем
                    await manager.broadcast(receive_message.model_dump())

    except asyncio.TimeoutError:
        await websocket.close()
        manager.disconnect(client_id)
    
    except ValidationError as e:
        await websocket.close()
        manager.disconnect(client_id)
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