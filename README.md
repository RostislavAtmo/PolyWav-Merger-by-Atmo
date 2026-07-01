<div align="center">

<img src="icon.png" alt="PolyWav Merger" width="128" height="128" />

# PolyWav Merger

**Merge recorder takes with wireless TX backups into clean polywav files — with clock-drift correction, BWF/iXML metadata preservation, and a built-in library browser.**

![Version](https://img.shields.io/badge/version-4.0.1--beta-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)

[English](#english) · [Русский](#русский)

</div>

---

## English

### Overview

PolyWav Merger is a desktop app for location sound workflows. It matches recorder polywav takes with long TX backup files by timecode, corrects clock drift, and outputs ready-to-edit polywav files with metadata intact.

The app has two main areas:

- **Merge** — batch conversion from recorder + TX folders to polywav
- **Library** — browse a folder of WAV files, inspect BWF/iXML metadata, play multichannel waveforms, edit notes, and trim clips

### Core merge workflow

1. Read poly files from the recorder and parse BWF/iXML metadata (Sound Devices, Zoom, Zaxcom, Tentacle, Cantar, and others)
2. Match TX backup files by timecode intersection (`time_ref` from the bext chunk)
3. Cut the matching TX segment to the recorder take length
4. Correct clock drift with FFT cross-correlation (CUDA/ROCm when available, CPU fallback). Search window ±1.5 s, with boom fallback
5. Normalize TX to −1 dBFS when needed to avoid clipping
6. Convert 32-bit TX audio to 24-bit
7. Build the final polywav: recorder tracks keep their order, TX tracks are sorted (boom first, then by channel index from filename)
8. Carry over metadata from the original recorder file

### Library & playback

- File table with scene, take, timecode, length, and sample rate
- Metadata panels: General Info, Recording Info, Track Info, Notes
- Multichannel waveform viewer with solo/mute, pan, volume, zoom, trim, and note saving
- Dark/light themes with selectable accent colors (including neutral Mono)

### Extra merge options

- **Per-scene TX filtering** — skip TX channels not present in a take's tracklist; mark channels as "always include" for plant/ambience mics
- **Recorder-tracks-off mode** — output TX tracks only, using the recorder file as the metadata source

### Performance

About 100 recorder files in ~5 minutes on an SSD. Full offload-to-conversion workflow is typically 10–15 minutes with a fast USB hub for TX downloads.

### Download (Beta 4.0.1)

**Windows**

| File | Description |
|---|---|
| `PolyWav_Merger_Setup_4.0.1-beta.exe` | Installer (recommended) |
| `polywav_merger.exe` | Portable single-file build |

Download from [Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases/tag/v4.0.1-beta).

The Windows build bundles **ffmpeg**, **sounddevice** (PortAudio), **soundfile**, and all Python/Qt dependencies. No separate FFmpeg install is required.

**macOS**

Download the `.dmg` for Apple Silicon from [Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases).

On first launch: right-click the app → **Open** → confirm (Gatekeeper workaround; the app is not notarized yet).

### Build from source

```bash
git clone https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo.git
cd PolyWav-Merger-by-Atmo
pip install -r requirements.txt
python polywav_merger.py
```

For local development, place a static FFmpeg binary next to `polywav_merger.py` or in `ffmpeg_bin/`:

- Windows: `ffmpeg.exe`
- macOS/Linux: `ffmpeg`

Release builds include FFmpeg automatically.

### System requirements

- **Windows:** 10/11 x64
- **macOS:** 11.0+, Apple Silicon (arm64)
- SSD recommended for large batches

### Feedback

This is a beta. Bug reports and workflow feedback from working mixers are welcome:

- [Issues](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/issues)

The app is free. If it helps your workflow:

- [Patreon](https://patreon.com/atmo_sound)
- [Boosty](https://boosty.to/atmo.prod)

---

## Русский

### Обзор

PolyWav Merger — десктопное приложение для location sound. Оно сопоставляет polywav-дубли с рекордера с длинными TX backup-файлами по таймкоду, корректирует clock drift и выдаёт готовые polywav с сохранёнными метаданными.

В приложении два основных раздела:

- **Merge** — пакетная конвертация из папок рекордера и TX в polywav
- **Library** — просмотр папки с WAV, метаданные BWF/iXML, многоканальное воспроизведение, заметки и trim

### Основной merge-процесс

1. Читает poly-файлы с рекордера и парсит BWF/iXML (SD, Zoom, Zaxcom, Tentacle, Cantar и др.)
2. Находит совпадения с TX backup по пересечению таймкода (`time_ref` из bext)
3. Вырезает из TX участок длиной в дубль рекордера
4. Корректирует clock drift через FFT кросс-корреляцию (CUDA/ROCm при наличии, иначе CPU). Окно поиска ±1.5 с, есть boom fallback
5. Нормализует TX до −1 dBFS при превышении порога
6. Конвертирует 32-bit TX в 24-bit
7. Собирает polywav: дорожки рекордера в исходном порядке, TX сортируются (бум сверху, далее по индексу канала из имени файла)
8. Переносит метаданные из файла рекордера

### Library и воспроизведение

- Таблица файлов: scene, take, timecode, длина, sample rate
- Панели метаданных: General Info, Recording Info, Track Info, Notes
- Многоканальный waveform viewer: solo/mute, pan, volume, zoom, trim, сохранение заметок
- Тёмная/светлая тема с выбором акцентного цвета (включая нейтральный Mono)

### Дополнительные опции merge

- **Фильтрация TX по сцене** — пропуск TX-каналов, которых нет в треклисте дубля; режим «всегда включать» для plant/ambience
- **Режим без дорожек рекордера** — в итоговом файле только TX, метаданные берутся с рекордера

### Скорость

Около 100 файлов с рекордера за ~5 минут на SSD. Полный цикл от слива TX до готовых polywav обычно 10–15 минут при быстром USB-хабе.

### Скачать (Beta 4.0.1)

**Windows**

| Файл | Описание |
|---|---|
| `PolyWav_Merger_Setup_4.0.1-beta.exe` | Установщик (рекомендуется) |
| `polywav_merger.exe` | Portable single-file сборка |

Скачать: [Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases/tag/v4.0.1-beta).

Windows-сборка включает **ffmpeg**, **sounddevice** (PortAudio), **soundfile** и все зависимости Python/Qt. Отдельно ставить FFmpeg не нужно.

**macOS**

Скачайте `.dmg` для Apple Silicon на странице [Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases).

При первом запуске: правый клик по приложению → **Открыть** → подтвердить (обход Gatekeeper; приложение пока не нотаризовано).

### Сборка из исходников

```bash
git clone https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo.git
cd PolyWav-Merger-by-Atmo
pip install -r requirements.txt
python polywav_merger.py
```

Для локальной разработки положите статический FFmpeg рядом с `polywav_merger.py` или в `ffmpeg_bin/`:

- Windows: `ffmpeg.exe`
- macOS/Linux: `ffmpeg`

В релизных сборках FFmpeg уже включён.

### Системные требования

- **Windows:** 10/11 x64
- **macOS:** 11.0+, Apple Silicon (arm64)
- Для больших пакетов рекомендуется SSD

### Обратная связь

Сейчас это beta. Баг-репорты и замечания от практикующих звукорежиссёров приветствуются:

- [Issues](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/issues)

Программа бесплатная. Если она помогла в работе:

- [Patreon](https://patreon.com/atmo_sound)
- [Boosty](https://boosty.to/atmo.prod)

---

<div align="center">

**PolyWav Merger** © Atmo — MIT License

</div>
