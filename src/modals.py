"""
modals.py — Pantallas modales para WoW Raid Roster TUI
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from models import Player, Restriction, RosterState
from textual import on


class AddBossModal(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]

    def compose(self) -> ComposeResult:
        with Container(id="modal-box"):
            yield Label("➕  Añadir Boss", id="modal-title")
            yield Input(placeholder="Nombre del boss…", id="boss-name-input")
            with Horizontal(id="modal-buttons"):
                yield Button("Añadir", variant="primary", id="btn-add")
                yield Button("Cancelar", variant="default", id="btn-cancel")

    @on(Button.Pressed, "#btn-add")
    def do_add(self):
        val = self.query_one("#boss-name-input", Input).value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn-cancel")
    def do_cancel(self):
        self.dismiss(None)

    @on(Input.Submitted)
    def on_submit(self):
        self.do_add()


class AddRestrictionModal(ModalScreen[Restriction | None]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]

    def __init__(self, players: list[Player], bosses: list[str]):
        super().__init__()
        self._players = players
        self._bosses = bosses

    def compose(self) -> ComposeResult:
        player_opts = [(p.key, p.key) for p in self._players]
        boss_opts   = [(b, b) for b in self._bosses]
        type_opts   = [("✅ Force IN", "force_in"), ("❌ Force OUT", "force_out")]

        with Container(id="modal-box"):
            yield Label("🔒  Añadir Restricción", id="modal-title")
            yield Label("Tipo:")
            yield Select(options=type_opts,   id="r-type",   prompt="Tipo…")
            yield Label("Jugador:")
            yield Select(options=player_opts, id="r-player", prompt="Jugador…")
            yield Label("Boss:")
            yield Select(options=boss_opts,   id="r-boss",   prompt="Boss…")
            yield Label("Razón (opcional):")
            yield Input(placeholder="Razón…", id="r-reason")
            with Horizontal(id="modal-buttons"):
                yield Button("Añadir", variant="primary",  id="btn-add")
                yield Button("Cancelar", variant="default", id="btn-cancel")

    @on(Button.Pressed, "#btn-add")
    def do_add(self):
        rtype  = self.query_one("#r-type",   Select).value
        player = self.query_one("#r-player", Select).value
        boss   = self.query_one("#r-boss",   Select).value
        reason = self.query_one("#r-reason", Input).value.strip()
        if rtype and player and boss:
            self.dismiss(Restriction(str(rtype), str(player), str(boss), reason))
        else:
            self.app.notify("Completa todos los campos obligatorios", severity="warning")

    @on(Button.Pressed, "#btn-cancel")
    def do_cancel(self):
        self.dismiss(None)


class AssignModal(ModalScreen[None]):
    """Permite toggle de un jugador en todos los bosses desde una vista de jugador."""
    BINDINGS = [Binding("escape", "dismiss(None)", "Cerrar")]

    def __init__(self, state: RosterState, player: Player):
        super().__init__()
        self._state = state
        self._player = player
        self._boss_by_button_id: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Container(id="modal-box", classes="wide"):
            yield Label(
                f"⚔  Asignaciones: [{self._player.color}]{self._player.key}[/]",
                id="modal-title",
                markup=True,
            )
            yield Label("Haz clic en un boss para añadir/quitar al jugador:")
            with ScrollableContainer(id="assign-list"):
                self._boss_by_button_id.clear()
                for index, boss in enumerate(self._state.bosses):
                    assigned = self._player.key in self._state.assignments.get(boss, [])
                    icon = "✅" if assigned else "⬜"
                    button_id = f"aboss-{index}"
                    self._boss_by_button_id[button_id] = boss
                    yield Button(
                        f"{icon}  {boss}",
                        id=button_id,
                        classes="assign-btn" + (" assigned" if assigned else ""),
                    )
            yield Button("Cerrar", variant="default", id="btn-close")

    @on(Button.Pressed)
    def on_press(self, event: Button.Pressed):
        if event.button.id == "btn-close":
            self.dismiss(None)
            return
        if event.button.id and event.button.id.startswith("aboss-"):
            boss = self._boss_by_button_id.get(event.button.id)
            if boss is None:
                return
            self._state.toggle_assignment(boss, self._player.key)
            assigned = self._player.key in self._state.assignments.get(boss, [])
            icon = "✅" if assigned else "⬜"
            event.button.label = f"{icon}  {boss}"
            if assigned:
                event.button.add_class("assigned")
            else:
                event.button.remove_class("assigned")
            self.app.notify(
                f"{'Añadido a' if assigned else 'Eliminado de'} {boss}", timeout=1.5
            )
