"""
PolyWav Merger v8.0
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

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QFileDialog,
    QFrame, QScrollArea, QSizePolicy, QProgressBar, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
    QCheckBox, QMenu
)
from PySide6.QtCore import (
    Qt, QSize, Signal, QThread, QObject, QTimer, QRect, QRectF, QPoint
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath,
    QBrush, QPen, QLinearGradient, QIcon, QPixmap, QImage, QPalette,
    QKeySequence, QShortcut
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
# PALETTE
# ══════════════════════════════════════════════════════════════════
COLORS = {
    "bg":           "#1a1a1e",
    "card":         "#222226",
    "card_light":   "#2a2a2e",
    "card_inset":   "#151518",
    "shadow_dark":  "#0a0a0c",
    "shadow_light": "#2e2e34",
    "highlight":    "#3a3a40",
    "text":         "#ffffff",
    "text_secondary": "#8a8a94",
    "text_muted":   "#5a5a64",
    "accent":       "#ffffff",
    "border":       "#2a2a30",
    "success":      "#4ade80",
    "error":        "#f87171",
    "warning":      "#fbbf24",
}

STYLESHEET = f"""
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
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 14px;
    color: {COLORS['text']};
    min-height: 20px;
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
QTextEdit {{
    background-color: {COLORS['card_inset']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 14px;
    font-size: 12px;
    font-family: Consolas, monospace;
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
QScrollBar::handle:vertical:hover {{ background: {COLORS['highlight']}; }}
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
        stop: 0    #ffffff,
        stop: 0.5  #f3f3f8,
        stop: 1    #d6d6e0
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
    padding: 5px 10px;
    selection-background-color: {COLORS['highlight']};
}}
QFileDialog QComboBox {{
    background-color: {COLORS['card_inset']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 20px;
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
    padding: 4px 12px;
    min-width: 60px;
    min-height: 22px;
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
    color: {COLORS['bg']};
    border-color: {COLORS['accent']};
}}
QFileDialog QToolButton {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px 8px;
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
"""

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

TX_PROFILES = {
    "Deity DBTX / DXTX": {
        "description": "Deity DBTX lav + DXTX boom transmitters",
        "match": lambda name: bool(re.match(r"^(LAV\d*|BM)", name, re.IGNORECASE)),
        "track_name": lambda name: _deity_track_name(name),
        "chan_idx":   lambda name: _deity_chan_idx(name),
    },
    "Wisycom": {
        "description": "Wisycom MCR / MTP transmitters (WIS_ prefix)",
        "match": lambda name: bool(re.match(r"^WIS", name, re.IGNORECASE)),
        "track_name": lambda name: _smart_track_name(name, prefix="WIS"),
        "chan_idx":   lambda name: _smart_chan_idx(name),
    },
    "Zaxcom": {
        "description": "Zaxcom ZMT transmitters",
        "match": lambda name: bool(re.match(r"^ZAX", name, re.IGNORECASE)),
        "track_name": lambda name: _smart_track_name(name, prefix="ZAX"),
        "chan_idx":   lambda name: _smart_chan_idx(name),
    },
    "Lectrosonics": {
        "description": "Lectrosonics SMWB / DBSMD transmitters",
        "match": lambda name: bool(re.match(r"^LEC", name, re.IGNORECASE)),
        "track_name": lambda name: _smart_track_name(name, prefix="LEC"),
        "chan_idx":   lambda name: _smart_chan_idx(name),
    },
    "Generic (by number)": {
        "description": "Any transmitter — handles arbitrary file naming",
        "match": lambda name: True,
        "track_name": lambda name: _smart_track_name(name),
        "chan_idx":   lambda name: _smart_chan_idx(name),
    },
}

RECORDER_PROFILES = {
    "Zoom F-series":       "Standard Zoom BWF/iXML",
    "Sound Devices (all)": "Sound Devices MixPre / 8-series / Scorpio",
    "Zaxcom Nomad/Maxx":   "Zaxcom recorder",
    "Tentacle Sync E":     "Tentacle Sync recorder",
}


def _deity_track_name(name):
    if re.match(r"^BM", name, re.IGNORECASE): return f"DXTX_BM"
    m = re.match(r"^LAV(\d+)", name, re.IGNORECASE)
    if m: return f"DBTX_LAV{m.group(1)}"
    if re.match(r"^LAV", name, re.IGNORECASE): return "DBTX_LAV"
    return name[:12]

def _deity_chan_idx(name):
    if re.match(r"^BM", name, re.IGNORECASE): return 1
    m = re.match(r"^LAV(\d+)", name, re.IGNORECASE)
    return int(m.group(1)) if m else 30

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

def get_tx_info(basename: str, profile_name: str) -> dict:
    """Resolve track name + channel index for a TX file using selected profile."""
    name = os.path.splitext(basename)[0]
    
    # Auto-detect profile if "Auto" is selected
    if profile_name == "Auto (detect by filename)":
        for pname, pdef in TX_PROFILES.items():
            if pdef["match"](name):
                profile = pdef
                break
        else:
            profile = TX_PROFILES["Generic (by number)"]
    else:
        profile = TX_PROFILES.get(profile_name, TX_PROFILES["Generic (by number)"])
    
    return {
        "name":     profile["track_name"](name),
        "chan_idx": profile["chan_idx"](name),
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

        source_offset = off
        source_dur = r_dur
        ref_channel = None
        ref_channel_name = None
        primary_name = None        # what the user mapped (kept for logging)
        chan_missing = False
        align_result = None
        used_fallback = None       # None | "boom"
        boom_attempted = False

        if align_map:
            mapped = align_map.get(tn_base) or align_map.get(os.path.splitext(tn_base)[0])
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

def process_files(r_dir, tx_dir, o_dir, normalize, tx_only, tx_profile,
                  log_q, progress_q, stop_event, align_map=None,
                  filter_by_channel=False, always_include=None):
    def log(msg, tag="normal"): log_q.put((msg, tag))
    def prog(cur, total, name): progress_q.put((cur, total, name))

    always_include = always_include or set()

    r_files  = sorted([f for f in os.listdir(r_dir)  if f.lower().endswith(".wav")])
    tx_files = sorted([f for f in os.listdir(tx_dir) if f.lower().endswith(".wav")])
    norm_s   = "ON" if normalize else "OFF"
    align_s  = "ON" if align_map else "OFF"
    filter_s = "ON" if filter_by_channel else "OFF"
    log(f"Recorder: {len(r_files)} files  |  TX: {len(tx_files)} files  |  Normalize: {norm_s}  |  Clock offset correction: {align_s}  |  Channel filter: {filter_s}  |  Profile: {tx_profile}", "dim")
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
            off = r_start - dc["start"]

            # ── Channel-presence filter ───────────────────────────────
            # The TX is pulled in only if its target recorder channel is
            # actually present in THIS take's track list. Override via the
            # mapping dialog's "Always include" checkbox (for autonomous
            # plant mics on channels not physically on the recorder).
            if filter_by_channel:
                is_override = tn_base in always_include or base_no_ext in always_include
                if not is_override:
                    # Determine the TX's target channel:
                    #   1. Explicit mapping from the dialog (most reliable)
                    #   2. Auto-guess against this take's track names
                    target_name = (align_map.get(tn_base) or align_map.get(base_no_ext)) if align_map else None
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
            #   then by the profile-defined chan_idx (lower first),
            #   then alphabetical for stable tie-break.
            # Errors sink to the bottom so they don't push real tracks around.
            def _track_sort_key(result):
                tn = result.get("tn_base", "")
                if "error" in result:
                    return (3, 99999, tn.lower())
                ti = get_tx_info(os.path.splitext(tn)[0], tx_profile)
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
                ti = get_tx_info(os.path.splitext(tn_base)[0], tx_profile)
                hits.append({"file":tp,"name":tn_base,"track_name":ti["name"],
                             "offset":off_str,"dur":dur_str_h,"gain":gain,"sr":dc["sr"]})

        # No TX hits: emit a recorder-only POLY so takes aren't lost. In
        # TX-only mode we override the flag for this file and write recorder
        # tracks, with a "No TX signal" note in the iXML so the gap is visible
        # later in the metadata.
        fallback_no_tx = (not hits) and tx_only
        effective_tx_only = tx_only and bool(hits)

        if not hits:
            if fallback_no_tx:
                log("    (TX-only + no TX matches — exporting recorder with NO-TX note)", "warn")
            else:
                log("    (no TX matches — exporting recorder-only POLY)", "warn")

        out_path = os.path.join(o_dir, f"{rbase}_POLY.wav")
        if os.path.exists(out_path): log(f"    SKIP (exists): {rbase}_POLY.wav","dim"); continue

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
            for h in hits: ff += ["-ss",h["offset"],"-t",h["dur"],"-i",h["file"]]
            parts=[]; merge=""
            for j,h in enumerate(hits):
                ch=f"[{j}:a]"
                if h["sr"]!=r_sr: ch+=f"aresample={int(r_sr)}"+(f",volume={h['gain']:.6f}dB" if h["gain"] else "")
                elif h["gain"]:   ch+=f"volume={h['gain']:.6f}dB"
                else:             ch+="anull"
                ch+=f"[dd{j}]"; parts.append(ch); merge+=f"[dd{j}]"
            if len(hits)>1: parts.append(f"{merge}amerge=inputs={len(hits)}[out]")
            else:            parts.append(f"{merge}anull[out]")

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

        all_names = ([] if effective_tx_only else list(r_tnames))+[h["track_name"] for h in hits]
        extra_note = "No TX signal at this timecode" if fallback_no_tx else ""
        result = build_polywav(out_path, tmp, r_bext, r_ixml, all_names, f"{rbase}_POLY.wav", extra_note=extra_note)
        try: os.remove(tmp)
        except: pass
        if not os.path.exists(out_path):
            log(f"    ERROR: {result}","err"); continue

        sz   = round(os.path.getsize(out_path)/(1024*1024),1)
        n_ch = len(hits) if effective_tx_only else r_ch+len(hits)
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
                 align_map=None, filter_by_channel=False, always_include=None):
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


def select_directory_with_files(parent, label, current_path=""):
    """
    Folder picker that lets the user see files inside folders for orientation.

    Uses Qt's own non-native dialog with ShowDirsOnly=False on every platform
    so .wav files inside folders are visible — both the Win11 native folder
    picker and the macOS Finder folder-picker hide files in folder-select
    mode, which makes it hard to verify "this is the right folder, I see the
    .wav files I expect."

    Readability on any system theme (Win11 light, macOS light) is handled by
    the QFileDialog-scoped stylesheet rules and the explicit dark QPalette.
    """
    start_dir = current_path if current_path and os.path.isdir(current_path) else ""

    dialog = QFileDialog(parent, f"Select {label}")
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
    dialog.setNameFilters(["WAV files (*.wav)", "All files (*)"])
    _apply_dark_dialog_palette(dialog)
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
        radius = 24.0
        margin = 12.0
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        for i in range(14, 0, -1):
            alpha = int(26 * i / 14)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(10, 10, 12, alpha))
            spread = float(i) * 0.55
            shadow_rect = rect.adjusted(spread, spread + 2.0, -spread, -spread + 2.0)
            painter.drawRoundedRect(shadow_rect, radius, radius)

        for i in range(7, 0, -1):
            alpha = int(14 * i / 7)
            painter.setBrush(QColor(62, 62, 70, alpha))
            spread = float(i) * 0.35
            light_rect = rect.adjusted(-spread, -spread, spread, spread)
            painter.drawRoundedRect(light_rect, radius, radius)

        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0,  QColor(COLORS["card_light"]))
        gradient.setColorAt(0.5,QColor(COLORS["card"]))
        gradient.setColorAt(1,  QColor("#1e1e22"))
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor(255,255,255,12),1))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius-1, radius-1)


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

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label   = label
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
        w, h = self.width(), self.height(); radius = 14

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
        folder = select_directory_with_files(self, self._label, self._path)
        if folder:
            self._set_path_if_valid(folder)

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
        self.setFixedHeight(64)
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
        radius = 16.0
        rect = QRectF(8, 5, w - 16, h - 16)
        if not self._pressed:
            for i in range(10, 0, -1):
                alpha = int(24 * i / 10)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(10,10,12,alpha))
                spread = float(i) * 0.45
                painter.drawRoundedRect(
                    rect.adjusted(spread, spread + 2, -spread, -spread + 2),
                    radius, radius)
        path = QPainterPath()
        off = 2.0 if self._pressed else 0.0
        button_rect = rect.translated(off, off)
        path.addRoundedRect(button_rect, radius, radius)
        if self._danger:
            btn_color = QColor(COLORS["error"])
        else:
            btn_color = QColor("#f0f0f0") if self._hovered else QColor(COLORS["accent"])
        painter.fillPath(path, btn_color)
        painter.setPen(QColor(COLORS["bg"]))
        font = QFont(); font.setPixelSize(15); font.setWeight(QFont.DemiBold)
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

        # Compute filled width
        vmin = float(self.minimum())
        vmax = float(self.maximum())
        val = float(self.value())
        if vmax > vmin:
            ratio = max(0.0, min(1.0, (val - vmin) / (vmax - vmin)))
        else:
            ratio = 0.0

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
            grad.setColorAt(0.0, QColor("#ffffff"))
            grad.setColorAt(0.5, QColor("#f3f3f8"))
            grad.setColorAt(1.0, QColor("#d6d6e0"))
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

class ChannelMappingDialog(QDialog):
    # Compact combo style scoped to the dialog so the global 14px-padding
    # QComboBox style doesn't overflow the table rows.
    _COMBO_STYLE = f"""
        QComboBox {{
            background-color: {COLORS['card_inset']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 13px;
            color: {COLORS['text']};
            min-height: 0px;
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

    _CHECKBOX_STYLE = f"""
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

    def __init__(self, parent, tx_files, channel_labels, tx_profile):
        super().__init__(parent)
        self.setWindowTitle("Clock Drift Correction Mapping")
        self.setMinimumSize(900, 550)
        # Force dark background + palette so the dialog stays readable under
        # Win11 / macOS light system themes (same white-on-white bug we
        # fixed for QFileDialog — QDialog otherwise falls through to system bg).
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['bg']}; color: {COLORS['text']}; }}")
        _apply_dark_dialog_palette(self)
        self._channel_labels = channel_labels
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Match TX files to recorder reference channels")
        title.setStyleSheet(f"font-size: 17px; font-weight: 600; color: {COLORS['text']}; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Reference channel is used for clock-drift alignment. The same name also decides "
            "whether the TX gets pulled into a given take — if the channel isn't recorded in "
            "that take, the TX is skipped. Tick 'Always include' for autonomous plant mics on "
            "channels that don't physically exist on the recorder."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; background: transparent;")
        layout.addWidget(subtitle)

        self.table = QTableWidget(len(tx_files), 4)
        self.table.setHorizontalHeaderLabels(["TX file", "Detected name", "Recorder reference", "Always include"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
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
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        # Width for the reference-channel column fits "8: <longest-name>" comfortably.
        longest_label = max((len(lbl) for lbl in channel_labels), default=8)
        header.resizeSection(2, max(220, 18 + 9 * (longest_label + 4)))
        header.resizeSection(3, 130)

        self._rows = []
        for row, tx_file in enumerate(tx_files):
            track = get_tx_info(os.path.splitext(tx_file)[0], tx_profile)["name"]
            self.table.setItem(row, 0, QTableWidgetItem(tx_file))
            self.table.setItem(row, 1, QTableWidgetItem(track))
            self.table.setRowHeight(row, 44)

            # ── Reference channel combo ─────────────────────────
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(8, 6, 8, 6)
            cell_layout.setSpacing(0)
            combo = NoScrollComboBox()
            combo.setStyleSheet(self._COMBO_STYLE)
            combo.setFixedHeight(30)
            # Store channel NAME as data — the index can differ across recorder
            # files in a session, so we resolve the name → index per-file when
            # the alignment actually runs.
            combo.addItem("No correction", "")
            for label in channel_labels:
                combo.addItem(label, label)
            guess = guess_reference_channel(tx_file, track, channel_labels)
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

            self._rows.append((tx_file, combo, checkbox))
        layout.addWidget(self.table, 1)

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
                color: {COLORS['bg']};
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
        """Return (align_map, always_include).

        align_map      — {tx_filename: channel_name_str} for clock-drift alignment.
        always_include — set of tx_filenames that bypass the per-recorder
                         channel-presence filter (autonomous plant mics etc.)
        Both dicts/sets include the filename with AND without extension so
        lookups work regardless of which form the caller uses.
        """
        align_map = {}
        always_include = set()
        for tx_file, combo, checkbox in self._rows:
            channel = combo.currentData()
            base = os.path.splitext(tx_file)[0]
            if channel:
                align_map[tx_file] = str(channel)
                align_map[base] = str(channel)
            if checkbox.isChecked():
                always_include.add(tx_file)
                always_include.add(base)
        return align_map, always_include


# ══════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyWav Merger")
        self.setMinimumSize(480, 700)
        self.resize(520, 820)
        self._worker = None
        self._set_icon()

        central = QWidget()
        central.setObjectName("rootWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4,0,20,14)
        content_layout.setSpacing(16)
        self._create_header(content_layout)
        self._create_main_card(content_layout)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addSpacing(8)
        self._create_bottom(layout)

    def _set_icon(self):
        for name in ["icon.png", "icon_512.png", "icon.ico"]:
            p = resource_path(name)
            if p:
                self.setWindowIcon(QIcon(p))
                return

    def _create_header(self, layout):
        header = QWidget()
        header.setObjectName("appHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(0,0,0,10)
        hl.setSpacing(6)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        row.setSpacing(4)
        row.addWidget(LogoWidget())
        title = QLabel("PolyWav Merger")
        title.setStyleSheet(f"""
            font-size: 22px; font-weight: 600;
            color: {COLORS['text']}; letter-spacing: -0.5px;
        """)
        row.addWidget(title)
        hl.addLayout(row)
        sub = QLabel("Combine wireless TX recordings with recorder tracks")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        hl.addWidget(sub)
        layout.addWidget(header)

    def _create_main_card(self, layout):
        card = NeumorphicCard()
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(30,34,30,34)
        cl.setSpacing(16)

        self._sec(cl, "Recorder Folder")
        self.recorder_sel = FolderSelector("recorder folder")
        cl.addWidget(self.recorder_sel)

        self._sec(cl, "TX Recordings Folder")
        self.tx_sel = FolderSelector("TX folder")
        cl.addWidget(self.tx_sel)

        self._sec(cl, "Output Folder")
        self.output_sel = FolderSelector("output folder")
        cl.addWidget(self.output_sel)

        cl.addSpacing(4)
        self._sec(cl, "Settings")

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

        cl.addSpacing(4)
        self._sec(cl, "Progress")
        self.progress_bar = NeumorphicProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        # Soft white glow around the filled portion.
        progress_glow = QGraphicsDropShadowEffect(self.progress_bar)
        progress_glow.setBlurRadius(22)
        progress_glow.setColor(QColor(255, 255, 255, 70))
        progress_glow.setOffset(0, 0)
        self.progress_bar.setGraphicsEffect(progress_glow)
        cl.addWidget(self.progress_bar)

        self.prog_label = QLabel("Ready")
        self.prog_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; padding-left: 2px; background: transparent;")
        cl.addWidget(self.prog_label)

        cl.addSpacing(4)
        self._sec(cl, "Processing Log")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_text.setPlaceholderText("Processing output will appear here...")
        cl.addWidget(self.log_text)

        layout.addWidget(card)

    def _sec(self, layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            background: transparent;
            font-size: 13px; font-weight: 500;
            color: {COLORS['text_secondary']};
            padding-left: 2px; margin-bottom: 2px;
        """)
        layout.addWidget(lbl)

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

        # Recorder model and TX profile are auto-detected from file metadata —
        # the bext/iXML chunks are standard across every pro recorder, and TX
        # naming is auto-matched via prefix similarity + boom detection. No
        # dropdowns needed.
        tx_profile = "Auto (detect by filename)"

        # Show channel mapping dialog if clock correction OR channel filter is on
        align_map = None
        always_include = None
        filter_by_channel = self.filter_by_channel_toggle.isChecked()
        show_dialog = self.clock_correction_toggle.isChecked() or filter_by_channel

        if show_dialog:
            tx_dir = self.tx_sel.path()
            tx_files = sorted([f for f in os.listdir(tx_dir) if f.lower().endswith(".wav")])

            if tx_files:
                rec_channels = get_all_recorder_channel_names(self.recorder_sel.path())
                if rec_channels:
                    dialog = ChannelMappingDialog(
                        self, tx_files, rec_channels, tx_profile
                    )
                    if dialog.exec() == QDialog.Accepted:
                        align_map, always_include = dialog.mapping()
                        if align_map:
                            self._log(f"Channel mapping configured: {len(align_map)//2} files", "dim")
                        if always_include:
                            self._log(f"Always-include override: {len(always_include)//2} files", "dim")
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
        )
        self._worker.signals.log.connect(self._log)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, cur, total, name):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(cur)
        self.prog_label.setText(f"File {cur} / {total}  —  {name}")

    def _on_finished(self):
        self.start_btn.setText("Start Processing")
        self.start_btn.setDanger(False)
        self.prog_label.setText("Done")
        self._worker = None

    def _log(self, message: str, level: str = "info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {
            "info":    COLORS["text_secondary"],
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
    app.setStyleSheet(STYLESHEET)
    font = QFont("Segoe UI", 10)
    if sys.platform == "darwin":
        font = QFont("SF Pro Display", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

