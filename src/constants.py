"""
constants.py — Paleta de colores, iconos y mapas de rol para WoW Raid Roster TUI
"""

CLASS_COLORS: dict[str, str] = {
    "Death Knight": "#C41E3A",
    "Demon Hunter": "#A330C9",
    "Druid":        "#FF7C0A",
    "Evoker":       "#33937F",
    "Hunter":       "#AAD372",
    "Mage":         "#3FC7EB",
    "Monk":         "#00FF98",
    "Paladin":      "#F48CBA",
    "Priest":       "#FFFFFF",
    "Rogue":        "#FFF468",
    "Shaman":       "#0070DD",
    "Warlock":      "#8788EE",
    "Warrior":      "#C69B3A",
    "Unknown":      "#888888",
}

ROLE_ICON: dict[str, str] = {
    "Tank":   "🛡",
    "Heal":   "💚",
    "Melee":  "⚔",
    "Ranged": "🏹",
    "DPS":    "⚔",
}

BOSS_ICONS: list[str] = ["🐉", "💀", "☠", "👹", "🔥", "🌑", "⚡", "🌊", "🐍", "🦂"]
