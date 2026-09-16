# TS2MP4

Batch-converts `.ts` (MPEG transport stream) files to `.mp4` using FFmpeg.

When the video is already H.264 or HEVC (true of nearly all broadcast and streaming recordings), the streams are copied into the MP4 container without re-encoding. This is lossless and typically hundreds of times faster than realtime. Audio that MP4 can't hold as-is (e.g. MP2, AC-3) is converted to AAC, and subtitle/data streams are dropped. Other video codecs such as MPEG-2 are re-encoded to H.264, using NVIDIA NVENC when available with automatic CPU fallback. If a stream copy fails or its output doesn't validate, the file is re-encoded instead.

Each output is validated (it must exist, contain a video stream, and match the source duration within 1%) before the original `.ts` file is deleted (use `--keep-originals` to keep it). Files whose `.mp4` already exists in the output directory are skipped unless you pass `--overwrite`.

## Requirements

- Python 3.8+
- FFmpeg and FFprobe on your `PATH` (or pass their locations with `--ffmpeg-bin` / `--ffprobe-bin`)
- Optional: an NVIDIA GPU and an FFmpeg build with `h264_nvenc`

```bash
pip install -r requirements.txt
```

## Usage

Put `.ts` files in the input directory (default `C:\input`) and run:

```bash
python main.py
```

On Windows you can also double-click `run.bat`. Converted files are written to the output directory (default `C:\output`). Press `Ctrl+C` to stop; the file in progress is cancelled and its partial output removed.

### Command-line options

| Option | Description |
| --- | --- |
| `--input-dir PATH` | Directory containing input `.ts` files |
| `--output-dir PATH` | Directory where `.mp4` files are written |
| `--log-dir PATH` | Directory for logs, metrics, and health reports |
| `--ffmpeg-bin PATH` | Path to the `ffmpeg` executable |
| `--ffprobe-bin PATH` | Path to the `ffprobe` executable |
| `--mode auto\|remux\|encode` | `auto` (default) copies streams when possible and re-encodes otherwise; `remux` never re-encodes; `encode` always re-encodes |
| `--keep-originals` | Keep the `.ts` file after a successful conversion |
| `--overwrite` | Re-convert files whose output already exists |
| `--dry-run` | List what would be converted without changing anything |
| `--profile` | Write a cProfile performance report to the log directory |
| `--wizard` | Interactive configuration helper |

### Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `TS2MP4_INPUT_DIR` | `C:\input` | Input directory |
| `TS2MP4_OUTPUT_DIR` | `C:\output` | Output directory |
| `TS2MP4_LOG_DIR` | `logs` | Log directory |
| `TS2MP4_FFMPEG_BIN` | `ffmpeg` | FFmpeg executable |
| `TS2MP4_FFPROBE_BIN` | `ffprobe` | FFprobe executable |
| `TS2MP4_MODE` | `auto` | Conversion mode, see `--mode` |
| `TS2MP4_ENABLE_GPU` | `1` | Set to `0` to always encode on the CPU |
| `TS2MP4_FORCE_GPU` | `0` | Set to `1` to skip NVENC detection and use the GPU |
| `TS2MP4_GPU_MAX_ATTEMPTS` | `1` | GPU attempts before falling back to CPU |
| `TS2MP4_NVENC_PRESET` | `p4` | NVENC preset, `p1` (fastest) to `p7` (best quality) |
| `TS2MP4_CRF_VALUE` | `21` | Re-encode quality target (lower is better quality, larger files) |
| `TS2MP4_DELETE_ORIGINALS` | `1` | Set to `0` to keep original `.ts` files |
| `TS2MP4_OVERWRITE` | `0` | Set to `1` to overwrite existing outputs |
| `TS2MP4_MAX_CONCURRENT` | `1` | Number of files converted in parallel (capped at 2 on GPU) |

These can also be placed in a `.env` file in the directory you run the program from (`python main.py --wizard` creates one).

Precedence: command-line options > environment variables > `.env` file > defaults.

## Output

The `logs/` directory receives, per run:

- `conversion_*.log` — full run log
- `metrics_*.json` / `metrics_*.csv` — per-file conversion statistics
- `health_report_*.json` — CPU, memory, disk, and GPU snapshots

## Development

```bash
python -m pytest
```
