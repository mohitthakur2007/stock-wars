
const API = "https://stock-wars-1.onrender.com";

let roomCode = null;
let playerId = null;
let hostToken = null;
let isReady = false;
let pollTimer = null;
let auctionPollTimer = null;
let latestAuctionState = null;
let auctionScreenActive = false;
let resultsLoading = false;

const $ = (id) => document.getElementById(id);


// =====================================
// GENERAL HELPERS
// =====================================

function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.remove("hidden");

    clearTimeout(showToast.timer);

    showToast.timer = setTimeout(() => {
        toast.classList.add("hidden");
    }, 2500);
}


async function apiRequest(path, method = "GET", body = null) {
    const options = {
        method,
        headers: { "Content-Type": "application/json" }
    };

    if (body !== null) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(API + path, options);

    let data = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
    }

    return data;
}


function formatMoney(value) {
    return "₹" + Number(value || 0).toLocaleString("en-IN");
}


function saveSession() {
    localStorage.setItem("stockwars_session", JSON.stringify({
        roomCode,
        playerId,
        hostToken
    }));
}


function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }

    if (auctionPollTimer) {
        clearInterval(auctionPollTimer);
        auctionPollTimer = null;
    }
}


function clearSession() {
    localStorage.removeItem("stockwars_session");

    stopPolling();

    roomCode = null;
    playerId = null;
    hostToken = null;
    isReady = false;
    auctionScreenActive = false;
    latestAuctionState = null;
    resultsLoading = false;

    $("home-screen").classList.remove("hidden");
    $("lobby-screen").classList.add("hidden");
    $("game-screen").classList.add("hidden");
}


// =====================================
// LOBBY
// =====================================

function openLobby(room) {
    auctionScreenActive = false;
    resultsLoading = false;

    $("home-screen").classList.add("hidden");
    $("lobby-screen").classList.remove("hidden");
    $("game-screen").classList.add("hidden");

    $("display-code").textContent = room.code;

    $("setting-cash").textContent =
        formatMoney(room.starting_cash);

    $("setting-companies").textContent = room.company_count;
    $("setting-max").textContent = room.max_players;

    $("start-btn").classList.toggle("hidden", !hostToken);
    $("ready-btn").classList.remove("hidden");

    stopPolling();

    pollTimer = setInterval(refreshRoom, 2000);

    renderRoom(room);
}


function renderRoom(room) {
    const players = room.players || [];

    $("player-count").textContent =
        `${players.length}/${room.max_players}`;

    $("players-list").innerHTML = "";

    players.forEach(player => {
        const row = document.createElement("div");
        row.className = "player-row";

        const info = document.createElement("div");
        info.className = "player-info";

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = player.name.charAt(0).toUpperCase();

        const details = document.createElement("div");

        const name = document.createElement("div");
        name.className = "player-name";
        name.textContent = player.name;

        if (player.id === room.host_id) {
            const tag = document.createElement("span");
            tag.className = "host-tag";
            tag.textContent = "HOST";
            name.appendChild(tag);
        }

        details.appendChild(name);
        info.append(avatar, details);

        const status = document.createElement("span");
        status.className = "status-tag";

        if (player.ready) {
            status.classList.add("ready");
            status.textContent = "● READY";
        } else {
            status.textContent = "● NOT READY";
        }

        row.append(info, status);
        $("players-list").appendChild(row);
    });

    const me = players.find(p => p.id === playerId);

    if (!me) {
        showToast("You are no longer in this room.");
        clearSession();
        return;
    }

    isReady = me.ready;

    $("ready-btn").textContent = isReady
        ? "Cancel Ready"
        : "✓ I'm Ready";

    $("ready-btn").classList.toggle("primary-btn", !isReady);
    $("ready-btn").classList.toggle("secondary-btn", isReady);

    const allReady =
        players.length >= 2 &&
        players.every(p => p.ready);

    if (hostToken) {
        $("start-btn").disabled = !allReady;
        $("start-btn").style.opacity = allReady ? "1" : "0.4";
    }

    $("lobby-message").textContent = allReady
        ? "Everyone is ready. Host can start the auction!"
        : "Waiting for all players to get ready...";
}


async function refreshRoom() {
    if (!roomCode || auctionScreenActive) return;

    try {
        const room = await apiRequest(`/rooms/${roomCode}`);

        if (room.phase === "lobby") {
            renderRoom(room);
            return;
        }

        if (room.phase === "auction" || room.phase === "results") {
            startAuctionView();
        }

    } catch (error) {
        showToast(error.message);
        clearSession();
    }
}


// =====================================
// CREATE ROOM
// =====================================

$("create-btn").addEventListener("click", async () => {
    const name = $("host-name").value.trim();

    if (name.length < 2) {
        showToast("Enter a name with at least 2 characters.");
        return;
    }

    try {
        const result = await apiRequest("/rooms/create", "POST", {
            host_name: name,
            max_players: Number($("max-players").value),
            starting_cash: Number($("starting-cash").value),
            company_count: Number($("company-count").value)
        });

        roomCode = result.room.code;
        playerId = result.host_id;
        hostToken = result.host_token;

        saveSession();
        openLobby(result.room);

        showToast("Private room created!");

    } catch (error) {
        showToast(error.message);
    }
});


// =====================================
// JOIN ROOM
// =====================================

$("join-btn").addEventListener("click", async () => {
    const name = $("join-name").value.trim();
    const code = $("room-code").value.trim().toUpperCase();

    if (name.length < 2 || code.length !== 6) {
        showToast("Enter your name and a valid 6-character code.");
        return;
    }

    try {
        const result = await apiRequest(
            `/rooms/${code}/join`,
            "POST",
            { player_name: name }
        );

        roomCode = code;
        playerId = result.player.id;
        hostToken = null;

        saveSession();
        openLobby(result.room);

        showToast("Joined room successfully!");

    } catch (error) {
        showToast(error.message);
    }
});


// =====================================
// READY BUTTON
// =====================================

$("ready-btn").addEventListener("click", async () => {
    try {
        const result = await apiRequest(
            `/rooms/${roomCode}/ready/${playerId}`,
            "PATCH",
            { ready: !isReady }
        );

        renderRoom(result.room);

    } catch (error) {
        showToast(error.message);
    }
});


// =====================================
// START AUCTION
// =====================================

$("start-btn").addEventListener("click", async () => {
    const button = $("start-btn");

    button.disabled = true;
    button.textContent = "Starting auction...";

    try {
        await apiRequest(
            `/rooms/${roomCode}/start`,
            "POST",
            { host_token: hostToken }
        );

        startAuctionView();

    } catch (error) {
        showToast(error.message);
        button.disabled = false;
        button.textContent = "Start Auction →";
    }
});


// =====================================
// COPY ROOM CODE
// =====================================

$("copy-code").addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(roomCode);
        showToast("Room code copied!");
    } catch {
        showToast("Could not copy the room code.");
    }
});


// =====================================
// LEAVE ROOM
// =====================================

$("leave-btn").addEventListener("click", async () => {
    try {
        await apiRequest(
            `/rooms/${roomCode}/leave/${playerId}`,
            "DELETE"
        );

        clearSession();
        showToast("You have left the room.");

    } catch (error) {
        showToast(error.message);
    }
});


// =====================================
// START AUCTION VIEW
// =====================================

function startAuctionView() {
    if (auctionScreenActive) return;

    auctionScreenActive = true;

    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }

    $("lobby-screen").classList.add("hidden");
    $("home-screen").classList.add("hidden");
    $("game-screen").classList.remove("hidden");

    $("game-room-code").textContent = roomCode;

    $("auction-view").classList.remove("hidden");
    $("results-view").classList.add("hidden");

    refreshAuction();

    if (auctionPollTimer) {
        clearInterval(auctionPollTimer);
    }

    auctionPollTimer = setInterval(refreshAuction, 700);
}


// =====================================
// REFRESH AUCTION
// =====================================

async function refreshAuction() {
    if (!roomCode || !playerId) return;

    try {
        const state = await apiRequest(
            `/rooms/${roomCode}/auction/${playerId}`
        );

        if (state.phase === "results") {
            if (auctionPollTimer) {
                clearInterval(auctionPollTimer);
                auctionPollTimer = null;
            }

            showFinalResults();
            return;
        }

        if (state.phase !== "auction") return;

        latestAuctionState = state;

        renderAuction(state);

    } catch (error) {
        console.error("Auction refresh error:", error);
    }
}


// =====================================
// RENDER CURRENT COMPANY
// =====================================

function renderAuction(state) {
    const company = state.company;

    if (!company) return;

    $("target-company").textContent =
        state.target_company_id || "C--";

    $("auction-progress").textContent =
        `${state.auction_number} / ${state.total_companies}`;

    $("company-id").textContent = company.id;
    $("company-sector").textContent = company.sector || "-";
    $("company-business").textContent = company.business || "-";
    $("company-risk").textContent = company.risk || "-";
    $("company-growth").textContent = company.growth || "-";
    $("company-revenue").textContent =
        company.revenue_trend || "-";

    $("base-valuation").textContent =
        formatMoney(company.base_value);

    $("starting-bid").textContent =
        formatMoney(company.base_value / 2);

    $("highest-bid").textContent =
        state.highest_bid === null
            ? "No bids yet"
            : formatMoney(state.highest_bid);

    $("highest-bidder").textContent =
        state.highest_bidder || "None";

    $("your-cash").textContent =
        formatMoney(state.your_cash);

    $("minimum-bid").textContent =
        formatMoney(state.minimum_bid);

    $("auction-timer").textContent =
        Math.ceil(state.time_remaining);

    const isLeading =
        state.highest_bidder_id === playerId;

    const hasEnoughCash =
        Number(state.your_cash) >= Number(state.minimum_bid);

    const hasCompanySpace =
        Number(state.your_company_count) < 4;

    const canBid =
        !isLeading &&
        hasEnoughCash &&
        hasCompanySpace &&
        state.time_remaining > 0;

    $("bid-btn").disabled = !canBid;

    if (isLeading) {
        $("bid-message").textContent =
            "You are currently the highest bidder!";
    } else if (!hasCompanySpace) {
        $("bid-message").textContent =
            "You already own the maximum of 4 companies.";
    } else if (!hasEnoughCash) {
        $("bid-message").textContent =
            "You don't have enough cash for the minimum bid.";
    } else {
        $("bid-message").textContent = "";
    }

    renderAuctionPlayers(
        state.players || [],
        state.highest_bidder_id
    );
}


// =====================================
// LIVE PLAYERS
// =====================================

function renderAuctionPlayers(players, highestBidderId) {
    const container = $("auction-players");
    container.innerHTML = "";

    players.forEach(player => {
        const row = document.createElement("div");
        row.className = "auction-player-row";

        if (player.id === highestBidderId) {
            row.classList.add("leading");
        }

        const details = document.createElement("div");

        const name = document.createElement("strong");
        name.textContent =
            player.name + (player.id === playerId ? " (YOU)" : "");

        const info = document.createElement("small");
        info.textContent =
            `${player.company_count} companies owned`;

        details.append(name, info);

        const cash = document.createElement("strong");
        cash.textContent = formatMoney(player.cash);

        row.append(details, cash);
        container.appendChild(row);
    });
}


// =====================================
// PLACE BID
// =====================================

$("bid-btn").addEventListener("click", async () => {
    if (!latestAuctionState) return;

    const amount = Number($("bid-amount").value);

    if (!Number.isInteger(amount) || amount <= 0) {
        showToast("Enter a valid whole-number bid.");
        return;
    }

    $("bid-btn").disabled = true;

    try {
        await apiRequest(
            `/rooms/${roomCode}/bid`,
            "POST",
            {
                player_id: playerId,
                amount: amount
            }
        );

        $("bid-message").textContent =
            "Bid placed successfully!";

        $("bid-amount").value = "";

    } catch (error) {
        $("bid-message").textContent = error.message;
    }

    await refreshAuction();
});


// =====================================
// FINAL RESULTS
// =====================================

async function showFinalResults() {
    if (resultsLoading) return;

    resultsLoading = true;

    try {
        const results = await apiRequest(
            `/rooms/${roomCode}/results/${playerId}`
        );

        $("auction-view").classList.add("hidden");
        $("results-view").classList.remove("hidden");

        const winner = results.winner;

        $("winner-name").textContent =
            winner ? winner.name : "No winner";

        $("winner-value").textContent =
            winner ? formatMoney(winner.portfolio_value) : "₹0";

        $("winner-reason").textContent =
            results.winner_reason || "";

        renderFinalLeaderboard(results.leaderboard || []);
        renderCompanyReveal(results.companies || []);

    } catch (error) {
        resultsLoading = false;
        showToast(error.message);
    }
}


// =====================================
// FINAL LEADERBOARD
// =====================================

function renderFinalLeaderboard(players) {
    const container = $("final-leaderboard");
    container.innerHTML = "";

    players.forEach((player, index) => {
        const row = document.createElement("div");
        row.className = "final-player-row";

        const rank = document.createElement("div");
        rank.className = "final-rank";
        rank.textContent = `#${index + 1}`;

        const details = document.createElement("div");

        const name = document.createElement("strong");
        name.textContent = player.name;

        const info = document.createElement("small");
        info.textContent =
            `${player.company_count} companies · ` +
            `Target ${player.target_company_id}: ` +
            (player.target_completed ? "Completed" : "Not completed");

        details.append(name, info);

        const value = document.createElement("div");
        value.className = "final-portfolio-value";
        value.textContent = formatMoney(player.portfolio_value);

        row.append(rank, details, value);
        container.appendChild(row);
    });
}


// =====================================
// REVEAL NIFTY 100 COMPANIES
// =====================================


function renderCompanyReveal(companies) {
    const container = $("company-reveal");
    container.innerHTML = "";

    companies.forEach(company => {
        const row = document.createElement("div");
        row.className = "company-reveal-row";

        const details = document.createElement("div");

        const name = document.createElement("h3");
        name.textContent =
            `${company.name} (${company.symbol})`;

        const info = document.createElement("p");
        info.textContent =
            `Card: ${company.id} · ` +
            `Sector: ${company.sector} · ` +
            `Risk: ${company.risk} · ` +
            `Growth: ${company.growth} · ` +
            `Revenue: ${company.revenue_trend} · ` +
            `Hidden trait: ${company.hidden_trait} · ` +
            `Owner: ${company.owner_name || "Unsold"}`;

        details.append(name, info);

        const value = document.createElement("div");
        value.className = "reveal-value";

        // Final company valuation
        const finalValue = document.createElement("strong");
        finalValue.textContent =
            formatMoney(company.final_value);

        const baseValue = document.createElement("small");
        baseValue.textContent =
            `Base valuation: ${formatMoney(company.base_value)}`;

        value.append(finalValue, baseValue);

        // Purchase price and discount/premium
        const purchaseInfo = document.createElement("small");

        if (company.sold_price !== null &&
            company.sold_price !== undefined) {

            const discount =
                ((company.base_value - company.sold_price) /
                company.base_value) * 100;

            let purchaseText =
                `Bought: ${formatMoney(company.sold_price)}`;

            if (discount > 0) {
                purchaseText +=
                    ` · ${discount.toFixed(1)}% discount`;
            } else if (discount < 0) {
                purchaseText +=
                    ` · ${Math.abs(discount).toFixed(1)}% premium`;
            } else {
                purchaseText += " · At base valuation";
            }

            purchaseInfo.textContent = purchaseText;

        } else {
            purchaseInfo.textContent = "Unsold";
        }

        value.appendChild(purchaseInfo);

        row.append(details, value);
        container.appendChild(row);
    });
}

// =====================================
// RESTORE SESSION AFTER PAGE REFRESH
// =====================================

async function restoreSession() {
    const saved = localStorage.getItem("stockwars_session");

    if (!saved) return;

    try {
        const session = JSON.parse(saved);

        roomCode = session.roomCode;
        playerId = session.playerId;
        hostToken = session.hostToken;

        if (!roomCode || !playerId) {
            throw new Error("Invalid saved session.");
        }

        const room = await apiRequest(`/rooms/${roomCode}`);

        if (room.phase === "lobby") {
            openLobby(room);
        } else {
            startAuctionView();
        }

    } catch (error) {
        console.error("Session restore failed:", error);
        clearSession();
    }
}


// Start application
restoreSession();
