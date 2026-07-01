<div align="center">

<img src="icon.png" alt="PolyWav Merger" width="128" height="128" />

# PolyWav Merger

**Automatic merging of wireless TX backup recordings with main recorder takes
into polywav files — with clock-drift correction and full BWF/iXML metadata
preservation.**

![Version](https://img.shields.io/badge/version-4.0.1--beta-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)

[English](#english) · [Русский](#русский)

</div>

---

## English

### What it does

PolyWav Merger streamlines the workflow between wireless recording systems
and post-production. It saves hours of work — both on set and after.

Modern wireless systems already record very high-quality audio directly on
the transmitter: 32-bit recording, built-in timecode, mature ecosystems.
But we're still bound by the limits of the RF chain — dynamic range of the
codec, transmission range, compression, and the inherent unpredictability
of RF transmission.

The cleanest, most stable audio is often already sitting on the transmitter
itself. PolyWav Merger makes it practical to actually use it.

### How it works

1. Reads poly files from the recorder and parses BWF/iXML metadata
   (works with any recorder — Sound Devices, Zoom, Zaxcom, Tentacle,
   Cantar, etc.)
2. Analyzes backup files from the transmitters and finds matches by
   timecode intersection (`time_ref` from the bext chunk)
3. Cuts the matching segment out of the long TX file, equal in length
   to the recorder take
4. Corrects clock drift between recorder and TX using FFT cross-correlation
   (GPU-accelerated via CUDA/ROCm if available, CPU fallback otherwise).
   Lag search of ±1.5 seconds, with a boom fallback if the primary channel
   doesn't align
5. Normalizes the TX segment to −1 dBFS if it exceeds the threshold,
   to avoid digital clipping during conversion
6. Converts from 32-bit to 24-bit
7. Builds the polywav: recorder tracks keep their original order, TX
   tracks are sorted (boom always on top, then by channel index inferred
   from the filename)
8. All metadata from the original recorder file is automatically carried
   over into the final polywav

### Extra workflow features

**Smart per-scene TX filtering.** If a take didn't involve every cast
member, the program automatically skips the TX files whose channels aren't
in that take's tracklist. Transmitters running on autonomous channels —
plant mics, ambience setups, anything that should travel across all
takes — can be flagged as "always include" and they'll end up in every
polywav regardless of the tracklist.

**Recorder-tracks-off mode.** When generating the polywav, you can
disable the inclusion of recorder tracks in the final file and keep only
the TX tracks — effectively replacing recorder tracks with TX tracks.
In that mode the recorder becomes the monitoring hub, the place where
the overall session is logged, and the source of metadata, while the
transmitters become the primary audio source — insulated from all
the limitations of RF transmission.

### Speed

100 recorder files convert in roughly 5 minutes on an SSD.
For offloading from the transmitters, a high-bandwidth USB hub is
recommended. The entire process — from offload to finished conversion —
typically takes 10–15 minutes.

### Installation

**Windows** — Download the installer from the
[Releases page](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases),
or grab the standalone `.exe`.

**macOS** — Download the universal `.dmg` (Apple Silicon or Intel) from
the [Releases page](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases).
On first launch: right-click the app → Open → confirm
(this works around Gatekeeper since the app is not notarized yet).

### Build from source

```bash
git clone https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo.git
cd PolyWav-Merger-by-Atmo
pip install -r requirements.txt
python polywav_merger.py
```

A static FFmpeg binary is required at runtime — place `ffmpeg.exe`
(Windows) or `ffmpeg` (macOS/Linux) next to `polywav_merger.py`,
or inside a `ffmpeg_bin/` subfolder.

### Feedback & support

This is an early beta. Bug reports, feature suggestions, and workflow
notes from working location sound mixers are exactly what the project
needs. Open an [issue](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/issues)
or reach out directly.

The program is and always will be free. If it has helped you out,
supporting development goes a long way:

- [Patreon](https://patreon.com/atmo_sound)
- [Boosty](https://boosty.to/atmo.prod)

---

## Русский

### Что делает программа

PolyWav Merger упрощает интеграцию аудиоисходников с радиосистем
в постпродакшен. Программа экономит часы работы на съёмочной площадке
и после неё.

Современные радиосистемы уже умеют очень качественно писать звук прямо
на передатчик: 32-bit запись, встроенный таймкод, удобная экосистема
и эргономика. Но при этом мы по-прежнему зависим от ограничений
радиотракта — ширины динамического диапазона, дальности действия,
кодека и нестабильности RF-среды.

Самый чистый и стабильный звук часто уже лежит на самом передатчике.
PolyWav Merger делает работу с этими записями удобной.

### Как это работает

1. Читает poly-файлы с рекордера и парсит BWF/iXML метаданные
   (поддерживается любой рекордер — SD, Zoom, Zaxcom, Tentacle,
   Cantar и т.д.)
2. Анализирует backup-файлы с передатчиков и ищет совпадения
   по пересечению таймкода (`time_ref` из bext-чанка)
3. Вырезает из длинного TX-файла участок, равный длине дубля на рекордере
4. Корректирует clock drift между рекордером и TX через FFT
   кросс-корреляцию (GPU-ускорение через CUDA/ROCm если есть,
   fallback на CPU). Поиск лага ±1.5 секунды, есть boom fallback,
   если primary канал не сошёлся
5. Нормализует TX до −1 dBFS, если есть превышение порога,
   чтобы избежать цифрового клиппинга
6. Конвертирует из 32 в 24 бит
7. Собирает polywav: дорожки рекордера сохраняют исходный порядок,
   дорожки передатчиков сортируются (бум всегда сверху, дальше
   по индексу канала из имени файла)
8. Все метаданные оригинального файла рекордера автоматически
   переносятся в готовый polywav

### Дополнительные функции

**Умная фильтрация передатчиков по составу сцены.** Если в дубле
участвовали не все актёры, программа автоматически не включит в
polywav файлы тех TX, чьих каналов нет в треклисте этого дубля.
Передатчики, которые работают на автономных каналах (plant-микрофоны,
системы записи окружения), можно отдельно отметить как «всегда
включать» — они будут попадать во все дубли независимо от треклиста.

**Режим без дорожек рекордера.** При генерации polywav можно отключить
включение дорожек рекордера в конечный файл, оставив только дорожки
с передатчиков — как будто заменяя дорожки рекордера на дорожки из TX.
В этом режиме рекордер остаётся центром мониторинга, местом записи
общей сессии и источником метаданных, а сами передатчики становятся
основным источником звука — мы застрахованы от всех ограничений
радиопередачи.

### О скорости

100 файлов с рекордера конвертируются примерно за 5 минут при работе
с SSD. Для слива файлов с передатчиков рекомендуется USB-хаб с высокой
пропускной способностью. Весь процесс — от слива данных с передатчиков
до конца конвертации — обычно занимает 10–15 минут.

### Установка

**Windows** — скачайте установщик со страницы
[Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases),
или возьмите standalone `.exe`.

**macOS** — скачайте универсальный `.dmg` (Apple Silicon или Intel)
со страницы [Releases](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/releases).
При первом запуске: правый клик по приложению → Открыть → подтвердить
(обход Gatekeeper, так как приложение пока не нотаризовано).

### Сборка из исходников

```bash
git clone https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo.git
cd PolyWav-Merger-by-Atmo
pip install -r requirements.txt
python polywav_merger.py
```

Для работы требуется статический FFmpeg — положите `ffmpeg.exe`
(Windows) или `ffmpeg` (macOS/Linux) рядом с `polywav_merger.py`,
либо в подпапку `ffmpeg_bin/`.

### Обратная связь и поддержка

Сейчас это ранняя beta-версия. Баг-репорты, идеи новых функций и
заметки от практикующих звукорежиссёров — именно то, что нужно проекту.
Создавайте [issue](https://github.com/RostislavAtmo/PolyWav-Merger-by-Atmo/issues)
или пишите напрямую.

Программа полностью бесплатная и всегда такой останется. Если она вам
помогла — ваша поддержка очень поможет в развитии:

- [Patreon](https://patreon.com/atmo_sound)
- [Boosty](https://boosty.to/atmo.prod)

---

<div align="center">

**PolyWav Merger** © Atmo — Released under the MIT License

</div>
