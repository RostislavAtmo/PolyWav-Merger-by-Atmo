# Clock Drift Offset Correction Guide

## What is Clock Drift Correction?

When recording with wireless transmitters (TX) and a digital recorder, even if they're synchronized by timecode (TC), they can drift apart over time due to different clock frequencies. This tool uses waveform analysis to detect and correct this drift **after** TC matching.

## How It Works

### Three-Stage Process

#### 1️⃣ Intelligent Window Selection
The tool scans the **first 25 seconds** of each recorder file to find the best section for analysis:

- Downsamples to 2000 Hz (fast analysis)
- Applies 500 Hz lowpass filter (smooth, removes high-frequency noise)
- Tests chunks: 0-5s, 5-10s, 10-15s, 15-25s
- Scores each by: **Energy (RMS) 65%** + **Transients 35%**
- Picks **first "good" chunk** with sufficient activity

**Why not the very beginning?**
- Beginning often has pre-roll silence or room tone
- Middle sections typically have speaker activity/transients
- Algorithm finds where actual content starts

#### 2️⃣ Cross-Correlation Alignment
- Extracts reference channel from recorder
- Extracts matching TX track (with 0.5s padding on sides)
- Compares waveforms to find best time alignment
- Returns offset correction in milliseconds

#### 3️⃣ Adaptive Extraction
- TX files extracted with **0.5 seconds extra on each edge**
- Ensures context around matched transients
- Applied at original sample rate (no filtering in output)

## Using the Feature

### Setup (First Time)

1. **Enable Clock Drift Correction**
   - Toggle is ON by default
   - Found in Settings section

2. **Select Input Folders**
   - Recorder folder (with BWF/iXML metadata)
   - TX recordings folder
   - Output folder for PolyWAV files

3. **Select Recorder Model**
   - Used for metadata interpretation
   - Examples: Zoom F8n, Sound Devices 833, Tentacle Track E

4. **Configure TX Profile**
   - "Auto (detect by filename)" — recommended
   - Or specific: Deity DBTX, Wisycom, Zaxcom, Lectrosonics

### Running Processing

**Before processing starts, you'll see:**

**Channel Mapping Dialog**
```
┌─ Clock Drift Correction Mapping ────────────────────────┐
│                                                          │
│ Match TX files to recorder reference channels            │
│                                                          │
│ TX file          │ Detected name │ Recorder reference  │
├──────────────────┼───────────────┼─────────────────────┤
│ TX_DBTX_LAV1.wav │ DBTX_LAV1     │ 1: Lav (selected) │
│ TX_DXTX_BOOM.wav │ DXTX_BM       │ 2: Boom (selected)│
│ TX_WIRELESS.wav  │ TX_GENERIC    │ No correction      │
│                                                          │
│ [Cancel]  [Continue]                                   │
└─────────────────────────────────────────────────────────┘
```

### Understanding the Mapping

- **TX file**: Your transmitter file name
- **Detected name**: Auto-detected track identifier
- **Recorder reference**: Which recorder channel has this person
  - "No correction" = TX processed without offset correction
  - "1: Lav" = Use Lav channel as reference for offset
  - "5: Boom" = Use Boom channel as reference for offset

### Auto-Detection Examples

The system intelligently guesses:

```
TX_Alex_001.wav       → [1: Alex]        (name matching)
TX_LAV2_DBTX.wav      → [3: Lav2]        (LAV2 keyword + digit)
BOOM_001.wav          → [2: Boom]        (boom detection)
TX_Wireless_03.wav    → [4: Wireless]    (full filename)
GENERIC_FILE.wav      → [No suggestion]  (manual selection needed)
```

### Manual Adjustment

If auto-detection gets it wrong:

1. Click on any row in the **Recorder reference** column
2. Select the correct channel OR "No correction"
3. Proceed with processing

**When to use "No correction":**
- TX file has very poor/noisy audio
- TX file has different content than any recorder channel
- TX file is not miked by any recorder

## Processing Output

### What You Get

Each recorder file creates a **PolyWAV** with:

**Channels:**
1. Recorder track 1 (if not TX-only mode)
2. Recorder track 2 (if not TX-only mode)
3. TX file 1 (corrected for clock drift)
4. TX file 2 (corrected for clock drift)
5. ... and so on

**Metadata:**
- Scene, take, project info from recorder
- Track names for each channel
- Timecode from recorder
- All iXML metadata preserved

### File Names

```
Input recorder:  Rec_001_SCENE_T1.wav
TX files:        TX_LAV1_001.wav, TX_BOOM_001.wav
                 
Output:          Rec_001_SCENE_T1_POLY.wav
                 (contains all channels, pre-corrected)
```

## Troubleshooting

### Alignment shows "no reliable match"

**What it means:** Correlation score < 0.25 (too uncertain)

**Solutions:**
1. The recorder reference channel might be very different recording
2. Set this TX to "No correction" in the dialog
3. Try a different reference channel if available

### All channels drift together

**What it means:** Systematic drift affecting all TX files

**Solutions:**
1. This is likely a true timecode misalignment (not clock drift)
2. Verify timecode in recorder settings
3. Check transmitter sync status

### Extraction includes too much/too little padding

**Adjust in code:** Look for `padding = 0.5` variable
- Increase to 1.0 for more context
- Decrease to 0.25 for tighter sync
- Range: 0.1 to 2.0 seconds recommended

## Technical Details

### Why This Approach?

| Aspect | Traditional TC | Clock Drift Correction |
|--------|---|---|
| Source | TC metadata | Waveform analysis |
| Accuracy | ±1 frame (~42ms @ 24fps) | ±5-20ms |
| Robustness | Depends on TC sync | Independent of TC |
| Multiple TXs | One offset per session | Individual per TX |

### Parameters You Can Adjust

**In the code (`polywav_merger.py`):**

```python
# Analysis window scoring
choose_alignment_window():
    candidates = [(0.0, 5.0), (5.0, 5.0), (10.0, 5.0), (15.0, 10.0)]
    # Modify scan windows here
    
    threshold = max(best[0] * 0.55, 0.0008)
    # 0.55 = require 55% of best score
    # 0.0008 = minimum absolute threshold

# Transient scoring weight
score = rms * 0.65 + trans * 0.35
# 0.65 = energy weight
# 0.35 = transient weight

# Correlation minimum
if corr < 0.25:  # Increase for stricter validation
    return None

# Extraction padding
padding = 0.5  # Seconds on each side
```

## FAQ

**Q: Do I need this if my recorder and TX have perfect TC sync?**
A: Not necessarily. Use it if you hear drift issues during playback or long-form recordings (30+ min).

**Q: Can I use this with non-TC files?**
A: Clock drift correction requires the first recording match via TC. It won't work with free-running TC or non-sync recordings.

**Q: What if TX and recorder have different sample rates?**
A: No problem! The system automatically resamples to match the recorder's SR in the output.

**Q: Can I process multiple takes at once?**
A: Yes! Select all files in the folders and process. Each recorder file gets individual analysis.

**Q: How long does alignment detection take?**
A: ~1-2 seconds per TX file (analyzing first 25 seconds, cross-correlation computation).

**Q: Can I see the alignment details?**
A: Yes! Check the log window during processing:
```
[HH:MM:SS] ✓ ALIGN TX_LAV1.wav: ref CH1, offset +45.3 ms, corr 0.87, window 5-10s
           ↑ positive = TX starts LATER
```

## Expert Tips

### For Best Results

1. **Ensure clean recordings**
   - Quiet pre-roll before speaker
   - Clear transients (speech, taps, snaps)
   - Avoid only ambience/room tone recordings

2. **Choose informative reference channels**
   - LAV channels over ambient
   - Boom channel over room mic
   - Any channel with speaker activity

3. **Monitor the log output**
   - Look for consistency across files
   - If some files fail, check that TX file quality
   - Correction values typically ±100ms

4. **Verify Results**
   - Layer recorder and TX in DAW
   - Check sync at multiple points (0s, 30s, 60s)
   - Look for any pitch variations (indicates sample rate drift, not clock drift)

### Advanced Customization

**To use different window sizes:**
```python
# In choose_alignment_window() function:
candidates = [
    (0.0, 10.0),   # Longer first window
    (10.0, 10.0),
    (20.0, 10.0),
]
```

**To require stricter correlation:**
```python
if corr < 0.35:  # Changed from 0.25
    return None
```

**To extend padding:**
```python
padding = 1.0  # Changed from 0.5
```

## Support

If alignment isn't working:

1. **Check the log** for specific error messages
2. **Try without clock correction** to isolate the issue
3. **Verify TX audio quality** is similar to recorder reference
4. **Test with shorter files** first (faster debugging)

---

**Version:** v8.0 with Clock Drift Correction
**Last Updated:** May 2026
