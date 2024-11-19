import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime

from src.schemas import *
from src.exceptions import *

class ChatManager:
    """
    Класс, который управляет подключениями к чату.
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_times: Dict[str, datetime] = {}
        self.current_client_id = None

    async def wait_hello(self, websocket: WebSocket) -> HelloMessage:
        """
        Ожидает 10 секунды, пока не придет сообщение с типом "hello".
        В случае успешного получения сообщения, возвращает его.
        
        ### Param:
            - `websocket` (WebSocket): объект вебсокет соединения
        
        ### Exceptions:
            - `InvalidHelloError`: пришло невалидное приветственное сообщение от клиента
            - `ConnectionTimeoutError`: время ожидания вышло
        
        ### Return:
            - `HelloMessage` (HelloMessage): сообщение с типом "hello"
        """
        received_data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        hello_message = HelloMessage.model_validate(received_data)

        if hello_message.type != "hello":
            raise InvalidHelloError("Invalid hello message")

        return hello_message
    
    async def send_active_users(self, broadcast: bool = False):
        """
        Отправляет клиенту сообщение о подключенных пользователях.
        
        ### Param:
            - `broadcast` (bool): если True, то сообщение отправляется всем подключенным пользователям.
        """
        status_message = ChatStatus(
            data={"active_clients": list(manager.active_connections.keys())}
        )
        if broadcast:
            await self.broadcast(status_message.model_dump())
        else:
            await manager.send_personal_message(status_message.model_dump(), self.current_client_id)
    
    async def send_error_message(self, message: str):
        """
        Отправляет клиенту сообщение об ошибке.
        """
        error_message = ErrorMessage(
            data={"message": message}
        )
        await manager.send_personal_message(error_message.model_dump(), self.current_client_id)

    async def connect(self, websocket: WebSocket):
        """
        Открывает вебсокет соединение и добавляет пользователя в список подключенных. 
        Оповещает всех в чате о новом пользователе.
        
        ### Param:
            - `websocket` (WebSocket): объект вебсокет соединения
            
        ### Exceptions:
            - `InvalidHelloError`: пришло невалидное приветственное сообщение от клиента
            - `ConnectionTimeoutError`: время ожидания вышло
        """
        await websocket.accept()
        
        hello_message = self.wait_hello(websocket)
        self.current_client_id = hello_message.data["user"]

        self.active_connections[self.current_client_id] = websocket
        self.connection_times[self.current_client_id] = datetime.now()

        # сообщаем всем, что юзер подключился
        await self.broadcast(message={"type": "user_connected", "client_id": self.current_client_id})
        # отправляем сообщение о подключенных пользователях
        await self.send_active_users(broadcast=True)

    def disconnect(self, client_id: str):
        """
        Удаляет пользователя из списка подключенных.
        
        ### Param:
            - `client_id` (str): id пользователя, которого нужно удалить
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_times:
            del self.connection_times[client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        """
        Отправляет сообщение активному пользователю.
        
        ### Param:
            - `message` (dict): сообщение, которое нужно отправить
            - `client_id` (str): id пользователя, которому нужно отправить сообщение
        """
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """
        Отправляет сообщение всем подключенным пользователям, исключая те, которые в `exclude`.
        
        ### Param:
            - `message` (dict): сообщение, которое нужно отправить
            - `exclude` (Set[str]): пользователи, которым не нужно отправлять сообщение
        """
        for client_id in self.active_connections:
            # если exclude не None и client_id в exclude, то игнорируем
            if exclude and client_id in exclude:
                continue
            await self.send_personal_message(message, client_id)

    async def receive(self, websocket: WebSocket):
        """
        Обрабатывает полученное сообщение.
        
        ### Param:
            - `websocket` (WebSocket): объект вебсокет соединения
        """
        data = await websocket.receive_json()

        if data["type"] == "receive_status":
            await self.send_active_users()

        elif data["type"] == "send_message":
            if len(data["data"]["text"]) > 30:  # Ограничение на длину сообщения
                self.send_error_message("Сообщение слишком длинное")
            else:
                receive_message = ReceiveMessage(
                    data={
                        "sender": self.current_client_id,
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


manager = ChatManager()
