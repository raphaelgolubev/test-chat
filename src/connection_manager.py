from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_times: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id] = websocket
        self.connection_times[client_id] = datetime.now()
        # сообщаем всем, что юзер подключился
        await self.broadcast(message={"type": "user_connected", "client_id": client_id})
    
    async def send_event(self, event: dict, client_id: str):
        await self.active_connections[client_id].send_json(event)

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_times:
            del self.connection_times[client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, exclude: Set[str] = None):
        for client_id in self.active_connections:
            if exclude and client_id in exclude:
                continue
            await self.send_personal_message(message, client_id)


manager = ConnectionManager()
