
import time
from app.company_universe import generate_companies


def start_auction(room):
    """
    Initialize the auction using randomly selected NIFTY 100 companies.
    Assign one unique secret target company to every player.
    """

    companies = generate_companies(room["company_count"])

    company_ids = [company["id"] for company in companies]
    target_assignments = company_ids.copy()

    # Every player receives a unique target company.
    import random
    random.shuffle(target_assignments)

    for player, target_id in zip(
        room["players"].values(),
        target_assignments
    ):
        player["target_company_id"] = target_id

    room["companies"] = companies
    room["auction_index"] = 0
    room["auction_number"] = 1

    room["highest_bid"] = None
    room["highest_bidder_id"] = None

    room["auction_deadline"] = time.time() + 20
    room["phase"] = "auction"


def current_company(room):
    """Return the company currently being auctioned."""

    index = room["auction_index"]
    companies = room["companies"]

    if index >= len(companies):
        return None

    return companies[index]


def close_current_auction(room):
    """
    Close the current lot.
    Award the company to the highest bidder, if any.
    Move to the next company.
    """

    company = current_company(room)

    if company is None:
        room["phase"] = "results"
        return

    highest_bid = room["highest_bid"]
    bidder_id = room["highest_bidder_id"]

    # Award the company if someone placed a valid bid.
    if highest_bid is not None and bidder_id is not None:

        player = room["players"].get(bidder_id)

        if player:
            player["cash"] -= highest_bid
            player["companies"].append(company["id"])

            company["owner_id"] = bidder_id
            company["sold_price"] = highest_bid

    # Move to the next lot.
    room["auction_index"] += 1
    room["auction_number"] += 1

    room["highest_bid"] = None
    room["highest_bidder_id"] = None

    # Check whether all companies have been auctioned.
    if room["auction_index"] >= len(room["companies"]):
        room["phase"] = "results"
        room["auction_deadline"] = None
    else:
        room["auction_deadline"] = time.time() + 20


def advance_auction(room):
    """
    Automatically advance the auction when the timer expires.
    Called whenever a player requests auction state or places a bid.
    """

    if room["phase"] != "auction":
        return

    if room["auction_deadline"] is None:
        return

    if time.time() >= room["auction_deadline"]:
        close_current_auction(room)


def place_bid(room, player_id, amount):
    """
    Validate and place a player's bid.

    Returns:
        None: Bid successful.
        str: Error message if bid is invalid.
    """

    advance_auction(room)

    if room["phase"] != "auction":
        return "Auction is not active"

    player = room["players"].get(player_id)

    if not player:
        return "Player not found"

    company = current_company(room)

    if not company:
        return "No company is currently being auctioned"

    # Maximum four companies per player.
    if len(player["companies"]) >= 4:
        return "You already own the maximum of 4 companies"

    if company["owner_id"] is not None:
        return "This company has already been sold"

    if not isinstance(amount, int) or isinstance(amount, bool):
        return "Bid must be a whole number"

    if amount <= 0:
        return "Bid must be greater than zero"

    # Starting bid is 50% of base valuation.
    starting_bid = company["base_value"] // 2

    if room["highest_bid"] is None:
        minimum_bid = starting_bid
    else:
        minimum_bid = room["highest_bid"] + 100

    if amount < minimum_bid:
        return f"Minimum bid is ₹{minimum_bid}"

    if amount > player["cash"]:
        return "Insufficient cash"

    # Place the bid.
    room["highest_bid"] = amount
    room["highest_bidder_id"] = player_id

    # Every new bid resets timer to 5 seconds.
    room["auction_deadline"] = time.time() + 10

    return None


def get_auction_state(room, player_id):
    """
    Return auction information visible to a particular player.

    Company name, ticker and hidden trait are concealed.
    The player's target ID is visible only to that player.
    """

    advance_auction(room)

    if room["phase"] != "auction":
        return {
            "phase": room["phase"]
        }

    player = room["players"].get(player_id)

    if not player:
        return None

    company = current_company(room)

    if company is None:
        return {
            "phase": "results"
        }

    if room["highest_bid"] is None:
        minimum_bid = company["base_value"] // 2
    else:
        minimum_bid = room["highest_bid"] + 100

    time_remaining = max(
        0,
        round(room["auction_deadline"] - time.time(), 1)
    )

    highest_bidder = room["players"].get(
        room["highest_bidder_id"]
    ) if room["highest_bidder_id"] else None

    # Public player information.
    players = []

    for p in room["players"].values():
        players.append({
            "id": p["id"],
            "name": p["name"],
            "cash": p["cash"],
            "company_count": len(p["companies"])
        })

    return {
        "phase": "auction",

        "company": {
            "id": company["id"],
            "sector": company["sector"],
            "business": company["business"],
            "risk": company["risk"],
            "growth": company["growth"],
            "revenue_trend": company["revenue_trend"],
            "base_value": company["base_value"]
        },

        "auction_number": room["auction_number"],
        "total_companies": len(room["companies"]),

        "highest_bid": room["highest_bid"],
        "highest_bidder_id": room["highest_bidder_id"],
        "highest_bidder": (
            highest_bidder["name"]
            if highest_bidder else None
        ),

        "minimum_bid": minimum_bid,
        "time_remaining": time_remaining,

        "your_cash": player["cash"],
        "your_company_count": len(player["companies"]),

        # Secret target: visible only to the requesting player.
        "target_company_id": player["target_company_id"],

        "players": players
    }


def get_final_results(room):
    """
    Calculate final company valuations and determine the winner.
    Reveal actual NIFTY 100 company names, symbols and hidden traits.
    """

    advance_auction(room)

    if room["phase"] != "results":
        return None

    leaderboard = []

    # Calculate final company values.
    for company in room["companies"]:

        base_value = company["base_value"]
        multiplier = company["hidden_multiplier"]

        final_value = round(base_value * multiplier)

        company["final_value"] = final_value

    # Calculate each player's portfolio.
    for player in room["players"].values():

        portfolio_value = player["cash"]

        owned_companies = []

        for company in room["companies"]:

            if company["owner_id"] == player["id"]:
                portfolio_value += company["final_value"]

                owned_companies.append(company["id"])

        target_id = player["target_company_id"]

        target_completed = target_id in owned_companies

        leaderboard.append({
            "player_id": player["id"],
            "name": player["name"],
            "remaining_cash": player["cash"],
            "owned_companies": owned_companies,
            "company_count": len(owned_companies),
            "target_company_id": target_id,
            "target_completed": target_completed,
            "portfolio_value": portfolio_value
        })

    # First priority: players who completed their target.
    eligible_players = [
        player
        for player in leaderboard
        if player["target_completed"]
    ]

    # If nobody completes their target, consider everyone.
    if not eligible_players:
        eligible_players = leaderboard

    # Highest portfolio value wins.
    eligible_players.sort(
        key=lambda player: player["portfolio_value"],
        reverse=True
    )

    winner = eligible_players[0] if eligible_players else None

    # Reveal all company information.
    revealed_companies = []

    for company in room["companies"]:

        owner = room["players"].get(company["owner_id"])

        revealed_companies.append({
            "id": company["id"],
            "name": company["name"],
            "symbol": company["symbol"],
            "sector": company["sector"],
            "business": company["business"],
            "risk": company["risk"],
            "growth": company["growth"],
            "revenue_trend": company["revenue_trend"],
            "base_value": company["base_value"],
            "sold_price": company["sold_price"],
            "hidden_trait": company["hidden_trait"],
            "final_value": company["final_value"],
            "owner_id": company["owner_id"],
            "owner_name": owner["name"] if owner else None
        })

    return {
        "phase": "results",

        "winner": winner,

        "winner_reason": (
            "Completed secret target and achieved the highest portfolio value."
            if winner and winner["target_completed"]
            else "No player completed their secret target. Highest portfolio value wins."
        ),

        "leaderboard": sorted(
            leaderboard,
            key=lambda player: player["portfolio_value"],
            reverse=True
        ),

        "companies": revealed_companies
    }
