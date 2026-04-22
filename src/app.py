"""
app.py — Aplicación principal WoW Raid Roster TUI
"""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.css.query import NoMatches
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
)
from textual import on, work

from constants import BOSS_ICONS, CLASS_COLORS, ROLE_ICON
from models import Restriction, RosterState, demo_state
from modals import AddBossModal, AddRestrictionModal, AssignModal
from styles import CSS
from widgets import RosterTable


class WoWRosterApp(App):
    TITLE = "WoW Raid Roster Manager"
    CSS = CSS

    BINDINGS = [
        Binding("a", "add_boss",           "Añadir Boss",        show=True),
        Binding("d", "delete_selected",    "Eliminar",           show=True),
        Binding("r", "add_restriction",    "Añadir Restricción", show=True),
        Binding("x", "delete_restriction", "Del. Restricción",   show=True),
        Binding("e", "edit_assignment",    "Editar Asignación",  show=True),
        Binding("o", "optimize",           "Optimizar",          show=True),
        Binding("s", "save_state",         "Guardar",            show=True),
        Binding("l", "load_state",         "Cargar",             show=True),
        Binding("q", "quit",               "Salir",              show=True),
    ]

    state: RosterState

    def __init__(self, state: RosterState | None = None):
        super().__init__()
        self.state = state or demo_state()

    # ── Layout ──────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("📋 Roster", id="tab-roster"):
                with Horizontal():
                    with Vertical(id="sidebar"):
                        yield Label("📊 Estadísticas", id="sidebar-title", markup=False)
                        yield Static(self._sidebar_stats(), id="sidebar-stats", markup=True)
                    with ScrollableContainer(id="roster-scroll"):
                        yield Container(id="roster-grid")
            with TabPane("👥 Jugadores", id="tab-players"):
                yield DataTable(id="players-table", cursor_type="row")
            with TabPane("🐉 Bosses", id="tab-bosses"):
                with Vertical():
                    yield Label("🐉 Bosses activos", classes="section-title")
                    yield ListView(id="bosses-list")
                    with Horizontal(id="bosses-controls"):
                        yield Button("➕ Añadir Boss", id="btn-add-boss", variant="primary")
                        yield Button("🗑 Eliminar seleccionado", id="btn-del-boss")
            with TabPane("🔒 Restricciones", id="tab-restrictions"):
                with Vertical():
                    yield Label("🔒 Restricciones de asignación", classes="section-title")
                    yield DataTable(id="restrictions-table", cursor_type="row")
                    with Horizontal(id="restrictions-controls"):
                        yield Button("➕ Añadir Restricción", id="btn-add-restriction", variant="primary")
                        yield Button("🗑 Eliminar seleccionada", id="btn-del-restriction")
        yield Footer()

    def on_mount(self) -> None:
        self._build_roster_grid()
        self._build_players_table()
        self._build_bosses_list()
        self._build_restrictions_table()

    # ── Build helpers ────────────────────────────

    def _sidebar_stats(self) -> str:
        s = self.state
        total_players = len(s.players)
        tanks  = sum(1 for p in s.players if p.role == "Tank")
        heals  = sum(1 for p in s.players if p.role == "Heal")
        dps    = total_players - tanks - heals
        bosses = len(s.bosses)
        restrs = len(s.restrictions)
        force_in  = sum(1 for r in s.restrictions if r.type == "force_in")
        force_out = sum(1 for r in s.restrictions if r.type == "force_out")

        classes: dict[str, int] = {}
        for p in s.players:
            classes[p.cls] = classes.get(p.cls, 0) + 1

        lines = [
            f"[dim]Jugadores:[/dim]   [bold #aad372]{total_players}[/bold #aad372]",
            f"  [dim]🛡 Tanks:[/dim]  [#c69b3a]{tanks}[/#c69b3a]",
            f"  [dim]💚 Heals:[/dim]  [#3fc7eb]{heals}[/#3fc7eb]",
            f"  [dim]⚔ DPS:[/dim]    [#fff468]{dps}[/#fff468]",
            "",
            f"[dim]Bosses:[/dim]      [bold #aad372]{bosses}[/bold #aad372]",
            f"[dim]Restricciones:[/dim][bold #aad372]{restrs}[/bold #aad372]",
            f"  [dim]✅ Force IN:[/dim] [#aad372]{force_in}[/#aad372]",
            f"  [dim]❌ Force OUT:[/dim][#c41e3a]{force_out}[/#c41e3a]",
            "",
            "[dim]━━ Clases ━━[/dim]",
        ]
        for cls, count in sorted(classes.items(), key=lambda x: -x[1]):
            color = CLASS_COLORS.get(cls, "#888888")
            lines.append(f"  [{color}]{cls[:14]}[/{color}] [dim]{count}[/dim]")

        return "\n".join(lines)

    def _build_roster_grid(self):
        grid = self.query_one("#roster-grid", Container)
        grid.remove_children()
        for boss in self.state.bosses:
            grid.mount(
                Container(
                    RosterTable(boss, self.state.players, self.state),
                    classes="boss-card",
                )
            )

    def _build_players_table(self):
        table = self.query_one("#players-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Jugador", "Realm", "Clase", "Rol", "Spec", "Bosses")
        for p in sorted(self.state.players, key=lambda x: (x.role, x.name)):
            bosses_count = sum(
                1 for boss, assigned in self.state.assignments.items()
                if p.key in assigned
            )
            color = p.color
            role_icon = ROLE_ICON.get(p.role, "⚔")
            table.add_row(
                f"[{color}]{p.name}[/{color}]",
                f"[dim]{p.realm}[/dim]",
                f"[{color}]{p.cls}[/{color}]",
                f"{role_icon} {p.role}",
                p.spec or "—",
                f"[bold #aad372]{bosses_count}[/bold #aad372]",
                key=p.key,
            )

    def _build_bosses_list(self):
        lv = self.query_one("#bosses-list", ListView)
        lv.clear()
        for i, boss in enumerate(self.state.bosses):
            icon = BOSS_ICONS[i % len(BOSS_ICONS)]
            count = len(self.state.assignments.get(boss, []))
            lv.append(ListItem(Label(f"{icon}  {boss}  [dim]({count} jugadores)[/dim]", markup=True), name=boss))

    def _build_restrictions_table(self):
        table = self.query_one("#restrictions-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Tipo", "Jugador", "Boss", "Razón")
        for r in self.state.restrictions:
            tipo_str = "✅ Force IN" if r.type == "force_in" else "❌ Force OUT"
            color    = "#aad372" if r.type == "force_in" else "#c41e3a"
            player   = self.state.player_by_key(r.player_key)
            pcol     = player.color if player else "#888888"
            table.add_row(
                f"[{color}]{tipo_str}[/{color}]",
                f"[{pcol}]{r.player_key}[/{pcol}]",
                r.boss_name,
                r.reason or "—",
            )

    def _refresh_all(self):
        self._build_roster_grid()
        self._build_players_table()
        self._build_bosses_list()
        self._build_restrictions_table()
        try:
            self.query_one("#sidebar-stats", Static).update(self._sidebar_stats())
        except NoMatches:
            pass

    # ── Acciones ────────────────────────────────

    def action_add_boss(self):
        async def callback(name: str | None):
            if name:
                self.state.add_boss(name)
                self._refresh_all()
                self.notify(f"Boss '{name}' añadido", severity="information")
        self.push_screen(AddBossModal(), callback)

    def action_delete_selected(self):
        try:
            lv = self.query_one("#bosses-list", ListView)
            if lv.highlighted_child and lv.highlighted_child.name:
                boss = lv.highlighted_child.name
                self.state.remove_boss(boss)
                self._refresh_all()
                self.notify(f"Boss '{boss}' eliminado", severity="warning")
        except NoMatches:
            pass

    def action_add_restriction(self):
        async def callback(r: Restriction | None):
            if r:
                self.state.restrictions.append(r)
                self._refresh_all()
                self.notify(f"Restricción añadida: {r.type} {r.player_key} ↔ {r.boss_name}")
        self.push_screen(AddRestrictionModal(self.state.players, self.state.bosses), callback)

    def action_delete_restriction(self):
        try:
            table = self.query_one("#restrictions-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.state.restrictions):
                r = self.state.restrictions.pop(table.cursor_row)
                self._refresh_all()
                self.notify(f"Restricción eliminada: {r.player_key} ↔ {r.boss_name}", severity="warning")
        except (NoMatches, IndexError):
            pass

    def action_edit_assignment(self):
        """Abre modal de asignación para el jugador seleccionado en la tabla de jugadores."""
        try:
            table = self.query_one("#players-table", DataTable)
            row_key = table.cursor_row
            if row_key is not None and row_key < len(self.state.players):
                sorted_players = sorted(self.state.players, key=lambda x: (x.role, x.name))
                player = sorted_players[row_key]

                async def callback(_):
                    self._refresh_all()

                self.push_screen(AssignModal(self.state, player), callback)
        except (NoMatches, IndexError):
            self.notify("Selecciona un jugador en la pestaña Jugadores primero", severity="warning")

    def action_save_state(self):
        path = Path("roster_state.json")
        path.write_text(json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self.notify(f"Estado guardado en {path.resolve()}", severity="information")

    def action_load_state(self):
        path = Path("roster_state.json")
        if path.exists():
            self.state = RosterState.from_dict(json.loads(path.read_text(encoding="utf-8")))
            self._refresh_all()
            self.notify("Estado cargado desde roster_state.json", severity="information")
        else:
            self.notify("No se encontró roster_state.json", severity="warning")

    def action_optimize(self) -> None:
        """Lanza el solver MILP en un hilo de fondo y aplica los resultados."""
        self.notify("Optimizando roster… puede tardar unos segundos", timeout=15)
        self._solve_worker()

    @work(thread=True)
    def _solve_worker(self) -> None:
        try:
            from solver import SolverConfig, solve_roster
        except ImportError:
            self.call_from_thread(
                self.notify,
                "Instala pyomo:  pip install pyomo  (y GLPK para el solver)",
                severity="error",
                timeout=12,
            )
            return

        players_data = [
            {"key": p.key, "cls": p.cls, "role": p.role}
            for p in self.state.players
        ]
        restrictions_in = [
            (r.player_key, r.boss_name)
            for r in self.state.restrictions
            if r.type == "force_in"
        ]
        restrictions_out = [
            (r.player_key, r.boss_name)
            for r in self.state.restrictions
            if r.type == "force_out"
        ]
        n_heals = [self.state.heals_per_boss.get(b, 4) for b in self.state.bosses]
        config = SolverConfig(n_heals=n_heals)

        try:
            result = solve_roster(
                players_data,
                self.state.bosses,
                restrictions_in,
                restrictions_out,
                config,
            )
        except Exception as exc:
            self.call_from_thread(
                self.notify, f"Error del solver: {exc}", severity="error", timeout=12
            )
            return

        if result is not None:
            total = sum(len(v) for v in result.values())

            def apply_result() -> None:
                self.state.assignments = result
                self._refresh_all()
                self.notify(
                    f"Roster optimizado ✓  ({total} asignaciones totales)",
                    severity="information",
                )

            self.call_from_thread(apply_result)
        else:
            self.call_from_thread(
                self.notify,
                "No se encontró solución óptima. Revisa las restricciones.",
                severity="error",
                timeout=10,
            )

    # ── Botones ─────────────────────────────────

    @on(Button.Pressed, "#btn-add-boss")
    def on_add_boss(self):
        self.action_add_boss()

    @on(Button.Pressed, "#btn-del-boss")
    def on_del_boss(self):
        self.action_delete_selected()

    @on(Button.Pressed, "#btn-add-restriction")
    def on_add_restriction(self):
        self.action_add_restriction()

    @on(Button.Pressed, "#btn-del-restriction")
    def on_del_restriction(self):
        self.action_delete_restriction()
