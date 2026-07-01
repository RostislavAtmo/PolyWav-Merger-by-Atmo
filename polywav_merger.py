"""
PolyWav Merger 4.0.1-beta
Recorder + TX Conform Tool
Modern neumorphic UI — PySide6
"""

import sys
import os
import re
import math
import struct
import queue
import threading
import datetime
import subprocess
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import numpy as np
except ImportError:
    np = None

try:
    import soundfile as sf
except Exception:  # pragma: no cover - optional dependency
    sf = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency
    sd = None

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, QFileDialog,
    QFrame, QScrollArea, QSizePolicy, QProgressBar, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
    QCheckBox, QMenu, QGridLayout, QTabWidget, QSplitter, QAbstractItemView,
    QSlider, QScrollBar, QToolButton, QWidgetAction
)
from PySide6.QtCore import (
    Qt, QSize, Signal, QThread, QObject, QTimer, QRect, QRectF, QPoint,
    QSettings, QUrl, QEvent, QPropertyAnimation, QEasingCurve, QVariantAnimation
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath,
    QBrush, QPen, QLinearGradient, QIcon, QPixmap, QImage, QPalette,
    QKeySequence, QShortcut, QRegion
)

# ── Hide console on Windows ───────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

def resource_path(filename):
    for base in [
        getattr(sys, "_MEIPASS", None),
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]:
        if not base:
            continue
        path = os.path.join(base, filename)
        if os.path.exists(path):
            return path
    return None

# ══════════════════════════════════════════════════════════════════
# PALETTE / THEMES
# ══════════════════════════════════════════════════════════════════
# Scalar hex keys are used both in QSS (build_stylesheet) and in custom
# paintEvent code. Tuple keys (neu_shadow / neu_edge / card_edge) are only
# consumed by paint code via QColor(*value) and never referenced in QSS.
# Shared accent ids (mono = classic white CTA on dark, neutral gray on light).
ACCENT_IDS = ("blue", "green", "yellow", "orange", "red", "purple", "mono")

# Neumorphic surface geometry — Apple/Linear-tight radii, softer depth.
CARD_PAINT_RADIUS = 16.0
CARD_PAINT_MARGIN = 8.0

THEMES = {
    "dark": {
        "bg":           "#121214",
        "card":         "#1c1c20",
        "card_light":   "#242428",
        "card_inset":   "#161618",
        "shadow_dark":  "#08080a",
        "shadow_light": "#2c2c32",
        "highlight":    "#34343c",
        "text":         "#f5f5f7",
        "text_secondary": "#a1a1aa",
        "text_muted":   "#6b6b76",
        "accent":       "#5B9AFF",
        "border":       "#2a2a30",
        "success":      "#4D9FFF",
        "error":        "#f87171",
        "warning":      "#f59e0b",
        "notice":       "#38bdf8",
        # paint-only extras (preserve the existing dark look)
        "card_grad_bottom": "#1e1e22",
        "neu_shadow":   (6, 6, 10),
        "neu_edge":     (72, 72, 82),
        "card_edge":    (255, 255, 255, 18),
        "accent_hover": "#78ADFF",
        "on_accent":    "#101218",
        "prog_a":       "#7BB0FF",
        "prog_b":       "#5B9AFF",
        "prog_c":       "#3D7AD9",
    },
    "light": {
        "bg":           "#f4f5f7",
        "card":         "#ffffff",
        "card_light":   "#ffffff",
        "card_inset":   "#eceef2",
        "shadow_dark":  "#c8ccd4",
        "shadow_light": "#ffffff",
        "highlight":    "#b4bcc8",
        "text":         "#18181b",
        "text_secondary": "#52525b",
        "text_muted":   "#71717a",
        "accent":       "#7EB0FF",
        "border":       "#d8dce3",
        "success":      "#34C759",
        "error":        "#dc2626",
        "warning":      "#d97706",
        "notice":       "#0ea5e9",
        "card_grad_bottom": "#f0f1f4",
        "neu_shadow":   (160, 168, 184),
        "neu_edge":     (255, 255, 255),
        "card_edge":    (0, 0, 0, 14),
        "accent_hover": "#69A3FF",
        "on_accent":    "#152238",
        "prog_a":       "#A8C8FF",
        "prog_b":       "#7EB0FF",
        "prog_c":       "#5A94F5",
    },
}

# Dark-theme accent presets — luminous candy colours tuned for dark surfaces.
DARK_ACCENTS = {
    "blue": {
        "accent": "#5B9AFF", "accent_hover": "#78ADFF", "on_accent": "#101218",
        "success": "#34C759", "notice": "#38BDF8",
        "prog_a": "#7BB0FF", "prog_b": "#5B9AFF", "prog_c": "#3D7AD9",
    },
    "green": {
        "accent": "#6FD84A", "accent_hover": "#86E866", "on_accent": "#101810",
        "success": "#5FD050", "notice": "#4BC943",
        "prog_a": "#9AE878", "prog_b": "#6FD84A", "prog_c": "#4AAF32",
    },
    "yellow": {
        "accent": "#FFD633", "accent_hover": "#FFE566", "on_accent": "#1a1810",
        "success": "#E6C200", "notice": "#D4AF00",
        "prog_a": "#FFE566", "prog_b": "#FFD633", "prog_c": "#C9AA00",
    },
    "orange": {
        "accent": "#FF9740", "accent_hover": "#FFAD66", "on_accent": "#1a1208",
        "success": "#F5821F", "notice": "#E86A00",
        "prog_a": "#FFAD66", "prog_b": "#FF9740", "prog_c": "#CC6510",
    },
    "red": {
        "accent": "#FF4D5C", "accent_hover": "#FF6673", "on_accent": "#1a0c0e",
        "success": "#E82233", "notice": "#D41828",
        "prog_a": "#FF6673", "prog_b": "#FF4D5C", "prog_c": "#B81825",
    },
    "purple": {
        "accent": "#A978C8", "accent_hover": "#BE8FDB", "on_accent": "#140f1a",
        "success": "#9354B8", "notice": "#7B3FA0",
        "prog_a": "#BE8FDB", "prog_b": "#A978C8", "prog_c": "#5E2F7A",
    },
    "mono": {
        "accent": "#F2F2F5", "accent_hover": "#FFFFFF", "on_accent": "#1a1a1e",
        "success": "#60a5fa", "notice": "#38bdf8",
        "prog_a": "#FFFFFF", "prog_b": "#F3F3F8", "prog_c": "#D6D6E0",
    },
}

# Light-theme accents — saturated but soft; chip borders unchanged in AccentSwatchButton.
LIGHT_ACCENTS = {
    "blue": {
        "accent": "#7EB0FF", "accent_hover": "#69A3FF", "on_accent": "#152238",
        "success": "#34C759", "notice": "#0ea5e9",
        "prog_a": "#A8C8FF", "prog_b": "#7EB0FF", "prog_c": "#5A94F5",
    },
    "green": {
        "accent": "#7DDF75", "accent_hover": "#6AD662", "on_accent": "#142016",
        "success": "#4CAF50", "notice": "#43A047",
        "prog_a": "#A8EBA5", "prog_b": "#7DDF75", "prog_c": "#52C44A",
    },
    "yellow": {
        "accent": "#FFE34D", "accent_hover": "#FFDB33", "on_accent": "#1a1810",
        "success": "#E6C200", "notice": "#D4AF00",
        "prog_a": "#FFF099", "prog_b": "#FFE34D", "prog_c": "#E6C84A",
    },
    "orange": {
        "accent": "#FFAB52", "accent_hover": "#FF9E38", "on_accent": "#1a1208",
        "success": "#F5821F", "notice": "#E86A00",
        "prog_a": "#FFC894", "prog_b": "#FFAB52", "prog_c": "#E8924A",
    },
    "red": {
        "accent": "#FF7A88", "accent_hover": "#FF6673", "on_accent": "#1a0c0e",
        "success": "#E82233", "notice": "#D41828",
        "prog_a": "#FFA8B0", "prog_b": "#FF7A88", "prog_c": "#E85563",
    },
    "purple": {
        "accent": "#C49AE0", "accent_hover": "#B888D8", "on_accent": "#140f1a",
        "success": "#9354B8", "notice": "#7B3FA0",
        "prog_a": "#DDB8F0", "prog_b": "#C49AE0", "prog_c": "#A070C8",
    },
    "mono": {
        "accent": "#8A8F99", "accent_hover": "#767C87", "on_accent": "#FFFFFF",
        "success": "#4CAF50", "notice": "#0ea5e9",
        "prog_a": "#A7ADB8", "prog_b": "#8A8F99", "prog_c": "#6B7079",
    },
}

# Active palette. Mutated in place by apply_theme so every paintEvent that
# reads COLORS["..."] picks up the new value on the next repaint.
COLORS = dict(THEMES["dark"])


# ══════════════════════════════════════════════════════════════════
# SETTINGS (QSettings — theme, pinned/last folders, last tab)
# ══════════════════════════════════════════════════════════════════
def _settings():
    return QSettings("PolyWavMerger", "PolyWav Merger")

def load_setting(key, default=None):
    val = _settings().value(key, default)
    return val if val is not None else default

def save_setting(key, value):
    _settings().setValue(key, value)

def load_string_list(key):
    """Return a list[str] from QSettings (handles single-value coercion)."""
    val = _settings().value(key, [])
    if val is None:
        return []
    if isinstance(val, str):
        return [val] if val else []
    try:
        return [str(x) for x in val]
    except TypeError:
        return []


# ══════════════════════════════════════════════════════════════════
# THEME MANAGER (live light/dark switching)
# ══════════════════════════════════════════════════════════════════
class _ThemeManager(QObject):
    changed = Signal(str)   # theme name

THEME = _ThemeManager()

def current_theme_name():
    return "light" if COLORS.get("bg") == THEMES["light"]["bg"] else "dark"

def current_light_accent():
    aid = load_setting("light_accent", "blue")
    return aid if aid in LIGHT_ACCENTS else "blue"

def current_dark_accent():
    aid = load_setting("dark_accent", "blue")
    return aid if aid in DARK_ACCENTS else "blue"

def current_accent():
    return (current_light_accent() if current_theme_name() == "light"
            else current_dark_accent())

def accent_presets():
    return LIGHT_ACCENTS if current_theme_name() == "light" else DARK_ACCENTS

def _accent_rgba(alpha=0.20):
    c = QColor(COLORS["accent"])
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"

def _accent_blend(strength=0.22):
    """Solid tint for selections — rgba() is unreliable in Qt table styles."""
    a = QColor(COLORS["accent"])
    base_key = "card_inset" if current_theme_name() == "light" else "card"
    b = QColor(COLORS[base_key])
    t = max(0.0, min(1.0, strength))
    return QColor(
        int(a.red() * t + b.red() * (1 - t)),
        int(a.green() * t + b.green() * (1 - t)),
        int(a.blue() * t + b.blue() * (1 - t)),
    )

def _selection_colors():
    light = current_theme_name() == "light"
    bg = _accent_blend(0.30 if light else 0.34)
    return bg.name(), COLORS["text"]

def _mono_stack():
    return "Consolas, 'JetBrains Mono', 'SF Mono', monospace"

def _mono_font(point_size=None):
    """Tabular-aligned monospace font for numeric table cells."""
    f = QFont("Consolas")
    f.setStyleHint(QFont.Monospace)
    if point_size:
        f.setPointSize(point_size)
    try:
        f.setStyleStrategy(QFont.PreferQuality)
    except Exception:
        pass
    return f

def _repaint_themed_widgets():
    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(build_stylesheet())
    for w in app.allWidgets():
        fn = getattr(w, "_apply_theme", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
        w.update()

def apply_light_accent(accent_id):
    """Swap the light-theme accent palette (saved + live if light is active)."""
    if accent_id not in LIGHT_ACCENTS:
        accent_id = "blue"
    save_setting("light_accent", accent_id)
    if current_theme_name() != "light":
        return
    COLORS.update(LIGHT_ACCENTS[accent_id])
    _repaint_themed_widgets()
    THEME.changed.emit("light")

def apply_dark_accent(accent_id):
    """Swap the dark-theme accent palette (saved + live if dark is active)."""
    if accent_id not in DARK_ACCENTS:
        accent_id = "blue"
    save_setting("dark_accent", accent_id)
    if current_theme_name() != "dark":
        return
    COLORS.update(DARK_ACCENTS[accent_id])
    _repaint_themed_widgets()
    THEME.changed.emit("dark")

def apply_accent(accent_id):
    """Persist and apply an accent for the active theme."""
    if current_theme_name() == "light":
        apply_light_accent(accent_id)
    else:
        apply_dark_accent(accent_id)

def apply_theme(name):
    """Switch the active palette in place and repaint the whole app live."""
    if name not in THEMES:
        return
    COLORS.clear()
    COLORS.update(THEMES[name])
    if name == "light":
        COLORS.update(LIGHT_ACCENTS[current_light_accent()])
    else:
        COLORS.update(DARK_ACCENTS[current_dark_accent()])
    _repaint_themed_widgets()
    save_setting("theme", name)
    THEME.changed.emit(name)


def build_stylesheet():
    sel_bg = _accent_rgba(0.18 if current_theme_name() == "dark" else 0.14)
    mono = _mono_stack()
    return f"""
QMainWindow, QWidget#rootWidget, QWidget#appHeader, QWidget#scrollContent {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
}}
QWidget {{
    color: {COLORS['text']};
}}
QLabel {{
    background: transparent;
    border: none;
}}
QComboBox {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: {COLORS['text']};
    min-height: 24px;
}}
QComboBox:hover {{ border-color: {COLORS['highlight']}; }}
QComboBox::drop-down {{ border: none; width: 32px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 12px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
    padding: 8px;
    selection-background-color: {COLORS['card_inset']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 10px 16px;
    border-radius: 8px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {COLORS['card_inset']};
}}
QLineEdit {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 13px;
    color: {COLORS['text']};
    min-height: 24px;
}}
QLineEdit:hover {{ border-color: {COLORS['highlight']}; }}
QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
QComboBox:focus {{ border-color: {COLORS['accent']}; }}
QTextEdit#cardNotesEdit:focus {{
    border-color: {COLORS['accent']};
}}
QTextEdit {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 12px;
    font-family: {mono};
    color: {COLORS['text_secondary']};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px;
    border-radius: 4px; margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['shadow_light']};
    border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {COLORS['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QProgressBar {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    height: 12px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0    {COLORS['prog_a']},
        stop: 0.5  {COLORS['prog_b']},
        stop: 1    {COLORS['prog_c']}
    );
    border-radius: 6px;
    margin: 1px;
}}
NeumorphicCard, FolderSelector, LogoWidget, PrimaryButton {{
    background: transparent;
    border: none;
}}
QPushButton {{
    background: transparent;
    border: none;
}}
QScrollArea {{
    background-color: {COLORS['bg']};
}}

/* ── Folder picker (non-native QFileDialog) ───────────────────────
   The global "QWidget {{ color: text }}" rule sets a white text color
   but leaves background to the system. On Win11 light theme the file
   list area uses the system light background, so we get white-on-white.
   Style every QFileDialog child explicitly. */
QFileDialog {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
}}
QFileDialog QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
}}
QFileDialog QFrame {{
    background-color: {COLORS['bg']};
    border: none;
}}
QFileDialog QListView,
QFileDialog QTreeView,
QFileDialog QColumnView {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    alternate-background-color: {COLORS['card']};
    selection-background-color: {COLORS['highlight']};
    selection-color: {COLORS['text']};
}}
QFileDialog QListView::item:hover,
QFileDialog QTreeView::item:hover {{
    background-color: {COLORS['card_light']};
}}
QFileDialog QListView::item,
QFileDialog QTreeView::item {{
    min-height: 28px;
    padding: 4px 8px;
}}
QFileDialog QListView::item:selected,
QFileDialog QTreeView::item:selected {{
    background-color: {COLORS['highlight']};
    color: {COLORS['text']};
}}
QFileDialog QHeaderView::section {{
    background-color: {COLORS['card']};
    color: {COLORS['text_secondary']};
    border: none;
    padding: 6px 10px;
    font-weight: 500;
}}
QFileDialog QLineEdit {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 7px 10px;
    min-height: 26px;
    selection-background-color: {COLORS['highlight']};
}}
QFileDialog QComboBox {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 26px;
}}
QFileDialog QComboBox QAbstractItemView {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['highlight']};
}}
QFileDialog QPushButton {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 60px;
    min-height: 26px;
}}
QFileDialog QPushButton:hover {{
    background-color: {COLORS['card_light']};
    border-color: {COLORS['highlight']};
}}
QFileDialog QPushButton:pressed {{
    background-color: {COLORS['shadow_dark']};
}}
QFileDialog QPushButton:default {{
    background-color: {COLORS['accent']};
    color: {COLORS['on_accent']};
    border-color: {COLORS['accent']};
}}
QFileDialog QToolButton {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 24px;
}}
QFileDialog QToolButton:hover {{
    background-color: {COLORS['card_light']};
    border-color: {COLORS['highlight']};
}}
QFileDialog QLabel {{
    color: {COLORS['text']};
    background: transparent;
    border: none;
}}
QFileDialog QSplitter::handle {{
    background-color: {COLORS['border']};
}}
QFileDialog QScrollBar:vertical, QFileDialog QScrollBar:horizontal {{
    background: {COLORS['card_inset']};
    border: none;
}}

/* ── Tabs ─────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 11px;
    padding: 9px 22px;
    margin-right: 6px;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['card_light']};
    color: {COLORS['text']};
    border-color: {COLORS['highlight']};
}}
QTabBar::tab:hover {{ color: {COLORS['text']}; }}

/* ── Theme toggle (tab-bar corner) ────────────────────────────── */
QPushButton#themeToggle {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#themeToggle:hover {{
    border-color: {COLORS['highlight']};
    color: {COLORS['text']};
}}

/* ── Audio detail window (waveforms + mixer) ──────────────────── */
QSlider::groove:horizontal {{
    height: 4px; background: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']}; border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    height: 4px; background: {COLORS['accent']}; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 13px; height: 13px; margin: -6px 0; border-radius: 7px;
    background: {COLORS['accent']}; border: 1px solid {COLORS['shadow_dark']};
}}
QSlider::handle:horizontal:hover {{ background: {COLORS['accent_hover']}; }}
QPushButton#miniToggle {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    padding: 0px;
    font-size: 11px; font-weight: 700;
    min-width: 24px; max-width: 24px;
    min-height: 20px; max-height: 20px;
}}
QPushButton#miniToggle:hover {{ border-color: {COLORS['highlight']}; color: {COLORS['text']}; }}
QPushButton#saveNoteBtn {{
    background-color: {COLORS['accent']}; color: {COLORS['on_accent']};
    border: none; border-radius: 9px;
    padding: 7px 18px; font-size: 12px; font-weight: 600;
}}
QPushButton#saveNoteBtn:hover {{ background-color: {COLORS['accent_hover']}; }}
QPushButton#saveNoteBtn:disabled {{
    background-color: {COLORS['card_inset']}; color: {COLORS['text_muted']};
}}
QFrame#insetPanel {{
    background-color: {COLORS['card_inset']};
    border: none;
}}
QTextEdit#cardNotesEdit {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 10px 12px 10px 14px;
    font-size: 12px;
    color: {COLORS['text']};
}}
QPushButton#miniToggle[role="solo"]:checked {{
    background-color: {COLORS['warning']}; color: {COLORS['on_accent']};
    border-color: {COLORS['warning']};
}}
QPushButton#miniToggle[role="mute"]:checked {{
    background-color: {COLORS['error']}; color: {COLORS['on_accent']};
    border-color: {COLORS['error']};
}}
QPushButton#transportBtn {{
    background-color: {COLORS['accent']}; color: {COLORS['on_accent']};
    border: none; border-radius: 10px; padding: 9px 18px;
    font-size: 13px; font-weight: 600;
}}
QPushButton#transportBtn:hover {{ background-color: {COLORS['accent_hover']}; }}
QPushButton#transportBtn:disabled {{ background-color: {COLORS['card_inset']}; color: {COLORS['text_muted']}; }}
QPushButton#ghostBtn {{
    background-color: {COLORS['card_inset']}; color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']}; border-radius: 9px;
    padding: 8px 14px; font-size: 12px; font-weight: 500;
}}
QPushButton#ghostBtn:hover {{
    border-color: {COLORS['accent']};
    color: {COLORS['text']};
}}
QPushButton#ghostBtn:disabled {{ color: {COLORS['text_muted']}; }}
QScrollBar:horizontal {{
    background: transparent; height: 12px; border-radius: 6px; margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['shadow_light']}; border-radius: 5px; min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{ background: {COLORS['highlight']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* ── Audio detail window tabs ─────────────────────────────────── */
QTabWidget#detailTabs::pane {{
    border: none; background: transparent; top: -1px;
}}
QTabWidget#detailTabs QTabBar::tab {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 9px;
    padding: 7px 18px;
    margin-right: 5px;
    font-size: 12px; font-weight: 500;
}}
QTabWidget#detailTabs QTabBar::tab:selected {{
    background-color: {COLORS['card_light']};
    color: {COLORS['text']};
    border-color: {COLORS['highlight']};
}}
QTabWidget#detailTabs QTabBar::tab:hover {{ color: {COLORS['text']}; }}
"""

STYLESHEET = build_stylesheet()

# ══════════════════════════════════════════════════════════════════
# GPU ACCELERATION SUPPORT
# ══════════════════════════════════════════════════════════════════

def _detect_gpu_acceleration():
    """
    Detect available GPU acceleration:
    - CUDA (NVIDIA): cupy package
    - Metal (Apple Silicon): numpy with Metal acceleration
    - ROCm (AMD): rocm package
    - None: fallback to CPU
    """
    gpu_info = {"cuda": False, "metal": False, "rocm": False}
    
    # Try CUDA (NVIDIA)
    try:
        import cupy as cp
        if cp.cuda.is_available():
            gpu_info["cuda"] = True
            return gpu_info
    except (ImportError, AttributeError):
        pass
    
    # Try ROCm (AMD)
    try:
        import cupy as cp
        if hasattr(cp, 'rocm'):
            gpu_info["rocm"] = True
            return gpu_info
    except (ImportError, AttributeError):
        pass
    
    # Metal (Apple Silicon) - built-in numpy acceleration
    try:
        import numpy as np
        if sys.platform == "darwin":
            gpu_info["metal"] = True  # Metal acceleration via numpy
    except ImportError:
        pass
    
    return gpu_info

def _correlate_gpu(ref, tx, gpu_info, sample_rate, max_lag_sec=1.5):
    """
    FFT-based cross-correlation of tx against ref. Returns (lag_sec, score) or None.

    Convention: lag_sec > 0 means tx is delayed relative to ref by that many
    seconds — i.e. to align identical content, advance the tx extraction
    position by lag_sec.

    Inputs should be unit-energy normalized for the score to be in [-1, 1].

    GPU (cupy / CUDA / ROCm) is used when available; otherwise FFT runs on
    numpy. On Apple Silicon numpy uses the Accelerate framework so the CPU
    FFT path is already vectorized — no separate Metal branch is needed.
    """
    if np is None:
        return None
    if not len(ref) or not len(tx):
        return None

    n_max = max(len(ref), len(tx))
    if n_max < int(0.5 * sample_rate):
        return None

    max_lag = int(max_lag_sec * sample_rate)
    if max_lag <= 0:
        return None

    # Zero-pad to next power of 2 of (2 * n_max) so the FFT result is a
    # proper *linear* cross-correlation, not a circular one.
    L = 1
    while L < 2 * n_max:
        L *= 2

    full_np = None

    # Try GPU (cupy: CUDA / ROCm)
    if gpu_info.get("cuda") or gpu_info.get("rocm"):
        try:
            import cupy as cp
            tx_gpu = cp.asarray(tx, dtype=cp.float64)
            ref_gpu = cp.asarray(ref, dtype=cp.float64)
            fft_tx = cp.fft.rfft(tx_gpu, L)
            fft_ref = cp.fft.rfft(ref_gpu, L)
            # corr(tx, ref) so the peak sits at +D when tx is delayed by D
            full = cp.fft.irfft(fft_tx * cp.conj(fft_ref), L)
            full_np = cp.asnumpy(full)
        except Exception:
            full_np = None

    # CPU FFT fallback (also covers Apple Silicon via Accelerate)
    if full_np is None:
        try:
            tx_arr = np.asarray(tx, dtype=np.float64)
            ref_arr = np.asarray(ref, dtype=np.float64)
            fft_tx = np.fft.rfft(tx_arr, L)
            fft_ref = np.fft.rfft(ref_arr, L)
            full_np = np.fft.irfft(fft_tx * np.conj(fft_ref), L)
        except Exception:
            return None

    # In FFT-result indexing: index k corresponds to lag k (mod L). So
    # negative lags wrap to high indices via Python's modulo.
    best_lag = 0
    best_score = -float('inf')
    for lag in range(-max_lag, max_lag + 1):
        idx = lag % L
        score = float(full_np[idx])
        if score > best_score:
            best_score = score
            best_lag = lag

    return best_lag / float(sample_rate), best_score

_GPU_INFO = _detect_gpu_acceleration()

# ══════════════════════════════════════════════════════════════════
# TX PROFILE & RECORDER CONFIGURATIONS
# ══════════════════════════════════════════════════════════════════

def _smart_chan_idx(name):
    """
    Robust channel-index extraction for arbitrary TX naming conventions.

    Strategy (in order):
      1. L<n> / LAV<n> / LV<n> token surrounded by non-letters or string
         boundary — handles "L1", "LAV4", "MTP61_L1" -> 1, "ZOOM_L2_TAKE_3" -> 2.
      2. Last contiguous digit group — handles "TX_001" -> 1, "Channel_3" -> 3.
      3. 99 — purely alphabetical names ("TX_SASHA") sink to the bottom and
         get tie-broken alphabetically by the sort key.
    """
    n = str(name).upper()
    m = re.search(r"(?<![A-Z])L(?:A?V)?(\d+)(?![A-Z])", n)
    if m:
        return int(m.group(1))
    digits = re.findall(r"\d+", n)
    if digits:
        return int(digits[-1])
    return 99

def _smart_track_name(name, prefix=None):
    """Readable track name for arbitrary TX file names.

    Strips a leading "TX_" / "MIC_" so "TX_SASHA" reads as "SASHA". Keeps the
    rest of the name (capped to 16 chars) so the user still recognizes which
    transmitter the track came from in their DAW.
    """
    cleaned = re.sub(r"^(tx|mic)[_-]+", "", str(name), flags=re.IGNORECASE)
    cleaned = cleaned[:16] if cleaned else (str(name)[:16] or "TX")
    if prefix:
        idx = _smart_chan_idx(name)
        if idx != 99:
            return f"{prefix}_{idx}"
        return f"{prefix}_{cleaned}"
    return cleaned

def _clean_tx_prefix(prefix):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(prefix or "TX")).strip("_")
    return cleaned or "TX"

def _prefixed_tx_track_name(name, prefix="TX"):
    """Profile-independent TX track name for final iXML channel labels."""
    clean_prefix = _clean_tx_prefix(prefix)
    label = _tx_group_label(name)
    suffix = re.sub(r"^(tx|mic)[_-]+", "", str(label), flags=re.IGNORECASE)
    suffix = re.sub(r"[^A-Za-z0-9]+", "_", suffix).strip("_")
    if not suffix or suffix.lower() == clean_prefix.lower():
        return clean_prefix[:32]
    return f"{clean_prefix}_{suffix}"[:32]

def _is_boom_mic(*names):
    """Return True if any of the given names looks like a boom/overhead mic.

    Matches "BM", "BOOM", "BOOMPOLE", "BP" as letter-only words inside the
    name (so "BM_002", "TX_BOOM_01", "boompole" all hit; "lavbm01" does not).
    """
    boom_words = {"bm", "boom", "boompole", "bp"}
    for n in names:
        if not n:
            continue
        for w in re.findall(r"[a-z]+", str(n).lower()):
            if w in boom_words:
                return True
    return False

def get_tx_info(basename: str, profile_name: str, track_prefix="TX") -> dict:
    """Resolve profile-independent track name + sort index for a TX file."""
    name = os.path.splitext(basename)[0]

    return {
        "name":     _prefixed_tx_track_name(name, track_prefix),
        "chan_idx": _smart_chan_idx(name),
    }

# ══════════════════════════════════════════════════════════════════
# WAV BINARY HELPERS
# ══════════════════════════════════════════════════════════════════

def read_riff_chunks(data: bytes) -> list:
    chunks, pos = [], 12
    while pos < len(data) - 8:
        cid = data[pos:pos+4].decode("latin-1")
        csz = struct.unpack_from("<I", data, pos+4)[0]
        chunks.append({"id": cid, "offset": pos,
                       "size": csz, "data_offset": pos+8})
        if cid == "data": break
        pos += 8 + csz + (csz % 2)
    return chunks

def read_header(path, max_bytes=204800):
    with open(path, "rb") as f:
        return f.read(min(max_bytes, os.path.getsize(path)))

def parse_fmt(data, chunks):
    c = next((x for x in chunks if x["id"] == "fmt "), None)
    if not c: return None
    d = c["data_offset"]
    return {"channels":    struct.unpack_from("<H", data, d+2)[0],
            "sample_rate": struct.unpack_from("<I", data, d+4)[0],
            "bps":         struct.unpack_from("<H", data, d+14)[0]}

def parse_bext(data, chunks):
    c = next((x for x in chunks if x["id"] == "bext"), None)
    if not c: return None
    d = c["data_offset"]
    tref = struct.unpack_from("<Q", data, d+338)[0]
    cl   = max(0, min(256, c["size"] - 602))
    cod  = data[d+602:d+602+cl].rstrip(b"\x00\r\n").decode("latin-1", "replace")
    return {"time_ref": tref, "coding": cod}

def get_chunk_data(data, chunks, cid):
    c = next((x for x in chunks if x["id"] == cid), None)
    if not c: return None
    return data[c["data_offset"]:c["data_offset"] + c["size"]]

def parse_recorder_ixml(data, chunks):
    r = {"full_xml":"","speed_block":"","track_names":[],"scene":"","take":"",
         "file_uid":"","ubits":"","family_uid":"","file_set_idx":"",
         "tape":"","project":"","note":""}
    c = next((x for x in chunks if x["id"] == "iXML"), None)
    if not c: return r
    xml = data[c["data_offset"]:c["data_offset"]+c["size"]]\
               .rstrip(b"\x00").decode("utf-8", "replace")
    r["full_xml"] = xml
    def g(tag):
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", xml)
        return m.group(1).strip() if m else ""
    r["scene"]       = g("SCENE");   r["take"]        = g("TAKE")
    r["file_uid"]    = g("FILE_UID");r["ubits"]       = g("UBITS")
    r["tape"]        = g("TAPE");    r["project"]     = g("PROJECT")
    r["note"]        = g("NOTE");    r["family_uid"]  = g("FAMILY_UID")
    r["file_set_idx"]= g("FILE_SET_INDEX")
    m = re.search(r"<SPEED>(.*?)</SPEED>", xml, re.DOTALL)
    if m: r["speed_block"] = f"<SPEED>{m.group(1)}</SPEED>"
    tracks = {}
    for m in re.finditer(
            r"<TRACK>.*?<INTERLEAVE_INDEX>(\d+)</INTERLEAVE_INDEX>"
            r".*?<NAME>([^<]*)</NAME>.*?</TRACK>", xml, re.DOTALL):
        tracks[int(m.group(1))] = m.group(2).strip()
    r["track_names"] = [tracks[k] for k in sorted(tracks)]
    return r

def find_data_chunk(path):
    with open(path, "rb") as f:
        f.seek(12)
        while True:
            h = f.read(8)
            if len(h) < 8: break
            cid = h[:4].decode("latin-1")
            csz = struct.unpack_from("<I", h, 4)[0]
            if cid == "data": return f.tell(), csz
            f.seek(csz + (csz % 2), 1)
    return 0, 0

def get_peak_db(path, offset_sec, dur_sec):
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"RIFF": return -144.0
            f.read(8)
            sr = ch = bps = 0; is_float = False; data_offset = data_size = 0
            while True:
                h = f.read(8)
                if len(h) < 8: break
                cid = h[:4].decode("latin-1")
                csz = struct.unpack_from("<I", h, 4)[0]
                if cid == "fmt ":
                    fb = f.read(csz); tag = struct.unpack_from("<H",fb,0)[0]
                    ch  = struct.unpack_from("<H",fb,2)[0]
                    sr  = struct.unpack_from("<I",fb,4)[0]
                    bps = struct.unpack_from("<H",fb,14)[0]
                    is_float = (tag == 3) or (tag == 0xFFFE and bps == 32)
                    if csz % 2: f.read(1)
                elif cid == "data":
                    data_offset = f.tell(); data_size = csz; break
                else: f.seek(csz + (csz%2), 1)
            if not data_offset or not sr or not ch: return -144.0
            bpf = bps // 8; fsz = ch * bpf
            sp  = data_offset + int(offset_sec * sr) * fsz
            rb  = min(int(dur_sec * sr) * fsz, data_size - (sp - data_offset))
            if rb <= 0: return -144.0
            f.seek(sp); peak = 0.0; remaining = rb
            while remaining > 0:
                buf = f.read(min(4*1024*1024, remaining))
                if not buf: break
                if is_float:
                    for i in range(0, len(buf)-3, fsz):
                        v = abs(struct.unpack_from("<f", buf, i)[0])
                        if v > peak: peak = v
                else:
                    for i in range(0, len(buf)-2, fsz):
                        raw = buf[i]|(buf[i+1]<<8)|(buf[i+2]<<16)
                        if raw >= 8388608: raw -= 16777216
                        v = abs(raw)/8388607.0
                        if v > peak: peak = v
                remaining -= len(buf)
        return -144.0 if peak <= 0 else 20.0*math.log10(peak)
    except: return -144.0

def _xml_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _xml_unescape(s):
    """Reverse of _xml_escape for display (handles the common entities)."""
    return (str(s).replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&apos;", "'")
            .replace("&amp;", "&"))


# ══════════════════════════════════════════════════════════════════
# METADATA READING  (Library browser)
# ══════════════════════════════════════════════════════════════════

def _fps_from_rate(rate_str):
    """Parse an iXML TIMECODE_RATE ('30000/1001', '25/1', '25') to float fps."""
    if not rate_str:
        return None
    try:
        if "/" in rate_str:
            a, b = rate_str.split("/", 1)
            b = float(b)
            return float(a) / b if b else None
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return None


def _parse_speed_fields(xml):
    def g(*tags):
        for tag in tags:
            m = re.search(rf"<{tag}>([^<]*)</{tag}>", xml)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return ""
    return {
        "timecode_rate": g("TIMECODE_RATE"),
        "timecode_flag": g("TIMECODE_FLAG"),
        "timestamp_sr":  g("TIMESTAMP_SAMPLE_RATE_NUMERATOR",
                           "TIMESTAMP_SAMPLE_RATE"),
        "file_sr":       g("FILE_SAMPLE_RATE"),
        "digitizer_sr":  g("DIGITIZER_SAMPLE_RATE"),
        "bit_depth":     g("AUDIO_BIT_DEPTH"),
    }


def _parse_tracks_full(xml):
    """Parse <TRACK> blocks for channel/interleave/name/function."""
    tracks = []
    for m in re.finditer(r"<TRACK>(.*?)</TRACK>", xml, re.DOTALL):
        block = m.group(1)
        def g(tag):
            mm = re.search(rf"<{tag}>([^<]*)</{tag}>", block)
            return mm.group(1).strip() if mm else ""
        ci, ii = g("CHANNEL_INDEX"), g("INTERLEAVE_INDEX")
        nm, fn = g("NAME"), g("FUNCTION")
        if ci or ii or nm:
            tracks.append({"channel": ci or ii, "interleave": ii or ci,
                           "name": nm, "function": fn})
    def key(t):
        try:
            return int(t["interleave"])
        except (TypeError, ValueError):
            return 999
    return sorted(tracks, key=key)


def _samples_to_tc(time_ref, tc_sr, fps):
    """BWF time reference (samples since midnight) → 'HH:MM:SS:FF'."""
    if not tc_sr or tc_sr <= 0:
        return ""
    nominal = int(round(fps)) if fps and fps > 0 else 0
    secs = int(time_ref // tc_sr)
    rem  = time_ref - secs * tc_sr
    hh, mm, ss = secs // 3600, (secs % 3600) // 60, secs % 60
    if nominal:
        ff = int(rem / tc_sr * nominal)
        if ff >= nominal:
            ff = nominal - 1
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def _seconds_to_tc(dur, fps):
    """Duration in seconds → 'HH:MM:SS:FF' (or 'HH:MM:SS' without fps)."""
    if dur < 0:
        dur = 0
    total = int(dur)
    hh, mm, ss = total // 3600, (total % 3600) // 60, total % 60
    nominal = int(round(fps)) if fps and fps > 0 else 0
    if nominal:
        ff = int(round((dur - total) * nominal))
        if ff >= nominal:
            ff = nominal - 1
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def read_audio_metadata(path):
    """Read display metadata for a WAV file (channels, TC, scene/take, tracks…).

    Reuses the existing chunk/bext/iXML parsers. Reads only a header window so
    it stays fast on large poly files."""
    md = {
        "path": path, "name": os.path.basename(path), "error": None,
        "channels": 0, "sample_rate": 0, "bit_depth": 0, "duration_sec": 0.0,
        "start_tc": "", "length_tc": "", "frame_rate": "", "frame_rate_disp": "",
        "scene": "", "take": "", "project": "", "tape": "", "ubits": "",
        "note": "", "time_ref": 0, "tc_sample_rate": 0, "tracks": [],
        "size_bytes": 0,
    }
    try:
        md["size_bytes"] = os.path.getsize(path)
        hdr = read_header(path, 262144)
        if hdr[:4] != b"RIFF" or hdr[8:12] != b"WAVE":
            md["error"] = "Not a WAV file"
            return md
        chunks = read_riff_chunks(hdr)
        fmt = parse_fmt(hdr, chunks)
        if fmt:
            md["channels"]    = fmt["channels"]
            md["sample_rate"] = fmt["sample_rate"]
            md["bit_depth"]   = fmt["bps"]
        bxt = parse_bext(hdr, chunks)
        if bxt:
            md["time_ref"] = bxt["time_ref"]
        ix = parse_recorder_ixml(hdr, chunks)
        sp = {}
        if ix:
            md["scene"]   = _xml_unescape(ix["scene"]);   md["take"] = _xml_unescape(ix["take"])
            md["project"] = _xml_unescape(ix["project"]); md["tape"] = _xml_unescape(ix["tape"])
            md["ubits"]   = _xml_unescape(ix["ubits"]);   md["note"] = _xml_unescape(ix["note"])
            sp = _parse_speed_fields(ix["full_xml"])
            tracks = _parse_tracks_full(ix["full_xml"])
            if not tracks and ix["track_names"]:
                tracks = [{"channel": str(i + 1), "interleave": str(i + 1),
                           "name": n, "function": ""}
                          for i, n in enumerate(ix["track_names"])]
            md["tracks"] = tracks
        # Plain WAV (no iXML track list) — synthesize generic track names.
        if not md["tracks"] and md["channels"]:
            generic = (["MIX"] if md["channels"] == 1 else
                       ["L", "R"] if md["channels"] == 2 else
                       [f"CH{i}" for i in range(1, md["channels"] + 1)])
            md["tracks"] = [{"channel": str(i + 1), "interleave": str(i + 1),
                             "name": n, "function": ""}
                            for i, n in enumerate(generic)]

        dc = next((c for c in chunks if c["id"] == "data"), None)
        data_size = dc["size"] if dc else 0
        frame = (fmt["channels"] * (fmt["bps"] // 8)) if (fmt and fmt["bps"]) else 0
        if frame and fmt["sample_rate"]:
            md["duration_sec"] = (data_size // frame) / float(fmt["sample_rate"])

        fps = _fps_from_rate(sp.get("timecode_rate"))
        md["frame_rate"] = sp.get("timecode_rate", "")
        if fps:
            md["frame_rate_disp"] = (f"{fps:.3f}".rstrip("0").rstrip("."))
            flag = sp.get("timecode_flag", "").upper()
            if flag:
                is_df = ("DF" in flag) and ("ND" not in flag)
                md["frame_rate_disp"] += " DF" if is_df else " ND"
        tc_sr = 0
        ts = sp.get("timestamp_sr")
        if ts:
            try:
                tc_sr = int(float(ts))
            except ValueError:
                tc_sr = 0
        if not tc_sr:
            tc_sr = md["sample_rate"]
        md["tc_sample_rate"] = tc_sr
        if md["time_ref"] and tc_sr:
            md["start_tc"] = _samples_to_tc(
                md["time_ref"], tc_sr, fps or md["sample_rate"])
        md["length_tc"] = _seconds_to_tc(md["duration_sec"], fps)
    except Exception as e:  # noqa: BLE001 — surfaced in the UI
        md["error"] = str(e)
    return md


def _set_ixml_note(xml_bytes, note):
    """Return iXML bytes with <NOTE> replaced/inserted (UTF-8)."""
    xml = xml_bytes.rstrip(b"\x00").decode("utf-8", "replace")
    esc = _xml_escape(note)
    repl = f"<NOTE>{esc}</NOTE>"
    if re.search(r"<NOTE>.*?</NOTE>", xml, re.DOTALL):
        xml = re.sub(r"<NOTE>.*?</NOTE>", lambda _m: repl, xml, count=1, flags=re.DOTALL)
    elif "</BWFXML>" in xml:
        xml = xml.replace("</BWFXML>", f"\t{repl}\r\n</BWFXML>", 1)
    else:
        xml = xml + repl
    return xml.encode("utf-8")


def _set_bext_description(bext_bytes, note):
    """Return bext bytes with the 256-byte Description field set to note."""
    b = bytearray(bext_bytes)
    if len(b) < 256:
        b.extend(b"\x00" * (256 - len(b)))
    desc = note.replace("\r\n", " ").replace("\n", " ").encode("latin-1", "replace")[:256]
    b[0:256] = desc + b"\x00" * (256 - len(desc))
    return bytes(b)


def write_wav_note(path, note):
    """Safely write `note` into a WAV's iXML <NOTE> (and bext Description).

    The file is rebuilt into a sibling temp file (streaming the big data
    chunk) and then atomically swapped in with os.replace, so the original is
    never left partially written. Returns (ok: bool, error: str|None)."""
    tmp = path + ".tmp_note"
    try:
        if not os.path.isfile(path):
            return False, "File not found"
        with open(path, "rb") as f:
            if f.read(4) != b"RIFF":
                return False, "Not a RIFF/WAV file"
            f.read(4)
            if f.read(4) != b"WAVE":
                return False, "Not a WAV file"
            chunks = []
            while True:
                h = f.read(8)
                if len(h) < 8:
                    break
                cid = h[:4]
                sz = struct.unpack_from("<I", h, 4)[0]
                chunks.append({"id": cid, "off": f.tell(), "size": sz})
                f.seek(sz + (sz & 1), 1)

        has_ixml = any(c["id"] == b"iXML" for c in chunks)
        has_data = any(c["id"] == b"data" for c in chunks)
        new_ixml = None
        new_bext = None
        with open(path, "rb") as f:
            for c in chunks:
                if c["id"] == b"iXML":
                    f.seek(c["off"])
                    new_ixml = _set_ixml_note(f.read(c["size"]), note)
                elif c["id"] == b"bext" and c["size"] >= 256:
                    f.seek(c["off"])
                    new_bext = _set_bext_description(f.read(c["size"]), note)
        if not has_ixml:
            base = (b'<?xml version="1.0" encoding="UTF-8"?>\r\n'
                    b'<BWFXML>\r\n</BWFXML>\r\n')
            new_ixml = _set_ixml_note(base, note)

        # Ordered write plan: ("copy", chunk) or ("mod", id, bytes)
        plan = []
        for c in chunks:
            if c["id"] == b"data" and not has_ixml:
                plan.append(("mod", b"iXML", new_ixml))  # insert before data
            if c["id"] == b"iXML":
                plan.append(("mod", b"iXML", new_ixml))
            elif c["id"] == b"bext" and new_bext is not None:
                plan.append(("mod", b"bext", new_bext))
            else:
                plan.append(("copy", c))
        if not has_ixml and not has_data:
            plan.append(("mod", b"iXML", new_ixml))

        def total_of(sz):
            return 8 + sz + (sz & 1)
        riff_size = 4
        for item in plan:
            riff_size += total_of(len(item[2]) if item[0] == "mod" else item[1]["size"])

        with open(path, "rb") as src, open(tmp, "wb") as out:
            out.write(b"RIFF")
            out.write(struct.pack("<I", riff_size))
            out.write(b"WAVE")
            for item in plan:
                if item[0] == "mod":
                    cid, data = item[1], item[2]
                    out.write(cid)
                    out.write(struct.pack("<I", len(data)))
                    out.write(data)
                    if len(data) & 1:
                        out.write(b"\x00")
                else:
                    c = item[1]
                    out.write(c["id"])
                    out.write(struct.pack("<I", c["size"]))
                    src.seek(c["off"])
                    remaining = c["size"]
                    while remaining > 0:
                        buf = src.read(min(4 * 1024 * 1024, remaining))
                        if not buf:
                            break
                        out.write(buf)
                        remaining -= len(buf)
                    if c["size"] & 1:
                        out.write(b"\x00")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        return True, None
    except Exception as e:  # noqa: BLE001 — surfaced in the UI
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False, str(e)


def _set_ixml_time_reference(xml_bytes, new_tref):
    """Update BWF time-reference tags inside iXML if present (keeps TC in sync
    with the bext chunk after a head trim)."""
    xml = xml_bytes.rstrip(b"\x00").decode("utf-8", "replace")
    low = new_tref & 0xFFFFFFFF
    high = (new_tref >> 32) & 0xFFFFFFFF
    changed = False
    if re.search(r"<BWF_TIME_REFERENCE_LOW>.*?</BWF_TIME_REFERENCE_LOW>", xml, re.DOTALL):
        xml = re.sub(r"<BWF_TIME_REFERENCE_LOW>.*?</BWF_TIME_REFERENCE_LOW>",
                     lambda _m: f"<BWF_TIME_REFERENCE_LOW>{low}</BWF_TIME_REFERENCE_LOW>",
                     xml, count=1, flags=re.DOTALL)
        changed = True
    if re.search(r"<BWF_TIME_REFERENCE_HIGH>.*?</BWF_TIME_REFERENCE_HIGH>", xml, re.DOTALL):
        xml = re.sub(r"<BWF_TIME_REFERENCE_HIGH>.*?</BWF_TIME_REFERENCE_HIGH>",
                     lambda _m: f"<BWF_TIME_REFERENCE_HIGH>{high}</BWF_TIME_REFERENCE_HIGH>",
                     xml, count=1, flags=re.DOTALL)
        changed = True
    return xml.encode("utf-8") if changed else xml_bytes


def write_wav_trim(src_path, dst_path, start_frame, end_frame):
    """Write [start_frame, end_frame) of a WAV to dst_path, copying every other
    chunk verbatim and shifting the BWF start timecode by start_frame.

    Streams the (clipped) data chunk so huge poly files never load into RAM.
    Writes a temp file and atomically swaps it in, so a crash never leaves a
    half-written destination. Returns (ok, error)."""
    tmp = dst_path + ".tmp_trim"
    try:
        if not os.path.isfile(src_path):
            return False, "File not found"
        with open(src_path, "rb") as f:
            if f.read(4) != b"RIFF":
                return False, "Not a RIFF/WAV file"
            f.read(4)
            if f.read(4) != b"WAVE":
                return False, "Not a WAV file"
            chunks = []
            fmt = None
            while True:
                h = f.read(8)
                if len(h) < 8:
                    break
                cid = h[:4]
                sz = struct.unpack_from("<I", h, 4)[0]
                off = f.tell()
                chunks.append({"id": cid, "off": off, "size": sz})
                if cid == b"fmt ":
                    fb = f.read(min(sz, 40))
                    fmt = {
                        "tag": struct.unpack_from("<H", fb, 0)[0],
                        "ch":  struct.unpack_from("<H", fb, 2)[0],
                        "sr":  struct.unpack_from("<I", fb, 4)[0],
                        "bps": struct.unpack_from("<H", fb, 14)[0],
                    }
                    f.seek(off + sz + (sz & 1))
                else:
                    f.seek(sz + (sz & 1), 1)
        if not fmt or not fmt["ch"] or not fmt["bps"]:
            return False, "Missing fmt chunk"
        frame_bytes = fmt["ch"] * (fmt["bps"] // 8)
        data = next((c for c in chunks if c["id"] == b"data"), None)
        if not data:
            return False, "Missing data chunk"
        total_frames = data["size"] // frame_bytes
        start_frame = max(0, min(int(start_frame), total_frames))
        end_frame = max(start_frame, min(int(end_frame), total_frames))
        keep_frames = end_frame - start_frame
        if keep_frames <= 0:
            return False, "Empty trim range"
        new_data_size = keep_frames * frame_bytes
        data_skip = start_frame * frame_bytes

        # TC sample rate (BWF time_ref is in audio samples; honour an explicit
        # iXML TIMESTAMP_SAMPLE_RATE if it differs from the audio rate).
        new_bext = None
        new_ixml = None
        with open(src_path, "rb") as f:
            tc_sr = fmt["sr"]
            for c in chunks:
                if c["id"] == b"iXML":
                    f.seek(c["off"])
                    ix = f.read(c["size"])
                    sp = _parse_speed_fields(ix.rstrip(b"\x00").decode("utf-8", "replace"))
                    ts = sp.get("timestamp_sr")
                    if ts:
                        try:
                            tc_sr = int(float(ts)) or fmt["sr"]
                        except ValueError:
                            pass
            tc_shift = int(round(start_frame * tc_sr / fmt["sr"])) if fmt["sr"] else start_frame
            for c in chunks:
                if c["id"] == b"bext" and c["size"] >= 346:
                    f.seek(c["off"])
                    bb = bytearray(f.read(c["size"]))
                    old_tref = struct.unpack_from("<Q", bb, 338)[0]
                    struct.pack_into("<Q", bb, 338, old_tref + tc_shift)
                    new_bext = bytes(bb)
                elif c["id"] == b"iXML":
                    f.seek(c["off"])
                    ixb = f.read(c["size"])
                    # Shift iXML BWF time reference too (if it carries one).
                    base_tref = 0
                    bx = next((x for x in chunks if x["id"] == b"bext"), None)
                    if bx and bx["size"] >= 346:
                        with open(src_path, "rb") as f2:
                            f2.seek(bx["off"] + 338)
                            base_tref = struct.unpack_from("<Q", f2.read(8), 0)[0]
                    new_ixml = _set_ixml_time_reference(ixb, base_tref + tc_shift)

        plan = []
        for c in chunks:
            if c["id"] == b"data":
                plan.append(("data", c))
            elif c["id"] == b"bext" and new_bext is not None:
                plan.append(("mod", b"bext", new_bext))
            elif c["id"] == b"iXML" and new_ixml is not None:
                plan.append(("mod", b"iXML", new_ixml))
            else:
                plan.append(("copy", c))

        def total_of(sz):
            return 8 + sz + (sz & 1)
        riff_size = 4
        for item in plan:
            if item[0] == "mod":
                riff_size += total_of(len(item[2]))
            elif item[0] == "data":
                riff_size += total_of(new_data_size)
            else:
                riff_size += total_of(item[1]["size"])

        with open(src_path, "rb") as src, open(tmp, "wb") as out:
            out.write(b"RIFF")
            out.write(struct.pack("<I", riff_size))
            out.write(b"WAVE")
            for item in plan:
                if item[0] == "mod":
                    cid, blob = item[1], item[2]
                    out.write(cid)
                    out.write(struct.pack("<I", len(blob)))
                    out.write(blob)
                    if len(blob) & 1:
                        out.write(b"\x00")
                elif item[0] == "data":
                    out.write(b"data")
                    out.write(struct.pack("<I", new_data_size))
                    src.seek(item[1]["off"] + data_skip)
                    remaining = new_data_size
                    while remaining > 0:
                        buf = src.read(min(4 * 1024 * 1024, remaining))
                        if not buf:
                            break
                        out.write(buf)
                        remaining -= len(buf)
                    if new_data_size & 1:
                        out.write(b"\x00")
                else:
                    c = item[1]
                    out.write(c["id"])
                    out.write(struct.pack("<I", c["size"]))
                    src.seek(c["off"])
                    remaining = c["size"]
                    while remaining > 0:
                        buf = src.read(min(4 * 1024 * 1024, remaining))
                        if not buf:
                            break
                        out.write(buf)
                        remaining -= len(buf)
                    if c["size"] & 1:
                        out.write(b"\x00")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, dst_path)
        return True, None
    except Exception as e:  # noqa: BLE001 — surfaced in the UI
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False, str(e)


# ══════════════════════════════════════════════════════════════════
# AUDIO ENGINE  (waveform peaks + multichannel playback)
# ══════════════════════════════════════════════════════════════════

def peak_bucket_size(n, target_buckets=4096):
    """Pick a bucket width so long files keep a bounded peak summary."""
    if n <= 0:
        return 512
    return max(512, (n + target_buckets - 1) // target_buckets)


def compute_peaks(audio, bucket=None):
    """Build a min/max peak summary (per channel) for fast waveform drawing."""
    n, ch = audio.shape
    if bucket is None:
        bucket = peak_bucket_size(n)
    if n == 0:
        z = np.zeros((1, ch), dtype=np.float32)
        return z, z.copy(), bucket
    nb = (n + bucket - 1) // bucket
    pad = nb * bucket - n
    a = audio if pad == 0 else np.concatenate(
        [audio, np.zeros((pad, ch), dtype=audio.dtype)], axis=0)
    r = a.reshape(nb, bucket, ch)
    return r.min(axis=1).copy(), r.max(axis=1).copy(), bucket


def _accumulate_peak_block(pmin, pmax, data, frame_offset, bucket):
    """Merge one read block into global min/max peak buckets."""
    n = data.shape[0]
    i = 0
    while i < n:
        abs_frame = frame_offset + i
        bi = abs_frame // bucket
        bucket_end = (bi + 1) * bucket
        seg_len = min(n - i, bucket_end - abs_frame)
        seg = data[i:i + seg_len]
        pmin[bi] = np.minimum(pmin[bi], seg.min(axis=0))
        pmax[bi] = np.maximum(pmax[bi], seg.max(axis=0))
        i += seg_len


def load_wave_peaks(path, target_buckets=4096, read_block=262144):
    """Stream a WAV/polywav and build a compact peak summary without full decode."""
    if sf is None or np is None:
        raise RuntimeError("soundfile/numpy not available")
    with sf.SoundFile(path) as f:
        n = int(f.frames)
        ch = int(f.channels)
        sr = int(f.samplerate)
        if n == 0:
            z = np.zeros((1, ch), dtype=np.float32)
            return {"sr": sr, "n": 0, "channels": ch,
                    "pmin": z, "pmax": z.copy(), "bucket": 512}
        bucket = peak_bucket_size(n, target_buckets)
        nb = (n + bucket - 1) // bucket
        pmin = np.full((nb, ch), np.inf, dtype=np.float32)
        pmax = np.full((nb, ch), -np.inf, dtype=np.float32)
        pos = 0
        while pos < n:
            data = f.read(min(read_block, n - pos), dtype="float32", always_2d=True)
            if data.size == 0:
                break
            _accumulate_peak_block(pmin, pmax, data, pos, bucket)
            pos += data.shape[0]
        silent = ~np.isfinite(pmin[:, 0])
        pmin[silent] = 0.0
        pmax[silent] = 0.0
        return {"sr": sr, "n": n, "channels": ch,
                "pmin": pmin, "pmax": pmax, "bucket": bucket}


class PeakLoadWorker(QThread):
    """Fast peak-only load so waveforms appear without decoding the full file."""
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            self.loaded.emit(load_wave_peaks(self.path))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class AudioLoadWorker(QThread):
    """Loads audio for playback (mmap when possible). Peaks are loaded separately."""
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            if sf is None or np is None:
                raise RuntimeError("soundfile/numpy not available")
            try:
                data, sr = sf.read(
                    self.path, dtype="float32", always_2d=True, mmap=True)
            except TypeError:
                data, sr = sf.read(self.path, dtype="float32", always_2d=True)
            self.loaded.emit({"audio": data, "sr": int(sr)})
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class PlaybackEngine(QObject):
    """Streams an in-RAM multichannel buffer to stereo out via sounddevice.

    Per-channel gain / pan / mute / solo are read live inside the audio
    callback, so mixer tweaks apply instantly while playing."""
    stopped = Signal()

    def __init__(self):
        super().__init__()
        self._stream = None
        self._audio = None
        self._sr = 0
        self._ch = 0
        self._n = 0
        self._pos = 0
        self._master = 1.0
        self._gains = self._pans = self._mutes = self._solos = None

    def set_audio(self, audio, sr):
        self.stop()
        self._audio = audio
        self._n = int(audio.shape[0])
        self._ch = int(audio.shape[1])
        self._sr = int(sr)
        self._pos = 0
        self._gains = np.ones(self._ch, dtype=np.float32)
        self._pans = np.zeros(self._ch, dtype=np.float32)
        self._mutes = np.zeros(self._ch, dtype=bool)
        self._solos = np.zeros(self._ch, dtype=bool)

    def set_channel(self, i, gain=None, pan=None, mute=None, solo=None):
        if self._gains is None or not (0 <= i < self._ch):
            return
        if gain is not None:
            self._gains[i] = float(gain)
        if pan is not None:
            self._pans[i] = float(pan)
        if mute is not None:
            self._mutes[i] = bool(mute)
        if solo is not None:
            self._solos[i] = bool(solo)

    def set_master(self, gain):
        self._master = float(gain)

    def _mix_matrix(self):
        active = ~self._mutes
        if self._solos.any():
            active = active & self._solos
        g = self._gains * active.astype(np.float32) * self._master
        theta = (self._pans * 0.5 + 0.5) * (math.pi / 2.0)
        return (g * np.cos(theta)).astype(np.float32), (g * np.sin(theta)).astype(np.float32)

    def _callback(self, outdata, frames, time_info, status):  # noqa: ARG002
        start = self._pos
        if self._audio is None or start >= self._n:
            outdata.fill(0)
            raise sd.CallbackStop
        end = min(start + frames, self._n)
        n = end - start
        block = self._audio[start:end]
        L, R = self._mix_matrix()
        outdata[:n, 0] = block @ L
        outdata[:n, 1] = block @ R
        if n < frames:
            outdata[n:].fill(0)
        np.clip(outdata, -1.0, 1.0, out=outdata)
        self._pos = end

    def play(self, from_frame=None):
        if sd is None or self._audio is None:
            return False
        if from_frame is not None:
            self._pos = max(0, min(int(from_frame), self._n))
        if self._pos >= self._n:
            self._pos = 0
        self.stop()
        try:
            self._stream = sd.OutputStream(
                samplerate=self._sr, channels=2, dtype="float32",
                callback=self._callback, finished_callback=self._on_finished)
            self._stream.start()
            return True
        except Exception:
            self._stream = None
            return False

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _on_finished(self):
        self.stopped.emit()

    def is_playing(self):
        return self._stream is not None and self._pos < self._n

    def position(self):
        return self._pos

    def seek(self, frame):
        self._pos = max(0, min(int(frame), self._n))


class MetadataScanWorker(QThread):
    """Background folder scan — emits metadata per WAV so the UI stays live."""
    fileFound = Signal(dict)
    scanDone  = Signal(int)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            files = sorted(f for f in os.listdir(self.folder)
                           if f.lower().endswith(".wav"))
        except OSError:
            self.scanDone.emit(0)
            return
        n = 0
        for f in files:
            if self._stop.is_set():
                break
            self.fileFound.emit(read_audio_metadata(os.path.join(self.folder, f)))
            n += 1
        self.scanDone.emit(n)

def build_polywav(out_path, tmp_path, rec_bext, r_ixml, track_names, orig_filename, extra_note=""):
    try:
        hdr = read_header(tmp_path, 65536)
        if hdr[:4] != b"RIFF" or hdr[8:12] != b"WAVE": return "ERR_NOT_RIFF"
        chunks = read_riff_chunks(hdr)
        fc = next((x for x in chunks if x["id"] == "fmt "), None)
        if not fc: return "ERR_NO_FMT"
        fd = bytearray(hdr[fc["data_offset"]:fc["data_offset"]+fc["size"]])
        tag = struct.unpack_from("<H", fd, 0)[0]
        if tag == 0xFFFE:
            f_ch=struct.unpack_from("<H",fd,2)[0]; f_sr=struct.unpack_from("<I",fd,4)[0]
            f_bps=struct.unpack_from("<H",fd,14)[0]; f_al=f_ch*(f_bps//8); f_av=f_sr*f_al
            sub = fd[24] if len(fd)>=25 else 0x01
            nt  = 0x0003 if sub==0x03 else 0x0001
            fd  = struct.pack("<HHIIHH", nt, f_ch, f_sr, f_av, f_al, f_bps)
        fd = bytes(fd)
        dc = next((x for x in chunks if x["id"] == "data"), None)
        if dc: ao, asz = dc["data_offset"], dc["size"]
        else:
            ao, asz = find_data_chunk(tmp_path)
            if not ao: return "ERR_NO_DATA"
        n = len(track_names)
        xi = r_ixml
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>\r\n', "<BWFXML>\r\n",
            f"\t<IXML_VERSION>1.62</IXML_VERSION>\r\n",
            f"\t<PROJECT>{xi['project']}</PROJECT>\r\n",
            f"\t<SCENE>{xi['scene']}</SCENE>\r\n",
            f"\t<TAKE>{xi['take']}</TAKE>\r\n",
            f"\t<TAPE>{xi['tape']}</TAPE>\r\n",
            f"\t<CIRCLED>FALSE</CIRCLED>\r\n",
            f"\t<FILE_UID>{xi['file_uid']}</FILE_UID>\r\n",
            f"\t<UBITS>{xi['ubits']}</UBITS>\r\n",
            f"\t<NOTE>{_xml_escape(extra_note)}</NOTE>\r\n",
            f"\t{xi['speed_block']}\r\n",
            f"\t<HISTORY>\r\n\t\t<ORIGINAL_FILENAME>{orig_filename}</ORIGINAL_FILENAME>\r\n\t</HISTORY>\r\n",
            f"\t<FILE_SET>\r\n\t\t<TOTAL_FILES>1</TOTAL_FILES>\r\n",
            f"\t\t<FAMILY_UID>{xi['family_uid']}</FAMILY_UID>\r\n",
            f"\t\t<FILE_SET_INDEX>{xi['file_set_idx']}</FILE_SET_INDEX>\r\n\t</FILE_SET>\r\n",
            f"\t<AUDIO_FORMAT>MULTI</AUDIO_FORMAT>\r\n",
            f"\t<TRACK_LIST>\r\n\t\t<TRACK_COUNT>{n}</TRACK_COUNT>\r\n",
        ]
        for i, name in enumerate(track_names):
            idx = i + 1
            lines += [f"\t\t<TRACK>\r\n\t\t\t<CHANNEL_INDEX>{idx}</CHANNEL_INDEX>\r\n",
                      f"\t\t\t<INTERLEAVE_INDEX>{idx}</INTERLEAVE_INDEX>\r\n",
                      f"\t\t\t<NAME>{name}</NAME>\r\n\t\t</TRACK>\r\n"]
        lines += ["\t</TRACK_LIST>\r\n", "</BWFXML>\r\n"]
        xb = "".join(lines).encode("utf-8")
        def ct(l): return 8 + l + (l%2)
        def pad(l): return b"\x00" if l%2 else b""
        riff_sz = 4 + ct(len(fd)) + ct(len(rec_bext)) + ct(len(xb)) + ct(asz)
        with open(out_path, "wb") as out:
            out.write(b"RIFF"); out.write(struct.pack("<I", riff_sz)); out.write(b"WAVE")
            out.write(b"fmt "); out.write(struct.pack("<I",len(fd)));       out.write(fd);       out.write(pad(len(fd)))
            out.write(b"bext"); out.write(struct.pack("<I",len(rec_bext))); out.write(rec_bext); out.write(pad(len(rec_bext)))
            out.write(b"iXML"); out.write(struct.pack("<I",len(xb)));       out.write(xb);       out.write(pad(len(xb)))
            out.write(b"data"); out.write(struct.pack("<I",asz))
            with open(tmp_path,"rb") as src:
                src.seek(ao); rem=asz; buf=bytearray(1024*1024)
                while rem>0:
                    nr=src.readinto(memoryview(buf)[:min(len(buf),rem)])
                    if not nr: break
                    out.write(buf[:nr]); rem-=nr
            out.write(pad(asz))
        return "OK"
    except Exception as e: return f"ERROR: {e}"

def run_ffmpeg(args):
    ff = "ffmpeg"
    search_dirs = [
        getattr(sys, "_MEIPASS", None),
        os.path.join(getattr(sys, "_MEIPASS", "") or "", "ffmpeg_bin"),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin"),
        os.getcwd(),
        os.path.join(os.getcwd(), "ffmpeg_bin"),
    ]
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    for base in search_dirs:
        if not base:
            continue
        local = os.path.join(base, exe_name)
        if os.path.exists(local):
            ff = local
            break
    kwargs = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    p = subprocess.run([ff]+args, **kwargs)
    return p.returncode, p.stderr

def _ffmpeg_exe():
    ff = "ffmpeg"
    search_dirs = [
        getattr(sys, "_MEIPASS", None),
        os.path.join(getattr(sys, "_MEIPASS", "") or "", "ffmpeg_bin"),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin"),
        os.getcwd(),
        os.path.join(os.getcwd(), "ffmpeg_bin"),
    ]
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    for base in search_dirs:
        if not base:
            continue
        local = os.path.join(base, exe_name)
        if os.path.exists(local):
            return local
    return ff

def run_ffmpeg_binary(args):
    kwargs = {"capture_output": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run([_ffmpeg_exe()] + args, **kwargs)

def extract_analysis_audio(path, offset_sec, dur_sec, channel_idx=1, sample_rate=2000):
    if dur_sec <= 0:
        return []
    channel_idx = max(1, int(channel_idx))
    offset_sec = max(0.0, float(offset_sec))
    channel_expr = f"c0=c{channel_idx - 1}"
    p = run_ffmpeg_binary([
        "-loglevel", "error",
        "-ss", f"{offset_sec:.6f}",
        "-t", f"{float(dur_sec):.6f}",
        "-i", path,
        "-filter_complex",
        f"pan=mono|{channel_expr},lowpass=f=500,aresample={sample_rate}",
        "-map", "[out]" if False else "0:a:0",
        "-f", "f32le",
        "-"
    ])
    if p.returncode != 0 or not p.stdout:
        p = run_ffmpeg_binary([
            "-loglevel", "error",
            "-ss", f"{offset_sec:.6f}",
            "-t", f"{float(dur_sec):.6f}",
            "-i", path,
            "-filter:a", f"lowpass=f=500,aresample={sample_rate}",
            "-ac", "1",
            "-f", "f32le",
            "-"
        ])
    if p.returncode != 0 or not p.stdout:
        return []
    samples = struct.unpack("<" + "f" * (len(p.stdout) // 4), p.stdout[:len(p.stdout) // 4 * 4])
    return list(samples)

def extract_channel_analysis_audio(path, offset_sec, dur_sec, channel_idx=1, sample_rate=2000):
    if dur_sec <= 0:
        return []
    channel_idx = max(1, int(channel_idx))
    offset_sec = max(0.0, float(offset_sec))
    channel_expr = f"c0=c{channel_idx - 1}"
    p = run_ffmpeg_binary([
        "-loglevel", "error",
        "-ss", f"{offset_sec:.6f}",
        "-t", f"{float(dur_sec):.6f}",
        "-i", path,
        "-filter_complex",
        f"[0:a]pan=mono|{channel_expr},lowpass=f=500,aresample={sample_rate}[a]",
        "-map", "[a]",
        "-f", "f32le",
        "-"
    ])
    if p.returncode != 0 or not p.stdout:
        return []
    samples = struct.unpack("<" + "f" * (len(p.stdout) // 4), p.stdout[:len(p.stdout) // 4 * 4])
    return list(samples)

def _analysis_stats(samples):
    if not samples:
        return 0.0, 0.0
    rms = math.sqrt(sum(x * x for x in samples) / len(samples))
    if len(samples) < 2:
        return rms, 0.0
    trans = sum(abs(samples[i] - samples[i - 1]) for i in range(1, len(samples))) / (len(samples) - 1)
    return rms, trans

def _normalize_for_corr(samples):
    if not samples:
        return []
    mean = sum(samples) / len(samples)
    centered = [x - mean for x in samples]
    energy = math.sqrt(sum(x * x for x in centered))
    if energy <= 1e-9:
        return []
    return [x / energy for x in centered]

def _estimate_lag(ref, tx, sample_rate, max_lag_sec=0.5):
    ref = _normalize_for_corr(ref)
    tx = _normalize_for_corr(tx)
    n = min(len(ref), len(tx))
    if n < sample_rate:
        return None
    ref = ref[:n]
    tx = tx[:n]
    max_lag = min(int(max_lag_sec * sample_rate), n // 3)
    best_lag = 0
    best_score = -1.0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a = ref[:n - lag]
            b = tx[lag:n]
        else:
            a = ref[-lag:n]
            b = tx[:n + lag]
        if len(a) < sample_rate:
            continue
        score = sum(x * y for x, y in zip(a, b))
        if score > best_score:
            best_score = score
            best_lag = lag
    return best_lag / float(sample_rate), best_score

def _calculate_transient_score(samples):
    """
    Calculate transient activity as normalized sum of absolute differences.
    Higher values = more transients/changes in amplitude.
    """
    if len(samples) < 2:
        return 0.0
    # Sum of absolute differences between consecutive samples
    diffs = sum(abs(samples[i] - samples[i - 1]) for i in range(1, len(samples)))
    # Normalize by length
    return diffs / (len(samples) - 1)

def choose_alignment_windows(rec_path, ref_channel, rec_dur, scan_dur=30.0, chunk=5.0):
    """
    Return candidate alignment windows ordered best-first.

    Scans the first `scan_dur` seconds in `chunk`-second pieces, scores each
    by RMS + transient activity (downsampled to 2 kHz, lowpassed at 500 Hz),
    and returns the candidates sorted by descending score. The caller can
    then try them one by one until correlation passes.

    Earlier versions scanned only 0-25 s and returned a single window. For
    problematic files where that window happened to be unhelpful, alignment
    silently fell back to TC. Now we hand the caller a list, so it can keep
    trying further into the recording.
    """
    max_scan = min(scan_dur, rec_dur)
    if max_scan < 2.0:
        return []

    candidate_specs = []
    t = 0.0
    while t + 2.0 <= max_scan:
        dur = min(chunk, max_scan - t)
        if dur >= 2.0:
            candidate_specs.append((t, dur))
        t += chunk

    scored = []
    for start, dur in candidate_specs:
        samples = extract_channel_analysis_audio(rec_path, start, dur, ref_channel, sample_rate=2000)
        if not samples or len(samples) < 100:
            continue
        rms, _ = _analysis_stats(samples)
        trans = _calculate_transient_score(samples)
        score = rms * 0.65 + trans * 0.35
        scored.append({"score": score, "rms": rms, "trans": trans,
                       "start": start, "dur": dur})

    if not scored:
        return []

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def choose_alignment_window(rec_path, ref_channel, rec_dur):
    """Back-compat shim — first window of choose_alignment_windows."""
    windows = choose_alignment_windows(rec_path, ref_channel, rec_dur)
    return windows[0] if windows else None

def estimate_tc_offset_correction(rec_path, tx_path, ref_channel, tc_offset, rec_dur):
    """
    Estimate clock drift offset by correlating recorder reference with TX.

    Tries multiple alignment windows (scored by RMS + transient activity)
    across the first 30 seconds of audio. Returns the first window that
    crosses a high-confidence correlation threshold; if no window is
    high-confidence, returns the best borderline match (corr >= 0.25).

    1.5 s handle on each side covers up to ~1 s of constant drift while
    keeping the FFT cheap.
    """
    windows = choose_alignment_windows(rec_path, ref_channel, rec_dur)
    if not windows:
        return None

    handle = 1.5
    sample_rate = 2000
    HIGH_CONF = 0.50   # early-exit threshold
    MIN_CONF  = 0.25   # minimum to consider a result usable
    pad_n = int(handle * sample_rate)

    best_result = None

    for window in windows:
        ref = extract_channel_analysis_audio(
            rec_path, window["start"], window["dur"], ref_channel, sample_rate)
        if not ref:
            continue

        tx_start = max(0.0, tc_offset + window["start"] - handle)
        tx_dur = window["dur"] + 2.0 * handle
        tx = extract_channel_analysis_audio(tx_path, tx_start, tx_dur, 1, sample_rate)
        if not tx:
            continue

        # Pad ref so its content sits in the middle; lag=0 then means exact TC alignment.
        padded_ref = [0.0] * pad_n + ref + [0.0] * pad_n

        # Match lengths — ffmpeg's resampler may return ±a few samples.
        n = min(len(padded_ref), len(tx))
        if n < int(2.0 * sample_rate):
            continue
        padded_ref_trim = padded_ref[:n]
        tx_trim = tx[:n]

        # Unit-energy normalization makes the corr score amplitude-independent.
        ref_norm = _normalize_for_corr(padded_ref_trim)
        tx_norm = _normalize_for_corr(tx_trim)
        if not ref_norm or not tx_norm:
            continue

        result = _correlate_gpu(ref_norm, tx_norm, _GPU_INFO, sample_rate, max_lag_sec=handle)
        if not result:
            continue

        lag_sec, corr = result
        if corr < MIN_CONF:
            continue

        candidate = {
            "correction":   lag_sec,   # positive => TX delayed; advance TX start
            "corr":         corr,
            "window_start": window["start"],
            "window_dur":   window["dur"],
            "rms":          window["rms"],
            "trans":        window["trans"],
        }

        if corr >= HIGH_CONF:
            return candidate

        # Borderline — remember the best one and keep looking
        if best_result is None or corr > best_result["corr"]:
            best_result = candidate

    return best_result

# ══════════════════════════════════════════════════════════════════
# PARALLEL TX FILE PROCESSING
# ══════════════════════════════════════════════════════════════════

def _process_tx_file_for_offset(tx_info):
    """
    Process a single TX file for offset correction.
    Used for parallel processing with ThreadPoolExecutor.
    
    Args:
        tx_info: dict with keys: tp, dc, tn_base, off, r_dur, rp, align_map, tx_profile
    
    Returns:
        dict with results or None if failed
    """
    try:
        tp = tx_info["tp"]
        dc = tx_info["dc"]
        tn_base = tx_info["tn_base"]
        off = tx_info["off"]
        r_dur = tx_info["r_dur"]
        rp = tx_info["rp"]
        align_map = tx_info["align_map"]
        tx_profile = tx_info["tx_profile"]
        r_tnames = tx_info.get("r_tnames") or []
        target_channel_name = tx_info.get("target_channel_name")
        clock_correction = tx_info.get("clock_correction", bool(align_map))

        source_offset = off
        source_dur = r_dur
        ref_channel = None
        ref_channel_name = None
        primary_name = None        # what the user mapped (kept for logging)
        chan_missing = False
        align_result = None
        used_fallback = None       # None | "boom"
        boom_attempted = False

        if clock_correction and align_map:
            mapped = target_channel_name or _lookup_tx_group_value(align_map, tn_base)
            if isinstance(mapped, int):
                # Legacy: index-based mapping from older saved state
                ref_channel = mapped
            elif mapped:
                ref_channel_name = str(mapped)
                primary_name = ref_channel_name
                ref_channel = _resolve_channel_index(ref_channel_name, r_tnames)
                if ref_channel is None:
                    chan_missing = True

        # Primary alignment attempt (only if mapping resolved to a real channel)
        if ref_channel:
            align_result = estimate_tc_offset_correction(rp, tp, ref_channel, off, r_dur)

        # Boom fallback: only when the user actually requested alignment for
        # this TX (i.e. they set a mapping) AND the primary attempt failed.
        # Skip when the TX is itself a boom mic (no point aligning to self),
        # and when the primary ref already IS the boom channel.
        attempted_primary = (ref_channel is not None) or chan_missing
        if (not align_result and attempted_primary and r_tnames
                and not _is_boom_mic(tn_base)):
            boom_idx, boom_name = _find_boom_channel(r_tnames)
            if boom_idx and boom_idx != ref_channel:
                boom_attempted = True
                fb_align = estimate_tc_offset_correction(rp, tp, boom_idx, off, r_dur)
                if fb_align:
                    align_result = fb_align
                    ref_channel = boom_idx
                    ref_channel_name = boom_name
                    used_fallback = "boom"

        # Apply alignment if anything succeeded
        if align_result:
            source_offset = max(0.0, off + align_result["correction"])
            tx_total = dc["end"] - dc["start"]
            if source_offset + source_dur > tx_total:
                source_offset = max(0.0, tx_total - source_dur)

        return {
            "tp": tp,
            "tn_base": tn_base,
            "dc": dc,
            "source_offset": source_offset,
            "source_dur": source_dur,
            "ref_channel": ref_channel,
            "ref_channel_name": ref_channel_name,
            "primary_name": primary_name,
            "target_channel_name": target_channel_name or primary_name,
            "chan_missing": chan_missing,
            "used_fallback": used_fallback,
            "boom_attempted": boom_attempted,
            "align_result": align_result,
            "tx_profile": tx_profile,
            "tx_info": tx_info
        }
    except Exception as e:
        return {
            "error": str(e),
            "tn_base": tx_info.get("tn_base", "unknown"),
            "tp": tx_info.get("tp", "unknown")
        }

# ══════════════════════════════════════════════════════════════════
# PROCESSING THREAD
# ══════════════════════════════════════════════════════════════════

def _lookup_tx_group_value(mapping, filename):
    if not mapping:
        return None
    base = os.path.splitext(os.path.basename(str(filename)))[0]
    group_key = _clean_alnum(_tx_group_label(filename))
    return mapping.get(filename) or mapping.get(base) or mapping.get(group_key)

def process_files(r_dir, tx_dir, o_dir, normalize, tx_only, tx_profile,
                  log_q, progress_q, stop_event, align_map=None,
                  filter_by_channel=False, always_include=None,
                  keep_recorder_channels=None, tx_track_prefix="TX",
                  clock_correction=True):
    def log(msg, tag="normal"): log_q.put((msg, tag))
    def prog(cur, total, name): progress_q.put((cur, total, name))

    always_include = always_include or set()
    keep_recorder_channels = keep_recorder_channels or set()

    r_files  = sorted([f for f in os.listdir(r_dir)  if f.lower().endswith(".wav")])
    tx_files = sorted([f for f in os.listdir(tx_dir) if f.lower().endswith(".wav")])
    norm_s   = "ON" if normalize else "OFF"
    align_s  = "ON" if (clock_correction and align_map) else "OFF"
    filter_s = "ON" if filter_by_channel else "OFF"
    keep_s = f"{len(keep_recorder_channels)} recorder ch kept in TX-only" if keep_recorder_channels else "no recorder ch kept in TX-only"
    log(f"Recorder: {len(r_files)} files  |  TX: {len(tx_files)} files  |  Normalize: {norm_s}  |  Clock offset correction: {align_s}  |  Channel filter: {filter_s}  |  {keep_s}  |  TX prefix: {_clean_tx_prefix(tx_track_prefix)}", "dim")
    log("─"*60, "dim")

    # ── Cache TX metadata ─────────────────────────────────────────
    log("Scanning TX files...", "dim")
    tx_cache = {}
    for tn in tx_files:
        if stop_event.is_set(): return
        tp = os.path.join(tx_dir, tn)
        try:
            hdr = read_header(tp, 204800); chunks = read_riff_chunks(hdr)
            fmt = parse_fmt(hdr, chunks); bxt = parse_bext(hdr, chunks)
            if not fmt or not bxt or not fmt["sample_rate"]: continue
            sr = float(fmt["sample_rate"]); ch = fmt["channels"]; bps = fmt["bps"]
            t0 = bxt["time_ref"] / sr
            dc = next((x for x in chunks if x["id"] == "data"), None)
            if dc: dur = dc["size"] / (sr*ch*(bps/8))
            else:
                _, dsz = find_data_chunk(tp)
                if not dsz: continue
                dur = dsz / (sr*ch*(bps/8))
            tx_cache[tp] = {"sr":sr,"ch":ch,"bps":bps,"is_float":(bps==32),
                            "start":t0,"end":t0+dur}
        except Exception as e: log(f"  WARN: {tn}: {e}", "warn")
    log(f"TX cache: {len(tx_cache)} / {len(tx_files)} files ready", "dim")
    log("─"*60, "dim")

    total_created = 0; os.makedirs(o_dir, exist_ok=True)

    for idx, rn in enumerate(r_files, 1):
        if stop_event.is_set(): return
        prog(idx, len(r_files), rn)
        rp = os.path.join(r_dir, rn); rbase = os.path.splitext(rn)[0]
        try:
            rhdr = read_header(rp, 200000); rch = read_riff_chunks(rhdr)
            r_ixml = parse_recorder_ixml(rhdr, rch)
            r_bext = get_chunk_data(rhdr, rch, "bext")
            r_fmt  = parse_fmt(rhdr, rch)
            r_bxtm = parse_bext(rhdr, rch)
        except Exception as e:
            log(f"[{idx}/{len(r_files)}] SKIP (read error): {rn} — {e}", "warn"); continue

        if not r_bext or not r_fmt or not r_bxtm:
            log(f"[{idx}/{len(r_files)}] SKIP (no bext/fmt): {rn}", "warn"); continue

        r_sr    = float(r_fmt["sample_rate"]); r_ch = r_fmt["channels"]
        r_start = r_bxtm["time_ref"] / r_sr
        rdc = next((x for x in rch if x["id"] == "data"), None)
        if rdc: r_dur = rdc["size"] / (r_sr*r_ch*(r_fmt["bps"]/8))
        else:
            _, dsz = find_data_chunk(rp)
            r_dur = dsz/(r_sr*r_ch*(r_fmt["bps"]/8)) if dsz else 0.0
        r_end = r_start + r_dur; dur_str = f"{r_dur:.6f}"

        r_tnames = list(r_ixml["track_names"])
        if not r_tnames:
            if r_ch==1:   r_tnames = ["MIX"]
            elif r_ch==2: r_tnames = ["L","R"]
            else:         r_tnames = [f"CH{i}" for i in range(1,r_ch+1)]

        fps_m = re.search(r"<TIMECODE_RATE>([^<]+)</TIMECODE_RATE>", r_ixml["speed_block"])
        fps   = fps_m.group(1) if fps_m else "?"
        tc    = f"{int(r_start//3600):02d}:{int((r_start%3600)//60):02d}:{int(r_start%60):02d}.{int((r_start%1)*1000):03d}"
        log(f"[{idx}/{len(r_files)}]  {rn}   TC:{tc}  dur:{round(r_dur,1)}s  ch:{r_ch}  FPS:{fps}  {r_ixml['scene']} T{r_ixml['take']}", "file")
        if not tx_only: log(f"    Recorder: {' | '.join(r_tnames)}", "dim")

        hits = []

        # Prepare TX files for parallel processing
        tx_to_process = []
        for tp, dc in tx_cache.items():
            if not (r_start >= dc["start"] and r_end <= dc["end"]): continue
            tn_base = os.path.basename(tp)
            base_no_ext = os.path.splitext(tn_base)[0]
            group_key = _clean_alnum(_tx_group_label(tn_base))
            off = r_start - dc["start"]
            target_name = _lookup_tx_group_value(align_map, tn_base) if align_map else None

            # ── Channel-presence filter ───────────────────────────────
            # The TX is pulled in only if its target recorder channel is
            # actually present in THIS take's track list. Override via the
            # mapping dialog's "Always include" checkbox (for autonomous
            # plant mics on channels not physically on the recorder).
            if filter_by_channel:
                is_override = tn_base in always_include or base_no_ext in always_include or group_key in always_include
                if not is_override:
                    # Determine the TX's target channel:
                    #   1. Explicit mapping from the dialog (most reliable)
                    #   2. Auto-guess against this take's track names
                    if not target_name:
                        target_name = guess_tx_channel_name(tn_base, "", r_tnames)
                    if target_name:
                        if _resolve_channel_index(target_name, r_tnames) is None:
                            log(f"    SKIP {tn_base}: '{target_name}' not recorded in this take", "dim")
                            continue
                    # else: couldn't determine target channel → include (lenient default)

            tx_to_process.append({
                "tp": tp,
                "dc": dc,
                "tn_base": tn_base,
                "off": off,
                "r_dur": r_dur,
                "rp": rp,
                "align_map": align_map,
                "tx_profile": tx_profile,
                "r_tnames": r_tnames,
                "target_channel_name": target_name,
                "clock_correction": clock_correction,
            })
        
        # Process TX files in parallel (max 4 workers), then sort the results
        # deterministically so track positions are stable across files.
        if tx_to_process:
            max_workers = min(4, len(tx_to_process))
            results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_tx_file_for_offset, tx_info) for tx_info in tx_to_process]
                for future in as_completed(futures):
                    if stop_event.is_set(): return
                    results.append(future.result())

            # Track-order key:
            #   (0) boom/overhead mics always at the top,
            #   then by the filename-derived channel index (lower first),
            #   then alphabetical for stable tie-break.
            # Errors sink to the bottom so they don't push real tracks around.
            def _track_sort_key(result):
                tn = result.get("tn_base", "")
                if "error" in result:
                    return (3, 99999, tn.lower())
                ti = get_tx_info(os.path.splitext(tn)[0], tx_profile, tx_track_prefix)
                if _is_boom_mic(tn, ti["name"]):
                    return (0, ti["chan_idx"], tn.lower())
                return (1, ti["chan_idx"], tn.lower())

            results.sort(key=_track_sort_key)

            for result in results:
                if "error" in result:
                    log(f"    ERROR {result['tn_base']}: {result['error']}", "warn")
                    continue

                tp = result["tp"]
                tn_base = result["tn_base"]
                dc = result["dc"]
                source_offset = result["source_offset"]
                source_dur = result["source_dur"]
                ref_channel = result["ref_channel"]
                ref_channel_name = result.get("ref_channel_name")
                primary_name = result.get("primary_name")
                target_channel_name = result.get("target_channel_name")
                chan_missing = result.get("chan_missing", False)
                used_fallback = result.get("used_fallback")
                boom_attempted = result.get("boom_attempted", False)
                align_result = result["align_result"]

                ref_label = ref_channel_name or (f"CH{ref_channel}" if ref_channel else "")

                if align_result and used_fallback == "boom":
                    log(
                        f"    ALIGN {tn_base}: primary '{primary_name}' failed → fallback to boom {ref_label} (CH{ref_channel}), "
                        f"offset {align_result['correction']*1000:+.1f} ms, "
                        f"corr {align_result['corr']:.2f}, window {align_result['window_start']:.0f}-{align_result['window_start'] + align_result['window_dur']:.0f}s",
                        "ok"
                    )
                elif align_result:
                    log(
                        f"    ALIGN {tn_base}: ref {ref_label} (CH{ref_channel}), "
                        f"offset {align_result['correction']*1000:+.1f} ms, "
                        f"corr {align_result['corr']:.2f}, window {align_result['window_start']:.0f}-{align_result['window_start'] + align_result['window_dur']:.0f}s",
                        "ok"
                    )
                elif chan_missing and boom_attempted:
                    log(f"    ALIGN {tn_base}: '{primary_name}' missing in this file and boom fallback failed, using TC", "dim")
                elif chan_missing:
                    log(f"    ALIGN {tn_base}: channel '{primary_name}' not in this recorder file, using TC", "dim")
                elif ref_channel is None and primary_name:
                    # primary resolved earlier but got reset to None somewhere — shouldn't happen, leave a generic line
                    log(f"    ALIGN {tn_base}: no usable reference, using TC", "dim")
                elif primary_name and boom_attempted:
                    log(f"    ALIGN {tn_base}: primary '{primary_name}' and boom fallback both failed, using TC", "dim")
                elif primary_name:
                    log(f"    ALIGN {tn_base}: no reliable match on {primary_name}, using TC", "dim")

                off_str = f"{source_offset:.6f}"
                dur_str_h = f"{source_dur:.6f}"
                gain = 0.0
                if dc["is_float"] and normalize:
                    peak = get_peak_db(tp, source_offset, source_dur)
                    if peak > -1.0:
                        gain = -1.0 - peak
                        log(f"    ↳ {tn_base}  Peak:{round(peak,2)} dBFS  gain:{round(gain,2)} dB", "warn")
                    else:
                        log(f"    ↳ {tn_base}  Peak:{round(peak,2)} dBFS", "dim")
                else:
                    log(f"    ↳ {tn_base}  [{dc['bps']}-bit]", "normal")
                ti = get_tx_info(os.path.splitext(tn_base)[0], tx_profile, tx_track_prefix)
                hits.append({"file":tp,"name":tn_base,"track_name":ti["name"],
                             "offset":off_str,"dur":dur_str_h,"gain":gain,"sr":dc["sr"],
                             "target_channel": target_channel_name})

        # No TX hits: emit a recorder-only POLY so takes aren't lost. In
        # TX-only mode we override the flag for this file and write recorder
        # tracks, with a "No TX signal" note in the iXML so the gap is visible
        # later in the metadata.
        fallback_no_tx = (not hits) and tx_only
        effective_tx_only = tx_only and bool(hits)

        auto_keep_recorder_channels = set()
        if effective_tx_only and align_map:
            hit_targets = {
                str(h.get("target_channel", "")).strip().lower()
                for h in hits if h.get("target_channel")
            }
            expected_targets = {
                str(ch) for ch in align_map.values()
                if ch and not isinstance(ch, int)
            }
            for channel_name in expected_targets:
                if (_resolve_channel_index(channel_name, r_tnames) is not None
                        and channel_name.strip().lower() not in hit_targets):
                    auto_keep_recorder_channels.add(channel_name)
            if auto_keep_recorder_channels:
                log(
                    "    TX missing for mapped recorder channel(s): "
                    + " | ".join(sorted(auto_keep_recorder_channels))
                    + " — keeping recorder audio in TX-only output",
                    "warn"
                )

        if not hits:
            if fallback_no_tx:
                log("    (TX-only + no TX matches — exporting recorder with NO-TX note)", "warn")
            else:
                log("    (no TX matches — exporting recorder-only POLY)", "warn")

        out_path = os.path.join(o_dir, f"{rbase}_POLY.wav")
        if os.path.exists(out_path): log(f"    SKIP (exists): {rbase}_POLY.wav","dim"); continue

        # ── Assemble the TX-only output channel order ─────────────
        # Real TX hits and "missing-TX" recorder fallbacks are sorted TOGETHER
        # so a fallback channel lands exactly where its TX would have been if
        # it had been recorded. Manually kept wired recorder channels always
        # go at the very bottom, under the TX tracks.
        out_channels = []   # ordered list of channels for TX-only output
        keep_names = []     # recorder channel names pulled in (for logging)

        if effective_tx_only:
            def _name_sort_key(name_for_sort):
                ti = get_tx_info(os.path.splitext(name_for_sort)[0], tx_profile, tx_track_prefix)
                if _is_boom_mic(name_for_sort, ti["name"]):
                    return (0, ti["chan_idx"], name_for_sort.lower())
                return (1, ti["chan_idx"], name_for_sort.lower())

            def _tx_name_for_channel(channel_name):
                # Find a TX filename mapped to this recorder channel so the
                # fallback inherits the missing TX's sort position.
                target = channel_name.strip().lower()
                for tcp in tx_cache:
                    base = os.path.basename(tcp)
                    mapped = _lookup_tx_group_value(align_map, base) if align_map else None
                    if mapped and str(mapped).strip().lower() == target:
                        return base
                return None

            auto_lower = {c.strip().lower() for c in auto_keep_recorder_channels}

            # Sortable group: TX hits + missing-TX recorder fallbacks.
            sortable = []
            for h in hits:
                sortable.append({"kind": "tx", "hit": h, "name": h["track_name"],
                                 "sort": _name_sort_key(h["name"])})
            for ch_idx, track_name in enumerate(r_tnames, 1):
                if track_name and track_name.strip().lower() in auto_lower:
                    rep = _tx_name_for_channel(track_name) or track_name
                    sortable.append({"kind": "rec", "rec_idx": ch_idx, "name": track_name,
                                     "sort": _name_sort_key(rep)})
                    keep_names.append(track_name)
            sortable.sort(key=lambda it: it["sort"])

            # Bottom group: manually kept wired recorder channels (skip any
            # already placed as a fallback above).
            manual_lower = {c.strip().lower() for c in keep_recorder_channels}
            bottom = []
            for ch_idx, track_name in enumerate(r_tnames, 1):
                low = track_name.strip().lower() if track_name else ""
                if low and low in manual_lower and low not in auto_lower:
                    bottom.append({"kind": "rec", "rec_idx": ch_idx, "name": track_name})
                    keep_names.append(track_name)

            out_channels = sortable + bottom
            if keep_names:
                log(f"    TX-only keeps recorder: {' | '.join(keep_names)}", "dim")

        ff = ["-loglevel","error","-y"]
        if not effective_tx_only:
            ff += ["-i", rp]
            if hits:
                for h in hits: ff += ["-ss",h["offset"],"-t",h["dur"],"-i",h["file"]]
                parts=[]; merge="[0:a]"
                for j,h in enumerate(hits):
                    ch=f"[{j+1}:a]"
                    if h["sr"]!=r_sr: ch+=f"aresample={int(r_sr)}"+(f",volume={h['gain']:.6f}dB" if h["gain"] else "")
                    elif h["gain"]:   ch+=f"volume={h['gain']:.6f}dB"
                    else:             ch+="anull"
                    ch+=f"[d{j}]"; parts.append(ch); merge+=f"[d{j}]"
                parts.append(f"{merge}amerge=inputs={1+len(hits)}[out]")
            else:
                # Recorder-only pass-through (preserves channel count + sr)
                parts = ["[0:a]anull[out]"]
        else:
            parts = []
            rec_count = sum(1 for c in out_channels if c["kind"] == "rec")
            tx_base = 0
            rec_labels = []
            if rec_count > 0:
                # Recorder is input 0; split it so each kept channel can be
                # panned out independently (a link can't feed two filters).
                ff += ["-i", rp]
                tx_base = 1
                if rec_count == 1:
                    rec_labels = ["[0:a]"]
                else:
                    lbls = "".join(f"[r{i}]" for i in range(rec_count))
                    parts.append(f"[0:a]asplit={rec_count}{lbls}")
                    rec_labels = [f"[r{i}]" for i in range(rec_count)]

            # Add TX inputs in output order and remember their input indices.
            tx_input_idx = {}
            next_idx = tx_base
            for c in out_channels:
                if c["kind"] == "tx":
                    h = c["hit"]
                    ff += ["-ss", h["offset"], "-t", h["dur"], "-i", h["file"]]
                    tx_input_idx[id(h)] = next_idx
                    next_idx += 1

            # Build one filter stream per output channel, in final order.
            merge = ""
            rec_ptr = 0
            for k, c in enumerate(out_channels):
                if c["kind"] == "tx":
                    h = c["hit"]
                    ch = f"[{tx_input_idx[id(h)]}:a]"
                    if h["sr"]!=r_sr: ch+=f"aresample={int(r_sr)}"+(f",volume={h['gain']:.6f}dB" if h["gain"] else "")
                    elif h["gain"]:   ch+=f"volume={h['gain']:.6f}dB"
                    else:             ch+="anull"
                    ch+=f"[c{k}]"
                else:
                    src = rec_labels[rec_ptr]; rec_ptr += 1
                    ch = f"{src}pan=mono|c0=c{c['rec_idx'] - 1}[c{k}]"
                parts.append(ch); merge+=f"[c{k}]"

            if len(out_channels) > 1:
                parts.append(f"{merge}amerge=inputs={len(out_channels)}[out]")
            else:
                parts.append(f"{merge}anull[out]")

        ff += ["-filter_complex",";".join(parts),"-map","[out]"]
        use_float = effective_tx_only and not normalize
        ff += ["-c:a","pcm_f32le" if use_float else "pcm_s24le","-ar",str(int(r_sr))]
        tmp = out_path+".tmp.wav"; ff.append(tmp)
        rc, stderr = run_ffmpeg(ff)
        if stop_event.is_set(): return
        if not os.path.exists(tmp):
            log(f"    ERROR: ffmpeg failed","err")
            for ln in stderr.strip().splitlines()[-5:]:
                if ln.strip(): log(f"      {ln}","err")
            continue

        if effective_tx_only:
            all_names = [c["name"] for c in out_channels]
        else:
            all_names = list(r_tnames) + [h["track_name"] for h in hits]
        extra_note = "No TX signal at this timecode" if fallback_no_tx else ""
        result = build_polywav(out_path, tmp, r_bext, r_ixml, all_names, f"{rbase}_POLY.wav", extra_note=extra_note)
        try: os.remove(tmp)
        except: pass
        if not os.path.exists(out_path):
            log(f"    ERROR: {result}","err"); continue

        sz   = round(os.path.getsize(out_path)/(1024*1024),1)
        n_ch = len(out_channels) if effective_tx_only else r_ch+len(hits)
        log(f"    ✓  {rbase}_POLY.wav   {sz} MB   {n_ch} ch", "ok" if result=="OK" else "warn")
        log(f"       {' | '.join(all_names)}", "dim")
        total_created += 1

    prog(len(r_files), len(r_files), "Done")
    log("─"*60, "dim")
    log(f"Done. PolyWAV files created: {total_created}", "ok")

# ══════════════════════════════════════════════════════════════════
# WORKER THREAD
# ══════════════════════════════════════════════════════════════════

class WorkerSignals(QObject):
    log      = Signal(str, str)   # message, tag
    progress = Signal(int, int, str)  # cur, total, name
    finished = Signal()

class SignalQueue:
    def __init__(self, signal):
        self.signal = signal

    def put(self, item):
        self.signal.emit(*item)

class ProcessWorker(QThread):
    def __init__(self, r_dir, tx_dir, o_dir, normalize, tx_only, tx_profile,
                 align_map=None, filter_by_channel=False, always_include=None,
                 keep_recorder_channels=None, tx_track_prefix="TX",
                 clock_correction=True):
        super().__init__()
        self.r_dir             = r_dir
        self.tx_dir            = tx_dir
        self.o_dir             = o_dir
        self.normalize         = normalize
        self.tx_only           = tx_only
        self.tx_profile        = tx_profile
        self.align_map         = align_map or {}
        self.filter_by_channel = filter_by_channel
        self.always_include    = always_include or set()
        self.keep_recorder_channels = keep_recorder_channels or set()
        self.tx_track_prefix   = tx_track_prefix
        self.clock_correction  = clock_correction
        self.signals           = WorkerSignals()
        self._stop             = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            process_files(
                self.r_dir, self.tx_dir, self.o_dir,
                self.normalize, self.tx_only, self.tx_profile,
                SignalQueue(self.signals.log),
                SignalQueue(self.signals.progress),
                self._stop,
                self.align_map,
                self.filter_by_channel,
                self.always_include,
                self.keep_recorder_channels,
                self.tx_track_prefix,
                self.clock_correction,
            )
        except Exception:
            self.signals.log.emit("ERROR: unexpected processing failure", "err")
            for line in traceback.format_exc().strip().splitlines()[-8:]:
                self.signals.log.emit(f"  {line}", "err")
        finally:
            self.signals.finished.emit()


# ══════════════════════════════════════════════════════════════════
# CUSTOM WIDGETS  (from polywav_merger.py — unchanged)
# ══════════════════════════════════════════════════════════════════

def _apply_dark_dialog_palette(dialog):
    """
    Force a dark QPalette on the dialog so widgets that ignore the
    stylesheet (Windows 11 light theme's native file list, for instance)
    still render readably. Stylesheet handles the rest.
    """
    pal = dialog.palette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(COLORS["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(COLORS["card_inset"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLORS["card"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(COLORS["card"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(COLORS["highlight"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["text"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS["text_muted"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(COLORS["card"]))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLORS["text"]))
    dialog.setPalette(pal)


def select_directory_with_files(parent, label, current_path="", sidebar_paths=None):
    """
    Folder picker that lets the user see files inside folders for orientation.

    Uses Qt's own non-native dialog with ShowDirsOnly=False on every platform
    so .wav files inside folders are visible — both the Win11 native folder
    picker and the macOS Finder folder-picker hide files in folder-select
    mode, which makes it hard to verify "this is the right folder, I see the
    .wav files I expect."

    Readability on any system theme (Win11 light, macOS light) is handled by
    the QFileDialog-scoped stylesheet rules and the explicit dark QPalette.

    `sidebar_paths` are added to the dialog's left sidebar (pinned folders).
    """
    start_dir = current_path if current_path and os.path.isdir(current_path) else ""

    dialog = QFileDialog(parent, f"Select {label}")
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
    dialog.setNameFilters(["WAV files (*.wav)", "All files (*)"])
    _apply_dark_dialog_palette(dialog)
    if sidebar_paths:
        urls = list(dialog.sidebarUrls())
        existing = {u.toLocalFile() for u in urls}
        for p in sidebar_paths:
            if p and os.path.isdir(p) and p not in existing:
                urls.append(QUrl.fromLocalFile(p))
                existing.add(p)
        dialog.setSidebarUrls(urls)
    if start_dir:
        dialog.setDirectory(start_dir)
    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return ""
    selected = dialog.selectedFiles()
    if not selected:
        return ""
    path = selected[0]
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return path

class NeumorphicCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("neumorphicCard")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        radius = CARD_PAINT_RADIUS
        margin = CARD_PAINT_MARGIN
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        shadow_rgb = COLORS["neu_shadow"]
        for i in range(6, 0, -1):
            alpha = int(18 * i / 6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(shadow_rgb[0], shadow_rgb[1], shadow_rgb[2], alpha))
            spread = float(i) * 0.38
            shadow_rect = rect.adjusted(spread, spread + 1.0, -spread, -spread + 1.0)
            painter.drawRoundedRect(shadow_rect, radius, radius)

        edge_rgb = COLORS["neu_edge"]
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(edge_rgb[0], edge_rgb[1], edge_rgb[2], 22))
        painter.drawRoundedRect(rect.adjusted(-0.5, -0.5, 0.5, 0.5), radius, radius)

        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0,  QColor(COLORS["card_light"]))
        gradient.setColorAt(0.55, QColor(COLORS["card"]))
        gradient.setColorAt(1,  QColor(COLORS["card_grad_bottom"]))
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor(*COLORS["card_edge"]), 1))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)

    @staticmethod
    def paint_margin():
        return CARD_PAINT_MARGIN

    @staticmethod
    def content_margins():
        """Layout margins that keep children inside the painted rounded rect."""
        m = NeumorphicCard.paint_margin()
        return (int(m + 12), int(m + 16), int(m + 12), int(m + 14))


class RoundedClipFrame(QFrame):
    """Child clip container with rounded corners (tables, text fields)."""

    def __init__(self, radius=8, parent=None):
        super().__init__(parent)
        self._radius = radius
        self.setObjectName("insetPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        inset = 1.0
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        radius = max(1.0, self._radius - inset)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, QColor(COLORS["card_inset"]))
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_mask()

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_mask()

    def _apply_mask(self):
        if self.width() < 4 or self.height() < 4:
            return
        inset = 1.0
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        radius = max(1.0, self._radius - inset)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class SquircleFolderIcon(QWidget):
    """
    Flat 36×36 squircle with a folder glyph — styled to sit alongside the
    toggle switches: matte dark fill, 1-px border, muted glyph color, no
    gradient, no gloss. A whisper of drop shadow keeps it from looking glued
    to the surrounding card.
    """

    SIZE   = 36
    RADIUS = 10            # ~28 % of size → iOS-squircle proportion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._hovered = False

        # Very subtle drop shadow — just enough to suggest 1 px of elevation
        # without the iOS chiclet feel.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)

    def setHovered(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.SIZE, self.SIZE)
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        # 1. Flat fill — slightly lighter than the surrounding card_inset
        #    so the squircle reads as raised, but matte
        fill = QColor(COLORS["card_light"] if self._hovered else COLORS["card"])
        painter.fillPath(path, fill)

        # 2. 1-px border in the same border color the rest of the UI uses
        border_color = COLORS["highlight"] if self._hovered else COLORS["border"]
        painter.setPen(QPen(QColor(border_color), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                                self.RADIUS - 0.5, self.RADIUS - 0.5)

        # 3. Folder glyph in the muted-grey "text_secondary" colour the
        #    toggle thumb uses when off — same visual weight as the rest
        #    of the iconography
        glyph = QColor(COLORS["text"] if self._hovered else COLORS["text_secondary"])
        ix, iy = 7, 12
        body = QPainterPath()
        body.addRoundedRect(ix, iy + 3, 22, 13, 2.5, 2.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glyph)
        painter.drawPath(body)
        tab = QPainterPath()
        tab.moveTo(ix, iy + 3)
        tab.lineTo(ix, iy + 1)
        tab.quadTo(ix, iy, ix + 2, iy)
        tab.lineTo(ix + 8, iy)
        tab.lineTo(ix + 10, iy + 3)
        tab.closeSubpath()
        painter.drawPath(tab)


class FolderSelector(QWidget):
    pathChanged = Signal(str)

    _ICON_LEFT_MARGIN = 12

    def __init__(self, label: str, pin_key: str = None, parent=None):
        super().__init__(parent)
        self._label   = label
        self._pin_key = pin_key
        self._path    = ""
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        # A bit taller so the QGraphicsDropShadowEffect blur extends past the
        # squircle without getting clipped at top/bottom of the selector card.
        self.setFixedHeight(62)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Take focus on tab/click so Ctrl+V can be received as a keypress.
        self.setFocusPolicy(Qt.StrongFocus)
        # Show our own right-click menu instead of the default (none).
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

        self._icon = SquircleFolderIcon(self)
        self._icon.move(self._ICON_LEFT_MARGIN,
                        (self.height() - self._icon.SIZE) // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._icon.move(self._ICON_LEFT_MARGIN,
                        (self.height() - self._icon.SIZE) // 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height(); radius = 10

        # ── Card background ──────────────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)
        painter.fillPath(path, QColor(COLORS["card_inset"]))
        inner_shadow = QLinearGradient(0, 0, 0, 12)
        inner_shadow.setColorAt(0, QColor(0, 0, 0, 50))
        inner_shadow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(path, inner_shadow)
        border_color = COLORS["highlight"] if self._hovered else COLORS["border"]
        painter.setPen(QPen(QColor(border_color), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, radius, radius)

        # ── Path / placeholder text ─────────────────────────────
        # (squircle icon is a child widget — paints itself on top of us)
        text_x = self._ICON_LEFT_MARGIN + SquircleFolderIcon.SIZE + 12
        right_pad = 16
        text_color = COLORS["text"] if self._path else COLORS["text_secondary"]
        painter.setPen(QColor(text_color))
        font = QFont(); font.setPixelSize(14); painter.setFont(font)
        text = self._path if self._path else f"Click to select {self._label}..."
        metrics = painter.fontMetrics()
        text = metrics.elidedText(text, Qt.ElideMiddle, w - text_x - right_pad)
        painter.drawText(text_x, 0, w - text_x - right_pad, h,
                         Qt.AlignVCenter | Qt.AlignLeft, text)

    def enterEvent(self, e):
        self._hovered = True
        self._icon.setHovered(True)
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self._icon.setHovered(False)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Let contextMenuEvent handle it
            super().mousePressEvent(event)
            return
        # Left/middle click → folder picker
        self.setFocus(Qt.MouseFocusReason)
        folder = select_directory_with_files(
            self, self._label, self._path, sidebar_paths=self._load_pins())
        if folder:
            self._set_path_if_valid(folder)

    # ── Pinned folders ───────────────────────────────────────────
    def _pins_key(self):
        return f"pins/{self._pin_key}" if self._pin_key else None

    def _load_pins(self):
        if not self._pin_key:
            return []
        return load_string_list(self._pins_key())

    def _save_pins(self, pins):
        if self._pin_key:
            save_setting(self._pins_key(), pins)

    def _add_pin(self, path):
        if not (self._pin_key and path and os.path.isdir(path)):
            return
        pins = self._load_pins()
        if path not in pins:
            pins.append(path)
            self._save_pins(pins)

    def _remove_pin(self, path):
        self._save_pins([p for p in self._load_pins() if p != path])

    def contextMenuEvent(self, event):
        """Right-click → Paste path from clipboard."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['highlight']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['border']};
                margin: 4px 6px;
            }}
        """)
        menu.setToolTipsVisible(True)
        paste_action = menu.addAction("Paste path")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self._paste_from_clipboard)
        if self._path:
            menu.addSeparator()
            copy_action = menu.addAction("Copy current path")
            copy_action.setShortcut(QKeySequence.Copy)
            copy_action.triggered.connect(self._copy_to_clipboard)
            clear_action = menu.addAction("Clear")
            clear_action.triggered.connect(self._clear_path)

        if self._pin_key:
            pins = self._load_pins()
            fm = self.fontMetrics()
            menu.addSeparator()
            if self._path and self._path not in pins:
                pin_action = menu.addAction("Pin current folder")
                pin_action.triggered.connect(
                    lambda checked=False, p=self._path: self._add_pin(p))
            if pins:
                header = menu.addAction("Pinned folders")
                header.setEnabled(False)
                for p in pins:
                    act = menu.addAction(fm.elidedText(p, Qt.ElideMiddle, 360))
                    act.setToolTip(p)
                    if not os.path.isdir(p):
                        act.setEnabled(False)
                    act.triggered.connect(
                        lambda checked=False, path=p: self._set_path_if_valid(path))
                remove_menu = menu.addMenu("Remove pin")
                for p in pins:
                    ra = remove_menu.addAction(fm.elidedText(p, Qt.ElideMiddle, 360))
                    ra.setToolTip(p)
                    ra.triggered.connect(
                        lambda checked=False, path=p: self._remove_pin(path))
        menu.exec(event.globalPos())

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self._paste_from_clipboard()
            event.accept()
        elif event.matches(QKeySequence.Copy):
            self._copy_to_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _paste_from_clipboard(self):
        text = (QApplication.clipboard().text() or "").strip()
        # Strip surrounding quotes (Windows Explorer / shell typically wrap
        # paths with spaces in double quotes on copy).
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            text = text[1:-1]
        # Normalize separators (Windows users sometimes paste forward-slash paths).
        text = text.strip()
        if not text:
            return
        self._set_path_if_valid(text)

    def _copy_to_clipboard(self):
        if self._path:
            QApplication.clipboard().setText(self._path)

    def _clear_path(self):
        if self._path:
            self._path = ""
            self.pathChanged.emit("")
            self.update()

    def _set_path_if_valid(self, candidate):
        """Accept the candidate if it's a folder; if it's a file, use its parent."""
        if not candidate:
            return False
        if os.path.isdir(candidate):
            self._path = candidate
            self.pathChanged.emit(candidate)
            self.update()
            return True
        if os.path.isfile(candidate):
            parent = os.path.dirname(candidate)
            if parent and os.path.isdir(parent):
                self._path = parent
                self.pathChanged.emit(parent)
                self.update()
                return True
        return False

    def path(self): return self._path
    def setPath(self, p): self._path=p; self.update()


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, text: str, description: str="", parent=None):
        super().__init__(parent)
        self._text        = text
        self._description = description
        self._checked     = False
        self._enabled     = True
        self._thumb_pos   = 0.0
        self.setCursor(Qt.PointingHandCursor)
        # Uniform height across all toggles. The two-line variant previously
        # used 64 px which left ~30 px of empty space below the description
        # text — that made the gap to the next toggle look bigger than the
        # gap between two single-line toggles.
        self.setFixedHeight(48)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._anim_target = 0.0

    def _animate(self):
        diff = self._anim_target - self._thumb_pos
        if abs(diff) < 0.01:
            self._thumb_pos = self._anim_target
            self._timer.stop()
        else:
            self._thumb_pos += diff*0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        tw, th = 48, 28
        # Track sits at the same Y regardless of single/double-line content
        # so visual gaps between toggles stay uniform.
        tx, ty = 14, 10
        track_path = QPainterPath()
        track_path.addRoundedRect(tx, ty, tw, th, th//2, th//2)
        if self._checked:
            painter.fillPath(track_path, QColor(COLORS["accent"]))
        else:
            painter.fillPath(track_path, QColor(COLORS["card_inset"]))
            ig = QLinearGradient(tx, ty, tx, ty+8)
            ig.setColorAt(0, QColor(0,0,0,40)); ig.setColorAt(1, QColor(0,0,0,0))
            painter.fillPath(track_path, ig)
            painter.setPen(QPen(QColor(COLORS["border"]),1))
            painter.drawRoundedRect(tx, ty, tw-1, th-1, th//2, th//2)
        ts = 22; tm = 3
        travel = tw - ts - tm*2
        thumb_x = tx + tm + travel*self._thumb_pos
        thumb_y = ty + tm
        if not self._checked:
            painter.setBrush(QColor(0,0,0,30)); painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(thumb_x)+1, int(thumb_y)+1, ts, ts)
        tc = COLORS["bg"] if self._checked else COLORS["text_secondary"]
        painter.setBrush(QColor(tc)); painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(thumb_x), int(thumb_y), ts, ts)
        if self._checked and self._thumb_pos > 0.6:
            op = min(1.0,(self._thumb_pos-0.6)/0.4)
            cc = QColor(COLORS["accent"]); cc.setAlphaF(op)
            painter.setPen(QPen(cc, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            cx = int(thumb_x+ts//2); cy = int(thumb_y+ts//2)
            painter.drawLine(cx-4,cy,cx-1,cy+4)
            painter.drawLine(cx-1,cy+4,cx+5,cy-3)
        text_x = tx+tw+14
        text_color = COLORS["text"] if self._enabled else COLORS["text_muted"]
        painter.setPen(QColor(text_color))
        font = QFont(); font.setPixelSize(14); font.setWeight(QFont.Medium)
        painter.setFont(font)
        if self._description:
            painter.drawText(text_x, ty+3, self._text)
            painter.setPen(QColor(COLORS["text_muted"]))
            font.setPixelSize(12); font.setWeight(QFont.Normal)
            painter.setFont(font)
            painter.drawText(text_x, ty+22, self._description)
        else:
            painter.drawText(text_x, 0, w-text_x, h, Qt.AlignVCenter, self._text)

    def mousePressEvent(self, event):
        if not self._enabled: return
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)

    def isChecked(self): return self._checked
    def setChecked(self, v):
        if self._checked == v: return
        self._checked = v
        self._anim_target = 1.0 if v else 0.0
        self._timer.start(16)

    def setEnabled(self, v):
        self._enabled = v
        self.setCursor(Qt.PointingHandCursor if v else Qt.ForbiddenCursor)
        self.update()

    def isEnabled(self): return self._enabled


class PrimaryButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: none;")
        self._pressed = False
        self._danger  = False
        self._hovered = False

    def setDanger(self, v): self._danger=v; self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        radius = 12.0
        rect = QRectF(6, 4, w - 12, h - 10)
        if not self._pressed:
            shadow_rgb = COLORS["neu_shadow"]
            for i in range(5, 0, -1):
                alpha = int(16 * i / 5)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(shadow_rgb[0], shadow_rgb[1], shadow_rgb[2], alpha))
                spread = float(i) * 0.32
                painter.drawRoundedRect(
                    rect.adjusted(spread, spread + 1, -spread, -spread + 1),
                    radius, radius)
        path = QPainterPath()
        off = 2.0 if self._pressed else 0.0
        button_rect = rect.translated(off, off)
        path.addRoundedRect(button_rect, radius, radius)
        if self._danger:
            btn_color = QColor(COLORS["error"])
        else:
            btn_color = QColor(COLORS["accent_hover"]) if self._hovered else QColor(COLORS["accent"])
        painter.fillPath(path, btn_color)
        painter.setPen(QColor(COLORS["on_accent"]))
        font = QFont(); font.setPixelSize(14); font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(button_rect, Qt.AlignCenter, self.text())

    def enterEvent(self, e):  self._hovered=True;  self.update()
    def leaveEvent(self, e):  self._hovered=False; self.update()
    def mousePressEvent(self, e):   self._pressed=True;  self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self, e): self._pressed=False; self.update(); super().mouseReleaseEvent(e)


class LogoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 40)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._icon_pixmap = None
        self._try_load_icon()

    def _try_load_icon(self):
        for name in ["icon.png", "icon_512.png"]:
            p = resource_path(name)
            if p:
                px = QPixmap(p).scaled(40, 40, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
                self._icon_pixmap = px
                self.setFixedSize(48, 40)
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self._icon_pixmap:
            x = (w - self._icon_pixmap.width()) // 2
            y = (h - self._icon_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._icon_pixmap)
            return
        # Fallback — ((o)) logo
        cx, cy = w//2, h//2
        white = QColor(COLORS["text"])
        glow  = QColor(255,255,255,40)
        for i in range(3,0,-1):
            glow.setAlpha(20*i)
            pen = QPen(glow, 3+i*1.5); pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(cx-28,cy-12,20,24,120*16,120*16)
            painter.drawArc(cx-22,cy-10,16,20,125*16,110*16)
            painter.drawArc(cx+8, cy-12,20,24,-60*16,-120*16)
            painter.drawArc(cx+6, cy-10,16,20,-55*16,-110*16)
        pen = QPen(white,2.5); pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(cx-28,cy-12,20,24,120*16,120*16)
        painter.drawArc(cx-22,cy-10,16,20,125*16,110*16)
        painter.drawArc(cx+8, cy-12,20,24,-60*16,-120*16)
        painter.drawArc(cx+6, cy-10,16,20,-55*16,-110*16)
        painter.setPen(Qt.NoPen)
        for i in range(4,0,-1):
            glow.setAlpha(25*i); painter.setBrush(glow)
            r=4+i*2; painter.drawEllipse(cx-r,cy-r,r*2,r*2)
        painter.setBrush(white)
        painter.drawEllipse(cx-4,cy-4,8,8)


class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
    def wheelEvent(self, e): e.ignore()


class NeumorphicProgressBar(QProgressBar):
    """
    Progress bar with custom paint so the fill stays inside the rounded
    pill shape.

    Qt's default QProgressBar::chunk styling honours border-radius only on
    the chunk itself, not on the parent's rounded border. The chunk ends up
    rectangular (sharp top-left/bottom-left corners) inside a rounded bar.
    Custom painting lets us draw both the track and the chunk as proper
    pills sharing the same radius.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self._disp = 0.0        # animated display ratio (smoothed)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_tick)

    def _target_ratio(self):
        vmin = float(self.minimum())
        vmax = float(self.maximum())
        val = float(self.value())
        return max(0.0, min(1.0, (val - vmin) / (vmax - vmin))) if vmax > vmin else 0.0

    def _on_anim_tick(self, v):
        self._disp = float(v)
        self.update()

    def setValue(self, value):
        super().setValue(value)
        target = self._target_ratio()
        # Snap instantly on reset to zero; otherwise glide to the new value.
        if target <= 0.0:
            self._anim.stop()
            self._disp = 0.0
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(float(self._disp))
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        radius = h / 2.0
        track_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)
        painter.fillPath(track_path, QColor(COLORS["card_inset"]))

        # Subtle inner shadow at the top to anchor the bar visually
        inner = QLinearGradient(0, 0, 0, h * 0.5)
        inner.setColorAt(0, QColor(0, 0, 0, 60))
        inner.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(track_path, inner)

        ratio = max(0.0, min(1.0, self._disp))

        inset = 2.0
        inner_w = max(0.0, (w - 2.0 * inset) * ratio)
        if inner_w > 0:
            chunk_rect = QRectF(inset, inset, inner_w, h - 2.0 * inset)
            chunk_radius = max(0.0, (h - 2.0 * inset) / 2.0)

            # Use a smaller radius when the chunk is shorter than its height
            # so the leading edge stays inside the bar (avoid visual overflow).
            if chunk_rect.width() < chunk_radius * 2:
                chunk_radius = chunk_rect.width() / 2.0

            chunk_path = QPainterPath()
            chunk_path.addRoundedRect(chunk_rect, chunk_radius, chunk_radius)

            grad = QLinearGradient(0, chunk_rect.top(), 0, chunk_rect.bottom())
            grad.setColorAt(0.0, QColor(COLORS["prog_a"]))
            grad.setColorAt(0.5, QColor(COLORS["prog_b"]))
            grad.setColorAt(1.0, QColor(COLORS["prog_c"]))
            painter.fillPath(chunk_path, QBrush(grad))

        # Outline (1 px) matching the bar's pill shape
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(track_path)

def _recorder_channel_names(path):
    """Read the channel names from a single recorder file."""
    try:
        hdr = read_header(path, 200000)
        chunks = read_riff_chunks(hdr)
        fmt = parse_fmt(hdr, chunks)
        ixml = parse_recorder_ixml(hdr, chunks)
        ch_count = fmt["channels"] if fmt else 0
        names = list(ixml["track_names"]) if ixml else []
        if not names:
            if ch_count == 1:
                names = ["MIX"]
            elif ch_count == 2:
                names = ["L", "R"]
            else:
                names = [f"CH{i}" for i in range(1, ch_count + 1)]
        while len(names) < ch_count:
            names.append(f"CH{len(names) + 1}")
        return names[:ch_count]
    except Exception:
        return []

def get_all_recorder_channel_names(r_dir):
    """
    Aggregate channel names across ALL recorder files in r_dir.

    Track layouts can change between files in a session (e.g. an LAV gets
    added partway through). Scanning only the first file means later
    channels never appear in the mapping dialog. We preserve first-appearance
    order so the canonical layout still leads, with later additions appended.
    Returns a deduplicated list (case-insensitive de-dup, case-preserving).
    """
    r_files = sorted([f for f in os.listdir(r_dir) if f.lower().endswith(".wav")])
    if not r_files:
        return []
    seen_lower = set()
    out = []
    for fn in r_files:
        for n in _recorder_channel_names(os.path.join(r_dir, fn)):
            if not n:
                continue
            key = n.strip().lower()
            if key in seen_lower:
                continue
            seen_lower.add(key)
            out.append(n)
    return out

def get_first_recorder_channels(r_dir):
    """Back-compat shim — single-file channel list."""
    r_files = sorted([f for f in os.listdir(r_dir) if f.lower().endswith(".wav")])
    if not r_files:
        return []
    return _recorder_channel_names(os.path.join(r_dir, r_files[0]))

def _resolve_channel_index(channel_name, track_names):
    """Find the 1-based index of `channel_name` in `track_names` (case-insensitive)."""
    if not channel_name or not track_names:
        return None
    target = channel_name.strip().lower()
    for i, name in enumerate(track_names, 1):
        if name and name.strip().lower() == target:
            return i
    return None

def _find_boom_channel(track_names):
    """Return (1-based index, name) of the first boom-mic channel in
    `track_names`, or (None, None) if no boom channel is present."""
    if not track_names:
        return None, None
    for i, name in enumerate(track_names, 1):
        if name and _is_boom_mic(name):
            return i, name
    return None, None

def _name_tokens(name):
    """Extract name tokens, handling similar letters/digits"""
    base = os.path.splitext(os.path.basename(name))[0].lower()
    base = re.sub(r"(tx|lav|dbtx|dxtx|poly|wav|iso|track|trk)", " ", base)
    tokens = [t for t in re.split(r"[^a-z0-9а-яё]+", base) if len(t) >= 2]

    # Normalize similar-looking characters
    # L4 ~ LV4 ~ LAV4 ~ L-V-4
    normalized = []
    for token in tokens:
        # Replace common variations
        norm = token.replace("v", "u").replace("ü", "u")  # V↔U
        norm = norm.replace("0", "o")  # 0↔O
        norm = norm.replace("1", "i").replace("l", "i")  # 1↔I↔L
        normalized.append((token, norm))

    return tokens, normalized

def _clean_alnum(s):
    """Lowercase alphanumeric-only — used for prefix comparison."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def _prefix_similarity(tx_str, channel_str, max_chars=6):
    """
    Compare the first `max_chars` alphanumeric characters of two names.
    Designed for cases like LAV4_002 ≈ LAV4, Alex_TX_001 ≈ Alex,
    BOOM_05 ≈ BOOM, L4 ≈ LAV4.
    """
    a = _clean_alnum(os.path.splitext(os.path.basename(tx_str))[0])[:max_chars]
    b = _clean_alnum(channel_str)[:max_chars]
    if not a or not b:
        return 0

    # Strongest signal: one starts with the other ("lav4" prefix of "lav402")
    if a.startswith(b) or b.startswith(a):
        return min(len(a), len(b)) * 3

    # Substring (handles TX prefixes: "txboom" contains "boom")
    if b in a or a in b:
        return min(len(a), len(b)) * 2

    # Positional match (rough — half weight)
    n = min(len(a), len(b))
    matches = sum(1 for i in range(n) if a[i] == b[i])
    return matches

def guess_reference_channel(tx_file, tx_track_name, channel_labels):
    """
    Improved channel guessing with better pattern matching.
    Recognizes similar letters/digits: LAV4 ≈ L4 ≈ LV4, etc.

    First-6-chars prefix similarity is the dominant signal — it handles the
    common case where transmitter files are named "LAV4_002.wav",
    "LAV4_005.wav" and the recorder channel is just "LAV4".
    """
    tx_tokens, tx_norm = _name_tokens(tx_file)
    tx_track_tokens, tx_track_norm = _name_tokens(tx_track_name)

    # Combine both sources
    tx_all_tokens = set(tx_tokens + [t for t, _ in tx_track_tokens])
    tx_norm_tokens = set([norm for _, norm in tx_norm + tx_track_norm])

    best_idx = 0
    best_score = 0

    for idx, label in enumerate(channel_labels, 1):
        label_tokens, label_norm = _name_tokens(label)
        label_norm_tokens = set([norm for _, norm in label_norm])

        score = 0

        # Primary: first-6-chars prefix similarity between TX file/track name and channel label
        prefix_score = max(
            _prefix_similarity(tx_file, label, 6),
            _prefix_similarity(tx_track_name, label, 6),
        )
        score += prefix_score * 2

        # Exact token matching
        common_tokens = tx_all_tokens & set(label_tokens)
        score += len(common_tokens) * 5

        # Normalized token matching (handles L4 ≈ LAV4)
        common_norm = tx_norm_tokens & label_norm_tokens
        score += len(common_norm) * 3

        # Boom/lav detection
        tx_is_boom = any(t in {"bm", "boom", "boompole"} for t in tx_all_tokens)
        label_is_boom = any(t in {"bm", "boom", "boompole"} for t in label_tokens)
        if tx_is_boom and label_is_boom:
            score += 8

        tx_is_lav = any(t in {"lav", "lavalier"} for t in tx_all_tokens)
        label_is_lav = any(t in {"lav", "lavalier"} for t in label_tokens)
        if tx_is_lav and label_is_lav:
            score += 8

        # Digit matching
        tx_digits = set(re.findall(r"\d+", tx_file + tx_track_name))
        label_digits = set(re.findall(r"\d+", label))
        if tx_digits and tx_digits & label_digits:
            score += 4

        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx if best_score >= 4 else 0

def guess_tx_channel_name(tx_file, tx_track_name, channel_labels):
    """Return the channel NAME (not index) that best matches `tx_file`,
    or None if no plausible match (score < threshold)."""
    idx = guess_reference_channel(tx_file, tx_track_name, channel_labels)
    if idx and 1 <= idx <= len(channel_labels):
        return channel_labels[idx - 1]
    return None

def _tx_group_label(filename):
    """Return a stable TX-device label from a file name.

    The goal is to group files from the same recorder/transmitter:
      BOOM_TX_01.wav, BOOM_TX_02.wav -> BOOM_TX
      LAV4_002.wav, LAV4_005.wav     -> LAV4
      TX_SASHA_A001.wav              -> TX_SASHA
      MTP61_L1_0003.wav              -> MTP61_L1

    We only strip suffixes that look like take/file counters at the END of the
    name. Embedded device numbers like MTP61 or L1 are kept.
    """
    base = os.path.splitext(os.path.basename(str(filename)))[0].strip()
    if not base:
        return "TX"

    parts = [p for p in re.split(r"[_\-\.\s]+", base) if p]
    if len(parts) <= 1:
        return base

    def looks_like_counter(token):
        t = token.upper()
        if re.fullmatch(r"\d{2,6}", t):
            return True
        if re.fullmatch(r"[A-Z]\d{2,6}", t):
            return True
        if re.fullmatch(r"(TAKE|TAK|TK|T)\d{1,6}", t):
            return True
        if re.fullmatch(r"(FILE|F)\d{1,6}", t):
            return True
        return False

    while len(parts) > 1 and looks_like_counter(parts[-1]):
        parts.pop()

    return "_".join(parts) or base

def group_tx_files(tx_files, tx_profile, tx_track_prefix="TX"):
    """Group TX files by likely transmitter/recorder device prefix."""
    groups = {}
    for tx_file in sorted(tx_files):
        label = _tx_group_label(tx_file)
        key = _clean_alnum(label) or _clean_alnum(tx_file) or tx_file.lower()
        if key not in groups:
            track = get_tx_info(label, tx_profile, tx_track_prefix)["name"]
            groups[key] = {
                "key": key,
                "label": label,
                "track": track,
                "files": [],
            }
        groups[key]["files"].append(tx_file)

    def group_sort_key(group):
        ti = get_tx_info(group["label"], tx_profile, tx_track_prefix)
        boom = 0 if _is_boom_mic(group["label"], group["track"]) else 1
        return (boom, ti["chan_idx"], group["label"].lower())

    return sorted(groups.values(), key=group_sort_key)

class ChannelMappingDialog(QDialog):
    # Compact combo / checkbox styles scoped to the dialog so the global
    # 14px-padding QComboBox style doesn't overflow the table rows. Built per
    # instance (not at class scope) so they follow live theme changes.
    @staticmethod
    def _build_combo_style():
        return f"""
        QComboBox {{
            background-color: {COLORS['card_inset']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            color: {COLORS['text']};
            min-height: 24px;
        }}
        QComboBox:hover {{ border-color: {COLORS['highlight']}; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {COLORS['text_secondary']};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS['card']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 4px;
            selection-background-color: {COLORS['card_inset']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 12px;
            border-radius: 6px;
        }}
    """

    @staticmethod
    def _build_checkbox_style():
        return f"""
        QCheckBox {{
            background: transparent;
            spacing: 0px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {COLORS['border']};
            border-radius: 5px;
            background-color: {COLORS['card_inset']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {COLORS['highlight']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {COLORS['accent']};
            border-color: {COLORS['accent']};
            image: none;
        }}
    """

    def __init__(self, parent, tx_files, channel_labels, tx_profile, tx_track_prefix="TX"):
        super().__init__(parent)
        self._COMBO_STYLE = self._build_combo_style()
        self._CHECKBOX_STYLE = self._build_checkbox_style()
        self.setWindowTitle("TX / Recorder Mapping")
        self.setMinimumSize(980, 660)
        # Force dark background + palette so the dialog stays readable under
        # Win11 / macOS light system themes (same white-on-white bug we
        # fixed for QFileDialog — QDialog otherwise falls through to system bg).
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}")
        _apply_dark_dialog_palette(self)
        self._channel_labels = channel_labels
        self._tx_groups = group_tx_files(tx_files, tx_profile, tx_track_prefix)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Match TX groups to recorder reference channels")
        title.setStyleSheet(f"font-size: 17px; font-weight: 600; color: {COLORS['text']}; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Files with the same stable prefix are grouped automatically, so BOOM_TX_01, "
            "BOOM_TX_02 and BOOM_TX_03 are mapped once. Reference channel is used for "
            "clock-drift alignment and for deciding whether the TX belongs to each take. "
            "Tick 'Always include' for autonomous plant mics that should bypass this rule."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; background: transparent;")
        layout.addWidget(subtitle)

        self.table = QTableWidget(len(self._tx_groups), 4)
        self.table.setHorizontalHeaderLabels(["TX group", "Files", "Recorder reference", "Always include"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['card_inset']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                gridline-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['text_secondary']};
                border: none;
                padding: 10px;
                font-weight: 600;
            }}
        """)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        # Width for the reference-channel column fits "8: <longest-name>" comfortably.
        longest_label = max((len(lbl) for lbl in channel_labels), default=8)
        header.resizeSection(2, max(220, 18 + 9 * (longest_label + 4)))
        header.resizeSection(3, 130)

        self._rows = []
        for row, group in enumerate(self._tx_groups):
            label = group["label"]
            track = group["track"]
            files = group["files"]
            examples = ", ".join(files[:3])
            if len(files) > 3:
                examples += f" +{len(files) - 3}"
            group_item = QTableWidgetItem(f"{label}*")
            group_item.setToolTip("\n".join(files))
            self.table.setItem(row, 0, group_item)
            files_item = QTableWidgetItem(f"{len(files)} file{'s' if len(files) != 1 else ''}: {examples}")
            files_item.setToolTip("\n".join(files))
            self.table.setItem(row, 1, files_item)
            self.table.setRowHeight(row, 52)

            # ── Reference channel combo ─────────────────────────
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(8, 8, 8, 8)
            cell_layout.setSpacing(0)
            combo = NoScrollComboBox()
            combo.setStyleSheet(self._COMBO_STYLE)
            combo.setFixedHeight(36)
            # Store channel NAME as data — the index can differ across recorder
            # files in a session, so we resolve the name → index per-file when
            # the alignment actually runs.
            combo.addItem("No target / include by TC", "")
            for label in channel_labels:
                combo.addItem(label, label)
            guess = guess_reference_channel(group["label"], track, channel_labels)
            if not guess and files:
                guess = guess_reference_channel(files[0], track, channel_labels)
            combo.setCurrentIndex(guess if guess else 0)
            cell_layout.addWidget(combo, 1)
            self.table.setCellWidget(row, 2, cell)

            # ── Always-include checkbox ─────────────────────────
            check_cell = QWidget()
            check_layout = QHBoxLayout(check_cell)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setSpacing(0)
            check_layout.setAlignment(Qt.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setStyleSheet(self._CHECKBOX_STYLE)
            check_layout.addWidget(checkbox)
            self.table.setCellWidget(row, 3, check_cell)

            self._rows.append((group, combo, checkbox))
        layout.addWidget(self.table, 1)

        keep_title = QLabel("Recorder channels to keep in TX-only mode")
        keep_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_secondary']}; background: transparent;")
        layout.addWidget(keep_title)

        keep_hint = QLabel("These recorder tracks are kept when TX Only Mode is enabled. Leave all unchecked for pure TX-only output.")
        keep_hint.setWordWrap(True)
        keep_hint.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(keep_hint)

        keep_box = QWidget()
        keep_grid = QGridLayout(keep_box)
        keep_grid.setContentsMargins(0, 0, 0, 0)
        keep_grid.setHorizontalSpacing(18)
        keep_grid.setVerticalSpacing(8)
        self._keep_checks = []
        cols = 3
        for i, label in enumerate(channel_labels):
            cb = QCheckBox(label)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {COLORS['text_secondary']};
                    background: transparent;
                    spacing: 8px;
                    font-size: 12px;
                }}
                {self._CHECKBOX_STYLE}
            """)
            keep_grid.addWidget(cb, i // cols, i % cols)
            self._keep_checks.append((label, cb))
        layout.addWidget(keep_box)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cont = QPushButton("Continue")
        for btn in [cancel, cont]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['card_inset']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                    padding: 10px 20px;
                    color: {COLORS['text']};
                    font-size: 13px;
                }}
                QPushButton:hover {{ border-color: {COLORS['highlight']}; }}
            """)
        cont.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                border: 1px solid {COLORS['accent']};
                border-radius: 10px;
                padding: 10px 20px;
                color: {COLORS['on_accent']};
                font-weight: 600;
                font-size: 13px;
            }}
        """)
        cancel.clicked.connect(self.reject)
        cont.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(cont)
        layout.addLayout(buttons)

    def mapping(self):
        """Return (align_map, always_include, keep_recorder_channels).

        align_map      — {tx_filename: channel_name_str} for clock-drift alignment.
        always_include — set of tx_filenames that bypass the per-recorder
                         channel-presence filter (autonomous plant mics etc.)
        keep_recorder_channels — set of recorder channel names retained in TX-only.
        Both dicts/sets include the filename with AND without extension so
        lookups work regardless of which form the caller uses.
        """
        align_map = {}
        always_include = set()
        for group, combo, checkbox in self._rows:
            channel = combo.currentData()
            for tx_file in group["files"]:
                base = os.path.splitext(tx_file)[0]
                if channel:
                    align_map[tx_file] = str(channel)
                    align_map[base] = str(channel)
                    align_map[group["key"]] = str(channel)
                if checkbox.isChecked():
                    always_include.add(tx_file)
                    always_include.add(base)
                    always_include.add(group["key"])
        keep_recorder_channels = {
            label for label, checkbox in self._keep_checks if checkbox.isChecked()
        }
        return align_map, always_include, keep_recorder_channels

    def mapped_group_count(self):
        return sum(1 for _, combo, _ in self._rows if combo.currentData())

    def always_include_group_count(self):
        return sum(1 for _, _, checkbox in self._rows if checkbox.isChecked())


# ══════════════════════════════════════════════════════════════════
# ACCENT SWATCH  (light-theme candy-colour picker)
# ══════════════════════════════════════════════════════════════════

class AccentPickerButton(QWidget):
    """Compact toolbar control — shows current accent and opens the palette menu."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setMinimumWidth(92)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._hovered = False
        self._hp = 0.0
        self._target = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def _animate(self):
        diff = self._target - self._hp
        if abs(diff) < 0.02:
            self._hp = self._target
            self._timer.stop()
        else:
            self._hp += diff * 0.28
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self._target = 1.0
        if not self._timer.isActive():
            self._timer.start(16)

    def leaveEvent(self, e):
        self._hovered = False
        self._target = 0.0
        if not self._timer.isActive():
            self._timer.start(16)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        radius = 10.0
        t = self._hp
        fill = _lerp_color(COLORS["card_inset"], COLORS["card_light"], t)
        border = _lerp_color(COLORS["border"], COLORS["accent"], max(t, 0.35))
        rect = QRectF(0.5, 0.5, w - 1, h - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, fill)
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, radius, radius)
        chip_r = 6.0
        cx = 14.0
        cy = h / 2.0
        grad = QLinearGradient(cx - chip_r, cy - chip_r, cx + chip_r, cy + chip_r)
        base = QColor(COLORS["accent"])
        grad.setColorAt(0, base.lighter(112))
        grad.setColorAt(1, base.darker(108))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(QRectF(cx - chip_r, cy - chip_r, chip_r * 2, chip_r * 2))
        p.setPen(QColor(COLORS["text_secondary"]))
        font = QFont()
        font.setPixelSize(12)
        font.setWeight(QFont.Medium)
        p.setFont(font)
        p.drawText(QRectF(28, 0, w - 32, h), Qt.AlignVCenter | Qt.AlignLeft, "Accent")


class AccentMenuRow(QWidget):
    """One accent option row — chip + label, for the vertical palette popup."""
    clicked = Signal(str)

    def __init__(self, accent_id, color_hex, parent=None):
        super().__init__(parent)
        self.accent_id = accent_id
        self._selected = False
        self._hovered = False
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(6, 2, 10, 2)
        hl.setSpacing(10)
        self._chip = AccentSwatchButton(accent_id, color_hex)
        self._chip.clicked.connect(lambda: self.clicked.emit(accent_id))
        hl.addWidget(self._chip)
        self._label = QLabel(accent_id.capitalize())
        self._label.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 12px; background: transparent;")
        hl.addWidget(self._label, 1)

    def setSelected(self, on):
        if self._selected != on:
            self._selected = on
            self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.accent_id)

    def paintEvent(self, _e):
        if not (self._hovered or self._selected):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        fill = QColor(COLORS["accent"])
        fill.setAlpha(28 if self._selected else 16)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.fillPath(path, fill)


class AccentPalettePopup(QFrame):
    """Rounded vertical accent picker — one colour per row."""
    picked = Signal(str)
    _RADIUS = 14.0

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setObjectName("accentPopupRoot")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        pl = QVBoxLayout(self)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.setSpacing(2)
        self._rows = []
        presets = accent_presets()
        for aid in ACCENT_IDS:
            preset = presets.get(aid) or DARK_ACCENTS.get(aid, {})
            row = AccentMenuRow(aid, preset.get("accent", COLORS["accent"]))
            row.clicked.connect(self._on_pick)
            pl.addWidget(row)
            self._rows.append(row)
        self._sync_selection()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        radius = self._RADIUS - 1.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, QColor(COLORS["card"]))
        pen = QPen(QColor(COLORS["border"]), 1)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def _sync_selection(self):
        cur = current_accent()
        for row in self._rows:
            row.setSelected(row.accent_id == cur)

    def _on_pick(self, accent_id):
        self.picked.emit(accent_id)
        self.close()


class AccentSwatchButton(QWidget):
    """Small circular colour chip — Skittles-style accent picker for light theme."""
    clicked = Signal(str)
    SIZE = 32
    CHIP_R = 8.0

    def __init__(self, accent_id, color_hex, parent=None):
        super().__init__(parent)
        self.accent_id = accent_id
        self.color_hex = color_hex
        self._selected = False
        self._hovered = False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(accent_id.capitalize())

    def setSelected(self, on):
        if self._selected != on:
            self._selected = on
            self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.accent_id)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = self.CHIP_R
        # Chip — fixed size so hover/selection never clips the widget bounds.
        chip_grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        base = QColor(self.color_hex)
        chip_grad.setColorAt(0, base.lighter(115))
        chip_grad.setColorAt(1, base.darker(108))
        p.setPen(Qt.NoPen)
        p.setBrush(chip_grad)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        if self._selected:
            ring_r = r + 2.0
            p.setPen(QPen(QColor(COLORS["accent"]), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2))
        elif self._hovered:
            p.setPen(QPen(QColor(COLORS["highlight"]), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(cx - r - 1.5, cy - r - 1.5, (r + 1.5) * 2, (r + 1.5) * 2))


# ══════════════════════════════════════════════════════════════════
# NAV BUTTON  (custom tab / theme button with animated hover)
# ══════════════════════════════════════════════════════════════════

def _lerp_color(a, b, t):
    """Linear interpolation between two color specs (hex/name), t in [0,1]."""
    ca, cb = QColor(a), QColor(b)
    return QColor(
        int(round(ca.red()   + (cb.red()   - ca.red())   * t)),
        int(round(ca.green() + (cb.green() - ca.green()) * t)),
        int(round(ca.blue()  + (cb.blue()  - ca.blue())  * t)),
    )


class NavButton(QWidget):
    """Pill button used for the Merge/Library tabs and the theme toggle.

    Hover/selected state lightens the fill and border and brightens the text,
    matching the folder-icon hover in the picker — but animated smoothly via
    a hover-progress tween (same easing the ToggleSwitch uses).
    """
    clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text     = text
        self._hovered  = False
        self._selected = False
        self._hp       = 0.0      # hover/selected progress 0..1
        self._target   = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(40)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._update_width()

    def _update_width(self):
        fm = self.fontMetrics()
        self.setMinimumWidth(max(96, fm.horizontalAdvance(self._text) + 40))

    def setText(self, t):
        self._text = t
        self._update_width()
        self.update()

    def text(self):
        return self._text

    def setSelected(self, v):
        if self._selected != v:
            self._selected = v
            self._retarget()

    def _retarget(self):
        self._target = 1.0 if (self._selected or self._hovered) else 0.0
        if not self._timer.isActive():
            self._timer.start(16)

    def _animate(self):
        diff = self._target - self._hp
        if abs(diff) < 0.02:
            self._hp = self._target
            self._timer.stop()
        else:
            self._hp += diff * 0.25
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self._retarget()

    def leaveEvent(self, e):
        self._hovered = False
        self._retarget()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        radius = 10.0
        t = self._hp
        if self._selected:
            fill = _lerp_color(
                COLORS["card_inset"],
                _lerp_color(COLORS["card_light"], COLORS["accent"], 0.10),
                max(t, 0.65))
            border = _lerp_color(COLORS["border"], COLORS["accent"], max(t, 0.85))
            txt = QColor(COLORS["text"])
        else:
            fill   = _lerp_color(COLORS["card_inset"], COLORS["card_light"], t)
            border = _lerp_color(COLORS["border"],     COLORS["highlight"],  t)
            txt    = _lerp_color(COLORS["text_secondary"], COLORS["text"],   t)
        rect = QRectF(0.5, 0.5, w - 1, h - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, fill)
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, radius, radius)
        p.setPen(txt)
        font = QFont(); font.setPixelSize(12); font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.drawText(rect, Qt.AlignCenter, self._text)


# ══════════════════════════════════════════════════════════════════
# LIBRARY TAB  (Wave-Agent-style browser, neumorphic)
# ══════════════════════════════════════════════════════════════════

class KvValueField(QWidget):
    """Metadata value — uses full card width; scrolls only when text still overflows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._kv_raw = "—"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(False)
        self._scroll.setMinimumWidth(0)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._scroll.setFixedHeight(20)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._label = QLabel("—")
        self._label.setWordWrap(False)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self._scroll.setWidget(self._label)
        lay.addWidget(self._scroll, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def value_label(self):
        return self._label

    def _text_width(self):
        fm = self._label.fontMetrics()
        return fm.horizontalAdvance(self._kv_raw or "—") + 4

    def _sync_layout(self):
        avail = max(1, self.width())
        tw = self._text_width()
        self._label.setFixedWidth(max(tw, avail))
        if tw > avail:
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._scroll.setFixedHeight(24)
        else:
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._scroll.horizontalScrollBar().setValue(0)
            self._scroll.setFixedHeight(20)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_layout()

    def set_kv_text(self, text):
        self._kv_raw = text
        self._label.setText(text)
        self._label.setToolTip(text if text and text != "—" else "")
        self._sync_layout()
        self._scroll.horizontalScrollBar().setValue(0)


class LibraryTab(QWidget):
    _COLS = ["File", "Ch", "Scene", "Take", "Start TC", "Length", "Rate"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._themed = []          # (QLabel, template)
        self._meta = []            # metadata dicts, table-row order
        self._worker = None
        self._detail_windows = []  # keep refs so they aren't GC'd
        self._build()
        last = load_setting("library_folder", "")
        if last and os.path.isdir(last):
            self.folder_sel.setPath(last)
            self._reload(last)
        else:
            self._set_table_state(
                "No folder selected\n\nChoose a library folder above to browse recordings.")

    # ── themed-label registry (live theme) ───────────────────────
    def _themed_label(self, label, template):
        self._themed.append((label, template))
        label.setStyleSheet(template.format(**COLORS))
        return label

    def _sec(self, layout, text, compact=False):
        up = text.upper()
        lbl = QLabel(up)
        lb = lbl.fontMetrics().leftBearing(up[0]) if up else 0
        off = -(lb if lb > 0 else 0) - 3
        pad = f"padding: 0px; margin: 0px 0px 4px {off}px;"
        self._themed_label(
            lbl,
            "background: transparent; font-size: 11px; font-weight: 600; "
            f"letter-spacing: 0.06em; color: {{text_muted}}; {pad}")
        lbl.setMinimumHeight(18)
        layout.addWidget(lbl)
        return lbl

    def _apply_theme(self):
        for label, template in list(self._themed):
            try:
                label.setStyleSheet(template.format(**COLORS))
            except RuntimeError:
                self._themed.remove((label, template))
        self._style_tables()

    # ── build UI ─────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._sec(root, "Library Folder", compact=True)
        self.folder_sel = FolderSelector("library folder", pin_key="library")
        self.folder_sel.pathChanged.connect(self._reload)
        root.addWidget(self.folder_sel)

        self.count_label = QLabel("No folder selected")
        self._themed_label(
            self.count_label,
            "font-size: 11px; color: {text_muted}; "
            "background: transparent; padding-left: 2px;")
        root.addWidget(self.count_label)

        split = QSplitter(Qt.Vertical)
        split.setHandleWidth(10)
        split.setChildrenCollapsible(False)

        # File table
        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels(self._COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.doubleClicked.connect(self._open_detail)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, len(self._COLS)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        # Empty / loading / error overlay — centred message over the table body.
        self.table_overlay = QLabel(self.table)
        self.table_overlay.setAlignment(Qt.AlignCenter)
        self.table_overlay.setWordWrap(True)
        self.table_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._themed_label(
            self.table_overlay,
            "background: transparent; font-size: 13px; color: {text_muted};")
        self.table_overlay.hide()
        self.table.installEventFilter(self)

        split.addWidget(self.table)

        # Detail panels — two compact columns so almost everything is visible
        # without scrolling. Outer scroll stays only as a safety net.
        det_scroll = QScrollArea()
        det_scroll.setWidgetResizable(True)
        det_scroll.setFrameShape(QFrame.NoFrame)
        det_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        det_scroll.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        det = QWidget()
        det.setObjectName("scrollContent")
        dgrid = QGridLayout(det)
        dgrid.setContentsMargins(2, 2, 8, 6)
        dgrid.setHorizontalSpacing(12)
        dgrid.setVerticalSpacing(12)
        dgrid.setColumnStretch(0, 1)
        dgrid.setColumnStretch(1, 1)
        dgrid.setRowStretch(0, 1)
        dgrid.setRowStretch(1, 1)

        gen_card, self._gen_labels = self._kv_card("General Info", [
            ("name", "Name"), ("channels", "Channels"),
            ("scene", "Scene"), ("take", "Take"),
            ("project", "Project"), ("tape", "Tape"), ("ubits", "UBits"),
        ])
        rec_card, self._rec_labels = self._kv_card("Recording Info", [
            ("sample_rate", "Sample Rate"), ("bit_depth", "Bit Depth"),
            ("frame_rate", "Frame Rate"), ("start_tc", "Start TC"),
            ("length", "Length"), ("time_ref", "Samples / Midnight"),
            ("tc_sample_rate", "TC Sample Rate"),
        ])

        # Track table card
        pad = NeumorphicCard.content_margins()
        trk_card = NeumorphicCard()
        tcl = QVBoxLayout(trk_card)
        tcl.setContentsMargins(*pad)
        tcl.setSpacing(4)
        self._sec(tcl, "Track Info", compact=True)
        trk_inset = RoundedClipFrame(8)
        trk_inset_l = QVBoxLayout(trk_inset)
        trk_inset_l.setContentsMargins(1, 1, 1, 1)
        trk_inset_l.setSpacing(0)
        self.track_table = QTableWidget(0, 4)
        self.track_table.setHorizontalHeaderLabels(
            ["Ch", "Intlv", "Name", "Function"])
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.track_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.track_table.setShowGrid(False)
        self.track_table.setFrameShape(QFrame.NoFrame)
        self.track_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.track_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.track_table.verticalHeader().setDefaultSectionSize(26)
        self.track_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        th = self.track_table.horizontalHeader()
        th.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(2, QHeaderView.Stretch)
        th.setSectionResizeMode(3, QHeaderView.Stretch)
        th.setDefaultAlignment(Qt.AlignCenter)
        th.setFixedHeight(28)
        trk_inset_l.addWidget(self.track_table)
        trk_inset.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tcl.addWidget(trk_inset)
        tcl.addStretch(1)
        trk_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Notes card (editable)
        notes_card = NeumorphicCard()
        ncl = QVBoxLayout(notes_card)
        ncl.setContentsMargins(*pad)
        ncl.setSpacing(4)
        self._sec(ncl, "Notes", compact=True)
        notes_inset = RoundedClipFrame(8)
        notes_inset_l = QVBoxLayout(notes_inset)
        notes_inset_l.setContentsMargins(0, 0, 0, 0)
        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("cardNotesEdit")
        self.notes_edit.setPlaceholderText("Select a file to edit its note…")
        self.notes_edit.setMinimumHeight(56)
        self.notes_edit.setFrameShape(QFrame.NoFrame)
        self.notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        notes_inset_l.addWidget(self.notes_edit, 1)
        notes_inset.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ncl.addWidget(notes_inset, 1)
        note_row = QHBoxLayout()
        note_row.setContentsMargins(0, 6, 0, 0)
        note_row.setSpacing(10)
        self.note_status = QLabel("")
        self._themed_label(
            self.note_status,
            "font-size: 11px; color: {text_muted}; background: transparent;")
        self.save_note_btn = QPushButton("Save Note")
        self.save_note_btn.setObjectName("saveNoteBtn")
        self.save_note_btn.setCursor(Qt.PointingHandCursor)
        self.save_note_btn.setEnabled(False)
        self.save_note_btn.clicked.connect(self._save_note)
        note_row.addWidget(self.note_status, 1)
        note_row.addWidget(self.save_note_btn)
        ncl.addLayout(note_row)
        notes_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for c in (gen_card, rec_card, trk_card, notes_card):
            c.setMinimumWidth(0)
        dgrid.addWidget(gen_card, 0, 0)
        dgrid.addWidget(trk_card, 0, 1)
        dgrid.addWidget(rec_card, 1, 0)
        dgrid.addWidget(notes_card, 1, 1)
        det_scroll.setWidget(det)
        split.addWidget(det_scroll)
        split.setSizes([210, 470])

        root.addWidget(split, 1)
        self._style_tables()
        self._fit_track_table()

    def _kv_card(self, title, rows):
        card = NeumorphicCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(*NeumorphicCard.content_margins())
        cl.setSpacing(2)
        self._sec(cl, title, compact=True)
        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 72)
        labels = {}
        for r, (key, disp) in enumerate(rows):
            k = QLabel(disp + ":")
            k.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            self._themed_label(
                k, "font-size: 11px; color: {text_muted}; background: transparent;")
            field = KvValueField()
            v = field.value_label()
            v.setMinimumWidth(0)
            self._themed_label(
                v, "font-size: 12px; font-family: " + _mono_stack() + "; "
                "color: {text}; background: transparent;")
            grid.addWidget(k, r, 0, Qt.AlignTop | Qt.AlignLeft)
            grid.addWidget(field, r, 1, Qt.AlignTop)
            labels[key] = field
        cl.addLayout(grid, 1)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return card, labels

    def _table_style(self):
        sel_bg, sel_fg = _selection_colors()
        return f"""
            QTableWidget {{
                background-color: {COLORS['card_inset']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                gridline-color: {COLORS['border']};
                color: {COLORS['text']};
                font-size: 12px;
                selection-background-color: {sel_bg};
                selection-color: {sel_fg};
            }}
            QTableWidget::item {{ padding: 7px 10px; }}
            QTableWidget::item:selected {{
                background-color: {sel_bg};
                color: {sel_fg};
            }}
            QHeaderView {{ background-color: transparent; }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['text_muted']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.06em;
            }}
            QHeaderView::section:first {{ border-top-left-radius: 9px; }}
            QHeaderView::section:last {{ border-top-right-radius: 9px; }}
            QTableCornerButton::section {{ background-color: {COLORS['card']}; border: none; }}
        """

    def _track_table_style(self):
        return f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                gridline-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
            QTableWidget::item {{ padding: 4px 10px 4px 12px; border: none; }}
            QTableWidget::item:selected {{
                background-color: {COLORS['highlight']};
                color: {COLORS['text']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['text_secondary']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 4px 10px 4px 12px;
                font-weight: 600;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['card']};
                border: none; width: 0px; max-width: 0px;
            }}
        """

    def _fit_track_table(self):
        tbl = getattr(self, "track_table", None)
        if tbl is None:
            return
        tbl.resizeRowsToContents()
        hdr = tbl.horizontalHeader().height()
        row_h = 0
        for i in range(tbl.rowCount()):
            row_h += tbl.rowHeight(i)
        if tbl.rowCount() == 0:
            row_h = tbl.verticalHeader().defaultSectionSize()
        frame = tbl.frameWidth() * 2
        h = hdr + row_h + frame
        tbl.setFixedHeight(h)
        inset = tbl.parentWidget()
        if inset is not None:
            inset_m = inset.layout().contentsMargins()
            inset.setFixedHeight(h + inset_m.top() + inset_m.bottom())
            inset.updateGeometry()
        card = inset.parentWidget() if inset is not None else None
        if card is not None:
            card.updateGeometry()

    def _set_kv(self, field, text):
        if isinstance(field, KvValueField):
            field.set_kv_text(text)
            return
        label = field
        label.setToolTip(text if text and text != "—" else "")
        label._kv_raw = text
        label.setText(text)

    def _refresh_kv_elision(self):
        for d in (getattr(self, "_gen_labels", {}), getattr(self, "_rec_labels", {})):
            for field in d.values():
                raw = getattr(field, "_kv_raw", None)
                if raw is not None:
                    self._set_kv(field, raw)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_kv_elision()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh_kv_elision)
        QTimer.singleShot(0, self._position_overlay)

    def _apply_table_palette(self, table):
        sel_bg, sel_fg = _selection_colors()
        pal = table.palette()
        pal.setColor(QPalette.ColorRole.Highlight, QColor(sel_bg))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(sel_fg))
        table.setPalette(pal)

    def _style_tables(self):
        style = self._table_style()
        if getattr(self, "table", None) is not None:
            self.table.setStyleSheet(style)
            self._apply_table_palette(self.table)
        if getattr(self, "track_table", None) is not None:
            self.track_table.setStyleSheet(self._track_table_style())

    # ── table state overlay (empty / loading / error) ────────────
    def eventFilter(self, obj, event):
        if obj is getattr(self, "table", None) and event.type() == QEvent.Resize:
            self._position_overlay()
        return super().eventFilter(obj, event)

    def _position_overlay(self):
        ov = getattr(self, "table_overlay", None)
        if ov is None:
            return
        vp = self.table.viewport()
        top = self.table.horizontalHeader().height()
        ov.setGeometry(8, top, max(0, vp.width() - 16),
                       max(0, self.table.height() - top))

    def _set_table_state(self, message):
        """Show a centred overlay message, or hide it when message is falsy."""
        ov = getattr(self, "table_overlay", None)
        if ov is None:
            return
        if message and self.table.rowCount() == 0:
            ov.setText(message)
            self._position_overlay()
            ov.show()
            ov.raise_()
        else:
            ov.hide()

    # ── data flow ────────────────────────────────────────────────
    def _reload(self, path):
        save_setting("library_folder", path or "")
        if self._worker is not None:
            # Drop stale signals so queued fileFound emits can't append to the
            # cleared table after we start the next scan.
            try:
                self._worker.fileFound.disconnect()
                self._worker.scanDone.disconnect()
            except (RuntimeError, TypeError):
                pass
            if self._worker.isRunning():
                self._worker.stop()
                self._worker.wait(2000)
        self.table.setRowCount(0)
        self._meta = []
        self._clear_details()
        if not (path and os.path.isdir(path)):
            self.count_label.setText("No folder selected")
            self._set_table_state(
                "No folder selected\n\nChoose a library folder above to browse recordings.")
            return
        self.count_label.setText("Scanning…")
        self._set_table_state("Scanning folder…")
        self._worker = MetadataScanWorker(path)
        self._worker.fileFound.connect(self._add_file)
        self._worker.scanDone.connect(self._scan_done)
        self._worker.start()

    def _scan_done(self, n):
        if self.sender() is not self._worker:
            return
        self.count_label.setText(
            f"{n} file{'s' if n != 1 else ''}" if n else "No WAV files found")
        if n:
            self._set_table_state(None)
            if self.table.currentRow() < 0:
                self.table.selectRow(0)
        else:
            self._set_table_state(
                "No WAV files found\n\nThis folder has no readable WAV recordings.")

    def _add_file(self, md):
        if self.sender() is not self._worker:
            return
        self._set_table_state(None)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._meta.append(md)
        rate = f"{md['sample_rate'] / 1000:.1f}k" if md["sample_rate"] else ""
        vals = [md["name"], str(md["channels"]) if md["channels"] else "",
                md["scene"], md["take"], md["start_tc"], md["length_tc"], rate]
        mono = _mono_font()
        for c, val in enumerate(vals):
            it = QTableWidgetItem(val)
            if c != 0:
                it.setTextAlignment(Qt.AlignCenter)
            if c in (1, 3, 4, 5, 6):
                it.setFont(mono)
            if md.get("error") and c == 0:
                it.setToolTip(md["error"])
            self.table.setItem(r, c, it)

    def _clear_details(self):
        for d in (getattr(self, "_gen_labels", {}), getattr(self, "_rec_labels", {})):
            for v in d.values():
                if isinstance(v, KvValueField):
                    v.set_kv_text("—")
                else:
                    v.setText("—")
        if hasattr(self, "track_table"):
            self.track_table.setRowCount(0)
            self._fit_track_table()
        if hasattr(self, "notes_edit"):
            self.notes_edit.clear()
            self.save_note_btn.setEnabled(False)
            self.note_status.setText("")

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._meta):
            return
        md = self._meta[row]
        sr = f"{md['sample_rate']} Hz" if md["sample_rate"] else "—"
        self._set_kv(self._gen_labels["name"], md["name"])
        self._set_kv(self._gen_labels["channels"], str(md["channels"]) or "—")
        self._set_kv(self._gen_labels["scene"], md["scene"] or "—")
        self._set_kv(self._gen_labels["take"], md["take"] or "—")
        self._set_kv(self._gen_labels["project"], md["project"] or "—")
        self._set_kv(self._gen_labels["tape"], md["tape"] or "—")
        self._set_kv(self._gen_labels["ubits"], md["ubits"] or "—")
        self._set_kv(self._rec_labels["sample_rate"], sr)
        self._set_kv(self._rec_labels["bit_depth"],
            f"{md['bit_depth']}-bit" if md["bit_depth"] else "—")
        fr = md["frame_rate_disp"] or md["frame_rate"] or "—"
        self._set_kv(self._rec_labels["frame_rate"], fr)
        self._set_kv(self._rec_labels["start_tc"], md["start_tc"] or "—")
        self._set_kv(self._rec_labels["length"], md["length_tc"] or "—")
        self._set_kv(self._rec_labels["time_ref"],
            str(md["time_ref"]) if md["time_ref"] else "—")
        self._set_kv(self._rec_labels["tc_sample_rate"],
            f"{md['tc_sample_rate']} Hz" if md["tc_sample_rate"] else "—")

        self.track_table.setRowCount(0)
        mono = _mono_font()
        for t in md["tracks"]:
            r = self.track_table.rowCount()
            self.track_table.insertRow(r)
            for c, val in enumerate([t["channel"], t["interleave"],
                                     t["name"], t["function"]]):
                it = QTableWidgetItem(str(val))
                if c in (0, 1):
                    it.setTextAlignment(Qt.AlignCenter)
                    it.setFont(mono)
                if c in (2, 3) and val:
                    it.setToolTip(str(val))
                self.track_table.setItem(r, c, it)

        self._fit_track_table()

        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(md["note"])
        self.notes_edit.blockSignals(False)
        self.save_note_btn.setEnabled(not md.get("error"))
        self.note_status.setText("")
        QTimer.singleShot(0, self._refresh_kv_elision)

    def _open_detail(self, index):
        row = index.row() if hasattr(index, "row") else self.table.currentRow()
        if row < 0 or row >= len(self._meta):
            return
        md = self._meta[row]
        if md.get("error") or not md.get("channels"):
            return
        win = AudioDetailWindow(md, self.window())
        win.setAttribute(Qt.WA_DeleteOnClose, True)
        win.destroyed.connect(lambda *_: self._forget_detail(win))
        self._detail_windows.append(win)
        win.show()

    def _forget_detail(self, win):
        try:
            self._detail_windows.remove(win)
        except ValueError:
            pass

    def _save_note(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._meta):
            return
        md = self._meta[row]
        note = self.notes_edit.toPlainText()
        self.save_note_btn.setEnabled(False)
        self.note_status.setText("Saving…")
        ok, err = write_wav_note(md["path"], note)
        if ok:
            md["note"] = note
            # Keep the file-table tooltip / cached metadata consistent.
            self.note_status.setText("Saved")
            QTimer.singleShot(2500, lambda: self.note_status.setText("")
                              if self.note_status else None)
        else:
            self.note_status.setText(f"Error: {err}")
        self.save_note_btn.setEnabled(True)


# ══════════════════════════════════════════════════════════════════
# AUDIO DETAIL WINDOW  (waveforms + mixer + trim)
# ══════════════════════════════════════════════════════════════════

LANE_PAD = 10          # horizontal inset inside a waveform lane
WAVE_LANE_H = 132      # vertical size of each waveform lane
STRIP_W  = 196         # fixed width of the per-track mixer strip column


def _fmt_clock(frames, sr):
    if not sr:
        return "0:00.000"
    s = max(0.0, frames / sr)
    m = int(s // 60)
    return f"{m}:{s - m * 60:06.3f}"


def _skeuo_groove_rect(p, rect, radius=5.0):
    """Paint a recessed neumorphic groove (track background)."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0, QColor(COLORS["shadow_dark"]))
    grad.setColorAt(0.45, QColor(COLORS["card_inset"]))
    grad.setColorAt(1, QColor(COLORS["card_light"]))
    p.fillPath(path, grad)
    p.setPen(QPen(QColor(COLORS["shadow_dark"]), 1))
    p.drawPath(path)


def _skeuo_thumb(p, cx, cy, r=6.0, hot=False):
    """Paint a raised circular slider thumb."""
    shadow = QColor(COLORS["shadow_dark"])
    shadow.setAlpha(90)
    p.setPen(Qt.NoPen)
    p.setBrush(shadow)
    p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 1.2, r * 2, r * 2))
    grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
    hi = QColor(COLORS["accent_hover"] if hot else COLORS["accent"])
    lo = QColor(COLORS["accent"]).darker(112)
    grad.setColorAt(0, hi.lighter(108))
    grad.setColorAt(0.55, hi)
    grad.setColorAt(1, lo)
    p.setBrush(grad)
    p.setPen(QPen(QColor(COLORS["shadow_dark"]), 1))
    p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
    gloss = QLinearGradient(cx - r, cy - r, cx - r, cy)
    gloss.setColorAt(0, QColor(255, 255, 255, 70))
    gloss.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(gloss)
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(cx - r + 1.5, cy - r + 1.5, r * 2 - 3, r - 1))


def _paint_playhead(p, px, top, bottom):
    """Playhead line with soft glow (no cap). Follows the active accent."""
    col = QColor(COLORS["accent"])
    glow = QColor(col)
    glow.setAlpha(55)
    p.setPen(QPen(glow, 5))
    p.drawLine(int(px), int(top), int(px), int(bottom))
    p.setPen(QPen(col.darker(115), 1))
    p.drawLine(int(px) + 1, int(top), int(px) + 1, int(bottom))
    p.setPen(QPen(col.lighter(115), 2))
    p.drawLine(int(px), int(top), int(px), int(bottom))


SLIDER_THUMB_R = 6
SLIDER_GROOVE_INSET = SLIDER_THUMB_R + 4


class SkeuoVolumeSlider(QWidget):
    """Horizontal gain fader — fills from the left (skeuomorphic)."""
    valueChanged = Signal(int)
    DEFAULT = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min, self._max = -60, 12
        self._value = self.DEFAULT
        self._dragging = False
        self._hot = False
        self.setFixedHeight(26)
        self.setMinimumWidth(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Volume (Alt+click to reset)")

    def value(self):
        return self._value

    def setValue(self, v, emit=True):
        v = int(max(self._min, min(self._max, v)))
        if v == self._value:
            return
        self._value = v
        self.update()
        if emit:
            self.valueChanged.emit(v)

    def _groove(self):
        ins = SLIDER_GROOVE_INSET
        return QRectF(ins, 9, max(8, self.width() - 2 * ins), 8)

    def _thumb_x(self):
        g = self._groove()
        t = (self._value - self._min) / (self._max - self._min)
        x = g.left() + t * g.width()
        return max(g.left() + SLIDER_THUMB_R, min(g.right() - SLIDER_THUMB_R, x))

    def _value_at(self, x):
        g = self._groove()
        t = (x - g.left()) / g.width()
        t = max(0.0, min(1.0, t))
        return int(round(self._min + t * (self._max - self._min)))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = self._groove()
        _skeuo_groove_rect(p, g, 4)
        tx = self._thumb_x()
        if tx > g.left() + 1:
            fill = QRectF(g.left(), g.top() + 1, tx - g.left(), g.height() - 2)
            fg = QLinearGradient(fill.topLeft(), fill.topRight())
            fg.setColorAt(0, QColor(COLORS["accent"]).darker(108))
            fg.setColorAt(1, QColor(COLORS["accent"]))
            fp = QPainterPath()
            fp.addRoundedRect(fill, 3, 3)
            p.fillPath(fp, fg)
        _skeuo_thumb(p, tx, g.center().y(), SLIDER_THUMB_R, self._hot)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if e.modifiers() & Qt.AltModifier:
            self.setValue(self.DEFAULT)
            e.accept()
            return
        self._dragging = True
        self._hot = True
        self.setValue(self._value_at(e.position().x()))
        e.accept()

    def mouseMoveEvent(self, e):
        if self._dragging:
            self.setValue(self._value_at(e.position().x()))
            e.accept()

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self._hot = False
        self.update()

    def enterEvent(self, e):
        self._hot = True
        self.update()

    def leaveEvent(self, e):
        if not self._dragging:
            self._hot = False
            self.update()


class SkeuoPanSlider(QWidget):
    """Centre-zero pan — accent fill grows left OR right from the middle."""
    valueChanged = Signal(int)
    DEFAULT = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min, self._max = -100, 100
        self._value = self.DEFAULT
        self._dragging = False
        self._hot = False
        self.setFixedHeight(26)
        self.setMinimumWidth(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Pan (Alt+click to reset)")

    def value(self):
        return self._value

    def setValue(self, v, emit=True):
        v = int(max(self._min, min(self._max, v)))
        if v == self._value:
            return
        self._value = v
        self.update()
        if emit:
            self.valueChanged.emit(v)

    def _groove(self):
        ins = SLIDER_GROOVE_INSET
        return QRectF(ins, 9, max(8, self.width() - 2 * ins), 8)

    def _centre_x(self):
        return self._groove().center().x()

    def _thumb_x(self):
        g = self._groove()
        t = (self._value - self._min) / (self._max - self._min)
        x = g.left() + t * g.width()
        return max(g.left() + SLIDER_THUMB_R, min(g.right() - SLIDER_THUMB_R, x))

    def _value_at(self, x):
        g = self._groove()
        t = (x - g.left()) / g.width()
        t = max(0.0, min(1.0, t))
        return int(round(self._min + t * (self._max - self._min)))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = self._groove()
        _skeuo_groove_rect(p, g, 4)
        cx = self._centre_x()
        tx = self._thumb_x()
        # Centre tick
        p.setPen(QPen(QColor(COLORS["text_muted"]), 1))
        p.drawLine(int(cx), int(g.top() + 1), int(cx), int(g.bottom() - 1))
        if abs(self._value) > 0:
            x0, x1 = (cx, tx) if self._value < 0 else (cx, tx)
            left, right = min(x0, x1), max(x0, x1)
            if right - left > 0.5:
                fill = QRectF(left, g.top() + 1, right - left, g.height() - 2)
                fg = QLinearGradient(fill.topLeft(), fill.topRight())
                fg.setColorAt(0, QColor(COLORS["accent"]).darker(108))
                fg.setColorAt(1, QColor(COLORS["accent"]))
                fp = QPainterPath()
                fp.addRoundedRect(fill, 3, 3)
                p.fillPath(fp, fg)
        _skeuo_thumb(p, tx, g.center().y(), SLIDER_THUMB_R, self._hot)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if e.modifiers() & Qt.AltModifier:
            self.setValue(self.DEFAULT)
            e.accept()
            return
        self._dragging = True
        self._hot = True
        self.setValue(self._value_at(e.position().x()))
        e.accept()

    def mouseMoveEvent(self, e):
        if self._dragging:
            self.setValue(self._value_at(e.position().x()))
            e.accept()

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self._hot = False
        self.update()

    def enterEvent(self, e):
        self._hot = True
        self.update()

    def leaveEvent(self, e):
        if not self._dragging:
            self._hot = False
            self.update()


class TimeRuler(QWidget):
    """Thin time ruler that mirrors the shared view of the waveform lanes."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        win = self.win
        if win.sr <= 0:
            return
        inner = w - 2 * LANE_PAD
        if inner <= 0:
            return
        spp = win.fpp / win.sr
        target = 84 * spp
        nice = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30,
                60, 120, 300, 600, 1800, 3600]
        step = next((x for x in nice if x >= target), nice[-1])
        font = QFont(self.font())
        font.setPointSize(8)
        p.setFont(font)
        p.setPen(QPen(QColor(COLORS["text_secondary"])))
        t0 = win.view_start / win.sr
        first = math.ceil(t0 / step) * step
        t = first
        while True:
            x = LANE_PAD + (t * win.sr - win.view_start) / win.fpp
            if x > w - LANE_PAD + 1:
                break
            if x >= LANE_PAD - 1:
                m = int(t // 60)
                lbl = f"{m}:{t - m * 60:05.2f}" if step < 1 else (
                    f"{m}:{int(t - m * 60):02d}")
                p.drawText(int(x) + 2, h - 3, lbl)
            t += step

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        if delta == 0:
            return
        factor = 1 / 1.2 if delta > 0 else 1.2
        self.win.zoom(factor, anchor_x=e.position().x())
        e.accept()


class WaveLane(QWidget):
    """One channel's waveform, drawn in the neumorphic inset style. Shares the
    parent window's view (scroll/zoom) and supports click-to-seek and trim
    handle dragging."""

    def __init__(self, win, ch):
        super().__init__()
        self.win = win
        self.ch = ch
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(WAVE_LANE_H)
        self.setMouseTracking(True)
        self._cache_key = None
        self._cache = None
        self._drag = None      # None | "start" | "end" | "seek"

    def _wave_width(self):
        return max(1, self.width() - 2 * LANE_PAD)

    def _envelope(self):
        win = self.win
        key = (round(win.view_start, 2), round(win.fpp, 5), self._wave_width())
        if key == self._cache_key and self._cache is not None:
            return self._cache
        self._cache = win.lane_envelope(self.ch, self._wave_width())
        self._cache_key = key
        return self._cache

    def _x_for_frame(self, frame):
        return LANE_PAD + (frame - self.win.view_start) / self.win.fpp

    def _frame_for_x(self, x):
        return self.win.view_start + (x - LANE_PAD) * self.win.fpp

    def paintEvent(self, _e):
        win = self.win
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        lane_r = 14.0
        rect = QRectF(LANE_PAD, 3, w - 2 * LANE_PAD, h - 6)
        path = QPainterPath()
        path.addRoundedRect(rect, lane_r, lane_r)
        # Recessed lane (skeuomorphic inset)
        inset = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        inset.setColorAt(0, QColor(COLORS["shadow_dark"]))
        inset.setColorAt(0.35, QColor(COLORS["card_inset"]))
        inset.setColorAt(1, QColor(COLORS["card_light"]))
        p.fillPath(path, inset)
        p.setPen(QPen(QColor(COLORS["shadow_dark"]), 1))
        p.drawPath(path)
        p.setPen(QPen(QColor(COLORS["highlight"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), lane_r - 1, lane_r - 1)
        p.setClipPath(path)

        cy = rect.center().y()
        p.setPen(QPen(QColor(COLORS["border"]), 1))
        p.drawLine(int(rect.left() + 2), int(cy), int(rect.right() - 2), int(cy))

        env = self._envelope()
        if env is not None and (win.pmin is not None or win.audio is not None):
            mn, mx = env
            amp = rect.height() / 2.0 - 2.0
            x0 = rect.left()
            col = QColor(COLORS["accent"])
            if win.is_muted(self.ch):
                col = QColor(COLORS["text_muted"])
            elif win.has_solo() and not win.is_solo(self.ch):
                col.setAlpha(70)
            line_mode = win.fpp < 1.0 and win.audio is not None
            if line_mode:
                # Smooth oscilloscope-style trace of the actual samples.
                trace = QPainterPath()
                trace.moveTo(x0, cy - mx[0] * amp)
                for i in range(1, len(mx)):
                    trace.lineTo(x0 + i, cy - mx[i] * amp)
                # Soft body fill under the trace toward the centre line.
                body = QPainterPath(trace)
                body.lineTo(x0 + len(mx) - 1, cy)
                body.lineTo(x0, cy)
                body.closeSubpath()
                fillc = QColor(col)
                fillc.setAlpha(60)
                p.fillPath(body, fillc)
                pen = QPen(col, 1.6)
                pen.setJoinStyle(Qt.RoundJoin)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawPath(trace)
            else:
                wf = QPainterPath()
                wf.moveTo(x0, cy - mx[0] * amp)
                for i in range(len(mx)):
                    wf.lineTo(x0 + i, cy - mx[i] * amp)
                for i in range(len(mn) - 1, -1, -1):
                    wf.lineTo(x0 + i, cy - mn[i] * amp)
                wf.closeSubpath()
                wgrad = QLinearGradient(0, rect.top(), 0, rect.bottom())
                wgrad.setColorAt(0, col.lighter(125))
                wgrad.setColorAt(0.45, col)
                wgrad.setColorAt(1, col.darker(118))
                p.fillPath(wf, wgrad)
                pen = QPen(col.darker(130), 0.8)
                pen.setJoinStyle(Qt.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawPath(wf)

        # Trim region shading (outside the kept range is dimmed).
        if win.trim_active():
            xs = self._x_for_frame(win.trim_start)
            xe = self._x_for_frame(win.trim_end)
            shade = QColor(COLORS["bg"])
            shade.setAlpha(150)
            if xs > rect.left():
                p.fillRect(QRectF(rect.left(), rect.top(),
                                  min(xs, rect.right()) - rect.left(), rect.height()), shade)
            if xe < rect.right():
                p.fillRect(QRectF(max(xe, rect.left()), rect.top(),
                                  rect.right() - max(xe, rect.left()), rect.height()), shade)
            p.setPen(QPen(QColor(COLORS["notice"]), 2))
            for xx in (xs, xe):
                if rect.left() - 1 <= xx <= rect.right() + 1:
                    p.drawLine(int(xx), int(rect.top()), int(xx), int(rect.bottom()))

        # Playhead (skeuomorphic cap + glow).
        px = self._x_for_frame(win.play_frame)
        if rect.left() - 1 <= px <= rect.right() + 1:
            _paint_playhead(p, px, rect.top() + 2, rect.bottom() - 1)

    def mousePressEvent(self, e):
        win = self.win
        x = e.position().x()
        if win.trim_active():
            for name, frame in (("start", win.trim_start), ("end", win.trim_end)):
                if abs(x - self._x_for_frame(frame)) <= 6:
                    self._drag = name
                    return
        self._drag = "seek"
        win.seek(self._frame_for_x(x))

    def mouseMoveEvent(self, e):
        if not self._drag:
            return
        win = self.win
        frame = self._frame_for_x(e.position().x())
        if self._drag == "seek":
            win.seek(frame)
        elif self._drag == "start":
            win.set_trim(start=frame)
        elif self._drag == "end":
            win.set_trim(end=frame)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        if delta == 0:
            return
        factor = 1 / 1.2 if delta > 0 else 1.2
        self.win.zoom(factor, anchor_x=e.position().x())
        e.accept()


class MiniToggleButton(QPushButton):
    """Square solo/mute chip — glyph painted dead-centre (no font kerning bias)."""

    def __init__(self, letter, role, parent=None):
        super().__init__(parent)
        self._letter = letter
        self.setProperty("role", role)
        self.setCheckable(True)
        self.setFixedSize(24, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        role = self.property("role") or ""
        if self.isChecked():
            if role == "solo":
                fill, border, fg = (COLORS["warning"], COLORS["warning"],
                                    COLORS["on_accent"])
            else:
                fill, border, fg = (COLORS["error"], COLORS["error"],
                                      COLORS["on_accent"])
        else:
            fill = COLORS["card_inset"]
            border = COLORS["highlight"] if self.underMouse() else COLORS["border"]
            fg = COLORS["text"] if self.underMouse() else COLORS["text_secondary"]
        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        p.fillPath(path, QColor(fill))
        p.setPen(QPen(QColor(border), 1))
        p.drawPath(path)
        font = QFont(self.font())
        font.setPixelSize(11)
        font.setWeight(QFont.Bold)
        p.setFont(font)
        p.setPen(QColor(fg))
        p.setPen(QColor(fg))
        p.drawText(rect.toRect(), Qt.AlignCenter, self._letter)

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()


class TrackStrip(QWidget):
    """Per-track mixer column: name + Solo/Mute + Pan/Volume faders."""

    def __init__(self, win, ch, name):
        super().__init__()
        self.win = win
        self.ch = ch
        self.setFixedWidth(STRIP_W)
        self.setFixedHeight(92)
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 4, 12, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)

        self.name_lbl = QLabel(name or f"CH{ch + 1}")
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setWordWrap(False)
        fm = self.name_lbl.fontMetrics()
        self.name_lbl.setText(
            fm.elidedText(self.name_lbl.text(), Qt.ElideRight, STRIP_W - 16))
        self.name_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {COLORS['text']}; background: transparent;")
        self.name_lbl.setToolTip(name or f"CH{ch + 1}")
        grid.addWidget(self.name_lbl, 0, 0, 1, 2)

        self.solo_btn = MiniToggleButton("S", "solo")
        self.solo_btn.toggled.connect(self._on_solo)
        self.mute_btn = MiniToggleButton("M", "mute")
        self.mute_btn.toggled.connect(self._on_mute)
        solo_w = QWidget()
        solo_l = QHBoxLayout(solo_w)
        solo_l.setContentsMargins(0, 0, 0, 0)
        solo_l.addStretch(1)
        solo_l.addWidget(self.solo_btn)
        solo_l.addStretch(1)
        mute_w = QWidget()
        mute_l = QHBoxLayout(mute_w)
        mute_l.setContentsMargins(0, 0, 0, 0)
        mute_l.addStretch(1)
        mute_l.addWidget(self.mute_btn)
        mute_l.addStretch(1)
        grid.addWidget(solo_w, 1, 0)
        grid.addWidget(mute_w, 1, 1)

        self.pan = SkeuoPanSlider()
        self.pan.valueChanged.connect(self._on_pan)
        self.gain = SkeuoVolumeSlider()
        self.gain.valueChanged.connect(self._on_gain)
        grid.addWidget(self.pan, 2, 0)
        grid.addWidget(self.gain, 2, 1)

        self.pan_lbl = QLabel("Pan")
        self.pan_lbl.setAlignment(Qt.AlignCenter)
        self.pan_lbl.setStyleSheet(
            f"font-size: 9px; color: {COLORS['text_muted']}; background: transparent;")
        self.gain_lbl = QLabel("Volume")
        self.gain_lbl.setAlignment(Qt.AlignCenter)
        self.gain_lbl.setStyleSheet(
            f"font-size: 9px; color: {COLORS['text_muted']}; background: transparent;")
        grid.addWidget(self.pan_lbl, 3, 0)
        grid.addWidget(self.gain_lbl, 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def _on_solo(self, on):
        self.win.engine.set_channel(self.ch, solo=on)
        self.win.refresh_lanes()

    def _on_mute(self, on):
        self.win.engine.set_channel(self.ch, mute=on)
        self.win.refresh_lanes()

    def _on_pan(self, v):
        self.win.engine.set_channel(self.ch, pan=v / 100.0)

    def _on_gain(self, v):
        lin = 0.0 if v <= -60 else 10 ** (v / 20.0)
        self.win.engine.set_channel(self.ch, gain=lin)

    def refresh_theme(self):
        for lbl in (self.name_lbl, self.pan_lbl, self.gain_lbl):
            if lbl is self.name_lbl:
                lbl.setStyleSheet(
                    "font-size: 12px; font-weight: 600; "
                    f"color: {COLORS['text']}; background: transparent;")
            else:
                lbl.setStyleSheet(
                    f"font-size: 9px; color: {COLORS['text_muted']}; background: transparent;")
        self.pan.update()
        self.gain.update()


class AudioDetailWindow(QMainWindow):
    """Double-click target: per-track waveforms, mixer and trim tools."""

    def __init__(self, md, parent=None):
        super().__init__(parent)
        self.md = md
        self.path = md["path"]
        self.setWindowTitle(f"Waveform · {md['name']}")
        self.resize(1040, 680)
        self.setMinimumSize(720, 460)
        self.setFocusPolicy(Qt.StrongFocus)

        # Shared view / playback state
        self.audio = None
        self.sr = 0
        self.n = 0
        self.pmin = self.pmax = None
        self.bucket = 512
        self.fpp = 1000.0
        self.view_start = 0.0
        self.play_frame = 0
        self.trim_start = 0
        self.trim_end = 0
        self._trim_on = False
        self.lanes = []
        self.strips = []
        self.engine = PlaybackEngine()
        self.engine.stopped.connect(self._on_play_stopped)

        self._themed = []
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

        self._space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self._space_shortcut.setContext(Qt.WindowShortcut)
        self._space_shortcut.activated.connect(self._space_play)

        # Fade-in on first show (motivated: soften the window appearing).
        self._faded_in = False
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(190)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _start_audio_load(self):
        if self._audio_loader is not None and self._audio_loader.isRunning():
            return
        self._audio_loader = AudioLoadWorker(self.path)
        self._audio_loader.loaded.connect(self._on_audio_loaded)
        self._audio_loader.failed.connect(self._on_audio_load_failed)
        self._audio_loader.start()

    def showEvent(self, e):
        super().showEvent(e)
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)
        if not self._faded_in:
            self._faded_in = True
            self._fade_anim.start()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space_play()
            e.accept()
            return
        super().keyPressEvent(e)

    def _space_play(self):
        fw = QApplication.focusWidget()
        if fw is not None and isinstance(fw, (QLineEdit, QTextEdit)):
            return
        if not self.play_btn.isEnabled():
            return
        self._toggle_play()

    # ── view helpers (shared by lanes / ruler) ──────────────────
    def _lane_w(self):
        if self.lanes:
            return self.lanes[0]._wave_width()
        return max(1, self.width() - STRIP_W - 2 * LANE_PAD)

    def has_solo(self):
        return bool(self.engine._solos is not None and self.engine._solos.any())

    def is_solo(self, ch):
        return bool(self.engine._solos is not None and self.engine._solos[ch])

    def is_muted(self, ch):
        return bool(self.engine._mutes is not None and self.engine._mutes[ch])

    def trim_active(self):
        return self._trim_on

    def lane_envelope(self, ch, W):
        if W <= 0 or self.n <= 0:
            return None
        start = self.view_start
        fpp = self.fpp
        # Zoomed in enough that peak buckets would look like a staircase:
        # sample the real audio directly so the waveform stays smooth/detailed.
        if self.audio is not None and fpp < self.bucket:
            return self._sample_envelope(ch, W, start, fpp)
        if self.pmin is None:
            return None
        pmin = self.pmin[:, ch]
        pmax = self.pmax[:, ch]
        nb = pmin.shape[0]
        bk = self.bucket
        mn = np.zeros(W, dtype=np.float32)
        mx = np.zeros(W, dtype=np.float32)
        for x in range(W):
            b0 = int((start + x * fpp) / bk)
            b1 = int((start + (x + 1) * fpp) / bk) + 1
            if b0 < 0:
                b0 = 0
            if b1 > nb:
                b1 = nb
            if b1 <= b0:
                if b0 >= nb:
                    continue
                b1 = b0 + 1
            mn[x] = pmin[b0:b1].min()
            mx[x] = pmax[b0:b1].max()
        return mn, mx

    def _sample_envelope(self, ch, W, start, fpp):
        a = self.audio[:, ch]
        N = a.shape[0]
        mn = np.zeros(W, dtype=np.float32)
        mx = np.zeros(W, dtype=np.float32)
        if fpp >= 1.0:
            # More than one frame per pixel: true per-pixel min/max from samples.
            for x in range(W):
                s0 = int(start + x * fpp)
                s1 = int(start + (x + 1) * fpp) + 1
                if s0 < 0:
                    s0 = 0
                if s1 > N:
                    s1 = N
                if s1 <= s0:
                    if s0 >= N:
                        continue
                    s1 = s0 + 1
                seg = a[s0:s1]
                mn[x] = seg.min()
                mx[x] = seg.max()
            return mn, mx
        # Sub-sample zoom: interpolate the actual sample value at each pixel so
        # the trace is a smooth continuous curve instead of a blocky staircase.
        xs = start + np.arange(W, dtype=np.float64) * fpp
        idx = np.clip(xs, 0, N - 1)
        i0 = np.floor(idx).astype(np.int64)
        i1 = np.clip(i0 + 1, 0, N - 1)
        frac = (idx - i0).astype(np.float32)
        vals = (a[i0] * (1.0 - frac) + a[i1] * frac).astype(np.float32)
        mn[:] = vals
        mx[:] = vals
        return mn, mx

    # ── UI ───────────────────────────────────────────────────────
    def _themed_label(self, label, template):
        self._themed.append((label, template))
        label.setStyleSheet(template.format(**COLORS))
        return label

    def _section(self, layout, text, compact=False):
        lbl = QLabel(text)
        pad = "padding: 0px 0px 0px 4px; margin: 0px;" if compact else "padding-left: 6px;"
        self._themed_label(
            lbl,
            "background: transparent; font-size: 13px; font-weight: 600; "
            f"color: {{text_secondary}}; {pad}")
        lbl.setMinimumHeight(20)
        layout.addWidget(lbl)
        return lbl

    def _apply_theme(self):
        for label, template in list(self._themed):
            try:
                label.setStyleSheet(template.format(**COLORS))
            except RuntimeError:
                self._themed.remove((label, template))
        for s in self.strips:
            try:
                s.refresh_theme()
            except RuntimeError:
                pass
        self.refresh_lanes()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("rootWidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # Header / transport
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        title = QLabel(self.md["name"])
        self._themed_label(
            title, "font-size: 15px; font-weight: 600; color: {text};")
        hdr.addWidget(title)
        hdr.addStretch(1)
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("transportBtn")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._toggle_play)
        hdr.addWidget(self.play_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("ghostBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        hdr.addWidget(self.stop_btn)
        self.time_lbl = QLabel("0:00.000 / 0:00.000")
        self._themed_label(
            self.time_lbl,
            "font-size: 12px; color: {text_secondary}; font-family: Consolas, monospace;")
        hdr.addWidget(self.time_lbl)
        hdr.addSpacing(8)
        for txt, fn in (("–", lambda: self.zoom(1.6, anchor_x=self._zoom_anchor_x())),
                        ("+", lambda: self.zoom(1 / 1.6, anchor_x=self._zoom_anchor_x())),
                        ("Fit", self.fit)):
            b = QPushButton(txt)
            b.setObjectName("ghostBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            if txt != "Fit":
                b.setFixedWidth(40)
            hdr.addWidget(b)
        root.addLayout(hdr)

        self.main_split = QSplitter(Qt.Vertical)
        self.main_split.setHandleWidth(8)
        self.main_split.setChildrenCollapsible(False)

        wave_page = QWidget()
        wave_l = QVBoxLayout(wave_page)
        wave_l.setContentsMargins(0, 0, 0, 0)
        wave_l.setSpacing(8)

        # Ruler (aligned to lane drawing area via a fixed left spacer)
        ruler_row = QHBoxLayout()
        ruler_row.setSpacing(0)
        ruler_row.setContentsMargins(0, 0, 0, 0)
        sp = QWidget()
        sp.setFixedWidth(STRIP_W)
        ruler_row.addWidget(sp)
        self.ruler = TimeRuler(self)
        ruler_row.addWidget(self.ruler, 1)
        wave_l.addLayout(ruler_row)

        # Lanes
        self.lane_scroll = QScrollArea()
        self.lane_scroll.setWidgetResizable(True)
        self.lane_scroll.setFrameShape(QFrame.NoFrame)
        self.lane_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lane_host = QWidget()
        self.lane_host.setObjectName("scrollContent")
        self.lane_box = QVBoxLayout(self.lane_host)
        self.lane_box.setContentsMargins(0, 0, 0, 0)
        self.lane_box.setSpacing(6)
        self.lane_box.addStretch(1)
        self.lane_scroll.setWidget(self.lane_host)
        wave_l.addWidget(self.lane_scroll, 1)

        # Horizontal scrollbar (time navigation), aligned with lanes
        sb_row = QHBoxLayout()
        sb_row.setSpacing(0)
        sb_row.setContentsMargins(0, 0, 0, 0)
        sp2 = QWidget()
        sp2.setFixedWidth(STRIP_W)
        sb_row.addWidget(sp2)
        self.hscroll = QScrollBar(Qt.Horizontal)
        self.hscroll.valueChanged.connect(self._on_hscroll)
        sb_row.addWidget(self.hscroll, 1)
        wave_l.addLayout(sb_row)

        # Trim toolbar
        trim = QHBoxLayout()
        trim.setSpacing(8)
        self.trim_lbl = QLabel("Trim: off")
        self._themed_label(
            self.trim_lbl,
            "font-size: 12px; color: {text_secondary}; font-family: Consolas, monospace;")
        trim.addWidget(self.trim_lbl)
        trim.addStretch(1)
        for txt, fn, oid in (
                ("Enable Trim", self._toggle_trim, "ghostBtn"),
                ("Set Start ◄ Playhead", lambda: self.set_trim(start=self.play_frame), "ghostBtn"),
                ("Set End ► Playhead", lambda: self.set_trim(end=self.play_frame), "ghostBtn"),
                ("Trim → Save As…", self._trim_save_as, "ghostBtn"),
                ("Trim & Overwrite", self._trim_overwrite, "transportBtn")):
            b = QPushButton(txt)
            b.setObjectName(oid)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            trim.addWidget(b)
            if txt == "Enable Trim":
                self.trim_toggle_btn = b
        # Right spacer so the last button's edge lines up with the waveform
        # lane boxes (which are inset by LANE_PAD and the vertical scrollbar).
        self.trim_right_pad = QWidget()
        self.trim_right_pad.setFixedWidth(LANE_PAD)
        trim.addWidget(self.trim_right_pad)
        self.trim_status = QLabel("")
        self._themed_label(
            self.trim_status, "font-size: 11px; color: {text_muted};")
        wave_l.addLayout(trim)
        wave_l.addWidget(self.trim_status)
        self.main_split.addWidget(wave_page)

        root.addWidget(self.main_split, 1)

        # Notes — compact single-line strip, left edge aligned with the lane
        # boxes. Kept out of the splitter so waveforms get all vertical space.
        notes_row_w = QWidget()
        notes_row = QHBoxLayout(notes_row_w)
        notes_row.setContentsMargins(0, 2, 0, 0)
        notes_row.setSpacing(8)
        sp_notes = QWidget()
        sp_notes.setFixedWidth(int(STRIP_W + LANE_PAD))
        notes_row.addWidget(sp_notes)
        notes_lbl = QLabel("Notes")
        self._themed_label(
            notes_lbl,
            "background: transparent; font-size: 12px; font-weight: 600; "
            "color: {text_secondary};")
        notes_row.addWidget(notes_lbl)
        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("cardNotesEdit")
        self.notes_edit.setPlainText(self.md.get("note", ""))
        self.notes_edit.setPlaceholderText("Enter a note for this recording…")
        self.notes_edit.setFixedHeight(34)
        self.notes_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notes_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notes_edit.setFrameShape(QFrame.NoFrame)
        notes_row.addWidget(self.notes_edit, 1)
        self.note_status = QLabel("")
        self._themed_label(
            self.note_status,
            "font-size: 11px; color: {text_muted}; background: transparent;")
        notes_row.addWidget(self.note_status)
        self.save_note_btn = QPushButton("Save Note")
        self.save_note_btn.setObjectName("saveNoteBtn")
        self.save_note_btn.setCursor(Qt.PointingHandCursor)
        self.save_note_btn.clicked.connect(self._save_note)
        notes_row.addWidget(self.save_note_btn)
        notes_pad = QWidget()
        notes_pad.setFixedWidth(LANE_PAD)
        notes_row.addWidget(notes_pad)
        self._notes_right_pad = notes_pad
        root.addWidget(notes_row_w)

        self.status_lbl = QLabel("Loading waveform…")
        self._themed_label(self.status_lbl, "font-size: 12px; color: {text_muted};")
        root.addWidget(self.status_lbl)

        self._peak_loader = PeakLoadWorker(self.path)
        self._peak_loader.loaded.connect(self._on_peaks_loaded)
        self._peak_loader.failed.connect(self._on_load_failed)
        self._peak_loader.start()
        self._audio_loader = None

    # ── load ─────────────────────────────────────────────────────
    def _build_lanes(self, ch):
        names = [t["name"] for t in self.md.get("tracks", [])]
        while len(names) < ch:
            names.append(f"CH{len(names) + 1}")
        for c in range(ch):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(0)
            strip = TrackStrip(self, c, names[c])
            lane = WaveLane(self, c)
            rl.addWidget(strip)
            rl.addWidget(lane, 1)
            self.lane_box.insertWidget(self.lane_box.count() - 1, row)
            self.lanes.append(lane)
            self.strips.append(strip)

    def _status_text(self, ch=None):
        ch = ch if ch is not None else (self.pmin.shape[1] if self.pmin is not None else 0)
        if self.audio is None:
            return f"{ch} ch · {self.sr} Hz · {_fmt_clock(self.n, self.sr)} · loading audio…"
        if sd is None:
            return "Playback unavailable (sounddevice not installed)"
        return f"{ch} ch · {self.sr} Hz · {_fmt_clock(self.n, self.sr)}"

    def _on_peaks_loaded(self, d):
        self.pmin = d["pmin"]
        self.pmax = d["pmax"]
        self.bucket = d["bucket"]
        self.sr = d["sr"]
        self.n = int(d["n"])
        self.trim_start = 0
        self.trim_end = self.n
        ch = int(d.get("channels") or self.pmin.shape[1])
        self._build_lanes(ch)
        self.fit()
        # Lanes were just created; their real width isn't known until Qt runs a
        # layout pass. Re-fit once that settles so the waveform fills the full
        # width instead of leaving empty space on the right.
        QTimer.singleShot(0, self.fit)
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(sd is not None)
        self.status_lbl.setText(self._status_text(ch))
        self._update_time_label()
        self.refresh_lanes()
        self._start_audio_load()

    def _on_audio_loaded(self, d):
        self.audio = d["audio"]
        self.engine.set_audio(self.audio, self.sr)
        self.play_btn.setEnabled(sd is not None)
        ch = int(self.audio.shape[1])
        self.status_lbl.setText(self._status_text(ch))

    def _on_audio_load_failed(self, err):
        if self.pmin is not None:
            self.status_lbl.setText(
                f"{self._status_text()} · playback load failed: {err}")
        else:
            self._on_load_failed(err)

    def _on_load_failed(self, err):
        self.status_lbl.setText(f"Failed to load audio: {err}")

    # ── view / zoom / scroll ─────────────────────────────────────
    def _max_fpp(self):
        return max(1e-6, self.n / max(1, self._lane_w()))

    def _clamp_view(self):
        self.fpp = min(self.fpp, self._max_fpp())
        self.fpp = max(self.fpp, 0.05)
        total_px = self.n / self.fpp
        max_start = max(0.0, total_px - self._lane_w())
        self.view_start = min(max(0.0, self.view_start), max_start * self.fpp)

    def _sync_scrollbar(self):
        if self.n <= 0:
            return
        lane_w = self._lane_w()
        total_px = int(self.n / self.fpp)
        self.hscroll.blockSignals(True)
        self.hscroll.setRange(0, max(0, total_px - lane_w))
        self.hscroll.setPageStep(lane_w)
        self.hscroll.setSingleStep(max(1, lane_w // 12))
        self.hscroll.setValue(int(self.view_start / self.fpp))
        self.hscroll.blockSignals(False)

    def fit(self):
        if self.n <= 0:
            return
        self.fpp = self._max_fpp()
        self.view_start = 0.0
        self._clamp_view()
        self._sync_scrollbar()
        self.refresh_lanes()

    def _zoom_anchor_x(self):
        """Pixel anchor for toolbar zoom — playhead if visible, else view centre."""
        lane_w = self._lane_w()
        if self.n > 0:
            px = (self.play_frame - self.view_start) / self.fpp
            if LANE_PAD <= px <= LANE_PAD + lane_w:
                return px
        return LANE_PAD + lane_w / 2.0

    def zoom(self, factor, anchor_x=None):
        if self.n <= 0:
            return
        lane_w = self._lane_w()
        if anchor_x is None:
            anchor_x = LANE_PAD + lane_w / 2.0
        anchor_x = max(LANE_PAD, min(anchor_x, LANE_PAD + lane_w))
        anchor_frame = self.view_start + (anchor_x - LANE_PAD) * self.fpp
        self.fpp *= factor
        self._clamp_view()
        self.view_start = anchor_frame - (anchor_x - LANE_PAD) * self.fpp
        self._clamp_view()
        self._sync_scrollbar()
        self.refresh_lanes()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            pos = e.position()
            anchor_x = None
            w = self.childAt(int(pos.x()), int(pos.y()))
            while w is not None:
                if isinstance(w, (WaveLane, TimeRuler)):
                    pt = w.mapFrom(self, pos.toPoint())
                    anchor_x = float(pt.x())
                    break
                w = w.parentWidget()
            if anchor_x is None:
                anchor_x = self._zoom_anchor_x()
            factor = 1 / 1.2 if e.angleDelta().y() > 0 else 1.2
            self.zoom(factor, anchor_x=anchor_x)
            e.accept()
        else:
            super().wheelEvent(e)

    def _on_hscroll(self, value):
        self.view_start = value * self.fpp
        self.refresh_lanes()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sync_trim_pad()
        if self.n > 0:
            self._clamp_view()
            self._sync_scrollbar()
            self.refresh_lanes()

    def _sync_trim_pad(self):
        vsb = self.lane_scroll.verticalScrollBar()
        sb_w = vsb.width() if vsb.isVisible() else 0
        for name in ("trim_right_pad", "_notes_right_pad"):
            pad = getattr(self, name, None)
            if pad is not None:
                pad.setFixedWidth(LANE_PAD + sb_w)

    def refresh_lanes(self):
        self.ruler.update()
        for lane in self.lanes:
            lane.update()

    # ── playback ─────────────────────────────────────────────────
    def _toggle_play(self):
        if self.audio is None:
            self.status_lbl.setText(self._status_text() + " · please wait")
            return
        if self.engine.is_playing():
            self._stop()
        else:
            if self.engine.play(from_frame=self.play_frame):
                self.play_btn.setText("Pause")
                self._timer.start()

    def _stop(self):
        self.engine.stop()
        self._timer.stop()
        self.play_btn.setText("Play")

    def _on_play_stopped(self):
        self._timer.stop()
        self.play_btn.setText("Play")

    def _tick(self):
        self.play_frame = self.engine.position()
        # Follow the playhead if it scrolls out of view.
        lane_w = self._lane_w()
        x = (self.play_frame - self.view_start) / self.fpp
        if x < 0 or x > lane_w:
            self.view_start = self.play_frame - (lane_w * 0.3) * self.fpp
            self._clamp_view()
            self._sync_scrollbar()
        self._update_time_label()
        self.refresh_lanes()
        if not self.engine.is_playing():
            self._stop()

    def _update_time_label(self):
        self.time_lbl.setText(
            f"{_fmt_clock(self.play_frame, self.sr)} / {_fmt_clock(self.n, self.sr)}")

    def seek(self, frame):
        self.play_frame = int(max(0, min(frame, self.n)))
        self.engine.seek(self.play_frame)
        self._update_time_label()
        self.refresh_lanes()

    # ── trim ─────────────────────────────────────────────────────
    def _toggle_trim(self):
        self._trim_on = not self._trim_on
        if self._trim_on and self.trim_end <= self.trim_start:
            self.trim_start, self.trim_end = 0, self.n
        self.trim_toggle_btn.setText("Disable Trim" if self._trim_on else "Enable Trim")
        self._update_trim_label()
        self.refresh_lanes()

    def set_trim(self, start=None, end=None):
        if not self._trim_on:
            self._trim_on = True
            self.trim_toggle_btn.setText("Disable Trim")
        if start is not None:
            self.trim_start = int(max(0, min(start, self.trim_end - 1)))
        if end is not None:
            self.trim_end = int(min(self.n, max(end, self.trim_start + 1)))
        self._update_trim_label()
        self.refresh_lanes()

    def _update_trim_label(self):
        if not self._trim_on:
            self.trim_lbl.setText("Trim: off")
            return
        self.trim_lbl.setText(
            f"Keep {_fmt_clock(self.trim_start, self.sr)} → "
            f"{_fmt_clock(self.trim_end, self.sr)}  "
            f"({_fmt_clock(self.trim_end - self.trim_start, self.sr)})")

    def _trim_save_as(self):
        if not self._can_trim():
            return
        base, ext = os.path.splitext(self.path)
        suggested = f"{base}_trim{ext}"
        dst, _ = QFileDialog.getSaveFileName(
            self, "Save trimmed WAV", suggested, "WAV files (*.wav)")
        if dst:
            self._do_trim(dst, reopen=False)

    def _trim_overwrite(self):
        if not self._can_trim():
            return
        self._do_trim(self.path, reopen=True)

    def _can_trim(self):
        if self.n <= 0:
            return False
        if not self._trim_on:
            self.trim_status.setText("Enable trim and set start/end first.")
            return False
        if self.trim_end - self.trim_start < 1:
            self.trim_status.setText("Trim range is empty.")
            return False
        if self.trim_start <= 0 and self.trim_end >= self.n:
            self.trim_status.setText("Nothing to trim (full file selected).")
            return False
        return True

    def _do_trim(self, dst, reopen):
        self._stop()
        self.trim_status.setText("Writing…")
        ok, err = write_wav_trim(self.path, dst, self.trim_start, self.trim_end)
        if not ok:
            self.trim_status.setText(f"Error: {err}")
            return
        self.trim_status.setText(f"Saved: {os.path.basename(dst)}")
        if reopen:
            # Reload the now-trimmed file so the view reflects the new length.
            self.md = read_audio_metadata(self.path)
            self._reset_for_reload()

    def _reset_for_reload(self):
        self.engine.stop()
        for i in reversed(range(self.lane_box.count() - 1)):
            item = self.lane_box.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.lanes = []
        self.strips = []
        self.audio = None
        self.pmin = self.pmax = None
        self.play_frame = 0
        self._trim_on = False
        self.trim_toggle_btn.setText("Enable Trim")
        self._update_trim_label()
        self.status_lbl.setText("Reloading…")
        self._peak_loader = PeakLoadWorker(self.path)
        self._peak_loader.loaded.connect(self._on_peaks_loaded)
        self._peak_loader.failed.connect(self._on_load_failed)
        self._peak_loader.start()
        self._audio_loader = None

    def _save_note(self):
        note = self.notes_edit.toPlainText()
        self.save_note_btn.setEnabled(False)
        self.note_status.setText("Saving…")
        ok, err = write_wav_note(self.path, note)
        if ok:
            self.md["note"] = note
            self.note_status.setText("Saved")
            QTimer.singleShot(2500, lambda: self.note_status.setText("")
                              if self.note_status else None)
        else:
            self.note_status.setText(f"Error: {err}")
        self.save_note_btn.setEnabled(True)

    def closeEvent(self, e):
        try:
            self.engine.stop()
            self._timer.stop()
            for loader in (getattr(self, "_peak_loader", None),
                           getattr(self, "_audio_loader", None)):
                if loader is not None and loader.isRunning():
                    loader.wait(1500)
        except Exception:
            pass
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyWav Merger 4.0.1-beta")
        self.setMinimumSize(560, 700)
        self.resize(760, 900)
        self._worker = None
        self._theme_labels = []   # (QLabel, style-template) for live theming
        self._set_icon()

        central = QWidget()
        central.setObjectName("rootWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        self._create_toolbar(layout)
        layout.addSpacing(12)

        # ── Tabs (native bar hidden) ─────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().hide()
        self.tabs.addTab(self._build_merge_tab(), "Merge")
        self.tabs.addTab(self._build_library_tab(), "Library")
        layout.addWidget(self.tabs, 1)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Restore last active tab
        last_tab = 0
        try:
            last_tab = int(load_setting("last_tab", 0))
        except (TypeError, ValueError):
            last_tab = 0
        if not (0 <= last_tab < self.tabs.count()):
            last_tab = 0
        self._select_tab(last_tab)

    def _select_tab(self, idx):
        self.tabs.setCurrentIndex(idx)
        for j, b in enumerate(self._nav_buttons):
            b.setSelected(j == idx)

    def _on_tab_changed(self, idx):
        for j, b in enumerate(self._nav_buttons):
            b.setSelected(j == idx)
        save_setting("last_tab", idx)

    def _build_merge_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 12, 0, 0)
        tab_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 0, 8, 14)
        content_layout.setSpacing(12)
        self._create_main_card(content_layout)

        scroll.setWidget(content)
        tab_layout.addWidget(scroll, 1)
        tab_layout.addSpacing(8)
        self._create_bottom(tab_layout)
        return tab

    def _build_library_tab(self):
        self.library_tab = LibraryTab()
        return self.library_tab

    def _toggle_theme(self):
        new = "light" if current_theme_name() == "dark" else "dark"
        apply_theme(new)
        self._theme_btn.setText("Light" if new == "dark" else "Dark")
        self._sync_accent_picker()

    def _pick_accent(self, accent_id):
        apply_accent(accent_id)
        self._sync_accent_picker()

    def _sync_accent_picker(self):
        if hasattr(self, "_accent_btn") and self._accent_btn is not None:
            self._accent_btn.update()
        if hasattr(self, "_progress_glow") and self._progress_glow is not None:
            glow = QColor(COLORS["accent"])
            glow.setAlpha(90)
            self._progress_glow.setColor(glow)

    def _themed_label(self, label, style_template):
        """Register a QLabel whose inline style depends on COLORS so it can be
        re-styled live on theme change. style_template uses {key} placeholders
        resolved against COLORS."""
        self._theme_labels.append((label, style_template))
        label.setStyleSheet(style_template.format(**COLORS))
        return label

    def _apply_theme(self):
        """Re-apply inline styles for theme-dependent labels (called by
        apply_theme via allWidgets scan)."""
        for label, template in list(self._theme_labels):
            try:
                label.setStyleSheet(template.format(**COLORS))
            except RuntimeError:
                # Label was deleted — drop it.
                self._theme_labels.remove((label, template))
        self._sync_accent_picker()

    def _set_icon(self):
        for name in ["icon.png", "icon_512.png", "icon.ico"]:
            p = resource_path(name)
            if p:
                self.setWindowIcon(QIcon(p))
                return

    def _create_toolbar(self, layout):
        """Compact app chrome — logo, tabs, appearance controls."""
        bar = QWidget()
        bar.setObjectName("appHeader")
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 0, 4, 0)
        row.setSpacing(10)

        row.addWidget(LogoWidget())
        title = QLabel("PolyWav Merger")
        self._themed_label(
            title,
            "font-size: 17px; font-weight: 600; color: {text}; "
            "letter-spacing: -0.3px; padding-right: 6px;")
        title.setToolTip("Combine wireless TX recordings with recorder tracks")
        row.addWidget(title, 0, Qt.AlignVCenter)

        row.addSpacing(8)
        self._nav_buttons = []
        for i, name in enumerate(["Merge", "Library"]):
            b = NavButton(name)
            b.clicked.connect(lambda _=False, idx=i: self._select_tab(idx))
            row.addWidget(b)
            self._nav_buttons.append(b)

        row.addStretch(1)
        self._accent_btn = AccentPickerButton()
        self._accent_btn.clicked.connect(self._show_accent_menu)
        row.addWidget(self._accent_btn)
        self._theme_btn = NavButton(
            "Light" if current_theme_name() == "dark" else "Dark")
        self._theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_btn)
        layout.addWidget(bar)

    def _show_accent_menu(self):
        pop = AccentPalettePopup(self)
        pop.picked.connect(self._pick_accent)
        pop.adjustSize()
        btn = self._accent_btn
        x = btn.mapToGlobal(QPoint(0, 0)).x() + btn.width() - pop.width()
        y = btn.mapToGlobal(QPoint(0, btn.height())).y() + 6
        pop.move(max(8, x), y)
        pop.show()

    def _card_layout(self, card):
        cl = QVBoxLayout(card)
        m = NeumorphicCard.content_margins()
        cl.setContentsMargins(m[0], m[1], m[2], m[3])
        cl.setSpacing(14)
        return cl

    def _create_main_card(self, layout):
        paths = NeumorphicCard()
        pl = self._card_layout(paths)
        self._sec(pl, "Source Paths")
        self.recorder_sel = FolderSelector("recorder folder", pin_key="recorder")
        pl.addWidget(self.recorder_sel)
        self._sec(pl, "TX Recordings")
        self.tx_sel = FolderSelector("TX folder", pin_key="tx")
        pl.addWidget(self.tx_sel)
        self._sec(pl, "Output")
        self.output_sel = FolderSelector("output folder", pin_key="output")
        pl.addWidget(self.output_sel)
        pl.addSpacing(2)
        self._sec(pl, "TX Track Prefix")
        prefix_hint = QLabel(
            "Prefix for transmitter tracks in the final polywav. "
            "Original mic names are kept after it.")
        prefix_hint.setWordWrap(True)
        self._themed_label(
            prefix_hint,
            "font-size: 11px; color: {text_muted}; "
            "background: transparent; line-height: 1.4;")
        pl.addWidget(prefix_hint)
        self.tx_prefix_edit = QLineEdit("TX")
        self.tx_prefix_edit.setPlaceholderText("e.g. TX, ATMO, RF")
        self.tx_prefix_edit.setToolTip(
            "Prefix for transmitter tracks in the final polywav.\n"
            "Example: 'TX' gives TX_LAV1, TX_BOOM. 'ATMO' gives ATMO_LAV1.")
        self.tx_prefix_edit.textChanged.connect(self._update_prefix_preview)
        pl.addWidget(self.tx_prefix_edit)
        self.prefix_preview = QLabel()
        self._themed_label(
            self.prefix_preview,
            "font-size: 11px; font-family: " + _mono_stack() + "; "
            "color: {text_secondary}; background: transparent;")
        pl.addWidget(self.prefix_preview)
        self._update_prefix_preview(self.tx_prefix_edit.text())
        layout.addWidget(paths)

        proc = NeumorphicCard()
        cl = self._card_layout(proc)
        self._sec(cl, "Processing")

        self.convert_toggle = ToggleSwitch("Convert 32-bit float to 24-bit")
        self.convert_toggle.setChecked(True)
        self.convert_toggle.setEnabled(False)
        cl.addWidget(self.convert_toggle)

        self.tx_only_toggle = ToggleSwitch(
            "TX Only Mode",
            "Process TX files without recorder sync")
        self.tx_only_toggle.toggled.connect(self._on_tx_only_changed)
        cl.addWidget(self.tx_only_toggle)

        self.clock_correction_toggle = ToggleSwitch(
            "Clock Drift Offset Correction",
            "Use recorder channels as waveform references after TC match")
        self.clock_correction_toggle.setChecked(True)
        cl.addWidget(self.clock_correction_toggle)

        self.filter_by_channel_toggle = ToggleSwitch(
            "Match TX to recorder tracks",
            "Skip TX whose channel isn't recorded in this take (override per-TX in mapping)")
        self.filter_by_channel_toggle.setChecked(True)
        cl.addWidget(self.filter_by_channel_toggle)

        cl.addSpacing(2)
        self._sec(cl, "Progress")
        self.progress_bar = NeumorphicProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        # Soft white glow around the filled portion.
        progress_glow = QGraphicsDropShadowEffect(self.progress_bar)
        progress_glow.setBlurRadius(22)
        glow = QColor(COLORS["accent"])
        glow.setAlpha(90)
        progress_glow.setColor(glow)
        progress_glow.setOffset(0, 0)
        self.progress_bar.setGraphicsEffect(progress_glow)
        self._progress_glow = progress_glow
        cl.addWidget(self.progress_bar)

        self.prog_label = QLabel("Ready")
        self._themed_label(
            self.prog_label,
            "font-size: 11px; color: {text_muted}; "
            "padding-left: 2px; background: transparent;")
        cl.addWidget(self.prog_label)

        cl.addSpacing(2)
        self._sec(cl, "Log")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_text.setPlaceholderText("Processing output will appear here...")
        cl.addWidget(self.log_text)

        layout.addWidget(proc)

    def _sec(self, layout, text):
        lbl = QLabel(text.upper())
        self._themed_label(
            lbl,
            "background: transparent; font-size: 11px; font-weight: 600; "
            "letter-spacing: 0.07em; color: {text_muted}; margin-bottom: 4px;")
        layout.addWidget(lbl)

    def _update_prefix_preview(self, text):
        prefix = _clean_tx_prefix(text)
        self.prefix_preview.setText(
            f"Example: {prefix}_LAV1, {prefix}_BOOM")

    def _create_bottom(self, layout):
        self.start_btn = PrimaryButton("Start Processing")
        self.start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_btn)

    # ── Slots ─────────────────────────────────────────────────────

    def _on_tx_only_changed(self, checked):
        if checked:
            self.convert_toggle.setEnabled(True)
        else:
            self.convert_toggle.setChecked(True)
            self.convert_toggle.setEnabled(False)

    def _on_start_clicked(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            return

        if not os.path.isdir(self.recorder_sel.path()):
            self._log("ERROR: Please select recorder folder", "error"); return
        if not os.path.isdir(self.tx_sel.path()):
            self._log("ERROR: Please select TX recordings folder", "error"); return
        if not self.output_sel.path():
            self._log("ERROR: Please select output folder", "error"); return

        # Recorder metadata is read from standard bext/iXML chunks. TX output
        # names are profile-independent; only the user prefix is applied.
        tx_profile = "Generic (by number)"
        tx_track_prefix = _clean_tx_prefix(self.tx_prefix_edit.text())

        # Show channel mapping dialog if clock correction OR channel filter is on
        align_map = None
        always_include = None
        keep_recorder_channels = None
        filter_by_channel = self.filter_by_channel_toggle.isChecked()
        show_dialog = self.clock_correction_toggle.isChecked() or filter_by_channel

        if show_dialog:
            tx_dir = self.tx_sel.path()
            tx_files = sorted([f for f in os.listdir(tx_dir) if f.lower().endswith(".wav")])

            if tx_files:
                rec_channels = get_all_recorder_channel_names(self.recorder_sel.path())
                if rec_channels:
                    dialog = ChannelMappingDialog(
                        self, tx_files, rec_channels, tx_profile, tx_track_prefix
                    )
                    if dialog.exec() == QDialog.Accepted:
                        align_map, always_include, keep_recorder_channels = dialog.mapping()
                        if align_map:
                            self._log(f"Channel mapping configured: {dialog.mapped_group_count()} TX groups", "dim")
                        if always_include:
                            self._log(f"Always-include override: {dialog.always_include_group_count()} TX groups", "dim")
                        if keep_recorder_channels:
                            self._log(f"TX-only recorder channels kept: {len(keep_recorder_channels)}", "dim")
                    else:
                        self._log("Processing cancelled", "dim")
                        return

        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.prog_label.setText("Starting...")
        self.start_btn.setText("Stop Processing")
        self.start_btn.setDanger(True)

        self._worker = ProcessWorker(
            r_dir             = self.recorder_sel.path(),
            tx_dir            = self.tx_sel.path(),
            o_dir             = self.output_sel.path(),
            normalize         = self.convert_toggle.isChecked(),
            tx_only           = self.tx_only_toggle.isChecked(),
            tx_profile        = tx_profile,
            align_map         = align_map,
            filter_by_channel = filter_by_channel,
            always_include    = always_include,
            keep_recorder_channels = keep_recorder_channels,
            tx_track_prefix   = tx_track_prefix,
            clock_correction  = self.clock_correction_toggle.isChecked(),
        )
        self._worker.signals.log.connect(self._log)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, cur, total, name):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(cur)
        self.prog_label.setText(f"File {cur} / {total}  ·  {name}")

    def _on_finished(self):
        self.start_btn.setText("Start Processing")
        self.start_btn.setDanger(False)
        self.prog_label.setText("Done")
        self._worker = None

    def _log(self, message: str, level: str = "info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {
            "info":    COLORS["notice"],
            "normal":  COLORS["text_secondary"],
            "dim":     COLORS["text_muted"],
            "ok":      COLORS["success"],
            "success": COLORS["success"],
            "warn":    COLORS["warning"],
            "warning": COLORS["warning"],
            "err":     COLORS["error"],
            "error":   COLORS["error"],
            "file":    "#818cf8",
        }
        color = colors.get(level, COLORS["text_secondary"])
        self.log_text.append(
            f'<span style="color:{color}">[{ts}] {message}</span>')
        # Auto scroll
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    saved_theme = load_setting("theme", "dark")
    if saved_theme not in THEMES:
        saved_theme = "dark"
    COLORS.clear()
    COLORS.update(THEMES[saved_theme])
    if saved_theme == "light":
        COLORS.update(LIGHT_ACCENTS[current_light_accent()])
    else:
        COLORS.update(DARK_ACCENTS[current_dark_accent()])
    app.setStyleSheet(build_stylesheet())
    font = QFont("Segoe UI", 11)
    if sys.platform == "darwin":
        font = QFont("SF Pro Text", 11)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
