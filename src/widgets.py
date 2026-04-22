"""
widgets.py — Widgets reutilizables para WoW Raid Roster TUI
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, Static

from constants import BOSS_ICONS, ROLE_ICON
from models import Player, RosterState


class RosterTable(Static):
    """Tabla de roster para un boss."""

    def __init__(self, boss: str, players: list[Player], state: RosterState):
        super().__init__()
        self._boss = boss
        self._players = players
        self._state = state

    def render_table(self) -> str:
        assigned_keys = self._state.assignments.get(self._boss, [])
        assigned = [p for p in self._players if p.key in assigned_keys]
        assigned.sort(
            key=lambda p: (
                ["Tank", "Heal", "Ranged", "Melee"].index(p.role)
                if p.role in ["Tank", "Heal", "Ranged", "Melee"]
                else 99,
                p.name,
            )
        )

        tanks  = [p for p in assigned if p.role == "Tank"]
        heals  = [p for p in assigned if p.role == "Heal"]
        ranged = [p for p in assigned if p.role == "Ranged"]
        melee  = [p for p in assigned if p.role == "Melee"]

        lines = []
        for group_name, group in [("TANKS", tanks), ("HEALS", heals), ("RANGED", ranged), ("MELEE", melee)]:
            if group:
                lines.append(f"[dim]{group_name}[/dim]")
                for p in group:
                    icon = ROLE_ICON.get(p.role, "⚔")
                    color = p.color
                    lines.append(f"  {icon} [{color}]{p.name}[/{color}] [dim]({p.cls})[/dim]")

        lines.append(f"\n[dim]Total: {len(assigned)} jugadores[/dim]")
        return "\n".join(lines)

    def compose(self) -> ComposeResult:
        icon = BOSS_ICONS[self._state.bosses.index(self._boss) % len(BOSS_ICONS)]
        yield Label(f"{icon} [bold]{self._boss}[/bold]", classes="boss-header", markup=True)
        safe_id = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in self._boss.replace(" ", "_")
        )
        yield Static(self.render_table(), id=f"roster-{safe_id}", markup=True)
