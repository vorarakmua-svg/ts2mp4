# TS2MP4 Professional Video Converter - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)
10. [Performance Tuning](#performance-tuning)
11. [FAQ](#faq)

---

## Introduction

TS2MP4 is a professional-grade video converter designed to batch convert `.ts` (MPEG Transport Stream) files to `.mp4` format with GPU acceleration, validation, metrics collection, and comprehensive monitoring.

### Key Highlights

✨ GPU-accelerated encoding (NVIDIA NVENC)
⚡ Concurrent processing for faster conversions
📊 Detailed metrics and performance profiling
🏥 System health monitoring
🎯 Validation and quality assurance
🔧 Interactive configuration wizard
📈 Professional visual display with live statistics

---

## Features

### Core Features

- **GPU Acceleration**: Automatic NVIDIA NVENC detection with CPU fallback
- **Concurrent Processing**: Convert multiple files simultaneously
- **Validation**: Automatic output verification (duration, streams, integrity)
- **Progress Tracking**: Real-time progress with detailed statistics
- **Resource Management**: Intelligent concurrency and timeout management

### Phase 4: Testing & Observability

- **Pytest Test Suite**: 70%+ code coverage with comprehensive tests
- **Metrics Collection**: JSON/CSV export of conversion statistics
- **Health Monitoring**: Real-time system resource monitoring
- **Performance Profiling**: cProfile integration for performance analysis

### Phase 5: User Experience

- **Dry-Run Mode**: Simulate conversions without processing
- **Configuration Wizard**: Interactive setup assistant
- **Enhanced Error Messages**: Helpful suggestions and troubleshooting
- **Comprehensive Documentation**: Complete user guide and examples

---

## Requirements

### System Requirements

- **OS**: Windows, Linux, or macOS
- **Python**: 3.7 or higher
- **FFmpeg**: 4.0 or higher (with NVENC support for GPU acceleration)
- **FFprobe**: Usually bundled with FFmpeg

### Optional

- **NVIDIA GPU**: For hardware-accelerated encoding
- **CUDA**: For GPU support
- **GPUtil**: For GPU monitoring (auto-installed)

---

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg

#### Windows
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey:
```powershell
choco install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

### 3. Verify Installation

```bash
ffmpeg -version
ffprobe -version
python --version
```

### 4. Configure (Optional)

Run the interactive wizard:
```bash
python main.py --wizard
```

Or manually create a `.env` file (see [Configuration](#configuration))

---

## Quick Start

### Basic Usage

1. Place your `.ts` files in the input directory (default: `C:\input`)
2. Run the converter:
   ```bash
   python main.py
   ```
3. Converted `.mp4` files will be in the output directory (default: `C:\output`)

### With Custom Directories

```bash
python main.py --input-dir /path/to/input --output-dir /path/to/output
```

### Dry-Run (Test Without Converting)

```bash
python main.py --dry-run
```

---

## Configuration

### Method 1: Interactive Wizard (Recommended)

```bash
python main.py --wizard
```

The wizard will:
- Guide you through all configuration options
- Explain each setting
- Create a `.env` file with your preferences
- Optionally create required directories

### Method 2: Environment Variables

Create a `.env` file in the project root:

```env
# Directories
TS2MP4_INPUT_DIR=/path/to/input
TS2MP4_OUTPUT_DIR=/path/to/output
TS2MP4_LOG_DIR=logs

# FFmpeg
TS2MP4_FFMPEG_BIN=ffmpeg
TS2MP4_FFPROBE_BIN=ffprobe

# Encoding
TS2MP4_ENABLE_GPU=1
TS2MP4_FORCE_GPU=0
TS2MP4_NVENC_PRESET=p4
TS2MP4_CRF_VALUE=21

# Performance
TS2MP4_MAX_CONCURRENT=1
TS2MP4_SLEEP_BETWEEN=2
```

### Method 3: Command-Line Arguments

```bash
python main.py \
  --input-dir /custom/input \
  --output-dir /custom/output \
  --ffmpeg-bin /usr/local/bin/ffmpeg
```

### Configuration Priority

Command-line arguments > Environment variables > Default values

---

## Usage

### Basic Commands

#### Standard Conversion
```bash
python main.py
```

#### With Custom Settings
```bash
python main.py --input-dir ~/Videos/input --output-dir ~/Videos/output
```

#### Dry-Run Mode
```bash
python main.py --dry-run
```

#### With Profiling
```bash
python main.py --profile
```

#### Configuration Wizard
```bash
python main.py --wizard
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input-dir PATH` | Input directory | `C:\input` |
| `--output-dir PATH` | Output directory | `C:\output` |
| `--log-dir PATH` | Log directory | `logs` |
| `--ffmpeg-bin PATH` | FFmpeg executable | `ffmpeg` |
| `--ffprobe-bin PATH` | FFprobe executable | `ffprobe` |
| `--sleep-between N` | Sleep between conversions (s) | `2` |
| `--profile` | Enable performance profiling | `false` |
| `--dry-run` | Simulate without converting | `false` |
| `--wizard` | Run configuration wizard | `false` |
| `--help` | Show help message | - |

---

## Advanced Features

### 1. Concurrent Processing

Convert multiple files simultaneously:

```env
TS2MP4_MAX_CONCURRENT=4
```

**Recommendations:**
- CPU-only: 2-8 workers (depends on CPU cores)
- GPU: 1-2 workers (limited by VRAM)

### 2. Metrics Collection

Metrics are automatically exported after each batch:

- **JSON**: `logs/metrics_TIMESTAMP.json`
- **CSV**: `logs/metrics_TIMESTAMP.csv`

Contains:
- Success/failure rates
- Processing times
- Realtime factors
- File sizes
- Encoder information

### 3. Health Monitoring

Continuous health checks monitor:
- CPU usage
- Memory usage
- Disk space
- GPU utilization (if available)
- Process resources

Health reports: `logs/health_report_TIMESTAMP.json`

### 4. Performance Profiling

Enable profiling to analyze performance:

```bash
python main.py --profile
```

Generates:
- Text report: `logs/profile_TIMESTAMP.txt`
- Binary profile: `logs/profile_TIMESTAMP.prof`

Visualize with:
```bash
python -m snakeviz logs/profile_TIMESTAMP.prof
```

### 5. GPU Acceleration

#### Enable GPU
```env
TS2MP4_ENABLE_GPU=1
```

#### Force GPU (Fail if Unavailable)
```env
TS2MP4_FORCE_GPU=1
```

#### GPU Presets

| Preset | Speed | Quality | Use Case |
|--------|-------|---------|----------|
| `p1` | Fastest | Lower | Quick previews |
| `p2-p3` | Fast | Good | Real-time encoding |
| `p4` | Balanced | High | **Recommended** |
| `p5-p6` | Slow | Higher | Quality priority |
| `p7` | Slowest | Best | Archival |

---

## Troubleshooting

### Common Issues

#### 1. "FFmpeg not found"

**Solution:**
```bash
# Verify installation
ffmpeg -version

# Add to PATH or specify location
python main.py --ffmpeg-bin /path/to/ffmpeg
```

#### 2. "No .ts files found"

**Solution:**
- Check input directory path
- Verify files have `.ts` extension
- Check permissions
- Use `--dry-run` to test

#### 3. "GPU acceleration failed"

**Solution:**
- Update NVIDIA drivers
- Verify NVENC support: `ffmpeg -encoders | grep nvenc`
- Use CPU encoding: `TS2MP4_ENABLE_GPU=0`

#### 4. "Validation failed"

**Solution:**
- Check disk space
- Verify input file integrity
- Try CPU encoding
- Check FFmpeg/FFprobe versions

#### 5. "Insufficient disk space"

**Solution:**
- Free up space (need ~1.5x input size)
- Use different output directory
- Process smaller batches

### Getting Help

1. Check logs: `logs/conversion_TIMESTAMP.log`
2. Run with `--dry-run` to test configuration
3. Review health report: `logs/health_report_TIMESTAMP.json`
4. See error suggestions (auto-displayed)
5. Check GitHub Issues

---

## Performance Tuning

### CPU Encoding

**4-core CPU:**
```env
TS2MP4_MAX_CONCURRENT=3
```

**8-core CPU:**
```env
TS2MP4_MAX_CONCURRENT=6
```

### GPU Encoding

**Single GPU:**
```env
TS2MP4_MAX_CONCURRENT=1  # or 2 max
TS2MP4_NVENC_PRESET=p4
```

### Quality vs. Speed

**High Quality (Slower):**
```env
TS2MP4_CRF_VALUE=18
TS2MP4_NVENC_PRESET=p6
```

**Balanced (Recommended):**
```env
TS2MP4_CRF_VALUE=21
TS2MP4_NVENC_PRESET=p4
```

**Fast (Lower Quality):**
```env
TS2MP4_CRF_VALUE=28
TS2MP4_NVENC_PRESET=p2
```

### Benchmarking

Use profiling to identify bottlenecks:

```bash
python main.py --profile
```

Review:
- `logs/profile_TIMESTAMP.txt`
- `logs/metrics_TIMESTAMP.json`

---

## FAQ

### Q: What file formats are supported?

**A:** Input: `.ts` (MPEG Transport Stream). Output: `.mp4` (H.264 + AAC).

### Q: Does it delete original files?

**A:** Yes, after successful conversion and validation. Use `--dry-run` to test first.

### Q: Can I cancel mid-conversion?

**A:** Yes, press `Ctrl+C`. The current file will finish, then exit gracefully.

### Q: How do I preserve original files?

**A:** Currently, originals are deleted after successful conversion. This may be configurable in future versions.

### Q: What's the difference between CPU and GPU encoding?

**A:**
- GPU (NVENC): Faster, lower CPU usage, requires NVIDIA GPU
- CPU (libx264): Slower, uses more CPU, universally compatible

### Q: Can I use AMD or Intel GPUs?

**A:** Not currently. Only NVIDIA GPUs with NVENC are supported.

### Q: How much disk space do I need?

**A:** Approximately 1.5-2x the input file size for safety margin.

### Q: What's the recommended CRF value?

**A:**
- 18-20: Very high quality (large files)
- **21-23: Recommended** (good balance)
- 24-28: Medium quality (smaller files)

### Q: How do I run tests?

**A:**
```bash
# Install pytest
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Q: Where are metrics and logs stored?

**A:** In the `logs/` directory (configurable with `--log-dir`).

### Q: Can I batch multiple conversions?

**A:** Yes! All `.ts` files in the input directory are processed automatically.

---

## Examples

### Example 1: Basic Conversion

```bash
# Place files in C:\input
python main.py
# Output in C:\output
```

### Example 2: Custom Directories

```bash
python main.py \
  --input-dir ~/Downloads/videos \
  --output-dir ~/Videos/converted
```

### Example 3: High-Quality GPU Encoding

```bash
# Set environment
export TS2MP4_ENABLE_GPU=1
export TS2MP4_CRF_VALUE=18
export TS2MP4_NVENC_PRESET=p6

# Run
python main.py
```

### Example 4: Fast Concurrent CPU Encoding

```bash
export TS2MP4_MAX_CONCURRENT=6
export TS2MP4_CRF_VALUE=23
python main.py
```

### Example 5: Profiling and Analysis

```bash
# Enable profiling
python main.py --profile

# View results
cat logs/profile_TIMESTAMP.txt
python -m snakeviz logs/profile_TIMESTAMP.prof
```

---

## Support

- **Documentation**: This file
- **Issues**: [GitHub Issues](https://github.com/yourrepo/ts2mp4/issues)
- **Configuration Help**: Run `python main.py --wizard`
- **Testing**: Run `python main.py --dry-run`

---

## License

[Your License Here]

---

## Version

Current Version: **2.0.0** (Phase 4 & 5 Complete)

Last Updated: 2025-12-17
