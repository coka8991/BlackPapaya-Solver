from __future__ import annotations

import requests

from constants import ROLE_ICON
from models import Player, ROLE_ORDER, RosterState
from solver import SolverConfig, solve_roster


VALID_ROLES = {"Tank", "Heal", "Ranged", "Melee"}


def normalize_role(role: str | None) -> str:
    if role in VALID_ROLES:
        return role
    return "DPS"


def load_from_wowaudit(api_key: str, timeout: int = 10) -> RosterState:
    headers = {"accept": "application/json", "Authorization": api_key}

    wishlist_response = requests.get(
        "https://wowaudit.com/v1/wishlists",
        headers=headers,
        timeout=timeout,
    )
    characters_response = requests.get(
        "https://wowaudit.com/v1/characters",
        headers=headers,
        timeout=timeout,
    )

    wishlist_response.raise_for_status()
    characters_response.raise_for_status()

    wishlist = wishlist_response.json()
    characters = characters_response.json()

    players = [
        Player(
            name=character.get("name", ""),
            realm=character.get("realm", ""),
            cls=character.get("class", "Unknown"),
            role=normalize_role(character.get("role")),
            spec=character.get("spec", ""),
        )
        for character in characters
    ]

    bosses: list[str] = []
    for character in wishlist.get("characters", []):
        for instance in character.get("instances", []):
            for difficulty in instance.get("difficulties", []):
                encounters = difficulty.get("wishlist", {}).get("encounters", [])
                for encounter in encounters:
                    name = encounter.get("name")
                    if name and name not in bosses:
                        bosses.append(name)

    state = RosterState(players=players, bosses=bosses)
    for boss in bosses:
        state.assignments.setdefault(boss, [])
    return state


def restrictions_by_type(state: RosterState) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    active_bosses = set(state.active_bosses())
    restrictions_in = [
        (restriction.player_key, restriction.boss_name)
        for restriction in state.restrictions
        if restriction.type == "force_in" and restriction.boss_name in active_bosses
    ]
    restrictions_out = [
        (restriction.player_key, restriction.boss_name)
        for restriction in state.restrictions
        if restriction.type == "force_out" and restriction.boss_name in active_bosses
    ]
    return restrictions_in, restrictions_out


def build_solver_config(state: RosterState) -> SolverConfig:
    n_heals = [state.heals_per_boss.get(boss, 4) for boss in state.active_bosses()]
    return SolverConfig(n_heals=n_heals)


def build_solver_players(state: RosterState) -> list[dict[str, str]]:
    return [
        {"key": player.key, "cls": player.cls, "role": player.role}
        for player in state.players
    ]


def solve_roster_state(state: RosterState) -> dict[str, list[str]] | None:
    active_bosses = state.active_bosses()
    restrictions_in, restrictions_out = restrictions_by_type(state)
    return solve_roster(
        build_solver_players(state),
        active_bosses,
        restrictions_in,
        restrictions_out,
        build_solver_config(state),
    )


def build_sidebar_stats(state: RosterState) -> dict[str, int]:
    counts = {role: 0 for role in ROLE_ORDER}
    for player in state.players:
        if player.role in counts:
            counts[player.role] += 1

    active_bosses = state.active_bosses()
    active_bosses_set = set(active_bosses)
    force_in = sum(
        1
        for restriction in state.restrictions
        if restriction.type == "force_in" and restriction.boss_name in active_bosses_set
    )
    force_out = sum(
        1
        for restriction in state.restrictions
        if restriction.type == "force_out" and restriction.boss_name in active_bosses_set
    )
    return {
        "players": len(state.players),
        "bosses": len(active_bosses),
        "excluded_bosses": len(state.excluded_bosses),
        "tank": counts["Tank"],
        "heal": counts["Heal"],
        "ranged": counts["Ranged"],
        "melee": counts["Melee"],
        "restrictions": force_in + force_out,
        "force_in": force_in,
        "force_out": force_out,
    }


def build_boss_rows(state: RosterState, boss: str) -> list[dict[str, str | bool | None]]:
    rows: list[dict[str, str | bool | None]] = []
    assigned_keys = set(state.assignments.get(boss, []))
    for player in state.ordered_players():
        rows.append(
            {
                "player_key": player.key,
                "name": player.name,
                "realm": player.realm,
                "class": player.cls,
                "role": player.role,
                "role_icon": ROLE_ICON.get(player.role, "⚔"),
                "spec": player.spec or "—",
                "color": player.color,
                "restriction": state.restriction_type_for(player.key, boss),
                "assigned": player.key in assigned_keys,
            }
        )
    return rows


def build_roster_cards(state: RosterState) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for boss in state.active_bosses():
        rows = build_boss_rows(state, boss)
        cards.append(
            {
                "boss": boss,
                "rows": rows,
                "assigned_count": sum(1 for row in rows if row["assigned"]),
                "forced_count": sum(1 for row in rows if row["restriction"]),
            }
        )
    return cards


def build_solver_cards(
    state: RosterState,
    result: dict[str, list[str]] | None,
) -> list[dict[str, object]]:
    if not result:
        return []

    cards: list[dict[str, object]] = []
    for boss in state.active_bosses():
        players = [
            player
            for player_key in result.get(boss, [])
            if (player := state.player_by_key(player_key)) is not None
        ]
        grouped_players = state.grouped_players(players)
        cards.append(
            {
                "boss": boss,
                "total": len(players),
                "groups": [
                    {
                        "role": role,
                        "players": [
                            {
                                "name": player.name,
                                "class": player.cls,
                                "color": player.color,
                                "icon": ROLE_ICON.get(player.role, "⚔"),
                            }
                            for player in grouped_players[role]
                        ],
                    }
                    for role in ROLE_ORDER
                ],
            }
        )
    return cards


def build_excluded_boss_cards(state: RosterState) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for boss in state.excluded_bosses:
        cards.append(
            {
                "boss": boss,
                "assigned_count": len(state.assignments.get(boss, [])),
                "forced_count": sum(1 for restriction in state.restrictions if restriction.boss_name == boss),
            }
        )
    return cards