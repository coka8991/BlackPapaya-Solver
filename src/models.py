"""
models.py — Modelos de datos y estado para WoW Raid Roster TUI
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from constants import CLASS_COLORS


@dataclass
class Player:
    name: str
    realm: str
    cls: str = "Unknown"
    role: str = "DPS"
    spec: str = ""

    @property
    def key(self) -> str:
        return f"{self.name}-{self.realm}"

    @property
    def color(self) -> str:
        return CLASS_COLORS.get(self.cls, CLASS_COLORS["Unknown"])


@dataclass
class Restriction:
    type: str          # "force_in" | "force_out"
    player_key: str
    boss_name: str
    reason: str = ""


@dataclass
class RosterState:
    players: list[Player] = field(default_factory=list)
    bosses: list[str] = field(default_factory=list)
    assignments: dict[str, list[str]] = field(default_factory=dict)  # boss → [player_key]
    restrictions: list[Restriction] = field(default_factory=list)
    heals_per_boss: dict[str, int] = field(default_factory=dict)  # boss → healer count (default 4)

    def player_by_key(self, key: str) -> Optional[Player]:
        return next((p for p in self.players if p.key == key), None)

    def toggle_assignment(self, boss: str, player_key: str):
        if boss not in self.assignments:
            self.assignments[boss] = []
        if player_key in self.assignments[boss]:
            self.assignments[boss].remove(player_key)
        else:
            self.assignments[boss].append(player_key)

    def add_boss(self, name: str):
        if name and name not in self.bosses:
            self.bosses.append(name)
            self.assignments.setdefault(name, [])

    def remove_boss(self, name: str):
        if name in self.bosses:
            self.bosses.remove(name)
            self.assignments.pop(name, None)

    def to_dict(self) -> dict:
        return {
            "players": [asdict(p) for p in self.players],
            "bosses": self.bosses,
            "assignments": self.assignments,
            "restrictions": [asdict(r) for r in self.restrictions],
            "heals_per_boss": self.heals_per_boss,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RosterState":
        state = cls()
        state.players = [Player(**p) for p in d.get("players", [])]
        state.bosses = d.get("bosses", [])
        state.assignments = d.get("assignments", {})
        state.restrictions = [Restriction(**r) for r in d.get("restrictions", [])]
        state.heals_per_boss = d.get("heals_per_boss", {})
        return state


# ─────────────────────────────────────────────
# Datos de demostración
# ─────────────────────────────────────────────

def demo_state() -> RosterState:
    players_raw = [
        ("Lasttime",        "Uldum",       "Warrior",      "Tank",   "Protection"),
        ("Harrison",        "Zul'jin",     "Paladin",      "Tank",   "Protection"),
        ("Meuzen",          "Sanguino",    "Druid",        "Heal",   "Restoration"),
        ("Nîvla",           "Zul'jin",     "Priest",       "Heal",   "Holy"),
        ("Elcoka",          "Sanguino",    "Shaman",       "Heal",   "Restoration"),
        ("Esnâiper",        "Sanguino",    "Hunter",       "Ranged", "Marksmanship"),
        ("Fami",            "Zul'jin",     "Mage",         "Ranged", "Arcane"),
        ("Finnu",           "Dun Modr",    "Warlock",      "Ranged", "Affliction"),
        ("Culebra",         "Sanguino",    "Rogue",        "Melee",  "Assassination"),
        ("Bichodebicho",    "Zul'jin",     "Death Knight", "Melee",  "Unholy"),
        ("Gamisan",         "Dun Modr",    "Demon Hunter", "Melee",  "Havoc"),
        ("Gölden",          "Tarren Mill", "Monk",         "Melee",  "Windwalker"),
        ("Xhera",           "Zul'jin",     "Evoker",       "Ranged", "Devastation"),
        ("Rinhoa",          "Zul'jin",     "Druid",        "Ranged", "Balance"),
        ("Curandero",       "Sanguino",    "Priest",       "Heal",   "Discipline"),
        ("Tankhard",        "Zul'jin",     "Death Knight", "Tank",   "Blood"),
        ("Flameshot",       "Uldum",       "Hunter",       "Ranged", "Beast Mastery"),
        ("Shadowbolt",      "Sanguino",    "Warlock",      "Ranged", "Destruction"),
        ("Slicerino",       "Dun Modr",    "Rogue",        "Melee",  "Outlaw"),
        ("Frostbite",       "Zul'jin",     "Mage",         "Ranged", "Frost"),
        ("Holysmoke",       "Tarren Mill", "Paladin",      "Heal",   "Holy"),
        ("Ironbreaker",     "Sanguino",    "Warrior",      "Melee",  "Arms"),
    ]
    players = [Player(n, r, c, role, spec) for n, r, c, role, spec in players_raw]

    bosses = [
        "Imperator Averzian",
        "Vorasius",
        "Fallen-King Salhadaar",
        "Chimaerus",
    ]

    assignments = {
        "Imperator Averzian": [
            "Lasttime-Uldum", "Harrison-Zul'jin", "Meuzen-Sanguino", "Nîvla-Zul'jin",
            "Elcoka-Sanguino", "Esnâiper-Sanguino", "Fami-Zul'jin", "Finnu-Dun Modr",
            "Culebra-Sanguino", "Bichodebicho-Zul'jin", "Gamisan-Dun Modr", "Gölden-Tarren Mill",
            "Xhera-Zul'jin", "Rinhoa-Zul'jin", "Curandero-Sanguino", "Tankhard-Zul'jin",
            "Flameshot-Uldum", "Shadowbolt-Sanguino",
        ],
        "Vorasius": [
            "Harrison-Zul'jin", "Tankhard-Zul'jin", "Meuzen-Sanguino", "Nîvla-Zul'jin",
            "Elcoka-Sanguino", "Curandero-Sanguino", "Esnâiper-Sanguino", "Fami-Zul'jin",
            "Finnu-Dun Modr", "Culebra-Sanguino", "Bichodebicho-Zul'jin", "Gamisan-Dun Modr",
            "Gölden-Tarren Mill", "Xhera-Zul'jin", "Flameshot-Uldum", "Shadowbolt-Sanguino",
            "Slicerino-Dun Modr", "Frostbite-Zul'jin",
        ],
        "Fallen-King Salhadaar": [
            "Culebra-Sanguino", "Harrison-Zul'jin", "Nîvla-Zul'jin", "Bichodebicho-Zul'jin",
            "Finnu-Dun Modr", "Gamisan-Dun Modr", "Gölden-Tarren Mill", "Lasttime-Uldum",
            "Tankhard-Zul'jin", "Meuzen-Sanguino", "Elcoka-Sanguino", "Holysmoke-Tarren Mill",
            "Esnâiper-Sanguino", "Xhera-Zul'jin", "Rinhoa-Zul'jin", "Ironbreaker-Sanguino",
            "Flameshot-Uldum", "Frostbite-Zul'jin",
        ],
        "Chimaerus": [
            "Xhera-Zul'jin", "Rinhoa-Zul'jin", "Lasttime-Uldum", "Harrison-Zul'jin",
            "Meuzen-Sanguino", "Nîvla-Zul'jin", "Curandero-Sanguino", "Holysmoke-Tarren Mill",
            "Esnâiper-Sanguino", "Fami-Zul'jin", "Shadowbolt-Sanguino", "Slicerino-Dun Modr",
            "Frostbite-Zul'jin", "Gamisan-Dun Modr", "Gölden-Tarren Mill", "Ironbreaker-Sanguino",
            "Tankhard-Zul'jin", "Culebra-Sanguino",
        ],
    }

    restrictions = [
        Restriction("force_in",  "Lasttime-Uldum",        "Imperator Averzian", "Tanquea fase 2"),
        Restriction("force_in",  "Harrison-Zul'jin",      "Vorasius",           "Interrupt rotation"),
        Restriction("force_out", "Finnu-Dun Modr",        "Chimaerus",          "Baja confirmada"),
        Restriction("force_in",  "Xhera-Zul'jin",         "Chimaerus",          "Item prio"),
        Restriction("force_in",  "Rinhoa-Zul'jin",        "Chimaerus",          "Item prio"),
    ]

    return RosterState(players=players, bosses=bosses, assignments=assignments, restrictions=restrictions)
