from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
import re

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions

from config.Util import (
    ensure_ranked_storage,
    fetch_monthly_ranking,
    fetch_world_ranking,
    get_next_ranked_match_id,
    mark_ranked_match_result_published,
    persist_ranked_match_result,
)

# =============================
# Konstanten und Parser-Patterns fuer Queue, Threads und Ergebnisse.
# =============================
QUEUE_EMPTY_TEXT = "kein spieler"
MATCHES_FIELD_NAME = ":fire: Aktuelle Matches"
RESULTS_CHANNEL_ID = 1496937438025879723
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")
THREAD_SAFE_PATTERN = re.compile(r"[^a-z0-9-]")
SCORE_PATTERN = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")
AVERAGE_PATTERN = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*$")


# =============================
# WEBSITE - generate static html for displaying ranking on web
# =============================

def upload():
    os.system("git add .")
    os.system('git commit -m "update leaderboard"')
    os.system("git push")

async def generate_html(bot: commands.Bot):
    guild = bot.guilds[0] if bot.guilds else None

    # =============================
    # DATA
    # =============================

    player_data = await fetch_world_ranking(bot)
    monthly_data = await fetch_monthly_ranking(bot)

    top3 = player_data[:3]
    rest = player_data[3:]

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

    .card {background:#161b22;padding:20px;border-radius:20px;width:180px;transition:0.3s;}
    .card:hover {transform:scale(1.05);}

    .gold {border:2px solid gold;}
    .silver {border:2px solid silver;}
    .bronze {border:2px solid #cd7f32;}

    .avatar {width:70px;height:70px;border-radius:50%;}

    table {width:100%;border-collapse:collapse;margin-top:20px;}
    td {padding:10px;border-bottom:1px solid #222;}

    tr:hover {background:#161b22;}

    a {color:#58a6ff;text-decoration:none;font-weight:bold;}
    </style>
    </head>

    <body>

    <h1>🏆 RANKED DARTS Dashboard</h1>
    """

    # =============================
    # PODIUM
    # =============================

    html += "<div class='podium'>"
    classes = ["gold", "silver", "bronze"]

    for i, (user_id, world_rating) in enumerate(top3):

        name = f"User {user_id}"
        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if guild:
            m = guild.get_member(user_id)
            if m:
                name = m.display_name
                avatar = m.display_avatar.url

        html += f"""
        <div class='card {classes[i]}'>
        <img src="{avatar}" class="avatar"><br>
        <h2>#{i+1}</h2>
        <a href='player_{user_id}.html'>{name}</a>
        <p>{world_rating} ELO</p>
        </div>
        """

    html += "</div>"

    # =============================
    # TABLES
    # =============================

    html += "<div class='container'>"

    # 🌍 WORLD
    html += "<div style='width:40%'><h2>🌍 World Ranking</h2><table>"

    for i, (user_id, world_rating) in enumerate(player_data, 1):

        name = f"User {user_id}"
        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if guild:
            m = guild.get_member(user_id)
            if m:
                name = m.display_name
                avatar = m.display_avatar.url

        html += f"""
        <tr>
        <td>{i}</td>
        <td><img src="{avatar}" class="avatar"></td>
        <td><a href='player_{user_id}.html'>{name}</a></td>
        <td>{world_rating}</td>
        </tr>
        """

    html += "</table></div>"

    # 🗓️ MONTHLY
    html += "<div style='width:40%'><h2>🗓️ Monatsranking</h2><table>"

    for i, (user_id, monthly_rating) in enumerate(monthly_data, 1):

        name = f"User {user_id}"
        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if guild:
            m = guild.get_member(user_id)
            if m:
                name = m.display_name
                avatar = m.display_avatar.url

        html += f"""
        <tr>
        <td>{i}</td>
        <td><img src="{avatar}" class="avatar"></td>
        <td><a href='player_{user_id}.html'>{name}</a></td>
        <td>{monthly_rating}</td>
        </tr>
        """

    html += "</table></div>"

    html += "</div>"

    # =============================
    # PLAYER PROFILES
    # =============================

    # for i, (user_id, world_rating) in enumerate(player_data, 1):
    #
    #     name = f"User {user_id}"
    #     avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
    #
    #     if guild:
    #         m = guild.get_member(user_id)
    #         if m:
    #             name = m.display_name
    #             avatar = m.display_avatar.url
    #
    #     # Stats
    #     c.execute("SELECT COUNT(*) FROM matches WHERE winner_id=? AND status='confirmed'", (user_id,))
    #     wins = c.fetchone()[0]
    #
    #     c.execute("SELECT COUNT(*) FROM matches WHERE loser_id=? AND status='confirmed'", (user_id,))
    #     losses = c.fetchone()[0]
    #
    #     total = wins + losses
    #     winrate = round((wins / total) * 100, 1) if total > 0 else 0
    #
    #     # Monthly rank
    #     c.execute("SELECT user_id FROM monthly_points WHERE month=? ORDER BY monthly_rating DESC", (month,))
    #     monthly = [r[0] for r in c.fetchall()]
    #     monthly_rank = monthly.index(user_id) + 1 if user_id in monthly else "N/A"
    #
    #     # Average
    #     c.execute("""
    #         SELECT winner_id, winner_avg, loser_id, loser_avg
    #         FROM matches
    #         WHERE status='confirmed'
    #         AND (winner_id=? OR loser_id=?)
    #     """, (user_id, user_id))
    #
    #     rows = c.fetchall()
    #
    #     avgs = []
    #
    #     for winner_id, winner_avg, loser_id, loser_avg in rows:
    #
    #         # Spieler ist Gewinner
    #         if winner_id == user_id and winner_avg is not None:
    #             avgs.append(float(winner_avg))
    #
    #         # Spieler ist Verlierer
    #         if loser_id == user_id and loser_avg is not None:
    #             avgs.append(float(loser_avg))
    #
    #     # FINALER AVERAGE
    #     overall_avg = round(sum(avgs) / len(avgs), 2) if avgs else 0
    #
    #     history = ""
    #
    #     for p1, p2, winner, score, platform, wa, la, elo_gain, mid in c.execute("""
    #         SELECT player1_id, player2_id, winner_id, score, platform, winner_avg, loser_avg, elo_change, id
    #         FROM matches
    #         WHERE status='confirmed'
    #         AND (player1_id=? OR player2_id=?)
    #         ORDER BY id DESC
    #         LIMIT 5
    #     """, (user_id, user_id)):
    #
    #         opponent_id = p2 if user_id == p1 else p1
    #
    #         name_opponent = f"User {opponent_id}"
    #         if guild:
    #             m2 = guild.get_member(opponent_id)
    #             if m2:
    #                 name_opponent = m2.display_name
    #
    #         elo_gain = elo_gain if elo_gain else 0
    #
    #         if winner == user_id:
    #             result = "🟢 Win"
    #             match_avg = wa
    #             elo_text = f"+{elo_gain}"
    #         else:
    #             result = "🔴 Loss"
    #             match_avg = la
    #             elo_text = f"-{elo_gain}"
    #
    #         history += f"<li>{result} vs {name_opponent} ({score}) → {match_avg} ({elo_text} ELO)</li>"
    #
    #     profile_html = f"""
    #     <html>
    #     <body style='background:#0b0f14;color:white;font-family:Segoe UI;text-align:center'>
    #
    #     <div style="background:#161b22;padding:30px;margin:auto;margin-top:50px;width:400px;border-radius:20px;">
    #
    #     <img src="{avatar}" style="width:120px;height:120px;border-radius:50%;">
    #
    #     <h1>{name}</h1>
    #
    #     <p>🏆 Rating: {world_rating}</p>
    #     <p>🌍 Rank: {i}</p>
    #     <p>🗓️ Monatsrang: {monthly_rank}</p>
    #
    #     <p>🎯 Spiele: {total}</p>
    #     <p>📈 Winrate: {winrate}%</p>
    #
    #     <p>🎯 Ø Average: {overall_avg}</p>
    #
    #     <h3>🔥 Letzte Matches</h3>
    #     <ul>{history}</ul>
    #
    #     <br><a href="leaderboard.html">⬅ Zurück</a>
    #
    #     </div>
    #     </body>
    #     </html>
    #     """
    #
    #     with open(f"player_{user_id}.html", "w", encoding="utf-8") as f:
    #         f.write(profile_html)

    # =============================
    # SAVE
    # =============================

    html += "</body></html>"

    with open("leaderboard.html", "w", encoding="utf-8") as f:
        f.write(html)


# =============================
# Datenmodelle fuer den Laufzeit-Zustand von Panels, Matches und Ergebnissen.
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
        title=f"Match #{match.match_id:03d} bestaetigen",
        description=(
            f"{match.queue_name} Match zwischen <@{match.player_ids[0]}> und <@{match.player_ids[1]}>.\n"
            "Beide Spieler muessen bestaetigen, bevor das Match aktiv wird."
        ),
        colour=discord.Color.gold(),
    )
    embed.add_field(name="Bestaetigt", value=confirmed_mentions, inline=True)
    embed.add_field(name="Wartet auf", value=waiting_mentions, inline=True)
    return embed


def build_confirmed_match_embed(match: MatchState) -> discord.Embed:
    return discord.Embed(
        title=f"Match #{match.match_id:03d} bestaetigt",
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


def build_withdrawn_match_embed(match_id: int) -> discord.Embed:
    return discord.Embed(
        title=f"Match Ergebnis #{match_id:03d}",
        description="Das Match wurde zurueckgezogen.",
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


# =============================
# Parser und Normalisierung fuer Queue-Embeds, Thread-Namen und Formularwerte.
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
# Match-Bestaetigung: Buttons fuer Annahme oder Rueckzug eines neuen Matches.
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

        await interaction.response.send_message("Nur die beiden Spieler koennen hier reagieren.", ephemeral=True)
        return False

    @discord.ui.button(label="Bestaetigen", style=discord.ButtonStyle.success)
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        pending_match = self.cog.pending_matches.get(self.match_id)
        if pending_match is None:
            await interaction.response.send_message("Dieses Match ist nicht mehr offen.", ephemeral=True)
            return

        if interaction.user.id in pending_match.confirmed_user_ids:
            await interaction.response.send_message("Du hast dieses Match bereits bestaetigt.", ephemeral=True)
            return

        pending_match.confirmed_user_ids.add(interaction.user.id)

        if len(pending_match.confirmed_user_ids) < 2:
            await interaction.response.edit_message(embed=build_pending_match_embed(pending_match), view=self)
            return

        active_match = self.cog.confirm_pending_match(self.match_id)
        if active_match is None:
            await interaction.response.send_message("Das Match konnte nicht bestaetigt werden.", ephemeral=True)
            return

        self.stop()
        await interaction.response.edit_message(embed=build_confirmed_match_embed(active_match), view=None)
        thread = await self.cog.fetch_thread(active_match.thread_id)
        if thread is not None:
            await thread.send(
                "Wenn euer Match beendet ist, koennt ihr hier das Ergebnis eintragen:",
                view=ResultEntryView(self.cog, active_match.match_id),
            )
        await self.cog.refresh_panels(refresh_all=True)

    @discord.ui.button(label="Zurueckziehen", style=discord.ButtonStyle.danger)
    async def withdraw_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        del button
        pending_match = self.cog.pending_matches.pop(self.match_id, None)
        if pending_match is None:
            await interaction.response.send_message("Dieses Match ist nicht mehr offen.", ephemeral=True)
            return

        self.stop()
        await interaction.response.send_message("Match wurde zurueckgezogen.", ephemeral=True)
        results_channel = await self.cog.fetch_results_channel()
        if results_channel is not None:
            try:
                await results_channel.send(embed=build_withdrawn_match_embed(pending_match.match_id))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        thread = await self.cog.fetch_thread(pending_match.thread_id)
        if thread is not None:
            try:
                await thread.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


# =============================
# Ergebnis-Bestaetigung: Gegenspieler prueft und bestaetigt den Vorschlag.
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
            await interaction.response.send_message("Nur die beiden Spieler koennen das Ergebnis bestaetigen.", ephemeral=True)
            return False

        if interaction.user.id != self.confirmer_id:
            await interaction.response.send_message(
                f"Nur <@{self.confirmer_id}> kann dieses Ergebnis bestaetigen.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(label="Ergebnis bestaetigen", style=discord.ButtonStyle.success)
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
            await interaction.response.send_message("Guild-ID konnte nicht aufgeloest werden.", ephemeral=True)
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
                "Das Ergebnis wurde gespeichert, aber nicht in den Ergebnis-Channel gesendet. Bitte erneut bestaetigen.",
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

        await self.cog.refresh_panels(refresh_all=True)
        await interaction.followup.send("Ergebnis bestaetigt und gepostet.", ephemeral=True)



# =============================
# Ergebnis-Erfassung: Button im Match-Thread und Modal fuer Score, Average und Screenshot.
# =============================

class ResultEntryView(discord.ui.View):
    def __init__(self, cog: Ranked, match_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.match_id = match_id

    @discord.ui.button(label="Ergebnis posten", style=discord.ButtonStyle.success)
    async def post_result(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        match = self.cog.get_active_match_by_id(self.match_id)
        if match is None:
            await interaction.response.send_message("Dieses Match ist nicht mehr aktiv.", ephemeral=True)
            return

        if interaction.user.id not in match.player_ids:
            await interaction.response.send_message(
                "Nur die beiden Match-Spieler duerfen das Ergebnis eintragen.",
                ephemeral=True,
            )
            return

        if self.cog.pending_results.get(self.match_id) is not None:
            await interaction.response.send_message(
                "Fuer dieses Match wurde bereits ein Ergebnis eingetragen und wartet auf Bestaetigung.",
                ephemeral=True,
            )
            return

        message = interaction.message
        button.disabled = True
        await self.cog.open_result_modal(
            interaction,
            match_id=self.match_id,
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
            placeholder="Gewinner auswaehlen",
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
            await interaction.response.send_message("Bitte waehle einen Gewinner aus.", ephemeral=True)
            return

        score = parse_best_of_seven_score(self.score_input.value)
        if score is None:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Bitte gib einen gueltigen Best-of-7-Spielstand ein, z. B. 4:0 bis 4:3.",
                ephemeral=True,
            )
            return

        average_one = normalize_average(self.average_one_input.value)
        average_two = normalize_average(self.average_two_input.value)
        if average_one is None or average_two is None:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Die Averages muessen numerisch sein. Punkt und Komma sind erlaubt.",
                ephemeral=True,
            )
            return

        winner_id = int(self.winner_select.values[0])
        player_one_id, player_two_id = self.match.player_ids
        left_score, right_score = score

        if winner_id == player_one_id and left_score != 4:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Der ausgewaehlte Gewinner passt nicht zum Spielstand.",
                ephemeral=True,
            )
            return

        if winner_id == player_two_id and right_score != 4:
            await self.restore_result_entry_button()
            await interaction.response.send_message(
                "Der ausgewaehlte Gewinner passt nicht zum Spielstand.",
                ephemeral=True,
            )
            return

        screenshot = self.screenshot_upload.values[0] if self.screenshot_upload.values else None
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
                content=f"<@{confirmer_id}>, bitte bestaetige dieses Ergebnis.",
                view=confirmation_view,
            )
        except discord.HTTPException:
            self.cog.pending_results.pop(self.match.match_id, None)
            await self.restore_result_entry_button()
            await interaction.followup.send("Das Ergebnis konnte nicht im Match-Thread gesendet werden.", ephemeral=True)
            return

        pending_result.confirmation_message_id = message.id
        await interaction.followup.send("Ergebnis zur Bestaetigung in den Match-Thread gesendet.", ephemeral=True)


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
                await interaction.response.send_message("Keine Queue ausgewaehlt.", ephemeral=True)
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
                "Beides ist gerade nicht moeglich, weil in beiden Queues schon jemand wartet.",
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
        self.bot.add_view(QueuePanel(self))

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
            content=(
                f"{player_one.mention} {player_two.mention}\n"
                "Bestaetigt dieses Match oder zieht es zurueck."
            ),
            embed=build_pending_match_embed(pending_match),
            view=view,
        )
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

    def confirm_pending_match(self, match_id: int) -> MatchState | None:
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

    # Ergebnisvorschlaege und Panel-Aktualisierung nach Interaktionen.
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
                "Nur die beiden Match-Spieler duerfen das Ergebnis eintragen.",
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

    @app_commands.command(name="result", description="Oeffnet im Match-Thread das Ergebnisformular")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def result(self, interaction: discord.Interaction) -> None:
        await self.open_result_modal(interaction)

    @app_commands.command(name="world_ranking", description="Zeigt das aktuelle World Ranking")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def world_ranking(self, interaction: discord.Interaction) -> None:
        if getattr(self.bot, "db", None) is None:
            await interaction.response.send_message("Die Datenbank ist aktuell nicht verfuegbar.", ephemeral=True)
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
            await interaction.response.send_message("Die Datenbank ist aktuell nicht verfuegbar.", ephemeral=True)
            return

        rows = await fetch_monthly_ranking(self.bot)
        embed = build_ranking_embed(
            title="Monatsranking",
            rows=rows,
            empty_text="Fuer diesen Monat gibt es noch keine Ranked-Ergebnisse.",
        )
        await interaction.response.send_message(embed=embed)

    ## command
    # - stats
    # - match verlauf (letzten 10)
    # - top10 ranking
    # - export matches

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ranked(bot))
