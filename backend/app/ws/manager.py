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
        dead_connections = []
        event = message.get("event") if isinstance(message, dict) else None
        print(
            f"WS broadcast event={event!r} "
            f"clients={len(self.active_connections)}"
        )

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"WS broadcast send failed ({event}): {e}")
                # Drop only broken sockets, not serialization bugs on a live client.
                msg = str(e).lower()
                if "serializable" in msg or "not json" in msg:
                    continue
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)

    async def broadcast_new_export(self, batch_id: str, excel_file: str):
        await self.broadcast({
            "event": "excel_exported",
            "batch_id": batch_id,
            "file": excel_file
        })


manager = ConnectionManager()