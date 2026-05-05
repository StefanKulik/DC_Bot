from __future__ import annotations

import subprocess
import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
import re

import discord
from discord import app_commands
from discord.ext import commands

from config.Environment import RESULT_CHANNEL
from config.SqliteStore import (
    ensure_ranked_storage,
    fetch_active_ranked_matches,
    fetch_match_history,
    fetch_monthly_ranking,
    fetch_world_ranking,
    get_current_ranked_month_key,
    get_next_ranked_match_id,
    mark_ranked_match_result_published,
    persist_active_ranked_match,
    persist_ranked_match_result,
)


#
# TODO:
#   X - ranked extrahieren für Leon
#   X - db struktur anpassen an die von Leon für nahtlosen übergang
#   X - zurückziehen Button rausnehmen
#   X - Modal auf webseite verschönern
#   X - screenshot pflicht
#   ergebnis eintragen, score ist irrelevant wie rum geschrieben
#   backup system für result eintragen -> match speichern mit pending und command /result im thread, thread wird ja nicht gelöscht
#   wenn formular geöffnet aber auf abbrechen geklickt, dann soll der Button wieder aktiv sein

# =============================
# Konstanten und Parser-Patterns für Queue, Threads und Ergebnisse.
# =============================
QUEUE_EMPTY_TEXT = "kein spieler"
MATCHES_FIELD_NAME = ":fire: Aktuelle Matches"
RESULTS_CHANNEL_ID = RESULT_CHANNEL
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")
THREAD_SAFE_PATTERN = re.compile(r"[^a-z0-9-]")
SCORE_PATTERN = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")
AVERAGE_PATTERN = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*$")
REPO_ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD_FILE = "index.html"
PLAYER_DATA_FILE = "players.json"
RANKED_RESULT_STATUS_SQL = "status IN ('completed', 'confirmed') AND winner_id IS NOT NULL AND loser_id IS NOT NULL"

# =============================
# WEBSITE - generate static html for displaying ranking on web
# =============================

def run_git_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def get_current_git_branch() -> str | None:
    branch_result = run_git_command("branch", "--show-current")
    if branch_result.returncode != 0:
        print(f"git branch failed: {branch_result.stderr.strip()}")
        return None

    branch_name = branch_result.stdout.strip()
    if not branch_name:
        print("git branch failed: no current branch")
        return None

    return branch_name


def upload() -> bool:
    add_result = run_git_command("add", LEADERBOARD_FILE, PLAYER_DATA_FILE)
    if add_result.returncode != 0:
        print(f"git add failed: {add_result.stderr.strip()}")
        return False

    diff_result = run_git_command("diff", "--cached", "--quiet", "--", LEADERBOARD_FILE, PLAYER_DATA_FILE)
    if diff_result.returncode == 0:
        print("leaderboard unchanged")
        return False
    if diff_result.returncode != 1:
        print(f"git diff failed: {diff_result.stderr.strip()}")
        return False

    commit_result = run_git_command("commit", "-m", "update leaderboard")
    if commit_result.returncode != 0:
        print(f"git commit failed: {commit_result.stderr.strip()}")
        return False

    branch_name = get_current_git_branch()
    if branch_name is None:
        return False

    push_result = run_git_command("push", "--set-upstream", "origin", branch_name)
    if push_result.returncode != 0:
        print(f"git push failed: {push_result.stderr.strip()}")
        return False

    print("update pushed")
    return True


def parse_stored_average(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


async def build_player_profiles(
    bot: commands.Bot,
    player_data: list[tuple[int, int, int, int]],
    monthly_data: list[tuple[int, int, int, int]],
    get_player_display,
) -> dict[str, dict]:
    world_ranks = {user_id: rank for rank, (user_id, *_rest) in enumerate(player_data, start=1)}
    monthly_ranks = {user_id: rank for rank, (user_id, *_rest) in enumerate(monthly_data, start=1)}
    world_stats = {user_id: (rating, wins, losses) for user_id, rating, wins, losses in player_data}
    monthly_stats = {user_id: (rating, wins, losses) for user_id, rating, wins, losses in monthly_data}
    db = getattr(bot, "db", None)
    matches_by_player: dict[int, list[dict]] = {}
    averages_by_player: dict[int, list[float]] = {}
    recent_match_counts: dict[int, int] = {}
    all_player_ids = set(world_stats) | set(monthly_stats)

    if db is not None:
        async with db._lock:
            rows = db.connection.execute(
                f"""
                SELECT id, player1_id, player2_id, winner_id, loser_id,
                       platform, score, winner_avg, loser_avg, elo_change,
                       strftime('%Y-%m', timestamp) AS month_key
                FROM matches
                WHERE {RANKED_RESULT_STATUS_SQL}
                ORDER BY id DESC
                """
            ).fetchall()

        opponent_ids: set[int] = set()
        pending_entries: list[tuple[int, dict]] = []

        for row in rows:
            winner_id = int(row["winner_id"])
            loser_id = int(row["loser_id"])
            player_one_id = int(row["player1_id"]) if row["player1_id"] is not None else winner_id
            player_two_id = int(row["player2_id"]) if row["player2_id"] is not None else loser_id
            participants = {player_one_id, player_two_id, winner_id, loser_id}
            all_player_ids.update(participants)

            for user_id in (winner_id, loser_id):
                won = user_id == winner_id
                opponent_id = loser_id if won else winner_id
                opponent_ids.add(opponent_id)

                average_value = row["winner_avg"] if won else row["loser_avg"]
                player_average = "" if average_value is None else str(average_value)
                parsed_average = parse_stored_average(player_average)
                if parsed_average is not None:
                    averages_by_player.setdefault(user_id, []).append(parsed_average)

                if recent_match_counts.get(user_id, 0) >= 5:
                    continue

                elo_change = int(row["elo_change"] or 0)
                if not won:
                    elo_change = -elo_change

                recent_match_counts[user_id] = recent_match_counts.get(user_id, 0) + 1
                pending_entries.append(
                    (
                        user_id,
                        {
                            "matchId": int(row["id"]),
                            "result": "Win" if won else "Loss",
                            "opponentId": opponent_id,
                            "opponentName": None,
                            "score": row["score"] or "N/A",
                            "average": player_average or "N/A",
                            "eloChange": elo_change,
                            "queue": row["platform"],
                        },
                    )
                )

        opponent_names = {
            opponent_id: (await get_player_display(opponent_id))[0]
            for opponent_id in opponent_ids
        }
        for user_id, entry in pending_entries:
            entry["opponentName"] = opponent_names.get(entry["opponentId"], f"User {entry['opponentId']}")
            matches_by_player.setdefault(user_id, []).append(entry)

    player_ids = sorted(all_player_ids, key=lambda user_id: world_ranks.get(user_id, 999999))

    profiles: dict[str, dict] = {}
    for user_id in player_ids:
        name, avatar = await get_player_display(user_id)
        world_rating, world_wins, world_losses = world_stats.get(user_id, (1000, 0, 0))
        monthly_rating, monthly_wins, monthly_losses = monthly_stats.get(user_id, (0, 0, 0))
        averages = averages_by_player.get(user_id, [])
        matches = matches_by_player.get(user_id, [])

        total = world_wins + world_losses

        profiles[str(user_id)] = {
            "userId": user_id,
            "name": name,
            "avatar": avatar,
            "worldRating": world_rating,
            "worldRank": world_ranks.get(user_id),
            "worldWins": world_wins,
            "worldLosses": world_losses,
            "monthlyRating": monthly_rating,
            "monthlyRank": monthly_ranks.get(user_id),
            "monthlyWins": monthly_wins,
            "monthlyLosses": monthly_losses,
            "games": total,
            "winrate": round((world_wins / total) * 100, 1) if total else 0,
            "overallAverage": round(sum(averages) / len(averages), 2) if averages else 0,
            "recentMatches": matches,
        }

    return profiles


async def generate_html(bot: commands.Bot):
    guild = bot.guilds[0] if bot.guilds else None
    display_cache: dict[int, tuple[str, str]] = {}

    async def get_player_display(user_id: int) -> tuple[str, str]:
        cached = display_cache.get(user_id)
        if cached is not None:
            return cached

        name = f"User {user_id}"
        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if guild:
            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    member = None

            if member is not None:
                name = member.display_name
                avatar = member.display_avatar.url

        display_cache[user_id] = (name, avatar)
        return name, avatar

    # =============================
    # DATA
    # =============================

    print("fetch data")
    db = getattr(bot, "db", None)
    if db is not None:
        player_data = await db.fetch_world_ranking(limit=None)
        monthly_data = await db.fetch_monthly_ranking(get_current_ranked_month_key(), limit=None)
    else:
        player_data = await fetch_world_ranking(bot)
        monthly_data = await fetch_monthly_ranking(bot)

    top3 = player_data[:3]

    # =============================
    # HTML START
    # =============================

    html = """
    <html>
    <head>
    <style>
    body {background:#0b0f14;color:white;font-family:Segoe UI;text-align:center;}

    .container {display:flex;justify-content:center;gap:50px;margin-top:40px;}

    .podium {display:flex;justify-content:center;gap:30px;margin-top:30px;}

    .card {background:#161b22;padding:20px;border-radius:20px;width:180px;transition:0.3s;cursor:pointer;}
    .card:hover {transform:scale(1.05);}

    .gold {border:2px solid gold;}
    .silver {border:2px solid silver;}
    .bronze {border:2px solid #cd7f32;}

    .avatar {width:70px;height:70px;border-radius:50%;}

    table {width:100%;border-collapse:collapse;margin-top:20px;}
    td {padding:10px;border-bottom:1px solid #222;}

    tr[data-player-id] {cursor:pointer;}
    tr:hover {background:#161b22;}

    a {color:#58a6ff;text-decoration:none;font-weight:bold;}
    .player-link {color:#58a6ff;background:none;border:0;padding:0;font:inherit;font-weight:bold;cursor:pointer;}
    .player-link:hover {text-decoration:underline;}
    .modal-backdrop {align-items:center;background:rgba(0,0,0,.72);display:none;inset:0;justify-content:center;padding:20px;position:fixed;z-index:1000;}
    .modal-backdrop.open {display:flex;}
    .player-modal {background:#161b22;border:1px solid #30363d;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.45);max-width:500px;padding:30px;position:relative;text-align:center;width:min(400px, 100%);}
    .modal-close {background:#21262d;border:1px solid #30363d;border-radius:50%;color:white;cursor:pointer;font-size:22px;height:34px;line-height:28px;position:absolute;right:14px;top:14px;width:34px;}
    .modal-avatar {border-radius:50%;height:120px;width:120px;}
    .player-modal h1 {font-size:32px;margin:18px 0;}
    .player-modal p {font-size:16px;margin:10px 0;}
    .player-modal h3 {margin:22px 0 10px;}
    .match-list {display:inline-block;list-style:none;margin:0;padding-left:0;text-align:left;}
    .match-list li {margin:8px 0;}
    .modal-back-link {background:none;border:0;color:#58a6ff;cursor:pointer;font:inherit;font-weight:bold;margin-top:18px;padding:0;text-decoration:none;}
    .modal-back-link:hover {text-decoration:underline;}
    </style>
    </head>

    <body>

    <h1>🏆 RANKED DARTS Dashboard</h1>
    """

    # =============================
    # PODIUM
    # =============================

    print("build podium")
    html += "<div class='podium'>"
    classes = ["gold", "silver", "bronze"]

    for i, (user_id, world_rating, wins, losses) in enumerate(top3):
        name, avatar = await get_player_display(user_id)

        html += f"""
        <div class='card {classes[i]}' data-player-id="{user_id}">
        <img src="{avatar}" class="avatar"><br>
        <h2>#{i+1}</h2>
        <button type="button" class="player-link" data-player-id="{user_id}">{escape(name)}</button>
        <p>{world_rating} ELO</p>
        <p>{wins}W / {losses}L</p>
        </div>
        """

    html += "</div>"

    # =============================
    # TABLES
    # =============================

    html += "<div class='container'>"
    print("build world ranking")
    # 🌍 WORLD
    html += "<div style='width:40%'><h2>🌍 World Ranking</h2><table>"

    for i, (user_id, world_rating, wins, losses) in enumerate(player_data, 1):
        name, avatar = await get_player_display(user_id)

        html += f"""
        <tr data-player-id="{user_id}">
        <td>{i}</td>
        <td><img src="{avatar}" class="avatar"></td>
        <td><button type="button" class="player-link" data-player-id="{user_id}">{escape(name)}</button></td>
        <td>{world_rating}</td>
        <td>{wins}W / {losses}L</td>
        </tr>
        """

    html += "</table></div>"

    print("build monthly ranking")
    # 🗓️ MONTHLY
    html += "<div style='width:40%'><h2>🗓️ Monatsranking</h2><table>"

    for i, (user_id, monthly_rating, wins, losses) in enumerate(monthly_data, 1):
        name, avatar = await get_player_display(user_id)

        html += f"""
        <tr data-player-id="{user_id}">
        <td>{i}</td>
        <td><img src="{avatar}" class="avatar"></td>
        <td><button type="button" class="player-link" data-player-id="{user_id}">{escape(name)}</button></td>
        <td>{monthly_rating}</td>
        <td>{wins}W / {losses}L</td>
        </tr>
        """

    html += "</table></div>"

    html += "</div>"

    # =============================
    # Player Profiles
    # =============================
    print("build player profiles")

    player_profiles = await build_player_profiles(bot, player_data, monthly_data, get_player_display)
    with open(PLAYER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"players": player_profiles}, f, ensure_ascii=False, indent=2)


    # =============================
    # SAVE
    # =============================
    print("save")
    html += """
    <div id="player-modal-backdrop" class="modal-backdrop" aria-hidden="true">
        <div class="player-modal" role="dialog" aria-modal="true" aria-labelledby="modal-player-name">
            <button type="button" id="modal-close" class="modal-close" aria-label="Schliessen">&times;</button>
            <img id="modal-avatar" class="modal-avatar" src="" alt="">
            <h1 id="modal-player-name"></h1>
            <p id="modal-rating"></p>
            <p id="modal-world-rank"></p>
            <p id="modal-monthly-rank"></p>
            <p id="modal-games"></p>
            <p id="modal-winrate"></p>
            <p id="modal-average"></p>
            <h3>🔥 Letzte Matches</h3>
            <ul id="modal-matches" class="match-list"></ul>
        </div>
    </div>
    <script>
    let playerProfiles = {};

    function text(id, value) {
        document.getElementById(id).textContent = value;
    }

    function rankText(value) {
        return value ? "#" + value : "N/A";
    }

    function openPlayerModal(userId, fallbackAvatar) {
        const player = playerProfiles[String(userId)];
        if (!player) {
            return;
        }

        const jsonAvatarIsDefault = player.avatar && player.avatar.includes("/embed/avatars/0.png");
        document.getElementById("modal-avatar").src = jsonAvatarIsDefault && fallbackAvatar ? fallbackAvatar : player.avatar;
        text("modal-player-name", player.name);
        text("modal-rating", "🏆 Rating: " + player.worldRating);
        text("modal-world-rank", "🌍 Worldrank: " + rankText(player.worldRank));
        text("modal-monthly-rank", "🗓️ Monatsrang: " + rankText(player.monthlyRank));
        text("modal-games", "🎯 Spiele: " + player.games);
        text("modal-winrate", "📈 Winrate: " + player.winrate + "%");
        text("modal-average", "🎯 Ø Average: " + player.overallAverage);

        const matches = document.getElementById("modal-matches");
        matches.replaceChildren();
        if (!player.recentMatches.length) {
            const item = document.createElement("li");
            item.textContent = "Keine Matches vorhanden.";
            matches.appendChild(item);
        } else {
            player.recentMatches.forEach(match => {
                const item = document.createElement("li");
                const resultIcon = match.result === "Win" ? "🟢" : "🔴";
                const elo = match.eloChange > 0 ? "+" + match.eloChange : String(match.eloChange);
                item.textContent = resultIcon + " vs " + match.opponentName + " (" + match.score + ") | Avg: " + match.average + " | " + elo + " ELO";
                matches.appendChild(item);
            });
        }

        const backdrop = document.getElementById("player-modal-backdrop");
        backdrop.classList.add("open");
        backdrop.setAttribute("aria-hidden", "false");
    }

    function closePlayerModal() {
        const backdrop = document.getElementById("player-modal-backdrop");
        backdrop.classList.remove("open");
        backdrop.setAttribute("aria-hidden", "true");
    }

    fetch("players.json?v=" + Date.now(), { cache: "no-store" })
        .then(response => response.json())
        .then(data => {
            playerProfiles = data.players || {};
        })
        .catch(error => console.error("players.json konnte nicht geladen werden", error));

    document.addEventListener("click", event => {
        const playerTarget = event.target.closest("[data-player-id]");
        if (playerTarget) {
            const avatar =
                playerTarget.querySelector("img")?.src ||
                playerTarget.closest("tr")?.querySelector("img")?.src ||
                playerTarget.closest(".card")?.querySelector("img")?.src;
            openPlayerModal(playerTarget.dataset.playerId, avatar);
            return;
        }

        if (
            event.target.id === "player-modal-backdrop" ||
            event.target.id === "modal-close" ||
            event.target.id === "modal-back-link"
        ) {
            closePlayerModal();
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closePlayerModal();
        }
    });
    </script>
    </body></html>
    """

    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)
        print("html generated")


# =============================
# Datenmodelle für den Laufzeit-Zustand von Panels, Matches und Ergebnissen.
# =============================

@dataclass(slots=True)
class MatchState:
    match_id: int
    queue_name: str
    player_ids: tuple[int, int]
    thread_id: int


@dataclass(slots=True)
class PendingMatchState:
    match_id: int
    queue_name: str
    player_ids: tuple[int, int]
    thread_id: int
    confirmed_user_ids: set[int] = field(default_factory=set)


@dataclass(slots=True)
class PendingResultState:
    submission_id: int
    match_id: int
    winner_id: int
    score: tuple[int, int]
    score_text: str
    averages: dict[int, str]
    submitted_by: int
    thread_id: int
    screenshot: discord.Attachment | None = None
    confirmation_message_id: int | None = None


@dataclass(slots=True)
class PanelState:
    channel_id: int
    dartcounter_queue: list[int] = field(default_factory=list)
    scolia_queue: list[int] = field(default_factory=list)

    def get_queue(self, queue_name: str) -> list[int]:
        if queue_name == "DartCounter":
            return self.dartcounter_queue
        return self.scolia_queue


# =============================
# Darstellung: Queue-, Match-, Ergebnis- und Ranking-Embeds.
# =============================

def format_queue(queue: list[int]) -> str:
    if not queue:
        return QUEUE_EMPTY_TEXT
    return "\n".join(f"<@{user_id}>" for user_id in queue)


def format_active_matches(matches: list[MatchState]) -> str:
    return "\n".join(
        f"{match.queue_name} #{match.match_id:03d} <@{match.player_ids[0]}> vs <@{match.player_ids[1]}>"
        for match in matches
    )


def build_queue_embed(panel_state: PanelState, active_matches: list[MatchState]) -> discord.Embed:
    embed = discord.Embed(
        title=":dart: Dart Matchmaking",
        description="\u200b",
        colour=discord.Color.blurple(),
    )
    embed.add_field(name=":dart: DartCounter", value=format_queue(panel_state.dartcounter_queue), inline=False)
    embed.add_field(name=":blue_circle: Scolia", value=format_queue(panel_state.scolia_queue), inline=False)

    if active_matches:
        embed.add_field(name=MATCHES_FIELD_NAME, value=format_active_matches(active_matches), inline=False)

    return embed


def build_pending_match_embed(match: PendingMatchState) -> discord.Embed:
    confirmed_mentions = (
        "\n".join(f"<@{user_id}>" for user_id in match.player_ids if user_id in match.confirmed_user_ids)
        if match.confirmed_user_ids
        else "noch niemand"
    )
    waiting_mentions = (
        "\n".join(f"<@{user_id}>" for user_id in match.player_ids if user_id not in match.confirmed_user_ids)
        if len(match.confirmed_user_ids) < len(match.player_ids)
        else "niemand"
    )

    embed = discord.Embed(
        title=f"Match #{match.match_id:03d} bestätigen",
        description=(
            f"{match.queue_name} Match zwischen <@{match.player_ids[0]}> und <@{match.player_ids[1]}>.\n"
            "Beide Spieler müssen bestätigen, bevor das Match aktiv wird."
        ),
        colour=discord.Color.gold(),
    )
    embed.add_field(name="Bestätigt", value=confirmed_mentions, inline=True)
    embed.add_field(name="Wartet auf", value=waiting_mentions, inline=True)
    return embed


def build_confirmed_match_embed(match: MatchState) -> discord.Embed:
    return discord.Embed(
        title=f"Match #{match.match_id:03d} bestätigt",
        description=(
            f"{match.queue_name} <@{match.player_ids[0]}> vs <@{match.player_ids[1]}>\n"
            "Das Match ist jetzt aktiv."
        ),
        colour=discord.Color.green(),
    )


def build_result_embed(match: MatchState, result: PendingResultState) -> discord.Embed:
    embed = discord.Embed(
        title=f":bar_chart: Match Ergebnis #{match.match_id:03d}",
        description=f"{match.queue_name} <@{match.player_ids[0]}> vs <@{match.player_ids[1]}>",
        colour=discord.Color.dark_green(),
    )
    embed.add_field(name="Gewinner", value=f"<@{result.winner_id}>", inline=True)
    embed.add_field(name="Spielstand", value=result.score_text, inline=True)
    return embed
    return embed


def build_withdrawn_match_embed(match_id: int) -> discord.Embed:
    return discord.Embed(
        title=f"Match Ergebnis #{match_id:03d}",
        description="Das Match wurde zurückgezogen.",
        colour=discord.Color.red(),
    )


def build_ranking_embed(
    *,
    title: str,
    rows: list[tuple[int, int, int, int]],
    empty_text: str,
) -> discord.Embed:
    embed = discord.Embed(title=title, colour=discord.Color.gold())
    if not rows:
        embed.description = empty_text
        return embed

    lines = [
        f"**{index}.** <@{user_id}> | Rating: **{rating}** | W: {wins} | L: {losses}"
        for index, (user_id, rating, wins, losses) in enumerate(rows, start=1)
    ]
    embed.description = "\n".join(lines)
    return embed


def rank_value(rank: int | None) -> str:
    return f"#{rank}" if rank is not None else "N/A"


def build_stats_embed(
    *,
    player: discord.Member,
    world_rank: int | None,
    monthly_rank: int | None,
    rating: int,
    total: int,
    winrate: int | float,
) -> discord.Embed:
    embed = discord.Embed(title=f"📊 Stats von {player.display_name}")

    embed.add_field(name="🏆 Rating", value=str(rating), inline=False)
    embed.add_field(name="🌍 Global Rank", value=rank_value(world_rank), inline=False)
    embed.add_field(name="🗓️ Monthly Rank", value=rank_value(monthly_rank), inline=False)
    embed.add_field(name="🎯 Spiele", value=str(total), inline=False)
    embed.add_field(name="📈 Winrate", value=f"{winrate}%", inline=False)
    return embed


# =============================
# Parser und Normalisierung für Queue-Embeds, Thread-Namen und Formularwerte.
# =============================

def parse_queue(value: str) -> list[int]:
    if value.strip().lower() == QUEUE_EMPTY_TEXT:
        return []

    user_ids: list[int] = []
    for match in MENTION_PATTERN.finditer(value):
        user_id = int(match.group(1))
        if user_id not in user_ids:
            user_ids.append(user_id)
    return user_ids


def panel_state_from_embed(message: discord.Message) -> PanelState:
    state = PanelState(channel_id=message.channel.id)

    if not message.embeds:
        return state

    for field in message.embeds[0].fields:
        if "DartCounter" in field.name:
            state.dartcounter_queue = parse_queue(field.value)
        elif "Scolia" in field.name:
            state.scolia_queue = parse_queue(field.value)

    return state


def normalize_thread_part(value: str) -> str:
    normalized = value.lower().replace(" ", "-")
    normalized = THREAD_SAFE_PATTERN.sub("", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "spieler"


def normalize_average(value: str) -> str | None:
    stripped = value.strip()
    if not AVERAGE_PATTERN.fullmatch(stripped):
        return None
    return stripped.replace(".", ",")


def parse_best_of_seven_score(value: str) -> tuple[int, int] | None:
    match = SCORE_PATTERN.fullmatch(value)
    if match is None:
        return None

    left_score = int(match.group(1))
    right_score = int(match.group(2))
    if left_score == 4 and 0 <= right_score <= 3:
        return left_score, right_score
    if right_score == 4 and 0 <= left_score <= 3:
        return left_score, right_score
    return None


def shorten_label(value: str, limit: int = 28) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


# =============================
# Match-Bestätigung: Buttons für Annahme oder Rückzug eines neuen Matches.
# =============================

class PendingMatchView(discord.ui.View):
    def __init__(self, cog: Ranked, match_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.match_id = match_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        match = self.cog.pending_matches.get(self.match_id)
        if match is None:
            await interaction.response.send_message("Dieses Match ist nicht mehr offen.", ephemeral=True)
            return False

        if interaction.user.id in match.player_ids:
            return True

        await interaction.response.send_message("Nur die beiden Spieler können hier reagieren.", ephemeral=True)
        return False

    @discord.ui.button(label="Bestätigen", style=discord.ButtonStyle.success)
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        pending_match = self.cog.pending_matches.get(self.match_id)
        if pending_match is None:
            await interaction.response.send_message("Dieses Match ist nicht mehr offen.", ephemeral=True)
            return

        if interaction.user.id in pending_match.confirmed_user_ids:
            await interaction.response.send_message("Du hast dieses Match bereits bestätigt.", ephemeral=True)
            return

        pending_match.confirmed_user_ids.add(interaction.user.id)

        if len(pending_match.confirmed_user_ids) < 2:
            await interaction.response.edit_message(embed=build_pending_match_embed(pending_match), view=self)
            return

        active_match = await self.cog.confirm_pending_match(self.match_id)
        if active_match is None:
            await interaction.response.send_message("Das Match konnte nicht bestätigt werden.", ephemeral=True)
            return

        self.stop()
        await interaction.response.edit_message(embed=build_confirmed_match_embed(active_match), view=None)
        thread = await self.cog.fetch_thread(active_match.thread_id)
        if thread is not None:
            await thread.send(
                "Wenn euer Match beendet ist, könnt ihr hier das Ergebnis eintragen: Alternativ mit /result",
                view=ResultEntryView(self.cog, active_match.match_id),
            )
        await self.cog.refresh_panels(refresh_all=True)

    #
    # in Zukunft, vielleicht mit Admin-Rechten, sodass nur auf Anfrage der Admin das Match zurückziehen kann
    #
    # @discord.ui.button(label="Zurueckziehen", style=discord.ButtonStyle.danger)
    # async def withdraw_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
    #     del button
    #     pending_match = self.cog.pending_matches.pop(self.match_id, None)
    #     if pending_match is None:
    #         await interaction.response.send_message("Dieses Match ist nicht mehr offen.", ephemeral=True)
    #         return
    #
    #     self.stop()
    #     await interaction.response.send_message("Match wurde zurueckgezogen.", ephemeral=True)
    #     results_channel = await self.cog.fetch_results_channel()
    #     if results_channel is not None:
    #         try:
    #             await results_channel.send(embed=build_withdrawn_match_embed(pending_match.match_id))
    #         except (discord.NotFound, discord.Forbidden, discord.HTTPException):
    #             pass
    #     thread = await self.cog.fetch_thread(pending_match.thread_id)
    #     if thread is not None:
    #         try:
    #             await thread.delete()
    #         except (discord.NotFound, discord.Forbidden, discord.HTTPException):
    #             pass


# =============================
# Ergebnis-Bestätigung: Gegenspieler prueft und bestätigt den Vorschlag.
# =============================

class ResultConfirmationView(discord.ui.View):
    def __init__(self, cog: Ranked, match_id: int, submission_id: int, confirmer_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.match_id = match_id
        self.submission_id = submission_id
        self.confirmer_id = confirmer_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        result = self.cog.pending_results.get(self.match_id)
        match = self.cog.active_matches.get(self.match_id)

        if result is None or match is None:
            await interaction.response.send_message("Dieses Ergebnis ist nicht mehr offen.", ephemeral=True)
            return False

        if result.submission_id != self.submission_id:
            await interaction.response.send_message("Es gibt bereits einen neueren Ergebnisvorschlag.", ephemeral=True)
            return False

        if interaction.user.id not in match.player_ids:
            await interaction.response.send_message("Nur die beiden Spieler können das Ergebnis bestätigen.", ephemeral=True)
            return False

        if interaction.user.id != self.confirmer_id:
            await interaction.response.send_message(
                f"Nur <@{self.confirmer_id}> kann dieses Ergebnis bestätigen.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(label="Ergebnis bestätigen", style=discord.ButtonStyle.success)
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        result = self.cog.pending_results.get(self.match_id)
        match = self.cog.active_matches.get(self.match_id)
        if result is None or match is None or result.submission_id != self.submission_id:
            await interaction.response.send_message("Dieses Ergebnis ist nicht mehr offen.", ephemeral=True)
            return

        results_channel = await self.cog.fetch_results_channel()
        if results_channel is None:
            await interaction.response.send_message("Der Ergebnis-Channel konnte nicht gefunden werden.", ephemeral=True)
            return

        if interaction.guild_id is None:
            await interaction.response.send_message("Guild-ID konnte nicht aufgelöst werden.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        persisted, already_published = await persist_ranked_match_result(
            self.cog.bot,
            match,
            result,
            guild_id=interaction.guild_id,
            confirmed_by=interaction.user.id,
        )
        if not persisted:
            await interaction.followup.send(
                "Das Ergebnis konnte nicht in der Datenbank gespeichert werden. Match bleibt offen.",
                ephemeral=True,
            )
            return

        if already_published:
            self.stop()
            self.cog.pending_results.pop(self.match_id, None)
            self.cog.active_matches.pop(self.match_id, None)
            thread = await self.cog.fetch_thread(match.thread_id)
            if thread is not None:
                try:
                    await thread.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
            await self.cog.refresh_panels(refresh_all=True)
            await interaction.followup.send("Dieses Ergebnis wurde bereits verarbeitet. Match wurde geschlossen.", ephemeral=True)
            return

        try:
            results_message = await self.cog.send_result_message(results_channel, match, result)
        except discord.HTTPException:
            await interaction.followup.send(
                "Das Ergebnis wurde gespeichert, aber nicht in den Ergebnis-Channel gesendet. Bitte erneut bestätigen.",
                ephemeral=True,
            )
            return

        await mark_ranked_match_result_published(self.cog.bot, match.match_id, results_channel.id, results_message.id)

        self.stop()
        self.cog.pending_results.pop(self.match_id, None)
        self.cog.active_matches.pop(self.match_id, None)

        thread = await self.cog.fetch_thread(match.thread_id)
        if thread is not None:
            try:
                await thread.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        await generate_html(self.cog.bot)
        upload()
        await self.cog.refresh_panels(refresh_all=True)
        await interaction.followup.send("Ergebnis bestätigt und gepostet.", ephemeral=True)


# =============================
# Ergebnis-Erfassung: Button im Match-Thread und Modal fuer Score, Average und Screenshot.
# =============================

class ResultEntryView(discord.ui.View):
    def __init__(self, cog: Ranked, match_id: int | None = None) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.match_id = match_id

    @discord.ui.button(
        label="Ergebnis posten",
        style=discord.ButtonStyle.success,
        custom_id="ranked:result_entry",
    )
    async def post_result(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.match_id is None:
            if not isinstance(interaction.channel, discord.Thread):
                match = None
            else:
                match = self.cog.get_active_match_by_thread_id(interaction.channel.id)
        else:
            match = self.cog.get_active_match_by_id(self.match_id)

        if match is None:
            await interaction.response.send_message(
                "In diesem Thread wurde kein aktives Match gefunden.",
                ephemeral=True,
            )
            return

        if interaction.user.id not in match.player_ids:
            await interaction.response.send_message(
                "Nur die beiden Match-Spieler dürfen das Ergebnis eintragen.",
                ephemeral=True,
            )
            return

        if self.cog.pending_results.get(self.match_id) is not None:
            await interaction.response.send_message(
                "Für dieses Match wurde bereits ein Ergebnis eingetragen und wartet auf Bestätigung.",
                ephemeral=True,
            )
            return

        message = interaction.message
        button.disabled = True
        await self.cog.open_result_modal(
            interaction,
            match_id=match.match_id,
            entry_message_id=message.id if message is not None else None,
        )
        if message is not None:
            try:
                await message.edit(view=self)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


class ResultModal(discord.ui.Modal):
    def __init__(
        self,
        cog: Ranked,
        match: MatchState,
        guild: discord.Guild,
        entry_message_id: int | None = None,
    ) -> None:
        super().__init__(title=f"Ergebnis Match #{match.match_id:03d}")
        self.cog = cog
        self.match = match
        self.guild = guild
        self.entry_message_id = entry_message_id

        player_one = guild.get_member(match.player_ids[0])
        player_two = guild.get_member(match.player_ids[1])
        player_one_name = shorten_label(player_one.display_name if player_one else f"Spieler {match.player_ids[0]}")
        player_two_name = shorten_label(player_two.display_name if player_two else f"Spieler {match.player_ids[1]}")
        score_player_one_name = shorten_label(player_one_name, 14)
        score_player_two_name = shorten_label(player_two_name, 14)

        self.winner_select = discord.ui.Select(
            placeholder="Gewinner auswählen",
            required=True,
            options=[
                discord.SelectOption(label=player_one_name, value=str(match.player_ids[0])),
                discord.SelectOption(label=player_two_name, value=str(match.player_ids[1])),
            ],
        )
        self.score_input = discord.ui.TextInput(
            label=f"Spielstand ({score_player_one_name}:{score_player_two_name})",
            placeholder="z. B. 4:2",
            required=True,
            max_length=10,
        )
        self.average_one_input = discord.ui.TextInput(
            label=f"Average {player_one_name}",
            placeholder="z. B. 54,32 oder 54.32",
            required=True,
            max_length=20,
        )
        self.average_two_input = discord.ui.TextInput(
            label=f"Average {player_two_name}",
            placeholder="z. B. 48,76 oder 48.76",
            required=True,
            max_length=20,
        )
        self.screenshot_upload = discord.ui.FileUpload(
            required=False,
            min_values=0,
            max_values=1,
        )

        self.add_item(discord.ui.Label(text="Gewinner", component=self.winner_select))
        self.add_item(self.score_input)
        self.add_item(self.average_one_input)
        self.add_item(self.average_two_input)
        self.add_item(discord.ui.Label(text="Screenshot", component=self.screenshot_upload))

    async def restore_result_entry_button(self) -> None:
        if self.entry_message_id is None:
            return

        thread = await self.cog.fetch_thread(self.match.thread_id)
        if thread is None:
            return

        try:
            message = await thread.fetch_message(self.entry_message_id)
            await message.edit(view=ResultEntryView(self.cog, self.match.match_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not self.winner_select.values:
            await self.restore_result_entry_button()
            await interaction.response.send_message("Bitte wähle einen Gewinner aus.", ephemeral=True)
            return

        score = parse_best_of_seven_score(self.score_input.value)
        if score is None:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Bitte gib einen gültigen Best-of-7-Spielstand ein, z. B. 4:0 bis 4:3.",
                ephemeral=True,
            )
            return

        average_one = normalize_average(self.average_one_input.value)
        average_two = normalize_average(self.average_two_input.value)
        if average_one is None or average_two is None:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Die Averages müssen numerisch sein. Punkt und Komma sind erlaubt.",
                ephemeral=True,
            )
            return

        winner_id = int(self.winner_select.values[0])
        player_one_id, player_two_id = self.match.player_ids
        left_score, right_score = score

        if winner_id == player_one_id and left_score != 4:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Der ausgewählte Gewinner passt nicht zum Spielstand.",
                ephemeral=True,
            )
            return

        if winner_id == player_two_id and right_score != 4:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Der ausgewählte Gewinner passt nicht zum Spielstand.",
                ephemeral=True,
            )
            return

        screenshot = self.screenshot_upload.values[0] if self.screenshot_upload.values else None
        if screenshot is None:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Bitte hänge einen Screenshot an.",
                ephemeral=True,
            )
            return

        submission_id = self.cog.next_result_submission_id
        self.cog.next_result_submission_id += 1

        previous_result = self.cog.pending_results.get(self.match.match_id)
        if previous_result is not None:
            await self.cog.mark_result_submission_obsolete(previous_result)

        pending_result = PendingResultState(
            submission_id=submission_id,
            match_id=self.match.match_id,
            winner_id=winner_id,
            score=score,
            score_text=f"{left_score}:{right_score}",
            averages={
                player_one_id: average_one,
                player_two_id: average_two,
            },
            submitted_by=interaction.user.id,
            thread_id=self.match.thread_id,
            screenshot=screenshot,
        )
        self.cog.pending_results[self.match.match_id] = pending_result

        thread = await self.cog.fetch_thread(self.match.thread_id)
        if thread is None:
            self.cog.pending_results.pop(self.match.match_id, None)
            await self.restore_result_entry_button()
            await interaction.response.send_message("Der Match-Thread konnte nicht gefunden werden.", ephemeral=True)
            return

        confirmer_id = player_two_id if interaction.user.id == player_one_id else player_one_id
        confirmation_view = ResultConfirmationView(self.cog, self.match.match_id, submission_id, confirmer_id)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            message = await self.cog.send_result_message(
                thread,
                self.match,
                pending_result,
                content=f"<@{confirmer_id}>, bitte bestätige dieses Ergebnis.",
                view=confirmation_view,
            )
        except discord.HTTPException:
            self.cog.pending_results.pop(self.match.match_id, None)
            await self.restore_result_entry_button()
            await interaction.followup.send("Das Ergebnis konnte nicht im Match-Thread gesendet werden.", ephemeral=True)
            return

        pending_result.confirmation_message_id = message.id
        await interaction.followup.send("Ergebnis zur Bestätigung in den Match-Thread gesendet.", ephemeral=True)


# =============================
# Queue-Panel: Beitreten, Verlassen und automatisches Starten passender Matches.
# =============================

class QueuePanel(discord.ui.View):
    def __init__(self, cog: Ranked, panel_state: PanelState | None = None) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        if panel_state is not None:
            self.set_both_button_disabled(bool(panel_state.dartcounter_queue and panel_state.scolia_queue))

    def set_both_button_disabled(self, disabled: bool) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "queue_panel:both_join":
                item.disabled = disabled
                return

    @staticmethod
    def find_joined_queue(panel_state: PanelState, user_id: int) -> str | None:
        in_dartcounter = user_id in panel_state.dartcounter_queue
        in_scolia = user_id in panel_state.scolia_queue
        if in_dartcounter and in_scolia:
            return "Beides"
        if in_dartcounter:
            return "DartCounter"
        if in_scolia:
            return "Scolia"
        return None

    @staticmethod
    def has_waiting_opponent(queue: list[int], user_id: int) -> bool:
        return any(queued_user_id != user_id for queued_user_id in queue)

    async def update_queue(self,  interaction: discord.Interaction, *, queue_name: str | None, join: bool) -> None:
        message = interaction.message
        if message is None:
            await interaction.response.send_message("Das Queue-Embed konnte nicht gelesen werden.", ephemeral=True)
            return

        panel_state = self.cog.get_or_create_panel_state(message)
        user_id = interaction.user.id
        joined_queue = self.find_joined_queue(panel_state, user_id)

        if join:
            if queue_name is None:
                await interaction.response.send_message("Keine Queue ausgewählt.", ephemeral=True)
                return

            queue = panel_state.get_queue(queue_name)

            if self.cog.is_user_locked(user_id):
                await interaction.response.send_message(
                    "Du bist bereits in einem offenen oder aktiven Match und kannst keiner Queue beitreten.",
                    ephemeral=True,
                    delete_after=10,
                )
                return

            if user_id in queue:
                await interaction.response.send_message(
                    f"Du bist bereits in der {queue_name}-Queue.",
                    ephemeral=True,
                    delete_after=10,
                )
                return

            if joined_queue is not None and joined_queue != queue_name:
                await interaction.response.send_message(
                    f"Du bist bereits in der {joined_queue}-Queue. Verlasse sie zuerst, bevor du wechselst.",
                    ephemeral=True,
                    delete_after=10,
                )
                return

            queue.append(user_id)
            match_started = await self.cog.try_start_matches(message, panel_state, queue_name)
        else:
            if joined_queue is None:
                await interaction.response.send_message(
                    "Du bist aktuell in keiner Queue.",
                    ephemeral=True,
                    delete_after=10,
                )
                return

            panel_state.dartcounter_queue[:] = [
                queued_user_id for queued_user_id in panel_state.dartcounter_queue if queued_user_id != user_id
            ]
            panel_state.scolia_queue[:] = [
                queued_user_id for queued_user_id in panel_state.scolia_queue if queued_user_id != user_id
            ]
            match_started = False

        await self.cog.refresh_panels(
            interaction=interaction,
            current_message_id=message.id,
            refresh_all=match_started,
        )

    async def join_both_queues(self, interaction: discord.Interaction) -> None:
        message = interaction.message
        if message is None:
            await interaction.response.send_message("Das Queue-Embed konnte nicht gelesen werden.", ephemeral=True)
            return

        panel_state = self.cog.get_or_create_panel_state(message)
        user_id = interaction.user.id

        if self.cog.is_user_locked(user_id):
            await interaction.response.send_message(
                "Du bist bereits in einem offenen oder aktiven Match und kannst keiner Queue beitreten.",
                ephemeral=True,
                delete_after=10,
            )
            return

        dartcounter_has_opponent = self.has_waiting_opponent(panel_state.dartcounter_queue, user_id)
        scolia_has_opponent = self.has_waiting_opponent(panel_state.scolia_queue, user_id)
        if dartcounter_has_opponent and scolia_has_opponent:
            await interaction.response.send_message(
                "Beides ist gerade nicht möglich, weil in beiden Queues schon jemand wartet.",
                ephemeral=True,
                delete_after=10,
            )
            return

        if user_id not in panel_state.dartcounter_queue:
            panel_state.dartcounter_queue.append(user_id)
        if user_id not in panel_state.scolia_queue:
            panel_state.scolia_queue.append(user_id)

        if dartcounter_has_opponent:
            match_started = await self.cog.try_start_matches(message, panel_state, "DartCounter")
        elif scolia_has_opponent:
            match_started = await self.cog.try_start_matches(message, panel_state, "Scolia")
        else:
            match_started = False

        await self.cog.refresh_panels(
            interaction=interaction,
            current_message_id=message.id,
            refresh_all=match_started,
        )

    @discord.ui.button(
        label="DartCounter",
        style=discord.ButtonStyle.success,
        custom_id="queue_panel:dartcounter_join",
        row=0,
    )
    async def dartcounter_join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        await self.update_queue(interaction, queue_name="DartCounter", join=True)

    @discord.ui.button(
        label="Scolia",
        style=discord.ButtonStyle.primary,
        custom_id="queue_panel:scolia_join",
        row=0,
    )
    async def scolia_join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        await self.update_queue(interaction, queue_name="Scolia", join=True)

    @discord.ui.button(
        label="Beides",
        style=discord.ButtonStyle.secondary,
        custom_id="queue_panel:both_join",
        row=0,
    )
    async def both_join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        await self.join_both_queues(interaction)

    @discord.ui.button(
        label="Leave",
        style=discord.ButtonStyle.danger,
        custom_id="queue_panel:leave",
        row=0,
    )
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        await self.update_queue(interaction, queue_name=None, join=False)


# =============================
# Ranked-Cog: verbindet UI, Match-Status, Discord-Threads und Ranked-DB-Helper.
# =============================
class Ranked(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_matches: dict[int, MatchState] = {}
        self.pending_matches: dict[int, PendingMatchState] = {}
        self.pending_results: dict[int, PendingResultState] = {}
        self.next_match_id = 1
        self.next_result_submission_id = 1
        self.panel_states: dict[int, PanelState] = {}

    async def cog_load(self) -> None:
        await ensure_ranked_storage(self.bot)
        await self.restore_active_matches()
        self.bot.add_view(QueuePanel(self))
        self.bot.add_view(ResultEntryView(self))

    # In-Memory-Zustand fuer Panels, Queues und laufende Matches.
    def get_or_create_panel_state(self, message: discord.Message) -> PanelState:
        panel_state = self.panel_states.get(message.id)
        if panel_state is None:
            panel_state = panel_state_from_embed(message)
            self.panel_states[message.id] = panel_state
        return panel_state

    def get_active_match_by_thread_id(self, thread_id: int) -> MatchState | None:
        for match in self.active_matches.values():
            if match.thread_id == thread_id:
                return match
        return None

    def get_active_match_by_id(self, match_id: int) -> MatchState | None:
        return self.active_matches.get(match_id)

    async def restore_active_matches(self) -> None:
        restored_matches = await fetch_active_ranked_matches(self.bot)
        for restored_match in restored_matches:
            match = MatchState(
                match_id=restored_match["match_id"],
                queue_name=restored_match["queue_name"],
                player_ids=restored_match["player_ids"],
                thread_id=restored_match["thread_id"],
            )
            if await self.fetch_thread(match.thread_id) is None:
                continue
            self.active_matches[match.match_id] = match
            self.next_match_id = max(self.next_match_id, match.match_id + 1)

    def is_user_locked(self, user_id: int) -> bool:
        if any(user_id in match.player_ids for match in self.active_matches.values()):
            return True
        return any(user_id in match.player_ids for match in self.pending_matches.values())

    def remove_players_from_all_queues(self, player_ids: tuple[int, int]) -> None:
        matched_players = set(player_ids)

        for panel_state in self.panel_states.values():
            panel_state.dartcounter_queue[:] = [
                user_id for user_id in panel_state.dartcounter_queue if user_id not in matched_players
            ]
            panel_state.scolia_queue[:] = [
                user_id for user_id in panel_state.scolia_queue if user_id not in matched_players
            ]

    # Match-Erstellung und Statuswechsel von offen zu aktiv.
    async def create_pending_match(
        self,
        queue_message: discord.Message,
        *,
        queue_name: str,
        player_ids: tuple[int, int],
    ) -> bool:
        guild = queue_message.guild
        if guild is None:
            return False

        player_one = guild.get_member(player_ids[0])
        player_two = guild.get_member(player_ids[1])
        if player_one is None or player_two is None:
            return False

        match_id, self.next_match_id = await get_next_ranked_match_id(self.bot, self.next_match_id)

        thread_name = (
            f"match-{match_id:03d}-"
            f"{normalize_thread_part(player_one.display_name)}-"
            f"{normalize_thread_part(player_two.display_name)}"
        )[:100]

        if not isinstance(queue_message.channel, discord.TextChannel):
            return False

        try:
            thread = await queue_message.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
                invitable=False,
            )
            await thread.add_user(player_one)
            await thread.add_user(player_two)
        except (discord.Forbidden, discord.HTTPException):
            try:
                if "thread" in locals():
                    await thread.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
            return False

        pending_match = PendingMatchState(
            match_id=match_id,
            queue_name=queue_name,
            player_ids=player_ids,
            thread_id=thread.id,
        )
        self.pending_matches[match_id] = pending_match

        view = PendingMatchView(self, match_id)
        await thread.send(
            embed=build_pending_match_embed(pending_match),
            view=view,
        )
        # await thread.send(
        #     content=(
        #         f"{player_one.mention} {player_two.mention}\n"
        #         "Bestätigt dieses Match oder zieht es zurueck."
        #     ),
        #     embed=build_pending_match_embed(pending_match),
        #     view=view,
        # )
        return True

    async def try_start_matches(
        self,
        queue_message: discord.Message,
        panel_state: PanelState,
        queue_name: str,
    ) -> bool:
        queue = panel_state.get_queue(queue_name)
        match_started = False

        while len(queue) >= 2:
            player_one = queue.pop(0)
            player_two = queue.pop(0)
            player_ids = (player_one, player_two)

            pending_created = await self.create_pending_match(
                queue_message,
                queue_name=queue_name,
                player_ids=player_ids,
            )
            if not pending_created:
                queue.insert(0, player_two)
                queue.insert(0, player_one)
                break

            self.remove_players_from_all_queues(player_ids)
            match_started = True

        return match_started

    async def confirm_pending_match(self, match_id: int) -> MatchState | None:
        pending_match = self.pending_matches.pop(match_id, None)
        if pending_match is None:
            return None

        active_match = MatchState(
            match_id=pending_match.match_id,
            queue_name=pending_match.queue_name,
            player_ids=pending_match.player_ids,
            thread_id=pending_match.thread_id,
        )
        self.active_matches[match_id] = active_match
        await persist_active_ranked_match(self.bot, active_match)
        return active_match

    def build_embed_for_panel(self, message_id: int) -> discord.Embed:
        panel_state = self.panel_states[message_id]
        active_matches = sorted(self.active_matches.values(), key=lambda match: match.match_id)
        return build_queue_embed(panel_state, active_matches)

    # Discord-Objekte sicher nachladen, ohne bei fehlenden Rechten abzubrechen.
    async def fetch_panel_message(self, channel_id: int, message_id: int) -> discord.Message | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None

        if not isinstance(channel, discord.TextChannel):
            return None

        try:
            return await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def fetch_thread(self, thread_id: int) -> discord.Thread | None:
        thread = self.bot.get_channel(thread_id)
        if isinstance(thread, discord.Thread):
            return thread

        try:
            fetched = await self.bot.fetch_channel(thread_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

        if isinstance(fetched, discord.Thread):
            return fetched
        return None

    async def fetch_results_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(RESULTS_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            return channel

        try:
            fetched = await self.bot.fetch_channel(RESULTS_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

        if isinstance(fetched, discord.TextChannel):
            return fetched
        return None

    async def send_result_message(
        self,
        channel: discord.abc.Messageable,
        match: MatchState,
        result: PendingResultState,
        *,
        content: str | None = None,
        view: discord.ui.View | None = None,
    ) -> discord.Message:
        embed = build_result_embed(match, result)
        if result.screenshot is None:
            return await channel.send(content=content, embed=embed, view=view)

        file = await result.screenshot.to_file()
        embed.set_image(url=f"attachment://{file.filename}")
        return await channel.send(content=content, embed=embed, file=file, view=view)

    # Ergebnisvorschläge und Panel-Aktualisierung nach Interaktionen.
    async def mark_result_submission_obsolete(self, result: PendingResultState) -> None:
        if result.confirmation_message_id is None:
            return

        thread = await self.fetch_thread(result.thread_id)
        if thread is None:
            return

        try:
            message = await thread.fetch_message(result.confirmation_message_id)
            await message.edit(content="Veralteter Ergebnisvorschlag.", view=None)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    async def refresh_panels(
        self,
        *,
        interaction: discord.Interaction | None = None,
        current_message_id: int | None = None,
        refresh_all: bool = True,
    ) -> None:
        stale_message_ids: list[int] = []

        if current_message_id is not None and current_message_id in self.panel_states and interaction is not None:
            await interaction.response.edit_message(
                embed=self.build_embed_for_panel(current_message_id),
                view=QueuePanel(self, self.panel_states[current_message_id]),
            )
        elif interaction is not None and not interaction.response.is_done():
            await interaction.response.send_message("Queue aktualisiert.", ephemeral=True)

        if not refresh_all:
            return

        for message_id, panel_state in self.panel_states.items():
            if message_id == current_message_id:
                continue

            message = await self.fetch_panel_message(panel_state.channel_id, message_id)
            if message is None:
                stale_message_ids.append(message_id)
                continue

            try:
                await message.edit(embed=self.build_embed_for_panel(message_id), view=QueuePanel(self, panel_state))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                stale_message_ids.append(message_id)

        for message_id in stale_message_ids:
            self.panel_states.pop(message_id, None)

    async def open_result_modal(
        self,
        interaction: discord.Interaction,
        *,
        match_id: int | None = None,
        entry_message_id: int | None = None,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "Dieser Befehl funktioniert nur in einem aktiven Match-Thread.",
                ephemeral=True,
            )
            return

        match = self.get_active_match_by_id(match_id) if match_id is not None else self.get_active_match_by_thread_id(interaction.channel.id)
        if match is None or match.thread_id != interaction.channel.id:
            await interaction.response.send_message(
                "In diesem Thread wurde kein aktives Match gefunden.",
                ephemeral=True,
            )
            return

        if interaction.user.id not in match.player_ids:
            await interaction.response.send_message(
                "Nur die beiden Match-Spieler dürfen das Ergebnis eintragen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(ResultModal(self, match, interaction.guild, entry_message_id))

    # Slash-Commands fuer Admins.
    @app_commands.command(name="queue_panel", description="Sendet das Queue-Panel in den Chat")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def queue_panel(self, interaction: discord.Interaction) -> None:
        panel_state = PanelState(channel_id=interaction.channel_id)
        embed = build_queue_embed(panel_state, sorted(self.active_matches.values(), key=lambda match: match.match_id))
        view = QueuePanel(self, panel_state)

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        self.panel_states[message.id] = panel_state

    @app_commands.command(name="result", description="Öffnet im Match-Thread das Ergebnisformular")
    @app_commands.guild_only()
    async def result(self, interaction: discord.Interaction) -> None:
        await self.open_result_modal(interaction)

    @app_commands.command(name="world_ranking", description="Zeigt das aktuelle World Ranking")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def world_ranking(self, interaction: discord.Interaction) -> None:
        if getattr(self.bot, "db", None) is None:
            await interaction.response.send_message("Die Datenbank ist aktuell nicht verfügbar.", ephemeral=True)
            return

        rows = await fetch_world_ranking(self.bot)
        embed = build_ranking_embed(
            title="World Ranking",
            rows=rows,
            empty_text="Noch keine Ranked-Ergebnisse vorhanden.",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="monthly_ranking", description="Zeigt das aktuelle Monatsranking")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def monthly_ranking(self, interaction: discord.Interaction) -> None:
        if getattr(self.bot, "db", None) is None:
            await interaction.response.send_message("Die Datenbank ist aktuell nicht verfügbar.", ephemeral=True)
            return

        rows = await fetch_monthly_ranking(self.bot)
        embed = build_ranking_embed(
            title="Monatsranking",
            rows=rows,
            empty_text="Für diesen Monat gibt es noch keine Ranked-Ergebnisse.",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="update_leaderboard", description="Aktualisiert das HTML-Ranking")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def update_leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Leaderboard wird aktualisiert...", ephemeral=True)
        await generate_html(self.bot)
        upload()
        await interaction.edit_original_response(
            content="Aktualisierung ist fertig. https://stefankulik.github.io/discord-bot/"
        )

    @app_commands.command(name="stats", description="Zeigt die Ranked-Stats eines Spielers")
    @app_commands.guild_only()
    async def stats(self, interaction: discord.Interaction, player: discord.Member) -> None:
        db = getattr(self.bot, "db", None)
        if db is None:
            await interaction.response.send_message("Die Datenbank ist aktuell nicht verfÃ¼gbar.", ephemeral=True)
            return

        world_data = await db.fetch_world_ranking(limit=None)
        monthly_data = await db.fetch_monthly_ranking(get_current_ranked_month_key(), limit=None)

        world_ranks = {
            user_id: rank
            for rank, (user_id, _rating, _wins, _losses) in enumerate(world_data, start=1)
        }
        monthly_ranks = {
            user_id: rank
            for rank, (user_id, _rating, _wins, _losses) in enumerate(monthly_data, start=1)
        }
        world_stats = {
            user_id: (rating, wins, losses)
            for user_id, rating, wins, losses in world_data
        }

        rating, wins, losses = world_stats.get(player.id, (1000, 0, 0))
        total = wins + losses
        winrate = round((wins / total) * 100, 1) if total else 0

        embed = build_stats_embed(
            player=player,
            world_rank=world_ranks.get(player.id),
            monthly_rank=monthly_ranks.get(player.id),
            rating=rating,
            total=total,
            winrate=winrate,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="history", description="Match History des Users")
    async def history(self, interaction: discord.Interaction, player: discord.Member):

        matches = await fetch_match_history(self.bot, player)

        if not matches:
            await interaction.response.send_message("Keine Matches gefunden.")
            return

        text = f"📜 Match History von {player.display_name}:\n\n"

        for p1, p2, winner, score, platform, elo_gain in matches:

            opponent_id = p2 if player.id == p1 else p1
            opponent = interaction.guild.get_member(opponent_id)

            name = opponent.display_name if opponent else f"User {opponent_id}"

            elo_gain = elo_gain if elo_gain else 0

            if winner == player.id:
                result = "🏆 Win"
                elo_text = f"+{elo_gain}"
            else:
                result = "❌ Loss"
                elo_text = f"-{elo_gain}"

            text += f"{result} vs {name} ({platform}) ({elo_text} ELO)\n"
            text += f"Score: {score}\n\n"

        await interaction.response.send_message(text)

    # admin commands
    # - export matches
    # - edit_match

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ranked(bot))
