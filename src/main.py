"""
WoW Raid Roster TUI — Entry point
==================================
Uso:
    python main.py
    python main.py --api-key TU_KEY   (carga datos reales de wowaudit)
    python main.py --load estado.json

Controles:
    Tab / Shift+Tab  → navegar entre paneles
    Enter            → seleccionar / confirmar
    Escape           → cerrar modal / cancelar
    A                → añadir boss (desde panel Bosses)
    D                → eliminar boss seleccionado
    R                → añadir restricción
    X                → eliminar restricción seleccionada
    E                → editar asignación manual (toggle jugador↔boss)
    O                → optimizar con solver MILP
    S                → guardar estado a JSON
    L                → cargar estado desde JSON
    Q                → salir
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models import Player, RosterState
from app import WoWRosterApp


def load_from_wowaudit(api_key: str) -> RosterState | None:
    try:
        import requests as req
        headers = {"accept": "application/json", "Authorization": api_key}

        wishlist_r = req.get("https://wowaudit.com/v1/wishlists", headers=headers, timeout=10)
        chars_r    = req.get("https://wowaudit.com/v1/characters", headers=headers, timeout=10)

        wishlist = wishlist_r.json()
        chars    = chars_r.json()

        players = []
        for c in chars:
            role = c.get("role", "DPS")
            if role not in ("Tank", "Heal", "Ranged", "Melee"):
                role = "DPS"
            players.append(Player(
                name=c.get("name", ""),
                realm=c.get("realm", ""),
                cls=c.get("class", "Unknown"),
                role=role,
                spec=c.get("spec", ""),
            ))

        bosses: list[str] = []
        if wishlist.get("characters"):
            for instance in wishlist["characters"][0].get("instances", []):
                for diff in instance.get("difficulties", []):
                    for enc in diff.get("wishlist", {}).get("encounters", []):
                        if enc["name"] not in bosses:
                            bosses.append(enc["name"])

        return RosterState(players=players, bosses=bosses)
    except Exception as e:
        print(f"Error al cargar de wowaudit: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WoW Raid Roster TUI")
    parser.add_argument("--api-key", help="API key de wowaudit.com")
    parser.add_argument("--load",    help="Cargar estado desde fichero JSON")
    args = parser.parse_args()

    state: RosterState | None = None

    if args.load:
        path = Path(args.load)
        if path.exists():
            state = RosterState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            print(f"Estado cargado desde {path}")
        else:
            print(f"Fichero {path} no encontrado, usando demo", file=sys.stderr)

    if state is None and args.api_key:
        print("Cargando datos desde wowaudit.com…")
        state = load_from_wowaudit(args.api_key)
        if state is None:
            print("Fallando a datos de demostración")

    WoWRosterApp(state=state).run()