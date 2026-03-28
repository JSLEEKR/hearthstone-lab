"""Transparent overlay window for Hearthstone game helper.

Key design:
- Semi-transparent dark panel (NOT click-through — user needs to interact)
- Always on top of other windows
- Left-click + drag header to move
- Compact layout for game info
- Works in windowed/borderless Hearthstone
"""
from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont
import logging

logger = logging.getLogger(__name__)

# UI Constants
PANEL_BG = "#0d1117"  # Dark GitHub-style background
HEADER_BG = "#161b22"
TEXT_COLOR = "#58d68d"  # Green
TITLE_COLOR = "#f0c040"  # Gold
WARN_COLOR = "#e74c3c"
MUTED_COLOR = "#7f8c8d"
LETHAL_COLOR = "#ff0000"
BORDER_COLOR = "#30363d"
OPACITY = 0.85


class OverlayWindow:
    """Always-on-top overlay panel for game info."""

    def __init__(self, width: int = 280, height: int = 500, x: int = 0, y: int = 150):
        self.root = tk.Tk()
        self.root.title("HS Helper")
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.overrideredirect(True)  # No title bar
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", OPACITY)
        # DO NOT set -transparentcolor or WS_EX_TRANSPARENT
        # We want the panel visible and interactable

        self.root.config(bg=PANEL_BG)

        # Fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.text_font = tkfont.Font(family="Consolas", size=9)
        self.small_font = tkfont.Font(family="Consolas", size=8)

        # === HEADER (draggable) ===
        self.header = tk.Frame(self.root, bg=HEADER_BG, cursor="fleur")
        self.header.pack(fill="x")

        self.header_label = tk.Label(
            self.header, text="  HS Helper", font=self.title_font,
            bg=HEADER_BG, fg=TITLE_COLOR, anchor="w", pady=6, padx=4)
        self.header_label.pack(side="left", fill="x", expand=True)

        # Close button
        self.close_btn = tk.Label(
            self.header, text=" X ", font=self.text_font,
            bg=HEADER_BG, fg="#e74c3c", cursor="hand2", pady=6)
        self.close_btn.pack(side="right", padx=4)
        self.close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        # Drag bindings on header
        self.header.bind("<Button-1>", self._start_drag)
        self.header.bind("<B1-Motion>", self._on_drag)
        self.header_label.bind("<Button-1>", self._start_drag)
        self.header_label.bind("<B1-Motion>", self._on_drag)

        # === CONTENT AREA (scrollable) ===
        self.content = tk.Frame(self.root, bg=PANEL_BG)
        self.content.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        # Status bar
        self.status_label = tk.Label(
            self.content, text="Waiting for game...",
            font=self.small_font, bg=PANEL_BG, fg=MUTED_COLOR, anchor="w")
        self.status_label.pack(fill="x", pady=(2, 4))

        self._separator()

        # === MY INFO ===
        self._section_title("My Stats")
        self.stats_label = tk.Label(
            self.content, text="Turn: -\nHand: - | Deck: -\nBoard: -",
            font=self.text_font, bg=PANEL_BG, fg=TEXT_COLOR,
            anchor="w", justify="left")
        self.stats_label.pack(fill="x", pady=2)

        self._separator()

        # === AI RECOMMENDATIONS ===
        self._section_title("AI Recommendations")
        self.recs_label = tk.Label(
            self.content, text="Start a game to see recommendations",
            font=self.text_font, bg=PANEL_BG, fg=MUTED_COLOR,
            anchor="w", justify="left", wraplength=260)
        self.recs_label.pack(fill="x", pady=2)

        self._separator()

        # === OPPONENT INFO ===
        self._section_title("Opponent", color="#ff8844")
        self.opp_label = tk.Label(
            self.content, text="Hand: - | Deck: -",
            font=self.small_font, bg=PANEL_BG, fg="#ff8844",
            anchor="w", justify="left", wraplength=260)
        self.opp_label.pack(fill="x", pady=2)

        self._separator()

        # === EVENT LOG ===
        self._section_title("Recent Events", color=MUTED_COLOR)
        self.log_label = tk.Label(
            self.content, text="",
            font=self.small_font, bg=PANEL_BG, fg=MUTED_COLOR,
            anchor="w", justify="left", wraplength=260)
        self.log_label.pack(fill="x", pady=2)

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

    def _section_title(self, text: str, color: str = TITLE_COLOR):
        tk.Label(self.content, text=text, font=self.small_font,
                 bg=PANEL_BG, fg=color, anchor="w").pack(fill="x", pady=(4, 1))

    def _separator(self):
        tk.Frame(self.content, height=1, bg=BORDER_COLOR).pack(fill="x", pady=3)

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
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
            self.recs_label.config(text="No recommendations yet", fg=MUTED_COLOR)
            return

        lines = []
        for i, rec in enumerate(recs[:5]):
            prefix = "!! LETHAL" if rec.priority >= 100 else f"{i+1}."
            line = f"{prefix} {rec.action}: {rec.card_name}"
            if rec.target:
                line += f" -> {rec.target}"
            if rec.reason:
                line += f"\n   {rec.reason}"
            lines.append(line)

        is_lethal = recs[0].priority >= 100
        self.recs_label.config(
            text="\n".join(lines),
            fg=LETHAL_COLOR if is_lethal else TEXT_COLOR)

    def update_opponent(self, state):
        lines = [
            f"Hand: {state.opp_hand_count} | Deck: {state.opp_deck_remaining}",
            f"Board: {len(state.opp_board)} minions | HP: {state.opp_hero_health}",
        ]
        if state.opp_played_cards:
            played = [c.card_name or c.card_id for c in state.opp_played_cards[-5:]]
            lines.append(f"Played: {', '.join(played)}")
        self.opp_label.config(text="\n".join(lines))

    def update_events(self, events: list[str]):
        recent = events[-6:] if events else ["No events yet"]
        self.log_label.config(text="\n".join(recent))

    def run(self):
        self.root.mainloop()

    def schedule(self, ms: int, callback):
        self.root.after(ms, callback)
