from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HelloMessage(BaseModel):
    """ Приветственное сообщение от клиента """
    type: str = "hello"
    data: dict = {
        "user": str
    }

class StatusRequest(BaseModel):
    """ Запрос статуса от клиента """
    type: str = "receive_status"

class ChatStatus(BaseModel):
    """ Ответ сервера на запрос статуса и приветственное сообщение """
    type: str = "chat_status"
    data: dict = {
        "active_clients": List[str]
    }

class SendMessage(BaseModel):
    """ Отправка сообщения пользователем """
    type: str = "send_message"
    data: dict = {
        "receivers": Optional[List[str]],
        "text": str
    }

class ReceiveMessage(BaseModel):
    """ Получение нового сообщения клиентов """
    type: str = "receive_message"
    data: dict = {
        "sender": str,
        "timestamp": int,
        "text": str
    }

class ErrorMessage(BaseModel):
    """ Сообщение об ошибке """
    type: str = "error"
    data: dict = {
        "message": str
    }