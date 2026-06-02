from typing import List
from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead.append(connection)

        for d in dead:
            self.disconnect(d)

    async def broadcast_new_export(self, batch_id: str, excel_file: str):
        """Notify clients when a new Excel is exported"""
        await self.broadcast({
            "event": "excel_exported",
            "batch_id": batch_id,
            "file": excel_file
        })


# GLOBAL INSTANCE (use this everywhere)
manager = ConnectionManager()