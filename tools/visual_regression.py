#!/usr/bin/env python3
"""Pixel-diff visual regression: compare a fresh screenshot to a baseline PNG.

Pure stdlib PNG decode (zlib + manual chunk parsing; no Pillow dependency,
matching lint.py/trust_gate.py's stdlib-only philosophy) + per-pixel diff.
Capturing the "fresh" screenshot requires a real browser (Playwright/Chromium
or similar), which is NOT installed in this sandbox -- see docs/TESTS.md and
tests/visual_baselines/README.md. This tool's compare/diff engine is real,
tested, and runs today; the --capture-cmd hook that takes a screenshot is a
thin subprocess wrapper around whatever screenshot tool the caller has
available (e.g. `playwright screenshot`), and fails loudly (not silently) if
that command is missing or errors, rather than pretending to pass.

Usage:
    tools/visual_regression.py compare BASELINE.png CANDIDATE.png [--threshold 0.01]
    tools/visual_regression.py capture-and-compare NAME --url URL --capture-cmd 'CMD {url} {out}'
"""
from __future__ import annotations

import argparse
import re
import shlex
import shutil
import struct
import subprocess
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINES_DIR = REPO / "tests" / "visual_baselines"

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


class PngDecodeError(ValueError):
    pass


@dataclass
class Image:
    width: int
    height: int
    channels: int  # 3 (RGB) or 4 (RGBA)
    pixels: bytes  # raw, one byte per channel per pixel, row-major, no padding


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> bytes:
    stride = width * bpp
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for row in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + a) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                line[i] = (line[i] + ((a + b) // 2)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 0xFF
        else:
            raise PngDecodeError(f"unsupported PNG filter type {ftype} on row {row}")
        out[row * stride:(row + 1) * stride] = line
        prev = line
    return bytes(out)


def decode_png(path: Path) -> Image:
    """Decode an 8-bit, non-interlaced, non-palette PNG (RGB or RGBA) using
    only zlib + struct from stdlib. Raises PngDecodeError with a clear reason
    for any format this doesn't support -- never silently misreads pixels."""
    path = Path(path)
    data = path.read_bytes()
    if data[:8] != _PNG_SIG:
        raise PngDecodeError(f"{path}: not a PNG file (bad signature)")
    pos = 8
    width = height = bit_depth = color_type = None
    idat_chunks = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        cdata = data[pos + 8:pos + 8 + length]
        pos += 8 + length + 4  # skip CRC
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", cdata[:10])
        elif ctype == b"IDAT":
            idat_chunks.append(cdata)
        elif ctype == b"IEND":
            break
    if width is None:
        raise PngDecodeError(f"{path}: missing IHDR chunk")
    if bit_depth != 8:
        raise PngDecodeError(f"{path}: unsupported bit depth {bit_depth} (only 8-bit supported)")
    if color_type == 2:
        channels = 3
    elif color_type == 6:
        channels = 4
    else:
        raise PngDecodeError(f"{path}: unsupported PNG color type {color_type} "
                              f"(only truecolor=2 and truecolor+alpha=6 supported; "
                              f"no palette/grayscale/interlaced support)")
    raw = zlib.decompress(b"".join(idat_chunks))
    pixels = _unfilter(raw, width, height, channels)
    return Image(width=width, height=height, channels=channels, pixels=pixels)


@dataclass
class DiffResult:
    match: bool
    total_pixels: int
    differing_pixels: int
    fraction_diff: float
    reason: str = ""


def diff_images(baseline: Image, candidate: Image, threshold: float, pixel_tolerance: int = 8) -> DiffResult:
    """Compare two decoded images. `threshold` is the max acceptable FRACTION
    of pixels that may differ (0.0-1.0). A pixel counts as differing if any
    channel differs by more than `pixel_tolerance` (absorbs harmless
    compression/anti-aliasing noise without masking a real visual change)."""
    if baseline.width != candidate.width or baseline.height != candidate.height:
        total = baseline.width * baseline.height
        return DiffResult(
            match=False, total_pixels=total, differing_pixels=total, fraction_diff=1.0,
            reason=f"dimension mismatch: baseline {baseline.width}x{baseline.height} "
                   f"vs candidate {candidate.width}x{candidate.height}",
        )
    w, h = baseline.width, baseline.height
    bc, cc = baseline.channels, candidate.channels
    total_pixels = w * h
    differing = 0
    for i in range(total_pixels):
        b_off, c_off = i * bc, i * cc
        worst = 0
        for ch in range(min(3, bc, cc)):  # compare RGB only; ignore alpha for tolerance purposes
            d = abs(baseline.pixels[b_off + ch] - candidate.pixels[c_off + ch])
            if d > worst:
                worst = d
        if worst > pixel_tolerance:
            differing += 1
    fraction = differing / total_pixels if total_pixels else 0.0
    match = fraction <= threshold
    reason = "" if match else (
        f"{differing}/{total_pixels} pixels ({fraction * 100:.2f}%) differ by more than "
        f"tolerance {pixel_tolerance}, exceeding threshold {threshold * 100:.2f}%"
    )
    return DiffResult(match=match, total_pixels=total_pixels, differing_pixels=differing,
                       fraction_diff=fraction, reason=reason)


def compare_files(baseline_path: Path, candidate_path: Path, threshold: float) -> DiffResult:
    baseline = decode_png(baseline_path)
    candidate = decode_png(candidate_path)
    return diff_images(baseline, candidate, threshold)


def _redact(text: str) -> str:
    """Best-effort redaction of URL query strings and token-looking substrings
    from tool stderr before we print/log it (a capture URL can carry a signed
    token or session param). Never let a secret leak into the review log."""
    text = re.sub(r"([?&])\S*", r"\1<redacted-query>", text)
    text = re.sub(r"(?i)(token|key|secret|password|sig|signature)=\S+",
                  r"\1=<redacted>", text)
    return text


def capture_screenshot(capture_cmd: str, url: str, out_path: Path) -> None:
    """Run a caller-supplied screenshot command. `capture_cmd` is an argv
    TEMPLATE (parsed with shlex, NEVER run through a shell) that must contain
    the literal tokens `{url}` and `{out}`, e.g.:
        'playwright screenshot {url} {out} --viewport-size=1280,800'
    `{url}` and `{out}` are substituted as WHOLE argv elements, so shell
    metacharacters in the URL or output path cannot inject additional commands.
    Fails loudly (raises) if the templated binary isn't on PATH, if the command
    exits non-zero, or if it doesn't actually produce `out_path` -- this NEVER
    falls back to a fake/blank image on failure."""
    if "{url}" not in capture_cmd or "{out}" not in capture_cmd:
        raise ValueError("--capture-cmd must contain both {url} and {out} placeholders")
    # Tokenize the template FIRST, then substitute per-token, so {url}/{out}
    # each become exactly one argv element even if their value contains spaces
    # or shell metacharacters. No shell is ever invoked (shell=False).
    argv = []
    for tok in shlex.split(capture_cmd):
        if tok == "{url}":
            argv.append(url)
        elif tok == "{out}":
            argv.append(str(out_path))
        else:
            # Substitute placeholders that are embedded in a larger token
            # (e.g. "--output={out}") without re-tokenizing the value.
            argv.append(tok.replace("{url}", url).replace("{out}", str(out_path)))
    binary = argv[0]
    if shutil.which(binary) is None:
        raise RuntimeError(
            f"capture command's binary '{binary}' is not installed/on PATH. "
            f"This sandbox does not have a headless browser installed; visual "
            f"capture must be run in an environment that has one (see "
            f"tests/visual_baselines/README.md). Refusing to fake a screenshot."
        )
    result = subprocess.run(argv, shell=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"capture command failed (exit {result.returncode}): "
            f"{_redact(result.stderr.strip())}"
        )
    if not out_path.exists():
        raise RuntimeError(f"capture command exited 0 but did not produce {out_path}")


def cmd_compare(args) -> int:
    try:
        result = compare_files(Path(args.baseline), Path(args.candidate), args.threshold)
    except (PngDecodeError, FileNotFoundError) as exc:
        print(f"visual_regression.py: {exc}", file=sys.stderr)
        return 2
    if result.match:
        print(f"visual_regression.py: MATCH — {result.differing_pixels}/{result.total_pixels} "
              f"pixels differ ({result.fraction_diff * 100:.3f}%), within threshold "
              f"{args.threshold * 100:.2f}%.")
        return 0
    print(f"visual_regression.py: DIFF — {result.reason}", file=sys.stderr)
    return 1


def cmd_capture_and_compare(args) -> int:
    name = args.name
    baseline_path = BASELINES_DIR / f"{name}.png"
    if not baseline_path.exists():
        print(f"visual_regression.py: no baseline at {baseline_path}. "
              f"Run with --update-baseline once a capture succeeds to create it.", file=sys.stderr)
        if not args.update_baseline:
            return 2
    candidate_path = BASELINES_DIR / f"{name}.candidate.png"
    try:
        capture_screenshot(args.capture_cmd, args.url, candidate_path)
    except (ValueError, RuntimeError) as exc:
        print(f"visual_regression.py: capture failed — {exc}", file=sys.stderr)
        return 2

    if args.update_baseline or not baseline_path.exists():
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate_path, baseline_path)
        print(f"visual_regression.py: baseline updated at {baseline_path}.")
        return 0

    return cmd_compare(argparse.Namespace(baseline=str(baseline_path), candidate=str(candidate_path),
                                           threshold=args.threshold))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    p_compare = sub.add_parser("compare", help="compare two existing PNG files")
    p_compare.add_argument("baseline")
    p_compare.add_argument("candidate")
    p_compare.add_argument("--threshold", type=float, default=0.01, help="max fraction of pixels allowed to differ (default 0.01 = 1%%)")
    p_compare.set_defaults(func=cmd_compare)

    p_cap = sub.add_parser("capture-and-compare", help="capture a fresh screenshot and compare to (or create) a named baseline")
    p_cap.add_argument("name", help="baseline name, stored as tests/visual_baselines/NAME.png")
    p_cap.add_argument("--url", required=True)
    p_cap.add_argument("--capture-cmd", required=True, help="argv command template (parsed with shlex, NOT run through a shell) with {url} and {out} placeholders")
    p_cap.add_argument("--threshold", type=float, default=0.01)
    p_cap.add_argument("--update-baseline", action="store_true", help="overwrite/create the baseline instead of comparing to it")
    p_cap.set_defaults(func=cmd_capture_and_compare)

    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
