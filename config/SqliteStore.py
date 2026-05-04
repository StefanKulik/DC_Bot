from __future__ import annotations

import asyncio
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from discord.ext import commands


# =============================
# utils
# =============================
RANKING_START_RATING = 1000
ELO_K_FACTOR = 32

async def create_db_pool(bot: commands.Bot) -> None:
    print("Connect to SQLite database...")
    try:
        bot.db = SqliteDatabase("datenbank.db")
        await bot.db.connect()
    except Exception as exc:
        bot.db = None
        print(f"Database unavailable, continuing without DB features: {type(exc).__name__}: {exc}")
    else:
        print("SQLite database connected")

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def month_key_to_text(month_key: date) -> str:
    return month_key.isoformat()

def calculate_elo_winner_delta(winner_rating: int, loser_rating: int) -> int:
    expected_winner_score = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    return max(1, int(round(ELO_K_FACTOR * (1 - expected_winner_score))))


# =============================
# ranked-bot-db-zugriff
# =============================
def get_current_ranked_month_key() -> date:
    return datetime.now(timezone.utc).date().replace(day=1)

def to_ranked_database_average(value: str) -> str:
    return value.replace(",", ".")

async def ensure_ranked_storage(bot: commands.Bot) -> None:
    db = getattr(bot, "db", None)
    if db is None:
        return

    try:
        await db.ensure_ranked_storage()
        await rebuild_current_month_rankings(bot)
    except Exception as exc:
        print(f"Ranked DB persistence unavailable, falling back where possible: {type(exc).__name__}: {exc}")

async def get_next_ranked_match_id(bot: commands.Bot, fallback_match_id: int) -> tuple[int, int]:
    db = getattr(bot, "db", None)
    if db is None:
        return fallback_match_id, fallback_match_id + 1

    try:
        match_id = await db.get_next_match_id()
    except Exception as exc:
        print(f"Ranked match-id fetch failed, falling back to memory: {type(exc).__name__}: {exc}")
        return fallback_match_id, fallback_match_id + 1

    return int(match_id), fallback_match_id

async def rebuild_current_month_rankings(bot: commands.Bot) -> None:
    db = getattr(bot, "db", None)
    if db is None:
        return

    month_key = get_current_ranked_month_key()
    await db.rebuild_current_month_rankings(month_key)

async def persist_ranked_match_result(
    bot: commands.Bot,
    match: Any,
    result: Any,
    *,
    guild_id: int,
    confirmed_by: int,
) -> tuple[bool, bool]:
    db = getattr(bot, "db", None)
    if db is None:
        return False, False

    month_key = get_current_ranked_month_key()
    player_one_id, player_two_id = match.player_ids
    winner_id = result.winner_id

    guild = bot.get_guild(guild_id)
    player_one = guild.get_member(player_one_id) if guild is not None else None
    player_two = guild.get_member(player_two_id) if guild is not None else None
    player_one_name = player_one.display_name if player_one is not None else None
    player_two_name = player_two.display_name if player_two is not None else None

    return await db.persist_ranked_match_result(
        match_id=match.match_id,
        guild_id=guild_id,
        queue_name=match.queue_name,
        player_one_id=player_one_id,
        player_two_id=player_two_id,
        player_one_name=player_one_name,
        player_two_name=player_two_name,
        winner_id=winner_id,
        score=result.score,
        player_one_average=to_ranked_database_average(result.averages[player_one_id]),
        player_two_average=to_ranked_database_average(result.averages[player_two_id]),
        month_key=month_key,
        thread_id=match.thread_id,
        submitted_by=result.submitted_by,
        confirmed_by=confirmed_by,
        screenshot_url=result.screenshot.url if result.screenshot is not None else None,
    )

async def mark_ranked_match_result_published(
    bot: commands.Bot,
    match_id: int,
    channel_id: int,
    message_id: int,
) -> None:
    db = getattr(bot, "db", None)
    if db is None:
        return

    try:
        await db.mark_match_result_published(match_id, channel_id, message_id)
    except Exception as exc:
        print(f"Ranked match-result publish tracking failed: {type(exc).__name__}: {exc}")

async def fetch_world_ranking(bot: commands.Bot) -> list[tuple[int, int, int, int]]:
    db = getattr(bot, "db", None)
    if db is None:
        return []

    return await db.fetch_world_ranking()

async def fetch_monthly_ranking(bot: commands.Bot, month_key: int=None) -> list[tuple[int, int, int, int]]:
    db = getattr(bot, "db", None)
    if db is None:
        return []

    if month_key is None:
        month_key = get_current_ranked_month_key()
    return await db.fetch_monthly_ranking(month_key)


# =============================
# initialize sqlite database
# =============================
class SqliteDatabase:
    def __init__(self, path: Path | str = "datenbank.db") -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def connect(self) -> None:
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        await self.initialize()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("SQLite database is not connected")
        return self._connection

    async def close(self) -> None:
        async with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    async def initialize(self) -> None:
        async with self._lock:
            connection = self.connection
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS autorole (
                    guild_id INTEGER PRIMARY KEY,
                    memberrole_id INTEGER,
                    botrole_id INTEGER
                );

                CREATE TABLE IF NOT EXISTS bot_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ranked_players (
                    user_id INTEGER PRIMARY KEY,
                    world_rating INTEGER NOT NULL DEFAULT 1000,
                    world_wins INTEGER NOT NULL DEFAULT 0,
                    world_losses INTEGER NOT NULL DEFAULT 0,
                    last_known_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ranked_monthly_players (
                    user_id INTEGER NOT NULL,
                    month_key TEXT NOT NULL,
                    monthly_rating INTEGER NOT NULL DEFAULT 0,
                    monthly_wins INTEGER NOT NULL DEFAULT 0,
                    monthly_losses INTEGER NOT NULL DEFAULT 0,
                    last_known_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, month_key)
                );

                CREATE TABLE IF NOT EXISTS ranked_match_results (
                    match_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    queue_name TEXT NOT NULL,
                    player_one_user_id INTEGER NOT NULL,
                    player_two_user_id INTEGER NOT NULL,
                    winner_user_id INTEGER NOT NULL,
                    loser_user_id INTEGER NOT NULL,
                    player_one_score INTEGER NOT NULL,
                    player_two_score INTEGER NOT NULL,
                    player_one_average TEXT NOT NULL,
                    player_two_average TEXT NOT NULL,
                    world_points_awarded INTEGER NOT NULL,
                    world_points_deducted INTEGER NOT NULL DEFAULT 0,
                    monthly_points_awarded INTEGER NOT NULL,
                    monthly_points_deducted INTEGER NOT NULL DEFAULT 0,
                    winner_world_rating_before INTEGER,
                    loser_world_rating_before INTEGER,
                    winner_world_rating_after INTEGER,
                    loser_world_rating_after INTEGER,
                    winner_monthly_rating_before INTEGER,
                    loser_monthly_rating_before INTEGER,
                    winner_monthly_rating_after INTEGER,
                    loser_monthly_rating_after INTEGER,
                    month_key TEXT NOT NULL,
                    thread_id INTEGER NOT NULL,
                    submitted_by INTEGER NOT NULL,
                    confirmed_by INTEGER NOT NULL,
                    screenshot_url TEXT,
                    created_at TEXT NOT NULL,
                    published_at TEXT,
                    results_channel_id INTEGER,
                    results_message_id INTEGER
                );
                """
            )
            connection.commit()

    async def ensure_ranked_storage(self) -> None:
        await self.initialize()

    async def get_next_match_id(self) -> int:
        async with self._lock:
            row = self.connection.execute("SELECT value FROM bot_meta WHERE key = 'next_match_id'").fetchone()
            if row is None:
                max_row = self.connection.execute(
                    "SELECT COALESCE(MAX(match_id), 0) + 1 AS match_id FROM ranked_match_results"
                ).fetchone()
                match_id = int(max_row["match_id"])
                self.connection.execute(
                    "INSERT INTO bot_meta(key, value) VALUES('next_match_id', ?)",
                    (str(match_id + 1),),
                )
            else:
                match_id = int(row["value"])
                self.connection.execute(
                    "UPDATE bot_meta SET value = ? WHERE key = 'next_match_id'",
                    (str(match_id + 1),),
                )
            self.connection.commit()
            return match_id

    async def rebuild_current_month_rankings(self, month_key: date) -> None:
        month_text = month_key_to_text(month_key)
        async with self._lock:
            rows = self.connection.execute(
                """
                SELECT winner_user_id AS user_id, world_points_awarded AS won_points, 1 AS wins, 0 AS losses
                FROM ranked_match_results
                WHERE month_key = ?
                UNION ALL
                SELECT loser_user_id AS user_id, 0 AS won_points, 0 AS wins, 1 AS losses
                FROM ranked_match_results
                WHERE month_key = ?
                """,
                (month_text, month_text),
            ).fetchall()

            stats: dict[int, dict[str, int]] = {}
            for row in rows:
                user_stats = stats.setdefault(
                    int(row["user_id"]),
                    {"monthly_rating": 0, "monthly_wins": 0, "monthly_losses": 0},
                )
                user_stats["monthly_rating"] += int(row["won_points"])
                user_stats["monthly_wins"] += int(row["wins"])
                user_stats["monthly_losses"] += int(row["losses"])

            now = utc_now()
            for user_id, user_stats in stats.items():
                self.connection.execute(
                    """
                    INSERT INTO ranked_monthly_players(
                        user_id, month_key, monthly_rating, monthly_wins, monthly_losses, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, month_key) DO UPDATE
                    SET monthly_rating = excluded.monthly_rating,
                        monthly_wins = excluded.monthly_wins,
                        monthly_losses = excluded.monthly_losses,
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        month_text,
                        user_stats["monthly_rating"],
                        user_stats["monthly_wins"],
                        user_stats["monthly_losses"],
                        now,
                        now,
                    ),
                )
            self.connection.commit()

    def _upsert_player(self, user_id: int, last_known_name: str | None, now: str) -> None:
        self.connection.execute(
            """
            INSERT INTO ranked_players(user_id, last_known_name, created_at, updated_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE
            SET last_known_name = excluded.last_known_name,
                updated_at = excluded.updated_at
            """,
            (user_id, last_known_name, now, now),
        )

    def _upsert_monthly_player(self, user_id: int, month_text: str, last_known_name: str | None, now: str) -> None:
        self.connection.execute(
            """
            INSERT INTO ranked_monthly_players(user_id, month_key, last_known_name, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(user_id, month_key) DO UPDATE
            SET last_known_name = excluded.last_known_name,
                updated_at = excluded.updated_at
            """,
            (user_id, month_text, last_known_name, now, now),
        )

    async def persist_ranked_match_result(
        self,
        *,
        match_id: int,
        guild_id: int,
        queue_name: str,
        player_one_id: int,
        player_two_id: int,
        player_one_name: str | None,
        player_two_name: str | None,
        winner_id: int,
        score: tuple[int, int],
        player_one_average: str,
        player_two_average: str,
        month_key: date,
        thread_id: int,
        submitted_by: int,
        confirmed_by: int,
        screenshot_url: str | None,
    ) -> tuple[bool, bool]:
        month_text = month_key_to_text(month_key)
        loser_id = player_two_id if winner_id == player_one_id else player_one_id

        async with self._lock:
            existing = self.connection.execute(
                "SELECT published_at FROM ranked_match_results WHERE match_id = ?",
                (match_id,),
            ).fetchone()
            if existing is not None:
                return True, existing["published_at"] is not None

            now = utc_now()
            with self.connection:
                self._upsert_player(player_one_id, player_one_name, now)
                self._upsert_player(player_two_id, player_two_name, now)
                self._upsert_monthly_player(player_one_id, month_text, player_one_name, now)
                self._upsert_monthly_player(player_two_id, month_text, player_two_name, now)

                ratings = self.connection.execute(
                    """
                    SELECT user_id, world_rating
                    FROM ranked_players
                    WHERE user_id IN (?, ?)
                    """,
                    (player_one_id, player_two_id),
                ).fetchall()
                world_rating_map = {int(row["user_id"]): int(row["world_rating"]) for row in ratings}

                monthly_ratings = self.connection.execute(
                    """
                    SELECT user_id, monthly_rating
                    FROM ranked_monthly_players
                    WHERE month_key = ? AND user_id IN (?, ?)
                    """,
                    (month_text, player_one_id, player_two_id),
                ).fetchall()
                monthly_rating_map = {int(row["user_id"]): int(row["monthly_rating"]) for row in monthly_ratings}

                winner_world_before = world_rating_map[winner_id]
                loser_world_before = world_rating_map[loser_id]
                winner_monthly_before = monthly_rating_map[winner_id]
                loser_monthly_before = monthly_rating_map[loser_id]

                world_points_awarded = calculate_elo_winner_delta(winner_world_before, loser_world_before)
                world_points_deducted = -world_points_awarded
                monthly_points_awarded = world_points_awarded
                monthly_points_deducted = 0

                winner_world_after = winner_world_before + world_points_awarded
                loser_world_after = loser_world_before + world_points_deducted
                winner_monthly_after = winner_monthly_before + monthly_points_awarded
                loser_monthly_after = loser_monthly_before + monthly_points_deducted

                self.connection.execute(
                    """
                    INSERT INTO ranked_match_results(
                        match_id, guild_id, queue_name, player_one_user_id, player_two_user_id,
                        winner_user_id, loser_user_id, player_one_score, player_two_score,
                        player_one_average, player_two_average, world_points_awarded,
                        world_points_deducted, monthly_points_awarded, monthly_points_deducted,
                        winner_world_rating_before, loser_world_rating_before,
                        winner_world_rating_after, loser_world_rating_after,
                        winner_monthly_rating_before, loser_monthly_rating_before,
                        winner_monthly_rating_after, loser_monthly_rating_after, month_key,
                        thread_id, submitted_by, confirmed_by, screenshot_url, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match_id,
                        guild_id,
                        queue_name,
                        player_one_id,
                        player_two_id,
                        winner_id,
                        loser_id,
                        score[0],
                        score[1],
                        player_one_average,
                        player_two_average,
                        world_points_awarded,
                        world_points_deducted,
                        monthly_points_awarded,
                        monthly_points_deducted,
                        winner_world_before,
                        loser_world_before,
                        winner_world_after,
                        loser_world_after,
                        winner_monthly_before,
                        loser_monthly_before,
                        winner_monthly_after,
                        loser_monthly_after,
                        month_text,
                        thread_id,
                        submitted_by,
                        confirmed_by,
                        screenshot_url,
                        now,
                    ),
                )
                self.connection.execute(
                    """
                    UPDATE ranked_players
                    SET world_rating = world_rating + ?,
                        world_wins = world_wins + 1,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (world_points_awarded, now, winner_id),
                )
                self.connection.execute(
                    """
                    UPDATE ranked_players
                    SET world_rating = world_rating + ?,
                        world_losses = world_losses + 1,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (world_points_deducted, now, loser_id),
                )
                self.connection.execute(
                    """
                    UPDATE ranked_monthly_players
                    SET monthly_rating = monthly_rating + ?,
                        monthly_wins = monthly_wins + 1,
                        updated_at = ?
                    WHERE user_id = ? AND month_key = ?
                    """,
                    (monthly_points_awarded, now, winner_id, month_text),
                )
                self.connection.execute(
                    """
                    UPDATE ranked_monthly_players
                    SET monthly_losses = monthly_losses + 1,
                        updated_at = ?
                    WHERE user_id = ? AND month_key = ?
                    """,
                    (now, loser_id, month_text),
                )
            return True, False

    async def mark_match_result_published(self, match_id: int, channel_id: int, message_id: int) -> None:
        async with self._lock:
            self.connection.execute(
                """
                UPDATE ranked_match_results
                SET published_at = ?,
                    results_channel_id = ?,
                    results_message_id = ?
                WHERE match_id = ?
                """,
                (utc_now(), channel_id, message_id, match_id),
            )
            self.connection.commit()

    async def fetch_world_ranking(self, limit: int = 10) -> list[tuple[int, int, int, int]]:
        async with self._lock:
            rows = self.connection.execute(
                """
                SELECT user_id, world_rating, world_wins, world_losses
                FROM ranked_players
                ORDER BY world_rating DESC, world_wins DESC, user_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            (int(row["user_id"]), int(row["world_rating"]), int(row["world_wins"]), int(row["world_losses"]))
            for row in rows
        ]

    async def fetch_monthly_ranking(self, month_key: date, limit: int = 10) -> list[tuple[int, int, int, int]]:
        async with self._lock:
            rows = self.connection.execute(
                """
                SELECT user_id, monthly_rating, monthly_wins, monthly_losses
                FROM ranked_monthly_players
                WHERE month_key = ?
                ORDER BY monthly_rating DESC, monthly_wins DESC, user_id ASC
                LIMIT ?
                """,
                (month_key_to_text(month_key), limit),
            ).fetchall()
        return [
            (int(row["user_id"]), int(row["monthly_rating"]), int(row["monthly_wins"]), int(row["monthly_losses"]))
            for row in rows
        ]

