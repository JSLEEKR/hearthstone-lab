"""Transparent overlay window for Hearthstone game helper."""
from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont
import logging
import sys

logger = logging.getLogger(__name__)

# Colors
BG_COLOR = "black"  # Transparent
TEXT_COLOR = "#00ff88"
TITLE_COLOR = "#ffcc00"
WARN_COLOR = "#ff4444"
MUTED_COLOR = "#888888"
LETHAL_COLOR = "#ff0000"


class OverlayWindow:
    """Transparent always-on-top overlay for game info."""

    def __init__(self, width: int = 300, height: int = 600, x: int = 10, y: int = 100):
        self.root = tk.Tk()
        self.root.title("HS Helper")
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.overrideredirect(True)  # No title bar
        self.root.config(bg=BG_COLOR)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", BG_COLOR)
        self.root.attributes("-alpha", 0.9)

        # Try to make click-through on Windows
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)  # WS_EX_LAYERED | WS_EX_TRANSPARENT
        except Exception:
            pass  # Non-Windows or no ctypes

        # Fonts
        self.title_font = tkfont.Font(family="Consolas", size=12, weight="bold")
        self.text_font = tkfont.Font(family="Consolas", size=10)
        self.small_font = tkfont.Font(family="Consolas", size=8)

        # Main frame with semi-transparent background
        self.frame = tk.Frame(self.root, bg="#1a1a2e", relief="flat", bd=0)
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Header
        self.header = tk.Label(self.frame, text="HS Helper", font=self.title_font,
                               bg="#1a1a2e", fg=TITLE_COLOR, anchor="w")
        self.header.pack(fill="x", padx=8, pady=(8, 4))

        # Status
        self.status_label = tk.Label(self.frame, text="Waiting for game...",
                                     font=self.small_font, bg="#1a1a2e", fg=MUTED_COLOR, anchor="w")
        self.status_label.pack(fill="x", padx=8)

        # Separator
        tk.Frame(self.frame, height=1, bg="#333").pack(fill="x", padx=8, pady=4)

        # Stats section
        self.stats_label = tk.Label(self.frame, text="", font=self.text_font,
                                    bg="#1a1a2e", fg=TEXT_COLOR, anchor="w", justify="left")
        self.stats_label.pack(fill="x", padx=8, pady=2)

        # Separator
        tk.Frame(self.frame, height=1, bg="#333").pack(fill="x", padx=8, pady=4)

        # Recommendations section
        self.recs_title = tk.Label(self.frame, text="AI Recommendations",
                                   font=self.title_font, bg="#1a1a2e", fg=TITLE_COLOR, anchor="w")
        self.recs_title.pack(fill="x", padx=8, pady=(4, 2))

        self.recs_label = tk.Label(self.frame, text="", font=self.text_font,
                                   bg="#1a1a2e", fg=TEXT_COLOR, anchor="w", justify="left",
                                   wraplength=280)
        self.recs_label.pack(fill="x", padx=8, pady=2)

        # Separator
        tk.Frame(self.frame, height=1, bg="#333").pack(fill="x", padx=8, pady=4)

        # Event log section
        self.log_title = tk.Label(self.frame, text="Recent Events",
                                  font=self.small_font, bg="#1a1a2e", fg=MUTED_COLOR, anchor="w")
        self.log_title.pack(fill="x", padx=8, pady=(4, 2))

        self.log_label = tk.Label(self.frame, text="", font=self.small_font,
                                  bg="#1a1a2e", fg=MUTED_COLOR, anchor="w", justify="left",
                                  wraplength=280)
        self.log_label.pack(fill="x", padx=8, pady=2)

        # Opponent section
        self.opp_title = tk.Label(self.frame, text="Opponent",
                                  font=self.small_font, bg="#1a1a2e", fg="#ff8844", anchor="w")
        self.opp_title.pack(fill="x", padx=8, pady=(8, 2))

        self.opp_label = tk.Label(self.frame, text="", font=self.small_font,
                                  bg="#1a1a2e", fg="#ff8844", anchor="w", justify="left",
                                  wraplength=280)
        self.opp_label.pack(fill="x", padx=8, pady=2)

        # Dragging support (hold right-click to move)
        self.frame.bind("<Button-3>", self._start_drag)
        self.frame.bind("<B3-Motion>", self._on_drag)
        self._drag_x = 0
        self._drag_y = 0

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def update_status(self, text: str):
        self.status_label.config(text=text)

    def update_stats(self, stats: dict):
        lines = [
            f"Turn: {stats.get('turn', 0)}",
            f"Hand: {stats.get('hand_size', 0)} | Deck: {stats.get('deck_remaining', 0)}",
            f"Board: {stats.get('board_size', 0)} minions",
        ]
        self.stats_label.config(text="\n".join(lines))

    def update_recommendations(self, recs: list):
        if not recs:
            self.recs_label.config(text="No recommendations", fg=MUTED_COLOR)
            return

        lines = []
        for i, rec in enumerate(recs[:5]):
            prefix = "!!" if rec.priority >= 100 else f"{i+1}."
            line = f"{prefix} {rec.action}: {rec.card_name}"
            if rec.target:
                line += f" -> {rec.target}"
            if rec.reason:
                line += f"\n   {rec.reason}"
            lines.append(line)

        self.recs_label.config(text="\n".join(lines),
                               fg=LETHAL_COLOR if recs[0].priority >= 100 else TEXT_COLOR)

    def update_opponent(self, state):
        lines = [
            f"Hand: {state.opp_hand_count} | Deck: {state.opp_deck_remaining}",
            f"Board: {len(state.opp_board)} minions",
        ]
        if state.opp_played_cards:
            played = [c.card_name or c.card_id for c in state.opp_played_cards[-5:]]
            lines.append(f"Played: {', '.join(played)}")
        self.opp_label.config(text="\n".join(lines))

    def update_events(self, events: list[str]):
        recent = events[-8:] if events else []
        self.log_label.config(text="\n".join(recent))

    def run(self):
        self.root.mainloop()

    def schedule(self, ms: int, callback):
        """Schedule a callback on the GUI thread."""
        self.root.after(ms, callback)
