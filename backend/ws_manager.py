from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # chat_id -> lista de WebSocket-uri conectate la acel chat
        self.rooms: dict[int, list[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        await websocket.accept()          # acceptăm "strângerea de mână" WebSocket
        self.rooms.setdefault(chat_id, []).append(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket):
        room = self.rooms.get(chat_id, [])
        if websocket in room:
            room.remove(websocket)
        if not room:
            self.rooms.pop(chat_id, None)

    async def broadcast(self, chat_id: int, data: dict):
        # list(...) = copie, ca să putem modifica lista cât iterăm
        for ws in list(self.rooms.get(chat_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(chat_id, ws)   # conexiune moartă -> o scoatem


manager = ConnectionManager()