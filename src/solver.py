"""
solver.py — Pyomo MILP optimizer for WoW Raid Roster assignments
=================================================================
Maximises total vault slots across all players subject to:
  • Buff coverage per boss (at least one provider per active buff)
  • Role composition (tanks / healers / DPS count per boss)
  • Force-IN / force-OUT restrictions from RosterState
  • Minimum vault-slot guarantee per player (≥1 by default)

Requirements
------------
    pip install pyomo
    # GLPK solver (one of):
    #   conda install -c conda-forge glpk          (recommended)
    #   winget install GNUGlpk                     (Windows)
    #   sudo apt-get install glpk-utils            (Debian/Ubuntu)
    #   brew install glpk                          (macOS)

Vault-slot formula (WoW)
------------------------
    2 bosses → 1 slot  |  4 bosses → 2 slots  |  6 bosses → 3 slots
    vault = floor(n_bosses / 2)

    Encoded as two linear constraints per player:
        2·vault ≤ n_bosses          (ceiling)
        2·vault + 1 ≥ n_bosses      (floor)
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Optional Pyomo import (graceful degradation) ──────────────────────────────
try:
    from pyomo.environ import (
        Binary,
        ConcreteModel,
        Constraint,
        ConstraintList,
        Integers,
        Objective,
        SolverFactory,
        Var,
        maximize,
        value,
    )
    from pyomo.opt import SolverStatus, TerminationCondition

    PYOMO_AVAILABLE = True
except ImportError:
    PYOMO_AVAILABLE = False


# ── Class → buff/role mappings ────────────────────────────────────────────────

BUFFS: dict[str, list[str]] = {
    "Lust":              ["Shaman", "Mage", "Hunter", "Evoker"],
    "Intellect3%":       ["Mage"],
    "Stamina5%":         ["Priest"],
    "AttackPower5%":     ["Warrior"],
    "HuntersMark5%":     ["Hunter"],
    "PhysicalDmg5%":     ["Monk"],
    "MagicalDmg3%":      ["Demon Hunter"],
    "DR3%":              ["Paladin"],
    "Vers3%":            ["Druid"],
    "DR3.6%":            ["Rogue"],
    "Mastery2%":         ["Shaman"],
    "Healthstones_Gate": ["Warlock"],
}

# Maps solver role bucket → player role values in RosterState
ROLE_BUCKETS: dict[str, list[str]] = {
    "Tank": ["Tank"],
    "Heal": ["Heal"],
    "DPS":  ["Ranged", "Melee"],
}


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class SolverConfig:
    """Runtime parameters for :func:`solve_roster`."""

    # Per-boss healer count.  Padded with *default_heals* when shorter than
    # the boss list.
    n_heals: list[int] = field(default_factory=list)
    default_heals: int = 4

    # Tanks and total raid size per boss.
    n_tanks: int = 2
    raid_size: int = 20

    # Players exempt from the minimum-vault constraint (e.g. part-timers).
    excluded_players: list[str] = field(default_factory=list)

    # Minimum vault slots required for every non-excluded player.
    min_vault: int = 1

    # Buff-coverage definitions (maps buff name → list of WoW class strings).
    buffs: dict[str, list[str]] = field(default_factory=lambda: dict(BUFFS))

    # Buff keys whose coverage constraint is skipped.
    skip_buffs: list[str] = field(default_factory=lambda: ["PhysicalDmg5%"])


# ── Main solver function ───────────────────────────────────────────────────────

def solve_roster(
    players: list[dict],                        # [{"key": str, "cls": str, "role": str}, …]
    bosses: list[str],
    restrictions_in: list[tuple[str, str]],     # [(player_key, boss_name), …]
    restrictions_out: list[tuple[str, str]],    # [(player_key, boss_name), …]
    config: SolverConfig | None = None,
) -> dict[str, list[str]] | None:
    """
    Solve the MILP assignment problem.

    Parameters
    ----------
    players:
        List of player dicts with at least "key", "cls", and "role".
    bosses:
        Ordered list of boss names.
    restrictions_in:
        ``(player_key, boss_name)`` pairs that must be assigned.
    restrictions_out:
        ``(player_key, boss_name)`` pairs that must *not* be assigned.
    config:
        Solver configuration; uses defaults when *None*.

    Returns
    -------
    dict[str, list[str]]
        Mapping ``boss_name → [player_key, …]`` for the optimal roster, or
        ``None`` when no feasible solution was found.

    Raises
    ------
    ImportError
        If *pyomo* is not installed.
    RuntimeError
        If the GLPK solver binary cannot be located.
    """
    if not PYOMO_AVAILABLE:
        raise ImportError(
            "pyomo is required for roster optimization.\n"
            "Install with:  pip install pyomo\n"
            "GLPK solver:   conda install -c conda-forge glpk  "
            "(or see https://winglpk.sourceforge.net/ on Windows)"
        )

    if not players or not bosses:
        return None

    cfg = config or SolverConfig()

    # Pad n_heals to cover every boss
    n_heals_list: list[int] = list(cfg.n_heals)
    while len(n_heals_list) < len(bosses):
        n_heals_list.append(cfg.default_heals)

    player_keys: list[str] = [p["key"] for p in players]

    # Build provider sets
    buff_providers: dict[str, list[str]] = {
        buff: [p["key"] for p in players if p["cls"] in classes]
        for buff, classes in cfg.buffs.items()
        if buff not in cfg.skip_buffs
    }
    role_providers: dict[str, list[str]] = {
        role: [p["key"] for p in players if p["role"] in bucket]
        for role, bucket in ROLE_BUCKETS.items()
    }

    # ── Model ─────────────────────────────────────────────────────────────────
    m = ConcreteModel()

    # Binary assignment matrix
    m.C = Var(player_keys, bosses, domain=Binary)

    # Integer vault-slot variable per player [0, 3]
    m.vault = Var(player_keys, domain=Integers, bounds=(0, 3))

    # vault ↔ boss-count linkage:  vault = floor(sum_bosses / 2)
    m.vault_link = ConstraintList()
    for pk in player_keys:
        total = sum(m.C[pk, j] for j in bosses)
        m.vault_link.add(2 * m.vault[pk] <= total)
        m.vault_link.add(2 * m.vault[pk] + 1 >= total)

    # Buff coverage: each boss needs ≥1 provider per active buff
    m.buff_cov = ConstraintList()
    for j in bosses:
        for buff, providers in buff_providers.items():
            if providers:
                m.buff_cov.add(sum(m.C[p, j] for p in providers) >= 1)

    # Role composition per boss
    m.roles = ConstraintList()
    for j, n_h in zip(bosses, n_heals_list):
        n_dps = cfg.raid_size - cfg.n_tanks - n_h
        for role, n_req in [("Tank", cfg.n_tanks), ("Heal", n_h), ("DPS", n_dps)]:
            provs = role_providers.get(role, [])
            if provs:
                m.roles.add(sum(m.C[p, j] for p in provs) == n_req)

    # Force-IN restrictions
    valid_keys   = set(player_keys)
    valid_bosses = set(bosses)
    m.fixed_in = ConstraintList()
    for pk, boss in restrictions_in:
        if pk in valid_keys and boss in valid_bosses:
            m.fixed_in.add(m.C[pk, boss] == 1)

    # Force-OUT restrictions
    m.fixed_out = ConstraintList()
    for pk, boss in restrictions_out:
        if pk in valid_keys and boss in valid_bosses:
            m.fixed_out.add(m.C[pk, boss] == 0)

    # Minimum vault per non-excluded player
    non_excl = [pk for pk in player_keys if pk not in cfg.excluded_players]
    excl     = [pk for pk in cfg.excluded_players if pk in valid_keys]
    if non_excl and cfg.min_vault > 0:
        m.vault_min = Constraint(
            non_excl,
            rule=lambda md, pk: md.vault[pk] >= cfg.min_vault,
        )
    if excl:
        m.vault_none = Constraint(
            excl,
            rule=lambda md, pk: md.vault[pk] <= 0,
        )

    # Objective: maximise sum of vault slots
    m.obj = Objective(expr=sum(m.vault[pk] for pk in player_keys), sense=maximize)

    # ── Solve ─────────────────────────────────────────────────────────────────
    solver = SolverFactory("glpk")
    if not solver.available():
        raise RuntimeError(
            "GLPK solver executable not found.\n"
            "Install with:  conda install -c conda-forge glpk\n"
            "or download from https://winglpk.sourceforge.net/ (Windows)"
        )

    result = solver.solve(m, tee=False)

    if (
        result.solver.status == SolverStatus.ok
        and result.solver.termination_condition == TerminationCondition.optimal
    ):
        return {
            j: [pk for pk in player_keys if value(m.C[pk, j]) > 0.5]
            for j in bosses
        }

    return None
