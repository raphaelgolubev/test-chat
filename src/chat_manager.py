import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime

from src.schemas import *
from src.exceptions import *

class ChatRoom:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_times: Dict[str, datetime] = {}

class ChatManager:
    """
    Класс, который управляет подключениями к чату.
    """
    def __init__(self, room: ChatRoom):
        self.current_client_id = None
        self.room = room

    async def wait_hello(self, websocket: WebSocket) -> HelloMessage:
        """
        Ожидает 10 секунд, пока не придет сообщение с типом "hello".
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
            data={"active_clients": list(self.room.active_connections.keys())}
        )
        if broadcast:
            await self.broadcast(status_message.model_dump())
        else:
            await self.send_personal_message(status_message.model_dump(), self.current_client_id)
    
    async def send_error_message(self, message: str):
        """
        Отправляет клиенту сообщение об ошибке.
        """
        error_message = ErrorMessage(
            data={"message": message}
        )
        await self.send_personal_message(error_message.model_dump(), self.current_client_id)
    
    async def send_user_disconnected(self, client_id: str):
        """
        Оповещает всех в чате о том, что пользователь отключился.
        
        ### Param:
            - `client_id` (str): id пользователя, который был отключен
        """
        await self.broadcast(message={
            "type": "user_disconnected", 
            "client_id": client_id
        }, exclude=None)

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
        
        hello_message = await self.wait_hello(websocket)
        self.current_client_id = hello_message.data["user"]

        self.room.active_connections[self.current_client_id] = websocket
        self.room.connection_times[self.current_client_id] = datetime.now()
        
        print(f"Added new user {self.current_client_id}")
        print(f"{self.room.active_connections=}")

        # сообщаем всем, что юзер подключился
        await self.broadcast(message={"type": "user_connected", "client_id": self.current_client_id})
        # отправляем сообщение о подключенных пользователях
        await self.send_active_users(broadcast=True)

    def disconnect(self):
        """
        Удаляет пользователя из списка подключенных.
        """
        if self.current_client_id in self.room.active_connections:
            del self.room.active_connections[self.current_client_id]
        if self.current_client_id in self.room.connection_times:
            del self.room.connection_times[self.current_client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        """
        Отправляет сообщение активному пользователю.
        
        ### Param:
            - `message` (dict): сообщение, которое нужно отправить
            - `client_id` (str): id пользователя, которому нужно отправить сообщение
        """
        if client_id in self.room.active_connections:
            await self.room.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """
        Отправляет сообщение всем подключенным пользователям, исключая те, которые в `exclude`.
        
        ### Param:
            - `message` (dict): сообщение, которое нужно отправить
            - `exclude` (Set[str]): пользователи, которым не нужно отправлять сообщение
        """
        for client_id in self.room.active_connections:
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
                await self.send_error_message("Сообщение слишком длинное")
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
                        if receiver in self.room.active_connections:
                            await self.send_personal_message(receive_message.model_dump(), receiver)
                else:
                    # Отправка всем
                    await self.broadcast(receive_message.model_dump())
