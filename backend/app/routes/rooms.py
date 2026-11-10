
from fastapi import APIRouter, HTTPException

from app.models import (
    CreateRoomRequest,
    JoinRoomRequest,
    ReadyRequest,
    StartGameRequest,
    BidRequest
)

from app.room_manager import room_manager

from app.game_engine import (
    get_auction_state,
    place_bid,
    get_final_results
)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


def public_room(room):
    # Never expose secret target IDs through the public room response.
    players = []

    for player in room["players"].values():
        players.append({
            "id": player["id"],
            "name": player["name"],
            "cash": player["cash"],
            "ready": player["ready"],
            "company_count": len(player["companies"])
        })

    return {
        "code": room["code"],
        "host_id": room["host_id"],
        "max_players": room["max_players"],
        "starting_cash": room["starting_cash"],
        "company_count": room["company_count"],
        "phase": room["phase"],
        "players": players
    }


@router.post("/create")
def create_room(data: CreateRoomRequest):
    room, host_token = room_manager.create_room(
        data.host_name,
        data.max_players,
        data.starting_cash,
        data.company_count
    )

    return {
        "message": "Room created successfully",
        "room": public_room(room),
        "host_id": room["host_id"],
        "host_token": host_token
    }


@router.post("/{code}/join")
def join_room(code: str, data: JoinRoomRequest):
    code = code.upper()

    player, error = room_manager.join_room(
        code, data.player_name
    )

    if error:
        raise HTTPException(400, error)

    room = room_manager.get_room(code)

    return {
        "message": "Joined room successfully",
        "player": player,
        "room": public_room(room)
    }


@router.get("/{code}")
def get_room(code: str):
    room = room_manager.get_room(code.upper())

    if not room:
        raise HTTPException(404, "Room not found")

    return public_room(room)


@router.patch("/{code}/ready/{player_id}")
def update_ready(code: str, player_id: str, data: ReadyRequest):
    room, error = room_manager.set_ready(
        code.upper(), player_id, data.ready
    )

    if error:
        raise HTTPException(400, error)

    return {
        "message": "Ready status updated",
        "room": public_room(room)
    }


@router.post("/{code}/start")
def start_game(code: str, data: StartGameRequest):
    room, error = room_manager.start_game(
        code.upper(), data.host_token
    )

    if error:
        raise HTTPException(400, error)

    return {
        "message": "Game started!",
        "room": public_room(room)
    }


@router.delete("/{code}/leave/{player_id}")
def leave_room(code: str, player_id: str):
    room, error = room_manager.leave_room(
        code.upper(), player_id
    )

    if error:
        raise HTTPException(400, error)

    return {
        "message": "You left the room",
        "room": public_room(room) if room else None
    }


# ---------------------------------
# AUCTION ENDPOINTS
# ---------------------------------

@router.get("/{code}/auction/{player_id}")
def auction_state(code: str, player_id: str):
    room = room_manager.get_room(code.upper())

    if not room:
        raise HTTPException(404, "Room not found")

    state = get_auction_state(room, player_id)

    if state is None:
        raise HTTPException(404, "Player not found")

    return state


@router.post("/{code}/bid")
def submit_bid(code: str, data: BidRequest):
    room = room_manager.get_room(code.upper())

    if not room:
        raise HTTPException(404, "Room not found")

    error = place_bid(
        room,
        data.player_id,
        data.amount
    )

    if error:
        raise HTTPException(400, error)

    return {
        "message": "Bid placed successfully",
        "highest_bid": room["highest_bid"],
        "highest_bidder_id": room["highest_bidder_id"]
    }


@router.get("/{code}/results/{player_id}")
def final_results(code: str, player_id: str):
    room = room_manager.get_room(code.upper())

    if not room:
        raise HTTPException(404, "Room not found")

    if player_id not in room["players"]:
        raise HTTPException(404, "Player not found")

    results = get_final_results(room)

    if results is None:
        raise HTTPException(400, "Auction has not finished yet")

    return results
