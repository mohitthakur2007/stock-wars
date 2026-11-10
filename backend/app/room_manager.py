
import secrets
import string
import uuid

from app.game_engine import start_auction
class RoomManager:

    def __init__(self):
        self.rooms = {}

    def generate_code(self):
        characters = string.ascii_uppercase + string.digits

        while True:
            code = ''.join(
                secrets.choice(characters) for _ in range(6)
            )

            if code not in self.rooms:
                return code

    def create_room(
        self, host_name, max_players,
        starting_cash, company_count
    ):
        code = self.generate_code()
        host_id = str(uuid.uuid4())
        host_token = secrets.token_urlsafe(24)

        room = {
            "code": code,
            "host_id": host_id,
            "host_token": host_token,
            "max_players": max_players,
            "starting_cash": starting_cash,
            "company_count": company_count,
            "phase": "lobby",
            "players": {
                host_id: {
                    "id": host_id,
                    "name": host_name,
                    "cash": starting_cash,
                    "ready": False,
                    "companies": []
                }
            }
        }

        self.rooms[code] = room
        return room, host_token

    def join_room(self, code, player_name):
        room = self.rooms.get(code)

        if not room:
            return None, "Room not found"

        if room["phase"] != "lobby":
            return None, "Game has already started"

        if len(room["players"]) >= room["max_players"]:
            return None, "Room is full"

        player_id = str(uuid.uuid4())

        player = {
            "id": player_id,
            "name": player_name,
            "cash": room["starting_cash"],
            "ready": False,
            "companies": []
        }

        room["players"][player_id] = player
        return player, None

    def get_room(self, code):
        return self.rooms.get(code)

    def set_ready(self, code, player_id, ready):
        room = self.rooms.get(code)

        if not room:
            return None, "Room not found"

        if room["phase"] != "lobby":
            return None, "Lobby is closed"

        player = room["players"].get(player_id)

        if not player:
            return None, "Player not found"

        player["ready"] = ready
        return room, None

    def start_game(self, code, host_token):
        room = self.rooms.get(code)

        if not room:
            return None, "Room not found"

        if room["host_token"] != host_token:
            return None, "Only the host can start the game"

        if room["phase"] != "lobby":
            return None, "Game has already started"

        if len(room["players"]) < 2:
            return None, "At least 2 players are required"

        if not all(p["ready"] for p in room["players"].values()):
            return None, "All players must be ready"

        # Actually initialize the auction.
        start_auction(room)

        return room, None


    def leave_room(self, code, player_id):
        room = self.rooms.get(code)

        if not room:
            return None, "Room not found"

        if player_id not in room["players"]:
            return None, "Player not found"

        if player_id == room["host_id"]:
            del self.rooms[code]
            return None, None

        del room["players"][player_id]
        return room, None

room_manager = RoomManager()
