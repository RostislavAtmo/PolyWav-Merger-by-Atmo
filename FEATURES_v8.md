# PolyWav Merger v8.0 — Features Overview

## 🎙️ Core Functionality

PolyWav Merger combines wireless transmitter (TX) recordings with stationary recorder tracks into multi-channel BWF/iXML compliant audio files.

**Inputs:**
- Recorder file (Zoom, Sound Devices, Tentacle, Zaxcom, etc.)
- Multiple TX files (wireless lav mics, boom mics, etc.)

**Output:**
- Single multi-track PolyWAV file with all channels combined
- Full metadata preservation (TC, scene, take, track names)
- Automatic gain normalization option

---

## ✨ v8.0 New Features

### 🎯 Clock Drift Offset Correction (NEW)

Automatically detects and corrects audio timing drift between TX and recorder after timecode matching.

**How it works:**
1. Automatically proposes TX-to-recorder channel matching before processing
2. Analyzes first 25 seconds of recording to find optimal alignment window
3. Evaluates chunks by RMS energy and transient activity
4. Uses waveform cross-correlation to detect precise offset
5. Extracts TX with 0.5s padding for context preservation
6. Applies correction during PolyWAV rendering

**When to use:**
- Wireless TX recordings drift over time (different clock speeds)
- Long takes (30+ minutes) where TC sync degrades
- For highest professional accuracy

**Key parameters:**
- Scan window: First 25 seconds
- Analysis resolution: 2000 Hz downsampled + 500Hz lowpass
- Chunk evaluation: RMS (65%) + Transients (35%)
- Precision: ±5-20ms (vs ±42ms with TC alone)

### 📊 Smart Channel Mapping Dialog

Before processing starts with clock correction enabled:
- Shows all TX files with auto-detected names
- Proposes best-matching recorder reference channel
- User can manually adjust or set to "No correction"
- Intelligent auto-detection based on:
  - Filename matching
  - Transmitter type recognition (boom, lav, generic)
  - Channel number extraction

### 🔊 Enhanced Window Selection Algorithm

Instead of analyzing the same section every time:
- Scans 4 time windows: 0-5s, 5-10s, 10-15s, 15-25s
- Tests each for information content (energy + transients)
- Automatically selects first good chunk
- Avoids silence, room tone, or pre-roll
- Adapts to recording structure

### 📐 Intelligent Transient Detection

New scoring metric combines:
- **RMS Energy** (65% weight) — overall loudness
- **Transient Activity** (35% weight) — attack detection
- Finds sections with actual speaker content, not background

---

## 📋 Supported Transmitters & Recorders

### TX Profiles (Auto-Detection)
- ✓ Deity DBTX / DXTX (LAV prefix, BM boom)
- ✓ Wisycom MCR / MTP (WIS_ prefix)
- ✓ Zaxcom ZMT (ZAX prefix)
- ✓ Lectrosonics SMWB / DBSMD (LEC prefix)
- ✓ Generic / Custom (by filename numbers)

### Recorder Models
- Zoom F-series (F8n Pro, F6, F4, etc.)
- Sound Devices (MixPre series, 833, 888, Scorpio)
- Zaxcom Nomad/Maxx
- Tentacle Track E
- Any BWF/iXML compliant recorder

---

## 🎚️ Processing Options

### Clock Drift Offset Correction
- **ON** (default): Enable intelligent waveform alignment
- Shows channel mapping dialog before processing
- Each TX matched to recorder reference channel individually

### TX Only Mode
- Process TX files without recorder sync
- Useful for: backup files, isolated editing, wireless-only projects
- Bypasses recorder folder requirement

### Convert 32-bit to 24-bit
- **ON** (default): Normalize audio, reduce file size
- **OFF**: Preserve original bit depth

### TX Profile Selection
- Auto-detect by filename (recommended)
- Or manually select specific transmitter type
- Affects track naming in output

---

## 📊 Processing Flow

```
1. User selects folders + options
2. (if clock correction) → Channel mapping dialog
3. Scan TX files for metadata (SR, duration, TC reference)
4. For each recorder file:
   a. Read iXML metadata
   b. For each matching TX file:
      - Find best alignment window
      - Calculate offset correction
      - Extract TX (with padding if corrected)
   c. Mix all channels via ffmpeg
   d. Build PolyWAV with full metadata
   e. Output to folder
```

---

## 🔧 Technical Specifications

### Audio Analysis
- Downsample: 48000 Hz → 2000 Hz (for analysis only)
- Lowpass filter: 500 Hz (perceptually relevant frequencies)
- Window scan: First 25 seconds of file
- Chunk durations: 5-10 seconds each

### Alignment Detection
- Method: Normalized cross-correlation
- Maximum lag search: ±0.5 seconds
- Correlation threshold: 0.25 (confidence score)
- Precision: ~5-20ms typical

### Extraction & Padding
- When clock correction enabled: TX extracted with 0.5s padding each side
- When disabled: Exact TC-based extraction
- All resampling and processing at original recorder sample rate
- No lowpass filtering in final output

### Output Format
- Container: BWF (Broadcast Wave Format)
- Metadata: Full iXML preservation
- Bit depth: 24-bit PCM (configurable)
- Track layout: Recorder channels + TX channels
- Sample rate: Original recorder rate

---

## 📈 Performance

**Typical processing speed:**
- 1-minute take: ~5-10 seconds
- 10-minute take: ~30-60 seconds
- 30-minute take: ~2-4 minutes

**System requirements:**
- Python 3.10+
- ffmpeg (included in .exe build)
- 2GB RAM minimum
- Disk space: ~1.5x input size for temp + output

---

## 🐛 Troubleshooting

### Alignment shows "no reliable match"
**Cause:** Reference channel too different or noisy
**Solution:** Use "No correction" for that TX in the dialog

### Some TX files skipped
**Cause:** TX file doesn't contain timecode range of recorder
**Solution:** Verify TX file recording time overlaps

### Output quality degradation
**Cause:** Normalization gain too high
**Solution:** Check if peak levels are very low (-40dBFS+)

### Processing very slow
**Cause:** Large files or many TX channels
**Solution:** Process in smaller batches or upgrade CPU

---

## 📝 File Format Details

### Input Requirements
- **Recorder:** Must have BWF bext + iXML chunks (timecode, metadata)
- **TX files:** Standard WAV, metadata optional
- **Format:** PCM (16-bit, 24-bit, or 32-bit float)
- **Sample rates:** Any (auto-resampled to match recorder)

### Output Guarantees
- Multi-channel BWF/iXML with:
  - ✓ Timecode reference point
  - ✓ Scene, take, project metadata
  - ✓ Track names for each channel
  - ✓ Recording history notes
  - ✓ File UID and family UID
- ✓ Compatible with: Pro Tools, Nuendo, Reaper, Final Cut, Resolve, etc.

---

## 🎓 Best Practices

1. **Always keep originals** — PolyWav is for mixing, not archival
2. **Use matching sample rates** — Same SR for TX and recorder when possible
3. **Enable clock correction** — Especially for takes 10+ minutes long
4. **Monitor the log** — Watch for alignment confidence scores
5. **Verify in DAW** — Spot-check sync at multiple timecode points
6. **Use descriptive TX names** — "TX_ALEX_LAVALIER_01.wav" > "TX_001.wav"

---

## 🔄 Workflow Example

```
STEP 1: Open PolyWav Merger
├─ Select: D:\Recordings\ZoomF8n\
├─ TX folder: D:\Recordings\Wireless\
├─ Output: D:\PolyWavs\
└─ Model: "Zoom F8n Pro"

STEP 2: Settings
├─ Clock Drift Correction: ON
├─ TX Profile: Auto (detect)
├─ Normalize: ON
└─ TX Only: OFF

STEP 3: Click "Start Processing"
├─ [Dialog appears] Channel Mapping
│  ├─ TX_DBTX_LAV1.wav → 1: Lav (auto-detected)
│  ├─ TX_DXTX_BOOM.wav → 2: Boom (auto-detected)
│  └─ TX_Wireless.wav → No correction (manual)
└─ [OK] → Processing starts

STEP 4: Review output
├─ Log shows:
│  ├─ ✓ ALIGN TX_DBTX_LAV1.wav: offset +23.4ms
│  ├─ ✓ ALIGN TX_DXTX_BOOM.wav: offset -15.7ms
│  └─ ✓ Scene_Take_POLY.wav created [156 MB]
└─ Ready to edit in DAW
```

---

## 📚 Documentation

- **CLOCK_DRIFT_GUIDE.md** — Detailed feature guide
- **BUILD_GUIDE.txt** — Building from source
- **polywav_merger.py** — Full source code with comments

---

## 🎉 Summary

PolyWav Merger v8.0 with Clock Drift Correction provides:
- ✓ Automated multi-track PolyWAV creation
- ✓ Intelligent clock drift correction after TC sync
- ✓ Smart channel auto-mapping with user override
- ✓ Adaptive alignment window detection
- ✓ Full BWF/iXML metadata preservation
- ✓ Professional broadcast-ready output

Perfect for: Documentary, podcast, music, commercial production with wireless microphones!
