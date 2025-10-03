#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
convert_loudnorm_mp3.py (simplified usage)
 - 必須は -i のみ
 - 出力フォルダ指定がなければ input の 1つ上階層に output/＜同じフォルダ名＞ を作成
 - --target など省略時はデフォルト値を利用
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional, Tuple

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
logger = logging.getLogger("convert_loudnorm_mp3")
logger.setLevel(logging.INFO)

def setup_logging(log_file: Path, verbose: bool):
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter(LOG_FORMAT))

    fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.handlers.clear()
    logger.addHandler(ch)
    logger.addHandler(fh)

def run_cmd(cmd: List[str], timeout: int = 600) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        out = p.stdout.decode("utf-8", errors="ignore")
        err = p.stderr.decode("utf-8", errors="ignore")
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"
    except Exception as e:
        return 1, "", f"Exception: {e!r}"

def which_ffmpeg() -> Optional[str]:
    rc, out, err = run_cmd(["ffmpeg", "-version"])
    if rc == 0:
        first = (out or err).splitlines()[0] if (out or err) else "ffmpeg (no version info)"
        logger.info(first.strip())
        return "ffmpeg"
    else:
        logger.error("ffmpeg not found or failed to run. Please install ffmpeg and ensure it's in PATH.")
        return None

def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}-{i:03d}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

JSON_BLOCK_RE = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)

@dataclass
class LoudnormParams:
    input_i: float
    input_tp: float
    input_lra: float
    input_thresh: float
    target_offset: float

def parse_loudnorm_json(stderr_text: str) -> Optional[LoudnormParams]:
    m = JSON_BLOCK_RE.search(stderr_text)
    if not m:
        return None
    blob = m.group(0)
    try:
        data = json.loads(blob)
        return LoudnormParams(
            input_i=float(data.get("input_i")),
            input_tp=float(data.get("input_tp")),
            input_lra=float(data.get("input_lra")),
            input_thresh=float(data.get("input_thresh")),
            target_offset=float(data.get("target_offset")),
        )
    except Exception as e:
        logger.debug("JSON parse error: %r\nBlob was:\n%s", e, blob)
        return None

def first_pass_measure(in_path: Path, I: float, TP: float, LRA: float, timeout: int) -> Optional[LoudnormParams]:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i", str(in_path),
        "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
        "-f", "null", "-"
    ]
    rc, out, err = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        logger.error("First pass failed: %s\nstderr: %s", in_path, err[-1000:])
        return None
    return parse_loudnorm_json(err)

def second_pass_apply(in_path: Path, out_path: Path, p: LoudnormParams,
                      I: float, TP: float, LRA: float,
                      qscale: Optional[int], bitrate: Optional[str], threads: Optional[int], timeout: int) -> bool:
    af = (
        f"loudnorm=I={I}:TP={TP}:LRA={LRA}:"
        f"measured_I={p.input_i}:measured_TP={p.input_tp}:"
        f"measured_LRA={p.input_lra}:measured_thresh={p.input_thresh}:"
        f"offset={p.target_offset}:linear=true"
    )
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(in_path), "-af", af, "-c:a", "libmp3lame"]
    if qscale is not None:
        cmd += ["-q:a", str(qscale)]
    elif bitrate is not None:
        cmd += ["-b:a", str(bitrate)]
    else:
        cmd += ["-q:a", "2"]
    if threads is not None and threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [str(out_path)]
    rc, out, err = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        logger.error("Second pass failed: %s\nstderr: %s", in_path, err[-1000:])
        return False
    return True

def one_pass_fallback(in_path: Path, out_path: Path,
                      I: float, TP: float, LRA: float,
                      qscale: Optional[int], bitrate: Optional[str], threads: Optional[int], timeout: int) -> bool:
    af = f"loudnorm=I={I}:TP={TP}:LRA={LRA}"
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(in_path), "-af", af, "-c:a", "libmp3lame"]
    if qscale is not None:
        cmd += ["-q:a", str(qscale)]
    elif bitrate is not None:
        cmd += ["-b:a", str(bitrate)]
    else:
        cmd += ["-q:a", "2"]
    if threads is not None and threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [str(out_path)]
    rc, out, err = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        logger.error("One-pass fallback failed: %s\nstderr: %s", in_path, err[-1000:])
        return False
    return True

def list_mp3s(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.mp3") if p.is_file()])

def resolve_output_path(input_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg).expanduser().resolve()
    # デフォルト出力: input の親フォルダ直下に "output/<同じ名前>"
    parent = input_path.parent
    out_root = parent / "output" / input_path.name
    return out_root.resolve()

def main():
    ap = argparse.ArgumentParser(description="Batch two-pass loudnorm for MP3s (EBU R128)")
    ap.add_argument("-i", "--input", required=True, help="Input root folder")
    ap.add_argument("-o", "--output", help="Output root folder (省略時は input の親/output/同名フォルダ)")
    ap.add_argument("--target", type=float, default=-14.0, help="Target LUFS (default -14.0)")
    ap.add_argument("--tp", type=float, default=-1.5, help="True Peak limit dBTP (default -1.5)")
    ap.add_argument("--lra", type=float, default=11.0, help="Loudness range LRA (default 11.0)")
    ap.add_argument("--qscale", type=int, default=2, help="libmp3lame VBR quality (default 2)")
    ap.add_argument("--bitrate", type=str, help="CBR/ABR bitrate (指定時は qscale 無視)")
    ap.add_argument("--threads", type=int, default=0, help="ffmpeg threads (0=auto)")
    ap.add_argument("--timeout", type=int, default=900, help="Per-file timeout seconds")
    ap.add_argument("--one-pass-on-fail", action="store_true", default=True,
                    help="二段階 loudnorm が失敗した場合ワンパスで再試行 (デフォルト有効)")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()

    in_root = Path(args.input).expanduser().resolve()
    out_root = resolve_output_path(in_root, args.output)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"Input : {in_root}")
    print(f"Output: {out_root}")
    print(f"Target: I={args.target} LUFS, TP={args.tp} dBTP, LRA={args.lra}")

    if not which_ffmpeg():
        sys.exit(2)

    files = list_mp3s(in_root)
    if not files:
        logger.warning("No MP3 files found under: %s", in_root)
        return

    total = len(files)
    ok = 0
    fail = 0
    failed_files = []

    start_time = time.time()
    for idx, f in enumerate(files, 1):
        rel = f.relative_to(in_root)
        out_path = out_root / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = ensure_unique_path(out_path.with_suffix(".mp3"))

        logger.info("[%d/%d] Processing: %s", idx, total, f)

        params = first_pass_measure(f, args.target, args.tp, args.lra, timeout=args.timeout)
        if not params:
            logger.error("First pass measure failed, skipping: %s", f)
            if args.one_pass_on_fail:
                logger.info("Trying one-pass fallback...")
                if one_pass_fallback(f, out_path, args.target, args.tp, args.lra,
                                     args.qscale, args.bitrate, args.threads, timeout=args.timeout):
                    ok += 1
                    continue
            fail += 1
            failed_files.append(str(f))
            continue

        success = second_pass_apply(f, out_path, params,
                                    args.target, args.tp, args.lra,
                                    args.qscale, args.bitrate,
                                    None if args.threads == 0 else args.threads,
                                    args.timeout)
        if not success:
            if args.one_pass_on_fail:
                logger.info("Two-pass failed. Trying one-pass fallback: %s", f)
                if one_pass_fallback(f, out_path, args.target, args.tp, args.lra,
                                     args.qscale, args.bitrate, args.threads, timeout=args.timeout):
                    ok += 1
                    continue
            fail += 1
            failed_files.append(str(f))
        else:
            ok += 1

    elapsed = time.time() - start_time
    logger.info("Done. Success=%d, Fail=%d, Total=%d, Elapsed=%.1fs", ok, fail, total, elapsed)
    if failed_files:
        logger.warning("Failed files (%d):\n%s", len(failed_files), "\n".join(failed_files))

if __name__ == "__main__":
    main()

