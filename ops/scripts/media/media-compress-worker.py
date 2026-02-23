#!/usr/bin/env python3
import json
import os
import subprocess
import time
import fcntl
from pathlib import Path

HOME = Path.home()
MEDIA_ROOT = HOME / "Media"
ROOTS = [MEDIA_ROOT / "Filmes", MEDIA_ROOT / "Series"]
TMP_ROOT = MEDIA_ROOT / ".transcode-tmp"
STATE_PATH = HOME / "arr" / "security" / "transcode-state.json"
LOCK_PATH = HOME / "arr" / "security" / "transcode.lock"
ENV_PATH = HOME / "arr" / "config" / "media-compress.env"

VIDEO_EXTS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".wmv"}
ALREADY_COMPRESSED = {"hevc", "av1"}


def load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        if k and v and not os.environ.get(k):
            os.environ[k] = v


def as_bool(v: str, default=False):
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def run(cmd, timeout=None):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False))


def ffprobe_codec(path: Path, ffprobe_bin: str):
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=nokey=1:noprint_wrappers=1",
        str(path),
    ]
    p = run(cmd, timeout=180)
    if p.returncode != 0:
        return None, ((p.stderr or "") + (p.stdout or "")).strip()[:350]
    out = p.stdout.strip().splitlines()
    return (out[0].strip() if out else None), None


def temp_path_for(path: Path) -> Path:
    rel_parent = path.parent.relative_to(MEDIA_ROOT)
    out_dir = TMP_ROOT / rel_parent
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{path.name}.oc-tmp{path.suffix}"


def transcode(path: Path, tmp: Path, ffmpeg_bin: str, encoder: str, vt_q: str, x265_crf: str, x265_preset: str):
    base = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-map", "0"]

    if encoder == "hevc_videotoolbox":
        cmd = base + [
            "-c:v", "hevc_videotoolbox",
            "-allow_sw", "1",
            "-q:v", str(vt_q),
            "-tag:v", "hvc1",
            "-c:a", "copy",
            "-c:s", "copy",
            "-max_muxing_queue_size", "4096",
            str(tmp),
        ]
        p = run(cmd, timeout=60 * 60 * 6)
        if p.returncode == 0:
            return True, "videotoolbox"

        cmd2 = base + [
            "-c:v", "libx265",
            "-preset", str(x265_preset),
            "-crf", str(x265_crf),
            "-c:a", "copy",
            "-c:s", "copy",
            "-max_muxing_queue_size", "4096",
            str(tmp),
        ]
        p2 = run(cmd2, timeout=60 * 60 * 8)
        if p2.returncode == 0:
            return True, "fallback_x265"
        err = ((p.stderr or "") + "\n" + (p2.stderr or "")).strip()[:800]
        return False, err

    cmd = base + [
        "-c:v", encoder,
        "-c:a", "copy",
        "-c:s", "copy",
        "-max_muxing_queue_size", "4096",
        str(tmp),
    ]
    p = run(cmd, timeout=60 * 60 * 8)
    if p.returncode == 0:
        return True, "custom_encoder"
    return False, ((p.stderr or "") + (p.stdout or "")).strip()[:800]


def should_pick(path: Path, min_bytes: int, min_age_sec: int):
    if not path.is_file():
        return False
    if path.suffix.lower() not in VIDEO_EXTS:
        return False
    if path.name.startswith(".") or ".oc-tmp" in path.name or ".oc-bak" in path.name or path.name.endswith(".part"):
        return False
    st = path.stat()
    if st.st_size < min_bytes:
        return False
    if (time.time() - st.st_mtime) < min_age_sec:
        return False
    return True


def candidate_files(min_bytes: int, min_age_sec: int):
    files = []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            try:
                if should_pick(p, min_bytes, min_age_sec):
                    files.append(p)
            except FileNotFoundError:
                continue
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def main():
    load_env_file(ENV_PATH)

    ffmpeg_bin = os.environ.get("FFMPEG_BIN", "/opt/homebrew/bin/ffmpeg")
    ffprobe_bin = os.environ.get("FFPROBE_BIN", "/opt/homebrew/bin/ffprobe")
    encoder = os.environ.get("ENCODER", "hevc_videotoolbox")
    vt_q = os.environ.get("VT_Q", "60")
    x265_crf = os.environ.get("X265_CRF_FALLBACK", "23")
    x265_preset = os.environ.get("X265_PRESET_FALLBACK", "medium")

    min_size_mb = int(os.environ.get("MIN_SIZE_MB", "1500"))
    min_age_min = int(os.environ.get("MIN_AGE_MIN", "40"))
    scan_limit = int(os.environ.get("SCAN_LIMIT", "1"))
    dry_run = as_bool(os.environ.get("DRY_RUN", "0"))

    summary = {
        "timestamp": int(time.time()),
        "dryRun": dry_run,
        "encoder": encoder,
        "tmpRoot": str(TMP_ROOT),
        "processed": 0,
        "transcoded": 0,
        "skipped": 0,
        "errors": 0,
        "items": [],
    }

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lockf = LOCK_PATH.open("w")
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        summary["status"] = "busy"
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    state = load_state()
    min_bytes = min_size_mb * 1024 * 1024
    min_age_sec = min_age_min * 60

    try:
        for p in candidate_files(min_bytes, min_age_sec):
            rel = str(p.relative_to(HOME))
            st = p.stat()
            sig = f"{int(st.st_mtime)}:{st.st_size}"
            old = state.get(rel)
            if old and old.get("sig") == sig and old.get("status") in {"done", "skip_codec", "skip_not_smaller"}:
                continue

            summary["processed"] += 1
            codec, cerr = ffprobe_codec(p, ffprobe_bin)
            if cerr:
                summary["errors"] += 1
                state[rel] = {"sig": sig, "status": "error", "error": f"ffprobe:{cerr}", "ts": int(time.time())}
                summary["items"].append({"file": rel, "status": "error", "error": "ffprobe_failed"})
            elif codec in ALREADY_COMPRESSED:
                summary["skipped"] += 1
                state[rel] = {"sig": sig, "status": "skip_codec", "codec": codec, "ts": int(time.time())}
                summary["items"].append({"file": rel, "status": "skip_codec", "codec": codec})
            elif dry_run:
                summary["items"].append({"file": rel, "status": "would_transcode", "codec": codec, "size": st.st_size})
            else:
                tmp = temp_path_for(p)
                if tmp.exists():
                    tmp.unlink(missing_ok=True)

                ok, info = transcode(p, tmp, ffmpeg_bin, encoder, vt_q, x265_crf, x265_preset)
                if not ok or not tmp.exists():
                    summary["errors"] += 1
                    state[rel] = {"sig": sig, "status": "error", "error": f"transcode:{info}", "ts": int(time.time())}
                    summary["items"].append({"file": rel, "status": "error", "error": "transcode_failed"})
                    if tmp.exists():
                        tmp.unlink(missing_ok=True)
                else:
                    new_size = tmp.stat().st_size
                    if new_size >= int(st.st_size * 0.97):
                        tmp.unlink(missing_ok=True)
                        summary["skipped"] += 1
                        state[rel] = {
                            "sig": sig,
                            "status": "skip_not_smaller",
                            "oldBytes": st.st_size,
                            "newBytes": new_size,
                            "codec": codec,
                            "ts": int(time.time()),
                        }
                        summary["items"].append({"file": rel, "status": "skip_not_smaller", "old": st.st_size, "new": new_size})
                    else:
                        bak = p.with_name(p.name + ".oc-bak")
                        try:
                            if bak.exists():
                                bak.unlink(missing_ok=True)
                            os.replace(str(p), str(bak))
                            os.replace(str(tmp), str(p))
                            bak.unlink(missing_ok=True)
                            summary["transcoded"] += 1
                            pct = round((1 - (new_size / st.st_size)) * 100, 2)
                            state[rel] = {
                                "sig": f"{int(p.stat().st_mtime)}:{p.stat().st_size}",
                                "status": "done",
                                "codecBefore": codec,
                                "oldBytes": st.st_size,
                                "newBytes": new_size,
                                "savedPct": pct,
                                "mode": info,
                                "ts": int(time.time()),
                            }
                            summary["items"].append({"file": rel, "status": "done", "savedPct": pct, "old": st.st_size, "new": new_size, "mode": info})
                        except Exception as e:
                            summary["errors"] += 1
                            if not p.exists() and bak.exists():
                                os.replace(str(bak), str(p))
                            if tmp.exists():
                                tmp.unlink(missing_ok=True)
                            state[rel] = {"sig": sig, "status": "error", "error": f"replace:{str(e)[:220]}", "ts": int(time.time())}
                            summary["items"].append({"file": rel, "status": "error", "error": "replace_failed"})

            if summary["processed"] >= scan_limit:
                break

        save_state(state)
        summary["status"] = "ok"
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as e:
        save_state(state)
        summary["status"] = "fatal"
        summary["errors"] += 1
        summary["items"].append({"status": "fatal", "error": str(e)[:300]})
        print(json.dumps(summary, ensure_ascii=False))
        return 1
    finally:
        try:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lockf.close()


if __name__ == "__main__":
    raise SystemExit(main())
