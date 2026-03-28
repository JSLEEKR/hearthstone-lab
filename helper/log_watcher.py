"""Real-time Power.log watcher and parser for Hearthstone."""
from __future__ import annotations
import os
import re
import time
import threading
import queue
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default Power.log paths
POWER_LOG_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Blizzard" / "Hearthstone" / "Logs" / "Power.log",
    Path("C:/Program Files (x86)/Hearthstone/Logs/Power.log"),
    Path("C:/Program Files/Hearthstone/Logs/Power.log"),
]

LOG_CONFIG_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Blizzard" / "Hearthstone" / "log.config"

LOG_CONFIG_CONTENT = """[Power]
LogLevel=1
FilePrinting=True
ConsolePrinting=False
ScreenPrinting=False
Verbose=True
"""


@dataclass
class GameEvent:
    """A parsed game event from Power.log."""
    event_type: str  # "GAME_START", "TURN", "CARD_PLAYED", "CARD_DRAWN", "ATTACK", "DEATH", "GAME_END", etc.
    player: int = 0  # 1 or 2
    entity_id: int = 0
    card_id: str = ""
    card_name: str = ""
    zone_from: str = ""
    zone_to: str = ""
    tags: dict = field(default_factory=dict)
    target_id: int = 0
    block_type: str = ""
    raw_line: str = ""


def ensure_log_config():
    """Create log.config if it doesn't exist."""
    if not LOG_CONFIG_PATH.exists():
        LOG_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_CONFIG_PATH.write_text(LOG_CONFIG_CONTENT, encoding="utf-8")
        logger.info(f"Created log.config at {LOG_CONFIG_PATH}")
        return True
    return False


def find_power_log() -> Path | None:
    """Find Power.log on the system."""
    for path in POWER_LOG_PATHS:
        if path.exists():
            return path
    return None


class PowerLogParser:
    """Parse Power.log lines into GameEvents."""

    # Regex patterns (inspired by python-hslog tokens.py)
    RE_POWERLOG = re.compile(r"^D (\d+:\d+:\d+\.\d+) (\w+)\.(\w+)\(\) - (.+)$")
    RE_TAG_CHANGE = re.compile(r"TAG_CHANGE Entity=(.+) tag=(\w+) value=(\w+)")
    RE_FULL_ENTITY = re.compile(r"FULL_ENTITY - Creating ID=(\d+) CardID=(\w*)")
    RE_SHOW_ENTITY = re.compile(r"SHOW_ENTITY - Updating Entity=.+CardID=(\w+)")
    RE_BLOCK_START = re.compile(
        r"BLOCK_START BlockType=(\w+) Entity=\[.*?id=(\d+).*?cardId=(\w*).*?\].*?Target=\[.*?id=(\d+).*?\]"
        r"|BLOCK_START BlockType=(\w+)"
    )
    RE_CREATE_GAME = re.compile(r"CREATE_GAME")
    RE_PLAYER = re.compile(r"Player EntityID=(\d+) PlayerID=(\d+)")
    RE_TAG_VALUE = re.compile(r"tag=(\w+) value=(.+)")
    RE_GAME_ENTITY = re.compile(r"GameEntity EntityID=(\d+)")

    def __init__(self):
        self.current_block = None
        self.in_create_game = False
        self.current_entity_id = None

    def parse_line(self, line: str) -> GameEvent | None:
        """Parse a single Power.log line into a GameEvent."""
        # Only process GameState.DebugPrintPower lines (avoid duplicates)
        if "GameState.DebugPrintPower()" not in line:
            return None

        # Extract the message part
        m = self.RE_POWERLOG.match(line.strip())
        if not m:
            # Try indented lines (tag definitions inside entities)
            stripped = line.strip()
            if stripped.startswith("tag="):
                tm = self.RE_TAG_VALUE.match(stripped)
                if tm and self.current_entity_id:
                    return GameEvent(
                        event_type="TAG_SET",
                        entity_id=self.current_entity_id,
                        tags={tm.group(1): tm.group(2)},
                        raw_line=line,
                    )
            return None

        msg = m.group(4).strip()

        # CREATE_GAME
        if self.RE_CREATE_GAME.match(msg):
            self.in_create_game = True
            return GameEvent(event_type="GAME_START", raw_line=line)

        # FULL_ENTITY
        fm = self.RE_FULL_ENTITY.match(msg)
        if fm:
            eid = int(fm.group(1))
            cid = fm.group(2) or ""
            self.current_entity_id = eid
            return GameEvent(
                event_type="ENTITY_CREATE",
                entity_id=eid,
                card_id=cid,
                raw_line=line,
            )

        # TAG_CHANGE
        tm = self.RE_TAG_CHANGE.match(msg)
        if tm:
            entity_str = tm.group(1)
            tag = tm.group(2)
            value = tm.group(3)

            # Detect zone changes (card movement)
            if tag == "ZONE":
                event_type = "ZONE_CHANGE"
                if value == "HAND":
                    event_type = "CARD_DRAWN"
                elif value == "PLAY":
                    event_type = "CARD_PLAYED"
                elif value == "GRAVEYARD":
                    event_type = "CARD_DIED"
                elif value == "DECK":
                    event_type = "CARD_TO_DECK"

                # Extract entity ID from entity string
                eid_m = re.search(r"id=(\d+)", entity_str)
                cid_m = re.search(r"cardId=(\w+)", entity_str)
                player_m = re.search(r"player=(\d+)", entity_str)
                name_m = re.search(r"entityName=([^\]]+?)(?:\s+id=|\])", entity_str)

                return GameEvent(
                    event_type=event_type,
                    entity_id=int(eid_m.group(1)) if eid_m else 0,
                    card_id=cid_m.group(1) if cid_m else "",
                    card_name=name_m.group(1).strip() if name_m else "",
                    player=int(player_m.group(1)) if player_m else 0,
                    zone_to=value,
                    tags={tag: value},
                    raw_line=line,
                )

            # Detect turn changes
            if tag == "TURN":
                return GameEvent(
                    event_type="TURN",
                    tags={"TURN": value},
                    raw_line=line,
                )

            # Detect game end
            if tag == "PLAYSTATE" and value in ("WON", "LOST", "CONCEDED"):
                player_m = re.search(r"player=(\d+)", entity_str)
                return GameEvent(
                    event_type="GAME_END",
                    player=int(player_m.group(1)) if player_m else 0,
                    tags={"PLAYSTATE": value},
                    raw_line=line,
                )

            return None  # Skip other tag changes

        # BLOCK_START (attacks, spells, etc.)
        bm = self.RE_BLOCK_START.match(msg)
        if bm:
            block_type = bm.group(1) or bm.group(5) or ""
            if block_type in ("ATTACK", "PLAY", "POWER"):
                return GameEvent(
                    event_type="BLOCK_START",
                    block_type=block_type,
                    entity_id=int(bm.group(2)) if bm.group(2) else 0,
                    card_id=bm.group(3) if bm.group(3) else "",
                    target_id=int(bm.group(4)) if bm.group(4) else 0,
                    raw_line=line,
                )

        # SHOW_ENTITY (opponent card revealed)
        sm = self.RE_SHOW_ENTITY.match(msg)
        if sm:
            return GameEvent(
                event_type="CARD_REVEALED",
                card_id=sm.group(1),
                raw_line=line,
            )

        return None


class LogWatcher:
    """Watch Power.log in real-time and emit parsed events."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path or find_power_log()
        self.parser = PowerLogParser()
        self.event_queue: queue.Queue[GameEvent] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start watching in a background thread."""
        if not self.log_path:
            logger.error("Power.log not found. Is Hearthstone installed?")
            return False
        if not self.log_path.exists():
            logger.warning(f"Power.log not found at {self.log_path}. Start a game first.")

        self._running = True
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        logger.info(f"Watching {self.log_path}")
        return True

    def stop(self):
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def get_events(self) -> list[GameEvent]:
        """Get all pending events (non-blocking)."""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _watch(self):
        """Watch loop running in background thread."""
        last_size = 0

        while self._running:
            if not self.log_path or not self.log_path.exists():
                time.sleep(1)
                continue

            try:
                current_size = self.log_path.stat().st_size

                # File was truncated (new game session)
                if current_size < last_size:
                    last_size = 0
                    logger.info("Power.log truncated — new session detected")

                if current_size > last_size:
                    with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        last_size = f.tell()

                    for line in new_lines:
                        event = self.parser.parse_line(line)
                        if event:
                            self.event_queue.put(event)

            except Exception as e:
                logger.error(f"Watch error: {e}")

            time.sleep(0.1)  # Poll every 100ms
