"""
PolyWAV Builder  beta 1.0
Recorder + TX Conform Tool

pip install customtkinter requests pillow
python polywav_builder.py
"""

import sys, os, re, math, struct, queue, threading, datetime, subprocess
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageTk

# ── Hide console window on Windows ───────────────────────────────
if sys.platform == "win32":
    import ctypes
    try: ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except: pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ══════════════════════════════════════════════════════════════════
# PALETTE  — true neumorphism needs precise shadow math
# ══════════════════════════════════════════════════════════════════
BG         = "#16161a"   # base surface all elements sit on
RAISED_BG  = "#1c1c22"  # raised element bg (slightly lighter than BG)
INSET_BG   = "#111115"  # inset element bg  (slightly darker than BG)
SHADOW_D   = "#0a0a0d"  # dark shadow (bottom-right on raised, top-left on inset)
SHADOW_L   = "#262630"  # light shadow (top-left on raised, bottom-right on inset)
ACCENT     = "#FFC800"
ACCENT_H   = "#FFD84D"
ACCENT_DIM = "#8A6E00"
ACCENT_BG  = "#2a2200"
TEXT       = "#dddde8"
TEXT_DIM   = "#5a5a72"
TEXT_MUTED = "#3a3a4a"
LOG_BG     = "#0f0f13"
OK         = "#3dd68c"
WARN       = "#FFC800"
ERR        = "#f56565"
FILE_CLR   = "#7c8cff"
BORDER     = "#232330"

# ══════════════════════════════════════════════════════════════════
# TX PROFILES — extensible device registry
# Add new recorders / transmitters here without touching any logic
# ══════════════════════════════════════════════════════════════════
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
        "track_name": lambda name: f"WIS_{re.sub(r'[^0-9]','',name) or '?'}",
        "chan_idx":   lambda name: int(re.sub(r"[^0-9]","",name) or 99),
    },
    "Zaxcom": {
        "description": "Zaxcom ZMT transmitters",
        "match": lambda name: bool(re.match(r"^ZAX", name, re.IGNORECASE)),
        "track_name": lambda name: f"ZAX_{re.sub(r'[^0-9]','',name) or '?'}",
        "chan_idx":   lambda name: int(re.sub(r"[^0-9]","",name) or 99),
    },
    "Lectrosonics": {
        "description": "Lectrosonics SMWB / DBSMD transmitters",
        "match": lambda name: bool(re.match(r"^LEC", name, re.IGNORECASE)),
        "track_name": lambda name: f"LEC_{re.sub(r'[^0-9]','',name) or '?'}",
        "chan_idx":   lambda name: int(re.sub(r"[^0-9]","",name) or 99),
    },
    "Generic (by number)": {
        "description": "Any transmitter — track named by file number",
        "match": lambda name: True,
        "track_name": lambda name: f"TX_{re.sub(r'[^0-9]','',name) or name[:6]}",
        "chan_idx":   lambda name: int(re.sub(r"[^0-9]","",name) or 0) or 99,
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

def build_polywav(out_path, tmp_path, rec_bext, r_ixml, track_names, orig_filename):
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
            f"\t<NOTE></NOTE>\r\n",
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
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
    if os.path.exists(local): ff = local
    p = subprocess.run([ff]+args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stderr

# ══════════════════════════════════════════════════════════════════
# PROCESSING THREAD
# ══════════════════════════════════════════════════════════════════

def process_files(r_dir, tx_dir, o_dir, normalize, tx_only, tx_profile,
                  log_q, progress_q, stop_event):
    def log(msg, tag="normal"): log_q.put((msg, tag))
    def prog(cur, total, name): progress_q.put((cur, total, name))

    r_files  = sorted([f for f in os.listdir(r_dir)  if f.lower().endswith(".wav")])
    tx_files = sorted([f for f in os.listdir(tx_dir) if f.lower().endswith(".wav")])
    norm_s   = "ON" if normalize else "OFF"
    log(f"Recorder: {len(r_files)} files  |  TX: {len(tx_files)} files  |  Normalize: {norm_s}  |  Profile: {tx_profile}", "dim")
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
        for tp, dc in tx_cache.items():
            if not (r_start >= dc["start"] and r_end <= dc["end"]): continue
            tn_base = os.path.basename(tp)
            off = r_start - dc["start"]; off_str = f"{off:.6f}"; gain = 0.0
            if dc["is_float"] and normalize:
                peak = get_peak_db(tp, off, r_dur)
                if peak > -1.0:
                    gain = -1.0 - peak
                    log(f"    ↳ {tn_base}  Peak:{round(peak,2)} dBFS  gain:{round(gain,2)} dB", "warn")
                else:
                    log(f"    ↳ {tn_base}  Peak:{round(peak,2)} dBFS", "dim")
            else:
                log(f"    ↳ {tn_base}  [{dc['bps']}-bit]", "normal")
            ti = get_tx_info(os.path.splitext(tn_base)[0], tx_profile)
            hits.append({"file":tp,"name":tn_base,"track_name":ti["name"],
                         "offset":off_str,"dur":dur_str,"gain":gain,"sr":dc["sr"]})

        if not hits: log("    (no TX matches)", "dim"); continue

        out_path = os.path.join(o_dir, f"{rbase}_POLY.wav")
        if os.path.exists(out_path): log(f"    SKIP (exists): {rbase}_POLY.wav","dim"); continue

        ff = ["-loglevel","error","-y"]
        if not tx_only:
            ff += ["-i", rp]
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
        use_float = tx_only and not normalize
        ff += ["-c:a","pcm_f32le" if use_float else "pcm_s24le","-ar",str(int(r_sr))]
        tmp = out_path+".tmp.wav"; ff.append(tmp)
        rc, stderr = run_ffmpeg(ff)
        if stop_event.is_set(): return
        if not os.path.exists(tmp):
            log(f"    ERROR: ffmpeg failed","err")
            for ln in stderr.strip().splitlines()[-5:]:
                if ln.strip(): log(f"      {ln}","err")
            continue

        all_names = ([] if tx_only else list(r_tnames))+[h["track_name"] for h in hits]
        result = build_polywav(out_path, tmp, r_bext, r_ixml, all_names, f"{rbase}_POLY.wav")
        try: os.remove(tmp)
        except: pass
        if not os.path.exists(out_path):
            log(f"    ERROR: {result}","err"); continue

        sz   = round(os.path.getsize(out_path)/(1024*1024),1)
        n_ch = len(hits) if tx_only else r_ch+len(hits)
        log(f"    ✓  {rbase}_POLY.wav   {sz} MB   {n_ch} ch", "ok" if result=="OK" else "warn")
        log(f"       {' | '.join(all_names)}", "dim")
        total_created += 1

    prog(len(r_files), len(r_files), "Done")
    log("─"*60, "dim")
    log(f"Done. PolyWAV files created: {total_created}", "ok")


# ══════════════════════════════════════════════════════════════════
# NEUMORPHIC CANVAS WIDGETS
# Pure tkinter canvas — gives us real shadows impossible in CTk
# ══════════════════════════════════════════════════════════════════

class NeuFrame(tk.Canvas):
    """A raised or inset neumorphic panel drawn on a Canvas."""
    def __init__(self, parent, width, height, inset=False, radius=14, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=BG, highlightthickness=0, bd=0, **kw)
        self.width = width; self.height = height
        self._inset = inset; self._radius = radius
        self.bind("<Configure>", lambda e: self._draw())
        self.after_idle(self._draw)

    def _draw(self):
        self.delete("all")
        w, h, r = self.width, self.height, self._radius
        bg = INSET_BG if self._inset else RAISED_BG
        sl = SHADOW_D if self._inset else SHADOW_L  # top-left
        sr = SHADOW_L if self._inset else SHADOW_D  # bottom-right

        # Shadows inside bounds only (prevents artifacts on edges)
        if not self._inset:
            # Raised: bottom-right shadow
            self._rounded_rect(1, 1, w-1, h-1, r, sr)
            self._rounded_rect(2, 2, w, h, r, sr)
            # Raised: top-left highlight
            self._rounded_rect(0, 0, w-2, h-2, r, sl)
        else:
            # Inset: top-left shadow
            self._rounded_rect(1, 1, w-1, h-1, r, sl)
            # Inset: bottom-right shadow  
            self._rounded_rect(0, 0, w-1, h-1, r, sr)

        # Main surface
        self._rounded_rect(0, 0, w, h, r, bg)

    def _rounded_rect(self, x1, y1, x2, y2, r, color):
        r = min(r, max(1, (x2-x1)//2), max(1, (y2-y1)//2))
        if r < 1: r = 1
        pts = [
            x1+r,y1, x2-r,y1,
            x2,y1, x2,y1+r,
            x2,y2-r, x2,y2,
            x2-r,y2, x1+r,y2,
            x1,y2, x1,y2-r,
            x1,y1+r, x1,y1,
        ]
        self.create_polygon(pts, smooth=True, fill=color, outline="")


class NeuButton(tk.Canvas):
    """A raised neumorphic button with yellow accent + press animation."""
    def __init__(self, parent, text, command, width=220, height=46,
                 accent=False, danger=False, small=False, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=BG, highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._text    = text
        self._cmd     = command
        self.width    = width; self.height = height
        self._accent  = accent; self._danger = danger
        self._small   = small
        self._pressed = False
        self._hover = False
        self.after_idle(lambda: self._draw(False))
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)

    def _draw(self, pressed):
        self.delete("all")
        w, h = self.width, self.height; r = h // 2
        if self._accent:
            bg = ACCENT_H if self._hover and not pressed else ACCENT
        elif self._danger:
            bg = "#c03030" if self._hover and not pressed else ERR
        else:
            bg = SHADOW_L if self._hover and not pressed else RAISED_BG

        if pressed:
            # Inset — swap shadows (inside bounds only)
            self._rrect(1, 1, w-1, h-1, r, SHADOW_L)
            self._rrect(0, 0, w-1, h-1, r, SHADOW_D)
        else:
            # Raised (inside bounds only)
            self._rrect(1, 1, w-1, h-1, r, SHADOW_D)
            self._rrect(2, 2, w, h, r, SHADOW_D)
            self._rrect(0, 0, w-2, h-2, r, SHADOW_L)

        self._rrect(0, 0, w, h, r, bg)

        tc = BG if self._accent else (TEXT if not self._danger else "#fff")
        fs = 9 if self._small else 11
        fw = "bold"
        self.create_text(w//2+(1 if pressed else 0), h//2+(1 if pressed else 0),
                         text=self._text, fill=tc,
                         font=("Segoe UI", fs, fw))

    def _rrect(self, x1, y1, x2, y2, r, color):
        # Proper symmetric rounded rectangle, clip at bounds
        if x2 <= x1 or y2 <= y1: return
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        r = max(2, min(r, w//2, h//2))
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.create_polygon(pts, smooth=True, fill=color, outline="")

    def configure_text(self, text):
        self._text = text; self._draw(self._pressed)

    def configure_danger(self, danger):
        self._danger = danger; self._accent = False; self._draw(self._pressed)

    def configure_accent(self, accent):
        self._accent = accent; self._danger = False; self._draw(self._pressed)

    def _on_press(self,  e): self._pressed=True;  self._draw(True)
    def _on_release(self,e): self._pressed=False; self._draw(False); self._cmd()
    def _on_enter(self,  e): self._hover=True;    self._draw(self._pressed)
    def _on_leave(self,  e): self._hover=False;   self._draw(self._pressed)


class NeuEntry(tk.Frame):
    """An inset neumorphic text entry."""
    def __init__(self, parent, textvariable=None, width=400, **kw):
        super().__init__(parent, bg=BG, bd=0, **kw)
        self._cv = tk.Canvas(self, width=width, height=36,
                             bg=BG, highlightthickness=0, bd=0)
        self._cv.pack()
        self.width = width; self.height = 36
        self._draw_inset()
        self._entry = tk.Entry(self._cv, textvariable=textvariable,
                               font=("Segoe UI", 11),
                               bg=INSET_BG, fg=TEXT, bd=0,
                               insertbackground=ACCENT,
                               selectbackground=ACCENT_DIM,
                               highlightthickness=0, relief="flat")
        self._cv.create_window(18, 18, anchor="w",
                               window=self._entry, width=width-24, height=26)

    def _draw_inset(self):
        w, h, r = self.width, self.height, self.height//2
        c = self._cv
        for i in range(2,0,-1):
            self._rrect(c,-i,-i,w-i,h-i,r,SHADOW_L)
        for i in range(2,0,-1):
            self._rrect(c,i,i,w+i-1,h+i-1,r,SHADOW_D)
        self._rrect(c,0,0,w,h,r,INSET_BG)

    def _rrect(self, c, x1,y1,x2,y2,r,color):
        r=max(1,min(r,(x2-x1)//2,(y2-y1)//2))
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        c.create_polygon(pts,smooth=True,fill=color,outline="")


class NeuCheck(tk.Frame):
    """A neumorphic toggle checkbox."""
    def __init__(self, parent, text, variable, command=None, **kw):
        super().__init__(parent, bg=RAISED_BG, **kw)
        self._var = variable; self._cmd = command; self._enabled = True
        row = tk.Frame(self, bg=RAISED_BG); row.pack(fill="x", padx=14, pady=10)

        self._box = tk.Canvas(row, width=22, height=22,
                              bg=RAISED_BG, highlightthickness=0, cursor="hand2")
        self._box.pack(side="left")
        self._box.bind("<ButtonRelease-1>", self._toggle)
        self.after_idle(self._draw_box)

        self._lbl = tk.Label(row, text=text, font=("Segoe UI",10),
                             fg=TEXT, bg=RAISED_BG, cursor="hand2",
                             anchor="w", justify="left")
        self._lbl.pack(side="left", padx=10, fill="x", expand=True)
        self._lbl.bind("<ButtonRelease-1>", self._toggle)
        variable.trace_add("write", lambda *_: self._draw_box())

    def _draw_box(self):
        c = self._box; c.delete("all")
        on = self._var.get()
        bg = ACCENT if on else INSET_BG
        # Inset shadow when off, raised+filled when on
        if on:
            for i in range(2,0,-1): self._rr(c,-i,-i,22-i,22-i,6,SHADOW_L)
            for i in range(2,0,-1): self._rr(c,i,i,22+i-1,22+i-1,6,SHADOW_D)
        else:
            for i in range(2,0,-1): self._rr(c,-i,-i,22-i,22-i,6,SHADOW_D)
            for i in range(2,0,-1): self._rr(c,i,i,22+i-1,22+i-1,6,SHADOW_L)
        self._rr(c,0,0,22,22,6,bg)
        if on:
            c.create_line(5,11,9,15,17,7, fill=BG, width=2.5, capstyle="round", joinstyle="round")

    def _rr(self,c,x1,y1,x2,y2,r,color):
        r=max(1,min(r,(x2-x1)//2,(y2-y1)//2))
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        c.create_polygon(pts,smooth=True,fill=color,outline="")

    def _toggle(self, e=None):
        if not self._enabled: return
        self._var.set(not self._var.get())
        if self._cmd: self._cmd()

    def set_enabled(self, enabled):
        self._enabled = enabled
        col = TEXT if enabled else TEXT_MUTED
        self._lbl.configure(fg=col)
        self._draw_box()


class NeuProgressBar(tk.Canvas):
    """Neumorphic inset progress bar."""
    def __init__(self, parent, width=760, height=10, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=BG, highlightthickness=0, bd=0, **kw)
        self.width=width; self.height=height; self._val=0.0
        self.after_idle(self._draw)

    def set(self, val):
        self._val = max(0.0, min(1.0, val)); self._draw()

    def _draw(self):
        self.delete("all"); w,h=self.width,self.height; r=h//2
        # Inset track - shadows inside bounds only
        self._rr(1, 1, w-1, h-1, r, SHADOW_L)
        self._rr(0, 0, w-1, h-1, r, SHADOW_D)
        self._rr(0, 0, w, h, r, INSET_BG)
        # Fill
        fw = int((w-4)*self._val)
        if fw > 0:
            self._rr(2,2,fw+2,h-2,r-1,ACCENT)

    def _rr(self,x1,y1,x2,y2,r,color):
        if x2<=x1 or y2<=y1: return
        r=max(1,min(r,(x2-x1)//2,(y2-y1)//2))
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.create_polygon(pts,smooth=True,fill=color,outline="")


# ══════════════════════════════════════════════════════════════════
# MAIN APPLICATION WINDOW
# ══════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PolyWAV Builder")
        self.geometry("1000x950")
        self.minsize(800, 700)
        self.resizable(True, True)
        self.configure(fg_color=BG)

        self.log_q      = queue.Queue()
        self.progress_q = queue.Queue()
        self.stop_event = threading.Event()
        self.worker     = None

        self._build()
        self._poll()

    # ── Header ───────────────────────────────────────────────────
    def _build(self):
        self._build_header()
        scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG, scrollbar_button_color=RAISED_BG,
            scrollbar_button_hover_color=RAISED_BG, corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self._build_body(scroll_frame)
        self._build_bottom()

    def _create_fallback_logo(self, inner):
        """Fallback waveform logo if image not found"""
        logo = tk.Canvas(inner, width=48, height=48,
                         bg="#111113", highlightthickness=0)
        logo.pack(side="left", pady=10)
        bars = [8,20,12,30,16,34,14,26,10]
        bw,gap,sx = 3,1,3
        for i,bh in enumerate(bars):
            bx=sx+i*(bw+gap); by=24-bh//2
            logo.create_rectangle(bx,by,bx+bw,by+bh, fill=ACCENT, outline="", width=0)
        logo.create_line(10,40,38,40, fill=ACCENT_DIM, width=1.5, arrow="last",
                         arrowshape=(5,6,3))

    def _build_header(self):
        hdr = tk.Frame(self, bg="#111113", height=78)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        # Accent stripe
        tk.Frame(hdr, bg=ACCENT, height=3).pack(fill="x")
        inner = tk.Frame(hdr, bg="#111113"); inner.pack(fill="both",expand=True,padx=22)

        # ── Logo — search in multiple locations (works both dev and PyInstaller) ──
        def _asset_path(filename):
            """Find asset: PyInstaller _MEIPASS → script dir → current dir."""
            for base in [
                getattr(sys, "_MEIPASS", None),
                os.path.dirname(os.path.abspath(__file__)),
                os.getcwd(),
            ]:
                if base:
                    p = os.path.join(base, filename)
                    if os.path.exists(p): return p
            return None

        logo_loaded = False
        logo_png = _asset_path("logo_48.png")
        logo_ico = _asset_path("polywav_icon.ico")

        if logo_png:
            try:
                img = Image.open(logo_png).resize((52, 52), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(img)
                tk.Label(inner, image=self.logo_photo,
                         bg="#111113").pack(side="left", pady=10)
                # Set taskbar / window icon — prefer .ico on Windows, fallback to png
                if logo_ico and sys.platform == "win32":
                    try: self.iconbitmap(logo_ico)
                    except: self.iconphoto(False, self.logo_photo)
                else:
                    self.iconphoto(False, self.logo_photo)
                logo_loaded = True
            except Exception as e:
                pass

        if not logo_loaded:
            self._create_fallback_logo(inner)

        title_f = tk.Frame(inner, bg="#111113"); title_f.pack(side="left",padx=12,pady=10)
        tk.Label(title_f, text="POLYWAV BUILDER",
                 font=("Segoe UI",15,"bold"),
                 fg=ACCENT, bg="#111113").pack(anchor="w")
        tk.Label(title_f, text="Recorder  +  TX  Conform  Tool",
                 font=("Segoe UI",9), fg=TEXT_DIM, bg="#111113").pack(anchor="w")
        tk.Label(inner, text="beta 1.0", font=("Consolas",9),
                 fg=ACCENT_DIM, bg="#111113").pack(side="right",pady=10)

    # ── Body ─────────────────────────────────────────────────────
    def _build_body(self, parent):
        pad = {"padx":20}

        # ── Folder section ────────────────────────────────────────
        self._sec_label(parent, "SOURCE FOLDERS", **pad)

        self.r_var = self._folder_row_on(parent, "RECORDER", 760)
        self.tx_var = self._folder_row_on(parent, "TX FILES", 760)
        self.o_var = self._folder_row_on(parent, "OUTPUT", 760)

        self._sep(parent, **pad)

        # ── Device profiles ───────────────────────────────────────
        self._sec_label(parent, "DEVICE PROFILES", **pad)
        prof_card = NeuFrame(parent, 760, 90, radius=14)
        prof_card.pack(**pad, pady=(6,0))

        row1 = tk.Frame(prof_card, bg=RAISED_BG); row1.place(x=16,y=10)
        tk.Label(row1, text="TX Profile", font=("Segoe UI",9,"bold"),
                 fg=TEXT_DIM, bg=RAISED_BG, width=10, anchor="w").pack(side="left")
        self.tx_profile_var = ctk.StringVar(value="Auto (detect by filename)")
        tx_menu = ctk.CTkOptionMenu(row1,
            variable=self.tx_profile_var,
            values=["Auto (detect by filename)"] + list(TX_PROFILES.keys()),
            font=("Segoe UI",10), text_color=TEXT,
            fg_color=INSET_BG, button_color=RAISED_BG,
            button_hover_color=SHADOW_L, dropdown_fg_color=INSET_BG,
            dropdown_text_color=TEXT, dropdown_hover_color=RAISED_BG,
            corner_radius=8, width=300, height=30)
        tx_menu.pack(side="left", padx=8)

        row2 = tk.Frame(prof_card, bg=RAISED_BG); row2.place(x=16,y=50)
        tk.Label(row2, text="Recorder", font=("Segoe UI",9,"bold"),
                 fg=TEXT_DIM, bg=RAISED_BG, width=10, anchor="w").pack(side="left")
        self.rec_profile_var = ctk.StringVar(value="Zoom F-series")
        rec_menu = ctk.CTkOptionMenu(row2,
            variable=self.rec_profile_var,
            values=list(RECORDER_PROFILES.keys()),
            font=("Segoe UI",10), text_color=TEXT,
            fg_color=INSET_BG, button_color=RAISED_BG,
            button_hover_color=SHADOW_L, dropdown_fg_color=INSET_BG,
            dropdown_text_color=TEXT, dropdown_hover_color=RAISED_BG,
            corner_radius=8, width=300, height=30)
        rec_menu.pack(side="left", padx=8)

        self._sep(parent, **pad)

        # ── Options ───────────────────────────────────────────────
        self._sec_label(parent, "OPTIONS", **pad)

        opt_card = NeuFrame(parent, 760, 100, radius=14)
        opt_card.pack(**pad, pady=(6,0))

        self.norm_var = tk.BooleanVar(value=True)
        self.norm_chk = NeuCheck(opt_card,
            "Convert 32-bit float → 24-bit PCM   |   Peak > -1 dBFS → limit to -1 dBFS",
            self.norm_var)
        self.norm_chk.place(x=0, y=0, width=760, height=50)

        self.tx_only_var = tk.BooleanVar(value=False)
        self.tx_chk = NeuCheck(opt_card,
            "TX only mode   —   Recorder used as timecode anchor only, not included in output",
            self.tx_only_var, command=self._on_tx_only_toggle)
        self.tx_chk.place(x=0, y=50, width=760, height=50)

        self._sep(parent, **pad)

        # ── Progress ──────────────────────────────────────────────
        self._sec_label(parent, "PROGRESS", **pad)
        prog_card = NeuFrame(parent, 760, 56, radius=14)
        prog_card.pack(**pad, pady=(6,0))

        self.prog_bar = NeuProgressBar(prog_card, width=728, height=10)
        self.prog_bar.place(x=16, y=10)

        lrow = tk.Frame(prog_card, bg=RAISED_BG); lrow.place(x=16,y=30)
        self.prog_l = tk.Label(lrow, text="READY", font=("Consolas",8),
                               fg=ACCENT_DIM, bg=RAISED_BG)
        self.prog_l.pack(side="left")
        self.prog_r = tk.Label(lrow, text="", font=("Consolas",8),
                               fg=TEXT_DIM, bg=RAISED_BG)
        self.prog_r.pack(side="left", padx=20)

        self._sep(parent, **pad)

        # ── Log ───────────────────────────────────────────────────
        self._sec_label(parent, "LOG", **pad)
        log_outer = NeuFrame(parent, 760, 280, inset=True, radius=14)
        log_outer.pack(**pad, pady=(6,20))

        self.log_text = tk.Text(log_outer, font=("Consolas",9),
                                bg=LOG_BG, fg=TEXT, bd=0,
                                highlightthickness=0, relief="flat",
                                state="disabled", wrap="none",
                                insertbackground=ACCENT)
        sb = tk.Scrollbar(log_outer, command=self.log_text.yview,
                          bg=RAISED_BG, troughcolor=INSET_BG,
                          activebackground=SHADOW_L, width=10,
                          highlightthickness=0, bd=0, relief="flat")
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.place(x=4, y=4, width=730, height=272)
        sb.place(x=734, y=4, height=272, width=10)

        for tag,col in [("ok",OK),("warn",WARN),("err",ERR),
                        ("dim",TEXT_DIM),("file",FILE_CLR),("normal",TEXT)]:
            self.log_text.tag_config(tag, foreground=col)

        self._on_tx_only_toggle()

    def _build_bottom(self):
        bottom = tk.Frame(self, bg=RAISED_BG, height=80)
        bottom.pack(fill="x", side="bottom"); bottom.pack_propagate(False)
        tk.Frame(bottom, bg=SHADOW_D, height=1).pack(fill="x")

        self.start_btn = NeuButton(bottom, "▶   START PROCESSING",
                                   command=self._on_start,
                                   width=240, height=46, accent=True)
        self.start_btn.place(relx=0.5, rely=0.5, anchor="center")

    # ── UI helpers ────────────────────────────────────────────────
    def _sec_label(self, parent, text, **kw):
        row = tk.Frame(parent, bg=BG); row.pack(fill="x", pady=(14,4), **kw)
        tk.Frame(row, bg=ACCENT, width=3, height=13).pack(side="left")
        tk.Label(row, text=text, font=("Segoe UI",7,"bold"),
                 fg=ACCENT_DIM, bg=BG).pack(side="left", padx=8)

    def _sep(self, parent, **kw):
        tk.Frame(parent, bg=SHADOW_D, height=1).pack(fill="x", pady=(12,0), **kw)
        tk.Frame(parent, bg=SHADOW_L, height=1).pack(fill="x", pady=(0,12), **kw)

    def _folder_row_on(self, parent, label, total_w):
        """Build a folder row with label, entry and browse button."""
        var = tk.StringVar()
        
        # Container frame
        row = tk.Frame(parent, bg=RAISED_BG, height=50)
        row.pack(fill="x", padx=20, pady=3)
        row.pack_propagate(False)
        
        # Label
        tk.Label(row, text=label, font=("Segoe UI",9,"bold"),
                 fg=ACCENT, bg=RAISED_BG, width=10, anchor="w").pack(side="left", padx=8)
        
        # Entry with copy/paste support
        entry = tk.Entry(row, textvariable=var,
                         font=("Segoe UI",11),
                         bg=INSET_BG, fg=TEXT, bd=1, relief="solid",
                         insertbackground=ACCENT,
                         selectbackground=ACCENT_DIM,
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER)
        entry.pack(side="left", fill="both", expand=True, padx=8)
        
        # Enable standard cut/copy/paste
        entry.bind("<Control-c>", lambda e: self._copy_entry(entry, e))
        entry.bind("<Control-x>", lambda e: self._cut_entry(entry, e))
        entry.bind("<Control-v>", lambda e: self._paste_entry(entry, e))
        
        # Browse button
        btn = NeuButton(row, "Browse",
                        command=lambda v=var: self._browse(v),
                        width=74, height=30, small=True)
        btn.pack(side="left", padx=8)
        
        return var

    def _browse(self, var):
        p = filedialog.askdirectory()
        if p: var.set(p)

    def _copy_entry(self, entry, e):
        """Copy selected text to clipboard"""
        try:
            text = entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
        except: pass
        return "break"

    def _cut_entry(self, entry, e):
        """Cut selected text to clipboard"""
        try:
            text = entry.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
            entry.delete("sel.first", "sel.last")
        except: pass
        return "break"

    def _paste_entry(self, entry, e):
        """Paste text from clipboard"""
        try:
            text = self.clipboard_get()
            entry.delete("sel.first", "sel.last") if entry.selection_present() else None
            entry.insert("insert", text)
        except: pass
        return "break"

    def _on_tx_only_toggle(self):
        if self.tx_only_var.get():
            self.norm_chk.set_enabled(True)
        else:
            self.norm_var.set(True)
            self.norm_chk.set_enabled(False)

    # ── Log / progress ────────────────────────────────────────────
    def _log(self, msg, tag="normal"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_progress(self, cur, total, name):
        if total > 0: self.prog_bar.set(cur/total)
        self.prog_l.configure(text=f"FILE {cur} / {total}")
        self.prog_r.configure(text=name)

    def _poll(self):
        try:
            while True:
                msg, tag = self.log_q.get_nowait(); self._log(msg, tag)
        except queue.Empty: pass
        try:
            while True:
                c,t,n = self.progress_q.get_nowait(); self._set_progress(c,t,n)
        except queue.Empty: pass
        if self.worker and not self.worker.is_alive():
            self.worker = None
            self.start_btn.configure_text("▶   START PROCESSING")
            self.start_btn.configure_accent(True)
        self.after(80, self._poll)

    # ── Start / Stop ──────────────────────────────────────────────
    def _on_start(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.start_btn.configure_text("■  STOPPING...")
            self.start_btn.configure_danger(True)
            return

        r_dir  = self.r_var.get().strip()
        tx_dir = self.tx_var.get().strip()
        o_dir  = self.o_var.get().strip()

        if not os.path.isdir(r_dir):
            self._log("ERROR: Recorder folder not found", "err"); return
        if not os.path.isdir(tx_dir):
            self._log("ERROR: TX folder not found", "err"); return
        if not o_dir:
            self._log("ERROR: Output folder not set", "err"); return

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")
        self.prog_bar.set(0)
        self.prog_l.configure(text="FILE 0 / 0"); self.prog_r.configure(text="")

        self.stop_event.clear()
        self.start_btn.configure_text("■   STOP")
        self.start_btn.configure_danger(True)

        self.worker = threading.Thread(
            target=process_files,
            args=(r_dir, tx_dir, o_dir,
                  self.norm_var.get(), self.tx_only_var.get(),
                  self.tx_profile_var.get(),
                  self.log_q, self.progress_q, self.stop_event),
            daemon=True)
        self.worker.start()


if __name__ == "__main__":
    app = App()
    app.mainloop()