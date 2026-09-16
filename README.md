# TS2MP4

Batch-converts `.ts` (MPEG transport stream) files to `.mp4` using FFmpeg, with NVIDIA NVENC acceleration and automatic CPU fallback.

Each output is validated (it must exist, contain a video stream, and match the source duration within 1%) before the original `.ts` file is deleted.

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
| `TS2MP4_ENABLE_GPU` | `1` | Set to `0` to always encode on the CPU |
| `TS2MP4_FORCE_GPU` | `0` | Set to `1` to skip NVENC detection and use the GPU |
| `TS2MP4_GPU_MAX_ATTEMPTS` | `1` | GPU attempts before falling back to CPU |
| `TS2MP4_NVENC_PRESET` | `p4` | NVENC preset, `p1` (fastest) to `p7` (best quality) |
| `TS2MP4_CRF_VALUE` | `21` | Quality target (lower is better quality, larger files) |
| `TS2MP4_MAX_CONCURRENT` | `1` | Number of files converted in parallel |

Command-line options take precedence over environment variables.

## Output

The `logs/` directory receives, per run:

- `conversion_*.log` — full run log
- `metrics_*.json` / `metrics_*.csv` — per-file conversion statistics
- `health_report_*.json` — CPU, memory, disk, and GPU snapshots

## Development

```bash
python -m pytest
```
