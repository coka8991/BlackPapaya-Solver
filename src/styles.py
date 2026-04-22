"""
styles.py — Hoja de estilos CSS para WoW Raid Roster TUI
"""

CSS = """
Screen {
    background: #0a0a12;
}

Header {
    background: #1a0a2e;
    color: #c69b3a;
    text-style: bold;
}

Footer {
    background: #0d0d1a;
    color: #555577;
}

/* Tabs */
TabbedContent {
    height: 1fr;
}

TabPane {
    padding: 1 2;
}

/* Boss roster cards */
#roster-grid {
    layout: grid;
    grid-size: 2;
    grid-gutter: 1 2;
    height: auto;
}

.boss-card {
    border: solid #2a2a4a;
    background: #0f0f1e;
    padding: 1;
    height: auto;
    min-height: 12;
}

.boss-header {
    background: #1a1a3a;
    color: #c69b3a;
    text-style: bold;
    padding: 0 1;
    margin-bottom: 1;
}

/* Players panel */
#players-table {
    height: 1fr;
    border: solid #2a2a4a;
    background: #0f0f1e;
}

/* Bosses panel */
#bosses-list {
    height: 1fr;
    border: solid #2a2a4a;
    background: #0f0f1e;
}

#bosses-controls {
    height: auto;
    padding: 1 0;
}

/* Restricciones */
#restrictions-table {
    height: 1fr;
    border: solid #2a2a4a;
    background: #0f0f1e;
}

#restrictions-controls {
    height: auto;
    padding: 1 0;
}

/* Sidebar */
#sidebar {
    width: 30;
    border: solid #2a2a4a;
    background: #0f0f1e;
    padding: 1;
}

#sidebar-title {
    color: #c69b3a;
    text-style: bold;
    text-align: center;
    padding-bottom: 1;
    border-bottom: solid #2a2a4a;
    margin-bottom: 1;
}

.stat-label {
    color: #888899;
}

.stat-value {
    color: #aad372;
    text-align: right;
}

/* Modales */
ModalScreen {
    align: center middle;
    background: rgba(0,0,0,0.7);
}

#modal-box {
    background: #12122a;
    border: double #3a3a6a;
    padding: 2 3;
    width: 60;
    height: auto;
}

#modal-box.wide {
    width: 70;
    max-height: 40;
}

#modal-title {
    color: #c69b3a;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

#modal-buttons {
    margin-top: 1;
    align: center middle;
    height: auto;
}

#modal-buttons Button {
    margin: 0 1;
}

Input {
    background: #1a1a35;
    border: solid #3a3a6a;
    color: #ccccdd;
    margin-bottom: 1;
}

Input:focus {
    border: solid #c69b3a;
}

Select {
    background: #1a1a35;
    border: solid #3a3a6a;
    color: #ccccdd;
    margin-bottom: 1;
}

Button.assign-btn {
    width: 1fr;
    margin: 0 0 0 0;
    background: #1a1a35;
    color: #888899;
    border: none;
}

Button.assign-btn.assigned {
    background: #1a3a1a;
    color: #aad372;
}

Button.assign-btn:hover {
    background: #2a2a55;
}

Button.-primary {
    background: #2a4a2a;
    color: #aad372;
    border: solid #aad372;
}

Button.-primary:hover {
    background: #3a6a3a;
}

#assign-list {
    height: 20;
    border: solid #2a2a4a;
    padding: 0;
}

/* Stats sidebar specific */
.stat-row {
    layout: horizontal;
    height: auto;
    margin-bottom: 0;
}

DataTable {
    background: #0f0f1e;
    color: #ccccdd;
}

DataTable > .datatable--header {
    background: #1a1a3a;
    color: #c69b3a;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #2a2a4a;
}

DataTable > .datatable--row-hover {
    background: #1a1a30;
}

ListItem {
    background: #0f0f1e;
    padding: 0 1;
}

ListItem:hover {
    background: #1a1a30;
}

ListView:focus > ListItem.--highlight {
    background: #2a2a4a;
}

.section-title {
    color: #c69b3a;
    text-style: bold;
    border-bottom: solid #2a2a4a;
    margin-bottom: 1;
    padding-bottom: 0;
}

.help-text {
    color: #555577;
    text-style: italic;
}

/* Scrollable roster */
#roster-scroll {
    height: 1fr;
}
"""
