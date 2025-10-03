#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_mp3_loudness.py (no-logging, analysis-only)
- Recursively scans an input folder for *.mp3
- Extracts:
    duration_s, bitrate_bps, sample_rate_hz, channels
    mean_volume_dB, max_volume_dB            (ffmpeg volumedetect)
    loudnorm_I_LUFS, loudnorm_TP_dBTP,
    loudnorm_LRA_LU, loudnorm_thresh_dB,
    loudnorm_target_offset_dB                (ffmpeg loudnorm print_format=json)
- Writes a CSV report.
- If the output CSV already exists, a sequential suffix (-001, -002, ...) is added.
- No logging. Minimal console printing only.
- UnicodeDecodeError-safe subprocess handling.
Requirements:
  ffmpeg (in PATH)
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------- Small helpers ----------

def run_cmd(cmd: List[str], timeout: int = 600) -> Tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout_str, stderr_str).
       Decode with errors='ignore' to avoid UnicodeDecodeError."""
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        out = p.stdout.decode("utf-8", errors="ignore")
        err = p.stderr.decode("utf-8", errors="ignore")
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout"
    except Exception as e:
        return 1, "", f"Exception: {e!r}"

def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    parent = path.parent
    i = 1
    while True:
        cand = parent / f"{stem}-{i:03d}{suffix}"
        if not cand.exists():
            return cand
        i += 1

def check_ffmpeg() -> bool:
    rc, out, err = run_cmd(["ffmpeg", "-version"])
    return rc == 0

# ---------- Parsers ----------

VOL_MEAN_RE = re.compile(r"mean_volume:\s*([-+]?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)
VOL_MAX_RE  = re.compile(r"max_volume:\s*([-+]?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)

# loudnorm JSON appears on stderr; extract the JSON object
JSON_BLOCK_RE = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)

# For basic info (duration/bitrate/samplerate/channels) from ffmpeg banner
DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", re.IGNORECASE)
BR_RE  = re.compile(r"bitrate:\s*(\d+)\s*kb/s", re.IGNORECASE)
SR_CH_RE = re.compile(r"Audio:.*?,\s*(\d+)\s*Hz,\s*(stereo|mono|[0-9]+(?:\.[0-9]+)?\s*channels?)", re.IGNORECASE)
CH_MAP = {"mono": 1, "stereo": 2}

def parse_loudnorm_json(stderr_text: str) -> Optional[Dict[str, float]]:
    m = JSON_BLOCK_RE.search(stderr_text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return {
            "loudnorm_I_LUFS": float(data.get("input_i")),
            "loudnorm_TP_dBTP": float(data.get("input_tp")),
            "loudnorm_LRA_LU": float(data.get("input_lra")),
            "loudnorm_thresh_dB": float(data.get("input_thresh")),
            "loudnorm_target_offset_dB": float(data.get("target_offset")),
        }
    except Exception:
        return None

# ---------- Extractors ----------

def ffprobe_basic_info(path: Path, timeout: int) -> Dict[str, Optional[float]]:
    """Use ffmpeg banner to parse basic info. Missing fields remain None."""
    rc, out, err = run_cmd(["ffmpeg", "-hide_banner", "-i", str(path), "-f", "null", "-"], timeout=timeout)
    text = err or out
    info = {
        "duration_s": None,
        "bitrate_bps": None,
        "sample_rate_hz": None,
        "channels": None,
    }
    # Duration
    m = DUR_RE.search(text)
    if m:
        h, mm, ss = m.groups()
        try:
            info["duration_s"] = int(h) * 3600 + int(mm) * 60 + float(ss)
        except Exception:
            pass
    # Bitrate
    m = BR_RE.search(text)
    if m:
        try:
            kbps = int(m.group(1))
            info["bitrate_bps"] = kbps * 1000
        except Exception:
            pass
    # Sample rate & channels
    m = SR_CH_RE.search(text)
    if m:
        try:
            info["sample_rate_hz"] = int(m.group(1))
        except Exception:
            pass
        chs = m.group(2).lower().strip()
        if chs in CH_MAP:
            info["channels"] = CH_MAP[chs]
        else:
            # try "6 channels" or "5.1"
            n = None
            try:
                if "channel" in chs:
                    n = int(re.search(r"(\d+)", chs).group(1))
                elif "." in chs:
                    base = int(chs.split(".", 1)[0])
                    n = base + 1
                else:
                    n = int(chs)
            except Exception:
                n = None
            info["channels"] = n
    return info

def volumedetect(path: Path, timeout: int) -> Tuple[Optional[float], Optional[float]]:
    rc, out, err = run_cmd(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        timeout=timeout
    )
    if rc != 0:
        return None, None
    text = err or out
    mean_v = None
    max_v = None
    for line in text.splitlines():
        if mean_v is None:
            m = VOL_MEAN_RE.search(line)
            if m:
                try:
                    mean_v = float(m.group(1))
                except Exception:
                    pass
        if max_v is None:
            m = VOL_MAX_RE.search(line)
            if m:
                try:
                    max_v = float(m.group(1))
                except Exception:
                    pass
    return mean_v, max_v

def loudnorm_measure(path: Path, timeout: int) -> Optional[Dict[str, float]]:
    # Analysis-only: no CLI target/TP/LRA. Use typical defaults; print_format=json is what we need.
    rc, out, err = run_cmd(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        timeout=timeout
    )
    if rc != 0:
        return None
    return parse_loudnorm_json(err)

# ---------- Main ----------

def find_mp3s(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.mp3") if p.is_file()])

def main():
    ap = argparse.ArgumentParser(description="Analyze MP3 loudness and volume")
    ap.add_argument("-i", "--input", required=True, help="Input root folder")
    ap.add_argument("-o", "--output", default="mp3_loudness_report.csv", help="Output CSV path")
    ap.add_argument("--timeout", type=int, default=600, help="Per-command timeout seconds")
    args = ap.parse_args()

    in_root = Path(args.input).expanduser().resolve()
    out_csv = Path(args.output).expanduser().resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_csv = ensure_unique_path(out_csv)

    if not check_ffmpeg():
        print("ERROR: ffmpeg not found. Please install ffmpeg and ensure it's in PATH.", file=sys.stderr)
        sys.exit(2)

    files = find_mp3s(in_root)
    if not files:
        print(f"No MP3 files found under: {in_root}")
        return

    fieldnames = [
        "file",
        "duration_s",
        "bitrate_bps",
        "sample_rate_hz",
        "channels",
        "mean_volume_dB",
        "max_volume_dB",
        "loudnorm_I_LUFS",
        "loudnorm_TP_dBTP",
        "loudnorm_LRA_LU",
        "loudnorm_thresh_dB",
        "loudnorm_target_offset_dB",
        "error",  # optional error message per-file (kept in CSV; not a log file)
    ]

    ok = 0
    fail = 0
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        total = len(files)
        for idx, path in enumerate(files, 1):
            row = {"file": str(path),
                   "duration_s": None,
                   "bitrate_bps": None,
                   "sample_rate_hz": None,
                   "channels": None,
                   "mean_volume_dB": None,
                   "max_volume_dB": None,
                   "loudnorm_I_LUFS": None,
                   "loudnorm_TP_dBTP": None,
                   "loudnorm_LRA_LU": None,
                   "loudnorm_thresh_dB": None,
                   "loudnorm_target_offset_dB": None,
                   "error": ""}
            print(f"[{idx}/{total}] {path}")
            try:
                info = ffprobe_basic_info(path, args.timeout)
                row.update(info)

                mean_v, max_v = volumedetect(path, args.timeout)
                row["mean_volume_dB"] = mean_v
                row["max_volume_dB"] = max_v

                loud = loudnorm_measure(path, args.timeout)
                if loud:
                    row.update(loud)
                else:
                    row["error"] = "loudnorm_measure_failed"
                    fail += 1

                writer.writerow(row)
                if row["error"]:
                    # counted as fail above already
                    pass
                else:
                    ok += 1
            except Exception as e:
                row["error"] = f"exception: {e!r}"
                writer.writerow(row)
                fail += 1
                continue

    print(f"Done. Success={ok}, Fail={fail}, Total={len(files)}")
    print(f"Report: {out_csv}")

if __name__ == "__main__":
    main()

