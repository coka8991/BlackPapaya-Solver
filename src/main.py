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

from dataclasses import dataclass, field
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from models import RosterState
from services import (
    build_excluded_boss_cards,
    build_roster_cards,
    build_sidebar_stats,
    build_solver_cards,
    load_from_wowaudit,
    solve_roster_state,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@dataclass
class WebAppState:
    roster: RosterState = field(default_factory=RosterState)
    solver_result: dict[str, list[str]] | None = None
    api_key: str = ""
    message: str = ""
    error: str = ""


state = WebAppState()
app = FastAPI(title="Black Papaya Solver")

RESTRICTION_CYCLE = (None, "force_in", "force_out")


def build_template_context(request: Request) -> dict:
    return {
        "request": request,
        "state": state,
        "roster": state.roster,
        "result": state.solver_result,
        "stats": build_sidebar_stats(state.roster),
        "roster_cards": build_roster_cards(state.roster),
        "excluded_boss_cards": build_excluded_boss_cards(state.roster),
        "result_cards": build_solver_cards(state.roster, state.solver_result),
    }


def render_page(request: Request, template_name: str) -> HTMLResponse:
    return templates.TemplateResponse(template_name, build_template_context(request))


def set_feedback(*, message: str = "", error: str = "") -> None:
    state.message = message
    state.error = error


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return render_page(request, "index.html")


@app.post("/load", response_class=HTMLResponse)
def load_roster(request: Request, api_key: str = Form(...)) -> HTMLResponse:
    state.api_key = api_key.strip()
    state.solver_result = None

    if not state.api_key:
        set_feedback(error="Introduce una API key de WowAudit antes de cargar el roster.")
        return render_page(request, "partials/app_shell.html")

    try:
        roster = load_from_wowaudit(state.api_key)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "?"
        set_feedback(error=f"WowAudit devolvió HTTP {status_code}. Revisa la API key.")
        return render_page(request, "partials/app_shell.html")
    except requests.RequestException as exc:
        set_feedback(error=f"No se pudo contactar con WowAudit: {exc}")
        return render_page(request, "partials/app_shell.html")

    if not roster.players:
        set_feedback(error="WowAudit respondió sin jugadores para esta API key.")
        return render_page(request, "partials/app_shell.html")
    if not roster.bosses:
        set_feedback(error="WowAudit respondió sin bosses disponibles en la wishlist.")
        return render_page(request, "partials/app_shell.html")

    state.roster = roster
    set_feedback(
        message=f"Roster cargado: {len(roster.players)} jugadores y {len(roster.bosses)} bosses.",
    )
    return render_page(request, "partials/app_shell.html")


@app.post("/restrictions", response_class=HTMLResponse)
def update_restriction(
    request: Request,
    boss_name: str = Form(...),
    player_key: str = Form(...),
    restriction_type: str = Form(""),
    restriction_action: str = Form("set"),
) -> HTMLResponse:
    if not state.roster.has_boss(boss_name):
        set_feedback(error=f"Boss desconocido: {boss_name}")
        return render_page(request, "partials/app_shell.html")
    if not state.roster.has_player(player_key):
        set_feedback(error=f"Jugador desconocido: {player_key}")
        return render_page(request, "partials/app_shell.html")

    current = state.roster.restriction_type_for(player_key, boss_name)
    if restriction_action == "cycle":
        current_index = RESTRICTION_CYCLE.index(current)
        normalized = RESTRICTION_CYCLE[(current_index + 1) % len(RESTRICTION_CYCLE)]
    else:
        normalized = restriction_type if restriction_type in {"force_in", "force_out"} else None

    state.roster.set_restriction(player_key, boss_name, normalized)
    state.solver_result = None

    label = "sin restricción" if normalized is None else normalized.replace("_", " ")
    set_feedback(message=f"{player_key} en {boss_name}: {label}.")
    return render_page(request, "partials/app_shell.html")


@app.post("/bosses/exclude", response_class=HTMLResponse)
def exclude_boss(request: Request, boss_name: str = Form(...)) -> HTMLResponse:
    if not state.roster.has_boss(boss_name):
        set_feedback(error=f"Boss desconocido: {boss_name}")
        return render_page(request, "partials/app_shell.html")
    if state.roster.is_boss_excluded(boss_name):
        set_feedback(message=f"{boss_name} ya estaba excluido de la planificación.")
        return render_page(request, "partials/app_shell.html")

    state.roster.exclude_boss(boss_name)
    state.solver_result = None
    set_feedback(message=f"{boss_name} excluido de restricciones y del solver.")
    return render_page(request, "partials/app_shell.html")


@app.post("/bosses/include", response_class=HTMLResponse)
def include_boss(request: Request, boss_name: str = Form(...)) -> HTMLResponse:
    if not state.roster.has_boss(boss_name):
        set_feedback(error=f"Boss desconocido: {boss_name}")
        return render_page(request, "partials/app_shell.html")

    state.roster.include_boss(boss_name)
    state.solver_result = None
    set_feedback(message=f"{boss_name} restaurado para restricciones y planificación.")
    return render_page(request, "partials/app_shell.html")


@app.post("/solve", response_class=HTMLResponse)
def solve(request: Request) -> HTMLResponse:
    if not state.roster.players or not state.roster.bosses:
        set_feedback(error="Carga primero un roster válido antes de ejecutar el solver.")
        return render_page(request, "partials/app_shell.html")
    if not state.roster.active_bosses():
        set_feedback(error="No hay bosses activos para planificar. Restaura al menos uno antes de ejecutar el solver.")
        return render_page(request, "partials/app_shell.html")

    try:
        result = solve_roster_state(state.roster)
    except ImportError as exc:
        set_feedback(error=f"Falta una dependencia del solver: {exc}")
        return render_page(request, "partials/app_shell.html")
    except RuntimeError as exc:
        set_feedback(error=str(exc))
        return render_page(request, "partials/app_shell.html")
    except Exception as exc:
        set_feedback(error=f"El solver falló: {exc}")
        return render_page(request, "partials/app_shell.html")

    if result is None:
        state.solver_result = None
        set_feedback(error="No se encontró una solución factible con las restricciones actuales.")
        return render_page(request, "partials/app_shell.html")

    state.solver_result = result
    total_assignments = sum(len(players) for players in result.values())
    set_feedback(message=f"Solver ejecutado: {total_assignments} asignaciones propuestas.")
    return render_page(request, "partials/app_shell.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)