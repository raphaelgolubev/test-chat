from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, List


app = FastAPI()


# Хранение активных пользователей
active_users: Dict[str, WebSocket] = {}


@app.get("/")
async def root():
    return FileResponse("static/index.html")

